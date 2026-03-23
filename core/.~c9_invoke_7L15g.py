import boto3
import json
import subprocess
import os
import time
import base64
import re
from openai import OpenAI

# AWS clients
sqs = boto3.client('sqs')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# OpenAI client
openApi_client = OpenAI()

# ENV variables
QUEUE_URL = os.environ.get("QUEUE_URL")
INPUT_BUCKET = os.environ.get("INPUT_BUCKET")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "videos")

table = dynamodb.Table(TABLE_NAME)


# -----------------------------
# DynamoDB helpers
# -----------------------------
def update_status(video_id, status, progress=None):
    update_expr = "SET #s = :s"
    expr_values = {":s": status}
    expr_names = {"#s": "status"}

    if progress is not None:
        update_expr += ", progress = :p"
        expr_values[":p"] = progress

    table.update_item(
        Key={"video_id": video_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values,
        ExpressionAttributeNames=expr_names
    )


def mark_completed(video_id, hls_url):
    table.update_item(
        Key={"video_id": video_id},
        UpdateExpression="SET #s = :s, progress = :p, hls_url = :h",
        ExpressionAttributeValues={
            ":s": "completed",
            ":p": 100,
            ":h": hls_url
        },
        ExpressionAttributeNames={"#s": "status"}
    )


def save_ai_metadata(video_id, data):
    table.update_item(
        Key={"video_id": video_id},
        UpdateExpression="SET title = :t, tags = :tg, description = :d",
        ExpressionAttributeValues={
            ":t": data.get("title"),
            ":tg": data.get("tags"),
            ":d": data.get("description")
        }
    )


# -----------------------------
# AI Helpers
# -----------------------------
def extract_frame(input_file, output_image):
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-ss", "00:00:02",
        "-vframes", "1",
        output_image
    ], check=True)


def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_json(text):
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print("⚠️ JSON extraction failed:", e)

    return {
        "title": "Unknown",
        "tags": [],
        "description": text
    }


def analyze_video_frame(video_id, input_file):
    frame_path = f"/tmp/{video_id}.jpg"

    try:
        # Extract frame
        extract_frame(input_file, frame_path)

        if not os.path.exists(frame_path):
            raise Exception("Frame extraction failed")

        # Encode
        base64_image = encode_image(frame_path)

        # OpenAI request
        response = openApi_client.responses.create(
            model="gpt-4o-mini",
            input=[{
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Return ONLY valid JSON with keys: title (string), tags (array), description (string). No explanation."
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}"
                    }
                ]
            }]
        )

        output_text = response.output_text
        print("🧠 AI Response:", output_text)

        data = extract_json(output_text)

    except Exception as e:
        print("❌ OpenAI/AI error:", e)
        data = {
            "title": "Unknown",
            "tags": [],
            "description": str(e)
        }

    save_ai_metadata(video_id, data)


# -----------------------------
# Video Processing
# -----------------------------
def process_video(bucket, key):
    filename = os.path.basename(key)
    video_id, ext = os.path.splitext(filename)

    input_file = f"/tmp/{video_id}{ext}"
    hls_dir = f"/tmp/hls_{video_id}"

    print(f"\n🎬 Processing {filename}")

    update_status(video_id, "processing", 10)

    # Download
    s3.download_file(INPUT_BUCKET, key, input_file)

    # AI analysis
    analyze_video_frame(video_id, input_file)

    # HLS dir
    os.makedirs(hls_dir, exist_ok=True)

    # 360p
    subprocess.run([
        "ffmpeg","-y","-i",input_file,
        "-vf","scale=640:360",
        "-threads","2",
        "-c:v","libx264","-c:a","aac",
        "-preset","fast","-crf","23",
        "-g","48","-sc_threshold","0",
        "-f","hls","-hls_time","4",
        "-hls_list_size","0",
        "-hls_segment_filename",f"{hls_dir}/360p_%03d.ts",
        f"{hls_dir}/360p.m3u8"
    ], check=True)

    update_status(video_id, "processing", 40)

    # 480p
    subprocess.run([
        "ffmpeg","-y","-i",input_file,
        "-vf","scale=854:480",
        "-threads","2",
        "-c:v","libx264","-c:a","aac",
        "-preset","fast","-crf","23",
        "-g","48","-sc_threshold","0",
        "-f","hls","-hls_time","4",
        "-hls_list_size","0",
        "-hls_segment_filename",f"{hls_dir}/480p_%03d.ts",
        f"{hls_dir}/480p.m3u8"
    ], check=True)

    update_status(video_id, "processing", 70)

    # 720p
    subprocess.run([
        "ffmpeg","-y","-i",input_file,
        "-vf","scale=1280:720",
        "-threads","2",
        "-c:v","libx264","-c:a","aac",
        "-preset","fast","-crf","23",
        "-g","48","-sc_threshold","0",
        "-f","hls","-hls_time","4",
        "-hls_list_size","0",
        "-hls_segment_filename",f"{hls_dir}/720p_%03d.ts",
        f"{hls_dir}/720p.m3u8"
    ], check=True)

    update_status(video_id, "processing", 90)

    # Master playlist
    master_playlist = f"{hls_dir}/master.m3u8"
    with open(master_playlist, "w") as f:
        f.write("#EXTM3U\n")
        f.write("#EXT-X-STREAM-INF:BANDWIDTH=400000\n360p.m3u8\n")
        f.write("#EXT-X-STREAM-INF:BANDWIDTH=800000\n480p.m3u8\n")
        f.write("#EXT-X-STREAM-INF:BANDWIDTH=1400000\n720p.m3u8\n")

    print("📡 HLS generation complete")

    # Upload
    for file in os.listdir(hls_dir):
        s3.upload_file(
            os.path.join(hls_dir, file),
            OUTPUT_BUCKET,
            f"hls/{video_id}/{file}"
        )

    update_status(video_id, "processing", 95)

    hls_url = f"https://{OUTPUT_BUCKET}.s3.amazonaws.com/hls/{video_id}/master.m3u8"
    mark_completed(video_id, hls_url)

    print(f"✅ Completed {video_id}")


# -----------------------------
# SQS Polling
# -----------------------------
def poll_queue():
    print("🚀 Worker started...")

    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )

        messages = response.get("Messages", [])

        for msg in messages:
            body = json.loads(msg["Body"])
            bucket = body["bucket"]
            key = body["key"]

            try:
                process_video(bucket, key)

                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=msg["ReceiptHandle"]
                )

            except Exception as e:
                print("❌ Error:", e)

        time.sleep(1)


if __name__ == "__main__":
    poll_queue()