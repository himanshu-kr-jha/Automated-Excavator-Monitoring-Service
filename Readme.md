# Excavator Monitoring Setup

This document outlines the steps to create a Docker image, push it to an ECR repository, set up S3 buckets, IAM policies and roles, configure Amazon ECS, and create a Lambda function to automate the process.

## Prerequisites

- AWS CLI configured
- Docker installed
- AWS account with necessary permissions

## Steps

### 1. Create Docker Image

- best.pt
- Dockerfile
- process_video.py
- requirement.txt
Push it on ECR Repository named excavator_monitoring

### 2. Setup S3 bucket

- Create S3 bucket for video-input : excavator-video-input
- Create S3 bucket for video-output: excavator-video-output

### 3. Set the roles and policy

- Create Policy on IAM using provided Policy: excavator-monitor-s3-policy.json
- Create Role on IAM : excavator-monitor-taskRole containing above created policy and AmazonSSMReadOnlyAccess

### 4. Setup Amazon ECS:

- Create Cluster with name : excavator-monitor-cluster
- Create TaskDefinition and in container define the image you formed earlier with name [excavator-monitor-container] 
- Task Definition:  excavator-monitor-task:4  (this can differ as per the version of the image)

### 5. Create AWS lambda function to trigger S3 input bucket.
- Make sure to create it with new role with ECSFullAccess and Attach policy of S3ReadOnlyAccess
- Use the lambda_function.py code in the funtion you created.
- Put the trigger for the input bucket(excavator-video-input)
- Deploy the function.
### 6. Create AWS lambda function to trigger S3 output bucket.
- Make sure to have required s3 access and timestream access.
- Use the lambda_function_for_timestream.py code in lambda funtion on AWS to insert the data of state and probability to timestream database.
- Put the trigger for output bucket(excavator-video-output) so that lambda function can fetch the created json file for respective videos that was processed.
- Deploy the function.

#### This concludes the automated and scalable AWS architecture to process the excavator for its working.
##
~ [@himanshu-kr-jha](https://www.github.com/himanshu-kr-jha)