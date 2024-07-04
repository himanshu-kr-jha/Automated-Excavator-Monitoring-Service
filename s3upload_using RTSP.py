import cv2
from datetime import datetime
import pytz
import time
import boto3
import os
from threading import Thread


# Function for uploading the file into S3
def upload_to_s3(file_name):
    # s3_client = boto3.client('s3',
    #                          aws_access_key_id='--------',
    #                          aws_secret_access_key='---------')
    bucket_name = 'excavator-video-input'  # Mention bucket name which you created in S3
    path = 'webcammer/'  # Mention path where the files need to be uploaded
    upload_file_key = path + file_name
    s3_client.upload_file(file_name, bucket_name, upload_file_key)
    print("File uploaded successfully: " + str(file_name))
    os.remove(file_name)


# Function to get current timestamped filename
def get_file_name():
    tz = pytz.timezone('Asia/Kolkata')  # Reading time zone
    datetime_india_tz = datetime.now(tz)
    datetime_india = datetime_india_tz.replace(microsecond=0).replace(tzinfo=None)
    file_name = str(datetime_india) + '.mp4'  # Naming the file based on date and current time
    file_name = file_name.replace(':', '.')
    return file_name


# Function to handle the recording process
def record_video():
    remote_camera_url = 'your url'  # Example: 'rtsp://username:password@192.168.1.101:554/stream1'
    # This will return video from the remote camera stream
    cap = cv2.VideoCapture(remote_camera_url)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    while True:
        file_name = get_file_name()
        out = cv2.VideoWriter(file_name, fourcc, 20.0, (640, 480))  # Higher resolution and FPS
        start_time = time.time()
        print(f"Recording started for file: {file_name}")

        while time.time() - start_time < 60:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame from camera.")
                break
            out.write(frame)
            cv2.imshow("Original", frame)
            if cv2.waitKey(1) & 0xFF == ord('a'):
                cap.release()
                out.release()
                cv2.destroyAllWindows()
                upload_to_s3(file_name)
                exit()

        out.release()
        Thread(target=upload_to_s3, args=(file_name,)).start()

    cap.release()
    cv2.destroyAllWindows()


# Start the recording process
record_video()
