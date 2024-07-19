import boto3
import json
import requests

ecs_client = boto3.client('ecs')

def is_stream_active(camera_url):
    try:
        response = requests.get(camera_url, stream=True, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking stream {camera_url}: {e}")
        return False    

def lambda_handler(event, context):
    camera_urls = {
        "camera_1": 'rtsp://807e9439d5ca.entrypoint.cloud.wowza.com:1935/app-rC94792j/068b9c9a_stream2',
        "camera_2": 0,  # Replace with actual URL
    }
    duration = 60  # Recording duration in seconds
    bucket_name = 'excavator-monitor-video-input'
    path = 'webcammer/'

    successful_invocations = []

    for camera_id, camera_url in camera_urls.items():
        if is_stream_active(camera_url):
            try:
                response = ecs_client.run_task(
                    cluster='excavator-fetch-video-cluster',  # Replace with your ECS cluster name
                    launchType='FARGATE',
                    taskDefinition='excavator-fetch-video-task:1',  # Replace with your task definition
                    count=1,
                    platformVersion='LATEST',
                    networkConfiguration={
                        'awsvpcConfiguration': {
                            'subnets': [
                                'subnet-0cca720bedd414994',
                                'subnet-0b63dc41be2e8fc7e',
                                'subnet-0a3b8d6dbd19c0f19',
                                'subnet-01cbcc43f1072ccee',
                                'subnet-054f92ce49ceb04d8',
                                'subnet-0e729117d1cfc33ef',
                            ],  # Replace with your subnet ID
                            'assignPublicIp': 'ENABLED'
                        }
                    },
                    overrides={
                        'containerOverrides': [{
                            'name': 'excavator-fetch-container',  # Replace with your container name
                            'environment': [
                                {'name': 'CAMERA_ID', 'value': camera_id},
                                {'name': 'CAMERA_URL', 'value': camera_url},
                                {'name': 'DURATION', 'value': str(duration)},
                                {'name': 'BUCKET_NAME', 'value': bucket_name},
                                {'name': 'PATH', 'value': path}
                            ]
                        }]
                    }
                )
                successful_invocations.append(camera_id)
            except Exception as e:
                print(f"Failed to invoke recording task for {camera_id}: {e}")
        else:
            print(f"Stream inactive for camera {camera_id}")

    return {
        'statusCode': 200,
        'body': f"Recording initiated for cameras: {', '.join(successful_invocations)}"
    }
