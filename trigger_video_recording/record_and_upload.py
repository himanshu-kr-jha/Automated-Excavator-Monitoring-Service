import os
import time
import boto3
import cv2

def upload_to_s3(file_name, bucket_name, path):
    s3_client = boto3.client('s3')
    try:
        upload_file_key = path + file_name
        s3_client.upload_file(file_name, bucket_name, upload_file_key)
        print("File uploaded successfully: " + str(file_name))
        os.remove(file_name)
    except Exception as e:
        print(f"Failed to upload file {file_name} to S3: {e}")

def get_file_name(camera_id):
    epoch_time = int(time.time())
    file_name = f"{camera_id}_{epoch_time}.mp4"
    return file_name

def record_video(camera_id, camera_url, duration):
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        raise Exception(f"Failed to open camera {camera_id}")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 20.0
    frame_interval = 1.0 / fps
    file_name = get_file_name(camera_id)
    out = cv2.VideoWriter(file_name, fourcc, fps, (640, 480))

    start_time = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            raise Exception(f"Failed to read frame from camera {camera_id}")
        out.write(frame)
        if time.time() - start_time >= duration:
            break

    out.release()
    cap.release()
    return file_name

def main():
    camera_id = os.getenv('CAMERA_ID')
    camera_url = os.getenv('CAMERA_URL')
    duration = int(os.getenv('DURATION'))
    bucket_name = os.getenv('BUCKET_NAME')
    path = os.getenv('PATH')

    try:
        file_name = record_video(camera_id, camera_url, duration)
        upload_to_s3(file_name, bucket_name, path)
        print(f"File uploaded successfully: {file_name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
