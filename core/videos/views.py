# videos/views.py

import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .db import save_video 
from django.shortcuts import render
from django.http import JsonResponse
from .db import get_all_videos
from .pdf_utils import generate_styled_pdf
import boto3
import uuid
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import parser_classes
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.storage import default_storage







RAW_DIR = "storage/raw"


@api_view(['POST'])
@parser_classes([MultiPartParser])
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

upload_video = swagger_auto_schema(
    method='post',
    tags=['🎥 Video'],
    operation_summary="Upload video",
    manual_parameters=[
        openapi.Parameter(
            'file',
            openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True
        )
    ]
)(upload_video)


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
        


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        additional_properties=openapi.Schema(
            type=openapi.TYPE_STRING
        ),
        example={
          "title": "Invoice",
          "customer": "John Doe",
          "items": ["Laptop", "Mouse", "Keyboard"],
          "total_amount": "$1200",
          "status": "Paid"
        }
    )
)

@api_view(['POST'])
def generate_pdf_api(request):
    try:
        data = request.data

        file_url, filename = generate_styled_pdf(data)

        return Response({
            "success": True,
            "file_name": filename,
            "download_url": file_url
        })

    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)

    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "message": "Login successful",
            "token": token.key
        })
    else:
        return Response({
            "error": "Invalid credentials"
        }, status=status.HTTP_401_UNAUTHORIZED)
        



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    try:
        request.user.auth_token.delete()
        return Response({"message": "Logged out successfully"})
    except:
        return Response({"error": "Something went wrong"}, status=400)
        

@login_required
def home(request):
    return render(request, 'index.html')