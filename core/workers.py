import os
import django
import subprocess
import time

# 🔥 Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videotranscoder.settings')
django.setup()

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from videos.db import update_progress, save_video, get_all_videos

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "storage/raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "storage/processed")

channel_layer = get_channel_layer()


def send_ws_update(data):
    async_to_sync(channel_layer.group_send)(
        "videos_group",
        {
            "type": "send_update",
            "data": data
        }
    )


def process_videos():
    print("🚀 Worker started...\n")

    videos_db = get_all_videos()

    for file in os.listdir(RAW_DIR):

        input_path = os.path.join(RAW_DIR, file)

        # Output files
        output_720 = os.path.join(PROCESSED_DIR, f"720p_{file}.mp4")
        output_480 = os.path.join(PROCESSED_DIR, f"480p_{file}.mp4")

        # HLS folder
        hls_dir = os.path.join(PROCESSED_DIR, f"hls_{file}")

        # ✅ Skip already processed
        if os.path.exists(output_720) and os.path.exists(hls_dir):
            print(f"⚠️ Skipping already processed: {file}")
            continue

        if file in videos_db and videos_db[file]["status"] == "processed":
            print(f"✅ Already marked processed: {file}")
            continue

        print(f"🎬 Processing: {file}")

        # Update status
        save_video(file, "processing")

        # Progress simulation + WebSocket
        for p in range(0, 101, 20):
            print(f"📊 {file}: {p}%")

            update_progress(file, p)

            send_ws_update({
                "video": file,
                "progress": p,
                "status": "processing"
            })

            time.sleep(1)

        print("⚙️ Running FFmpeg (MP4 outputs)...")

        # 🎬 720p MP4
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", "scale=1280:720",
            "-c:v", "libx264",
            "-c:a", "aac",
            output_720
        ])

        # 🎬 480p MP4
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", "scale=854:480",
            "-c:v", "libx264",
            "-c:a", "aac",
            output_480
        ])

        print("📡 Generating Adaptive HLS streams...")

        os.makedirs(hls_dir, exist_ok=True)

        # 🎬 720p HLS
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", "scale=1280:720",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            "-crf", "23",
            "-g", "48",
            "-sc_threshold", "0",
            "-f", "hls",
            "-force_key_frames", "expr:gte(t,n_forced*4)",
            "-hls_time", "4",
            "-hls_list_size", "0",              
            "-hls_playlist_type", "vod",
            "-hls_segment_filename", os.path.join(hls_dir, "720p_%03d.ts"),
            os.path.join(hls_dir, "720p.m3u8")
        ])

        # 🎬 480p HLS
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", "scale=854:480",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            "-crf", "23",
            "-g", "48",
            "-sc_threshold", "0",
            "-f", "hls",
            "-force_key_frames", "expr:gte(t,n_forced*4)",
            "-hls_time", "4",
            "-hls_list_size", "0",              
            "-hls_playlist_type", "vod",
            "-hls_segment_filename", os.path.join(hls_dir, "480p_%03d.ts"),
            os.path.join(hls_dir, "480p.m3u8")
        ])

        #360p 
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", "scale=640:360",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            "-crf", "23",
            "-g", "48",
            "-sc_threshold", "0",
            "-f", "hls",
            "-force_key_frames", "expr:gte(t,n_forced*4)",
            "-hls_time", "4",
            "-hls_list_size", "0",              
            "-hls_playlist_type", "vod",
            "-hls_segment_filename", os.path.join(hls_dir, "360p_%03d.ts"),
            os.path.join(hls_dir, "360p.m3u8")
        ])

        # # 1080p 
        # subprocess.run([
        #     "ffmpeg", "-y",
        #     "-i", input_path,
        #     "-vf", "scale=1920:1080",
        #     "-c:v", "libx264",
        #     "-c:a", "aac",
        #     "-preset", "fast",
        #     "-crf", "23",
        #     "-g", "48",
        #     "-sc_threshold", "0",
        #     "-f", "hls",
        #     "-hls_time", "4",
        #     "-hls_playlist_type", "vod",
        #     "-hls_segment_filename", os.path.join(hls_dir, "1080p_%03d.ts"),
        #     os.path.join(hls_dir, "1080p.m3u8")
        # ])

        # 🎬 MASTER PLAYLIST (Adaptive Streaming)
        master_playlist = os.path.join(hls_dir, "master.m3u8")

        with open(master_playlist, "w") as f:
            f.write("#EXTM3U\n")

            f.write("#EXT-X-STREAM-INF:BANDWIDTH=400000\n")
            f.write("360p.m3u8\n")

            f.write("#EXT-X-STREAM-INF:BANDWIDTH=800000\n")
            f.write("480p.m3u8\n")

            f.write("#EXT-X-STREAM-INF:BANDWIDTH=1400000\n")
            f.write("720p.m3u8\n")

            print("✅ HLS Adaptive Streaming Ready")

        # Final update
        update_progress(file, 100)
        save_video(file, "processed")

        send_ws_update({
            "video": file,
            "progress": 100,
            "status": "processed"
        })

        print(f"🎉 Completed: {file}\n")

    print("✅ Worker cycle complete.\n")


if __name__ == "__main__":
    while True:
        process_videos()
        time.sleep(5)