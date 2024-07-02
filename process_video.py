import torch
import cv2
import numpy as np
import pandas as pd
import json
import os
import boto3
import click

# Load custom YOLOv5 model
model_path = 'best.pt'  # Update with your model path
_model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)

def detect_motion_and_process_frame(video_path, model, threshold_inside=500, threshold_outside=500):
    """
    Detects motion and processes frames to extract height data from a video.

    Args:
    video_path (str): Path to the video file.
    model: Object detection model for processing frames.
    threshold_inside (int): Minimum contour area to consider as movement inside the ROI.
    threshold_outside (int): Minimum contour area to consider as movement outside the ROI.

    Returns:
    DataFrame: DataFrame containing time, height, movement inside, and movement outside for each frame.
    """
    data = []

    # Initialize video capture
    cap = cv2.VideoCapture(video_path)
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    interval_5s = fps * 5

    roi = (250, 200, 500, frame_height - 200)
    if not cap.isOpened():
        print("Failed to open video")
        return pd.DataFrame()

    # Initialize background subtractor
    back_sub = cv2.createBackgroundSubtractorMOG2()

    # Initialize ORB detector
    orb = cv2.ORB_create()

    # Read the first frame
    ret, prev_frame = cap.read()
    if not ret:
        print("Failed to read video")
        cap.release()
        cv2.destroyAllWindows()
        return pd.DataFrame()

    # Convert first frame to grayscale
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

    initial_height = None  # Variable to store the initial height
    frames_processed = 0

    while cap.isOpened():
        # Read the next frame
        ret, frame = cap.read()
        if not ret:
            break

        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect ORB key points and descriptors in both frames
        kp1, des1 = orb.detectAndCompute(prev_gray, None)
        kp2, des2 = orb.detectAndCompute(gray, None)

        # Match descriptors using BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        # Sort matches by distance
        matches = sorted(matches, key=lambda x: x.distance)

        # Extract location of good matches
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        # Compute homography matrix
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        # Warp the current frame to align with the previous frame
        height, width = prev_gray.shape
        stabilized_frame = cv2.warpPerspective(frame, H, (width, height))

        # Apply background subtraction
        fg_mask = back_sub.apply(stabilized_frame)

        # Optionally, apply morphology to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        # Crop the region of interest from the foreground mask
        x, y, w, h = roi
        roi_mask = fg_mask[y:y + h, x:x + w]
        outside_roi_mask = np.copy(fg_mask)
        outside_roi_mask[y:y + h, x:x + w] = 0

        # Find contours of the moving objects in the ROI
        contours_roi = cv2.findContours(roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        contours_outside = cv2.findContours(outside_roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

        # Check if any contour area exceeds the threshold
        movement_detected_inside = any(cv2.contourArea(contour) > threshold_inside for contour in contours_roi)
        movement_detected_outside = any(cv2.contourArea(contour) > threshold_outside for contour in contours_outside)

        # Process frame to extract height data
        center_point, height, frame_rgb = process_frame(frame, model)
        if center_point:
            if initial_height is None:
                initial_height = height

            # Record data with timestamp
            timestamp = frames_processed / fps
            data.append([timestamp, height, movement_detected_inside, movement_detected_outside])

        frames_processed += 1

        if frames_processed % interval_5s == 0:
            print(f'Processed {frames_processed // fps} seconds of video.')

        # Update previous frame and gray image
        prev_gray = gray.copy()

    cap.release()

    # Create a DataFrame for the data
    df = pd.DataFrame(data, columns=['Time', 'Height', 'Movement_Inside', 'Movement_Outside'])

    return df

def process_frame(frame, model):
    # Convert frame to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Perform inference
    results = model(frame_rgb)

    # Extract bounding box coordinates and calculate center points and heights
    max_area = 0
    max_box = None
    for result in results.xyxy[0]:  # xyxy format
        x_min, y_min, x_max, y_max, confidence, class_id = result.tolist()
        area = (x_max - x_min) * (y_max - y_min)
        if area > max_area:
            max_area = area
            max_box = (x_min, y_min, x_max, y_max)

    if max_box:
        x_min, y_min, x_max, y_max = [int(coord) for coord in max_box]
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2
        height = y_max - y_min

        return (center_x, center_y), height, frame_rgb

    return None, None, frame_rgb

def status(df_height_data, video_file_name, interval):
    df = df_height_data

    df['height_change'] = df['Height'].diff().fillna(0)
    idle_change_min = -1
    idle_change_max = 1

    def determine_state(row):
        movement_inside = row['Movement_Inside']
        movement_outside = row['Movement_Outside']
        height_change = row['height_change']

        if height_change < idle_change_max and height_change > idle_change_min:
            if not movement_inside and movement_outside:
                return 'working'
            if not movement_inside and not movement_outside:
                return 'idle'
            if movement_inside and not movement_outside:
                return 'working'
            if movement_outside and movement_inside:
                return 'working'
        else:
            if not movement_inside and movement_outside:
                return 'working'
            else:
                return 'working'

    df['state'] = df.apply(determine_state, axis=1)
    df['interval'] = np.floor(df['Time'] / interval).astype(int)
    state_counts = df.groupby('interval')['state'].value_counts().unstack(fill_value=0)
    state_probabilities = state_counts.div(state_counts.sum(axis=1), axis=0)
    max_prob_state = state_probabilities.idxmax(axis=1)
    max_prob_value = state_probabilities.max(axis=1)
    result = pd.DataFrame({
        'interval': max_prob_state.index,
        'state': max_prob_state.values,
        'probability': max_prob_value.values
    })
    overall_state_count = result['state'].value_counts()
    overall_state = overall_state_count.idxmax()
    json_data = {
        "video_file": video_file_name,
        "result": result.to_dict(orient='records'),
        "overall_state": overall_state
    }
    json_file = f'{video_file_name}.json'
    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=4)

    return json_file

def process(video_path):
    interval = 60
    df = detect_motion_and_process_frame(video_path, _model, threshold_inside=4000, threshold_outside=2500)
    json_file = status(df, os.path.basename(video_path).split('.')[0], interval)
    return json_file

@click.command(name='process_video')
@click.option("--input_bucket", type=str, required=True, help="Path to the input S3 bucket")
@click.option("--input_filepath", type=str, required=True, help="Path to the input movie file")
@click.option("--output_bucket", type=str, required=True, help="Path to the output S3 bucket")
@click.option("--output_filepath", type=str, required=True, help="Path to the output movie file")
def cli(input_bucket, input_filepath, output_bucket, output_filepath):
    input_file_basename = os.path.basename(input_filepath)
    output_file_basename = os.path.basename(output_filepath)
    s3 = boto3.client('s3')
    s3.download_file(input_bucket, input_filepath, input_file_basename)
    json_file = process(input_file_basename)
    s3.upload_file(json_file, output_bucket, f'{os.path.basename(json_file)}')
    # s3.upload_file(output_file_basename, output_bucket, output_filepath)

if __name__ == "__main__":
    cli()
