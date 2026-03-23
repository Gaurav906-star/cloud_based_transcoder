# videos/views.py

import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .db import save_video 
from django.shortcuts import render
from django.http import JsonResponse
from .db import get_all_videos




RAW_DIR = "storage/raw"

@api_view(['POST'])
def upload_video(request):
    file = request.FILES['file']
    
    file_path = os.path.join(RAW_DIR, file.name)

    # ✅ Save file locally (simulate S3)
    s

    # ✅ Save metadata (THIS is where you add it)
    save_video(file.name, "uploaded")

    return Response({
        "message": "Uploaded locally",
        "filename": file.name
    })


def home(request):
    return render(request, "index.html")

DB_FILE = "storage/db.json"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "storage/processed")

@api_view(['GET'])
def list_videos(request):
        "url":f"https://transcoding-raw-videos.s3.amazonaws.com/{s3_key}"

    DB_FILE = "storage/db.json"
    PROCESSED_DIR = "storage/processed"

    if not os.path.exists(DB_FILE):
        return Response([])

    with open(DB_FILE) as f:
        data = json.load(f)

    result = []

    for name, info in data.items():
        status = info.get("status", "uploaded")

        # convert uploaded → processing (UI friendly)
        if status == "uploaded":
            status = "processing"

        result.append({
            "name": name,
            "status": status,
            "progress": info.get("progress", 0),
            "urls": {
                "720p": f"/media/720p_{name}",
                "480p": f"/media/480p_{name}"
            }
        })

    return Response(result)

# views.py
def videos_page(request):
    return render(request, "videos.html")





def get_videos(request):
    data = get_all_videos()

    result = []

    for name, info in data.items():

        status = info.get("status", "pending")
        progress = info.get("progress", 0)

        urls = {}

        # 720p
        path_720 = os.path.join(PROCESSED_DIR, f"720p_{name}.mp4")
        if os.path.exists(path_720):
            urls["720p"] = f"/media/720p_{name}.mp4"

        # 480p
        path_480 = os.path.join(PROCESSED_DIR, f"480p_{name}.mp4")
        if os.path.exists(path_480):
            urls["480p"] = f"/media/480p_{name}.mp4"

        # 🎬 HLS
        hls_path = os.path.join(PROCESSED_DIR, f"hls_{name}", "master.m3u8")
        hls_url = None
        if os.path.exists(hls_path):
            hls_url =  f"/media/hls_{name}/master.m3u8"

        result.append({
            "name": name,
            "status": status,
            "progress": progress,
            "urls": urls,
            "hls": hls_url   # 🔥 IMPORTANT
        })

    return JsonResponse(result, safe=False)