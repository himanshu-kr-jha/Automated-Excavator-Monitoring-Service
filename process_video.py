import torch
import cv2
import click
import os
import boto3

def bg_movement(frame, threshold, kernel, object_detector, roi_x, roi_y, roi_height, roi_width):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    blurred_frame = cv2.GaussianBlur(frame, (5, 5), 0)
    mask = object_detector.apply(blurred_frame)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    roi_mask = mask[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width]
    movement = cv2.countNonZero(roi_mask)
    return movement > threshold

def movement_detection(input_video_path, output_video_path):
    print("loading model")
    # model = load_model('best.pt')
    model = torch.hub.load('ultralytics/yolov5', 'custom', path='best.pt')
    cap = cv2.VideoCapture(input_video_path)
    num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    roi_x = 250
    roi_y = 200
    roi_width = 500
    roi_height = frame_height - roi_y

    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    object_detector = cv2.createBackgroundSubtractorMOG2()
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    video_writer = cv2.VideoWriter(output_video_path, fourcc, int(cap.get(cv2.CAP_PROP_FPS)), (frame_width, frame_height))

    initial_height = None

    for frame_index in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            break

        movement = bg_movement(frame, 8000, kernel, object_detector, roi_x, roi_y, roi_height, roi_width)

        text_x = frame_width - 200
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = model(frame_rgb)
        max_area = 0
        max_box = None

        for result in results.xyxy[0]:  # xyxy format
            x_min, y_min, x_max, y_max, confidence, class_id = result.tolist()
            area = (x_max - x_min) * (y_max - y_min)
            if area > max_area:
                max_area = area
                max_box = (x_min, y_min, x_max, y_max)

        center_x = center_y = height = height_diff = 0
        state = "idle"

        if max_box:
            x_min, y_min, x_max, y_max = [int(coord) for coord in max_box]
            center_x = (x_min + x_max) // 2
            center_y = (y_min + y_max) // 2
            height = y_max - y_min

            if initial_height is None:
                initial_height = height

            height_diff = abs(height - initial_height)

            if height_diff > 20 or movement:
                state = 'working'
            elif height_diff >= 2 and height_diff < 10 or movement:
                state = 'moving'

        print(f"Frame {frame_index} : {state}")

        cv2.putText(frame, f'State: {state}', (text_x, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2, cv2.LINE_AA)
        if max_box:
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            cv2.putText(frame, f'Height: {int(height)}', (center_x, center_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_width, roi_y + roi_height), (255, 0, 0), 2)
        
        video_writer.write(frame)

    cap.release()
    video_writer.release()
# print("going to execute the funtion")
# movement_detection('video2.mp4','processed-1.mp4')
# print("function executed")
@click.command(name='process_video')
@click.option("--input_bucket", type=str, required=True, help="path to the input S3 bucket")
@click.option("--input_filepath", type=str, required=True, help="path to the input movie file")
@click.option("--output_bucket", type=str, required=True, help="path to the output s3 bucket")
@click.option("--output_filepath", type=str, required=True, help="path to the output movie file")
def cli(input_bucket, input_filepath, output_bucket, output_filepath):
# determine input and output file basenames input_file_basename = os.path.basename(input_filepath)
    input_file_basename=os.path.basename(input_filepath)
    output_file_basename = os.path.basename(output_filepath)

# download video file from S3
    s3=boto3.client('s3')
    s3.download_file(input_bucket, input_filepath, input_file_basename)
    # process video file 
    movement_detection(input_file_basename, output_file_basename)
    # upload processed video file to S3 
    s3.upload_file(output_file_basename, output_bucket, output_filepath)
if __name__== "__main__":
    cli()