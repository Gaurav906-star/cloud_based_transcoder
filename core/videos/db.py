import boto3
from django.conf import settings
from datetime import datetime

dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-east-1'
)

table = dynamodb.Table('videos')  

def save_video(video_id, status):
    table.put_item(
        Item={
            'video_id': video_id,
            'status': status,
            'progress': 0,
            'created_at': datetime.utcnow().isoformat()
        }
    )


def update_progress(video_id, progress):
    table.update_item(
        Key={"video_id": video_id},
        UpdateExpression="SET progress = :p, #s = :s",
        ExpressionAttributeValues={   
            ":p": progress,          
            ":s": "processing"
        },
        ExpressionAttributeNames={
            "#s": "status"
        }
    )


def get_all_videos():
    response = table.scan()
    items = response.get("Items", []) 

    result = {}
    for item in items:
        result[item["video_id"]] = item

    return result
    

def mark_completed(video_id):
    table.update_item(
        Key={"video_id", video_id},
        UpdateExpression="SET #s = :s, progress = :p",
         ExpressionAttributeValues={   
            ":p": 100,          
            ":s": "completed"
        },
        ExpressionAttributeNames={
          "#s": "status"  
        }
        
        
        )