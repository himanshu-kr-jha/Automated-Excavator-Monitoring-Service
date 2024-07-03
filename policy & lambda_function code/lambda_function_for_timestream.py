import json
import boto3
from datetime import datetime, timezone

# Initialize the TimestreamWrite and S3 clients
timestream_write = boto3.client('timestream-write')
s3 = boto3.client('s3')

database_name = 'excavatorDB'
table_name = 'excavator_state_monitor'

def ensure_database_and_table_exist():
    try:
        # Check if database exists, if not, create it
        timestream_write.describe_database(DatabaseName=database_name)
    except timestream_write.exceptions.ResourceNotFoundException:
        timestream_write.create_database(DatabaseName=database_name)
        print(f"Created database {database_name}")

    try:
        # Check if table exists, if not, create it
        timestream_write.describe_table(DatabaseName=database_name, TableName=table_name)
    except timestream_write.exceptions.ResourceNotFoundException:
        timestream_write.create_table(DatabaseName=database_name, TableName=table_name)
        print(f"Created table {table_name} in database {database_name}")

def write_records_to_timestream(data):
    current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    timestamp = int(current_time.timestamp() * 1000)  # Timestream expects time in milliseconds since epoch

    records = []
    video_file = data['video_file']
    
    for result in data['result']:
        try:
            state = result['state']  # Attempt to convert 'state' to float
            if state == 'working':
                state = 1.0
            else:
                state = 0.0
            probability = float(result['probability'])  # Attempt to convert 'probability' to float
        except ValueError as ve:
            print(f"Skipping record due to invalid value: {ve}")
            continue
        
        multi_measure_record = {
            'Time': str(timestamp),
            'Dimensions': [
                {'Name': 'video_file', 'Value': video_file},
                {'Name': 'Time', 'Value': str(timestamp)},
            ],
            'MeasureName': 'multi_measure',
            'MeasureValueType': 'MULTI',
            'MeasureValues': [
                {
                    'Name': 'state',
                    'Value': str(state),  # Convert to string for insertion
                    'Type': 'DOUBLE'
                },
                {
                    'Name': 'probability',
                    'Value': str(probability),  # Convert to string for insertion
                    'Type': 'DOUBLE'
                }
            ]
        }

        records.append(multi_measure_record)
        print(records)
    
    try:
        response = timestream_write.write_records(
            DatabaseName=database_name,
            TableName=table_name,
            Records=records
        )
        print(f"Successfully wrote {len(records)} records to Timestream")
    except Exception as e:
        print(f"Error writing records to Timestream: {e}")

def lambda_handler(event, context):
    # Ensure the database and table exist
    ensure_database_and_table_exist()
    
    # Get the bucket name and key from the S3 event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Retrieve the JSON file from S3
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        json_content = json.loads(content)
        
        write_records_to_timestream(json_content)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully processed and wrote data to Timestream')
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error processing or writing data to Timestream: {str(e)}')
        }
