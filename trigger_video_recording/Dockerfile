FROM python:3.8-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install boto3 opencv-python-headless

# Copy the script
COPY record_and_upload.py /app/record_and_upload.py

CMD ["python", "/app/record_and_upload.py"]
