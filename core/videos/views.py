# videos/views.py

import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .db import save_video 
from django.shortcuts import render
from django.http import JsonResponse
from .db import get_all_videos
import boto3
import uuid




RAW_DIR = "storage/raw"

@api_view(['POST'])
def upload_video(request):
    file = request.FILES['file']
    video_id = str(uuid.uuid4())
    
    file_path = os.path.join(RAW_DIR, file.name)
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    s3_key = f"raw/{file.name}"
    
    s3_client.upload_fileobj(
        file,
        "transcoding-raw-videos",
        s3_key,
        ExtraArgs={
            "ContentType": file.content_type,
            "Metadata": {
            "video_id": video_id
        }
        }
        )
    
   
    # ✅ Save metadata (THIS is where you add it)
    save_video(video_id,file.name ,"uploaded")

    return Response({
        "message": "Uploaded locally",
        "filename": file.name,
        "s3_key":s3_key,
        "file_path":f"https://transcoding-raw-videos.s3.amazonaws.com/{s3_key}"
    })


def home(request):
    return render(request, "index.html")

DB_FILE = "storage/db.json"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "storage/processed")

@api_view(['GET'])
def list_videos(request):
    import json, os

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




dynamodb_resource = boto3.resource('dynamodb', region_name ='us-east-1')

def get_videos(request):
    try:
        table = dynamodb_resource.Table('videos')
        response = table.scan()
        items = response.get("Items", [])

        from datetime import datetime

        def safe_created_at(item):
            value = item.get("created_at")

            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", ""))
                except:
                    return datetime.min

            return datetime.min

        # ✅ SAFE SORT
        items.sort(key=safe_created_at, reverse=True)

        result = []
        for item in items:
            result.append({
                "id": item.get("video_id"),
                "name": item.get("file_name"),
                "status": item.get("status", "pending"),
                "progress": int(item.get("progress", 0)),
                "hls": item.get("hls_url"),
                "title": item.get("title"),
                "tags": item.get("tags", []),
                "description": item.get("description"),
                "created_at": item.get("created_at")
            })

        return JsonResponse(result, safe=False)

    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({
            "success": False,
            "data": [],
            "error": str(e)
        })