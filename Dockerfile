FROM python:3.9

# Install necessary system dependencies
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 libgl1-mesa-glx


COPY requirements.txt .
COPY process_video.py .
COPY best.pt .

RUN pip install -r requirements.txt

ENTRYPOINT python process_video.py \
    --input_bucket=${INPUT_BUCKET} \
    --input_filepath=${INPUT_FILEPATH} \
    --output_bucket=${OUTPUT_BUCKET} \
    --output_filepath=${OUTPUT_FILEPATH}