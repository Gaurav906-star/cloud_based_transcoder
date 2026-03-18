# videos/db.py

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "storage/db.json")

def save_video(video_id, status):
    data = {}

    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            data = json.load(f)

    data[video_id] = {
        "status": status
    }

    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

def update_progress(video_id, progress):

    with open(DB_FILE) as f:
        data = json.load(f)

    data[video_id]["progress"] = progress
    data[video_id]["status"] = "processing"

    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def get_all_videos():

    if not os.path.exists(DB_FILE):
        return {}

    with open(DB_FILE) as f:
        return json.load(f)