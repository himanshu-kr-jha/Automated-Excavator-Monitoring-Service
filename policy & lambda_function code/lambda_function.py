import json
import boto3
import os

def lambda_handler(event, context):
    input_bucket='excavator-video-input'
    output_bucket='excavator-video-output'
    
    input_filepath=event['Records'][0]['s3']['object']['key']
    basename,extension=os.path.splitext(input_filepath)
    output_filepath=basename+"-processed"+extension
    
    env_vars={
        'input_bucket':input_bucket,
        'input_filepath':input_filepath,
        'output_bucket':output_bucket,
        'output_filepath':output_filepath
    }
    print(env_vars)
    client=boto3.client('ecs')
    print("executing response")
    response= client.run_task(
        cluster='excavator-monitor-cluster',
        launchType='FARGATE',
        taskDefinition='excavator-monitor-task:4',
        count=1,
        platformVersion ='LATEST',
        networkConfiguration={
            'awsvpcConfiguration':{
                'subnets':[
                    'subnet-03f72311d16efebdd',
                    'subnet-04e78f72dfbe8a491'
                ],
                'assignPublicIp':'ENABLED'
            }
        },
        overrides={
            'taskRoleArn':'arn:aws:iam::891377186934:role/excavator-monitor-taskRole',
            'containerOverrides':[
                {
                    'name':'excavator-monitor-container',
                    'environment':[
                        {'name':'INPUT_BUCKET','value':input_bucket},
                        {'name':'INPUT_FILEPATH','value':input_filepath},
                        {'name':'OUTPUT_BUCKET','value':output_bucket},
                        {'name':'OUTPUT_FILEPATH','value':output_filepath}
                    ]
                }
                    
            ]
            
        }
    )
    