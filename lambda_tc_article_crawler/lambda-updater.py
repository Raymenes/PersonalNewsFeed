# https://boto3.amazonaws.com/v1/documentation/api/1.9.42/reference/services/lambda.html#id33

import boto3
import json
from datetime import datetime, timedelta

client = boto3.client('lambda', region_name='us-east-1')

def lambda_handler(event, context):
    # fetch yesterday's article 
    # as today's article might have not been published yet
    timestamp = str(datetime.now().timestamp())
    dateObj = datetime.today()
    dateObj -= timedelta(days=1)
    today_date_str = dateObj.strftime("%Y-%m-%d")
    
    update_response = client.update_function_configuration(
        FunctionName='daily-article-dev-scraper',
        Environment={
            'Variables': {
                'date': today_date_str
            }
        })

    invoke_response = client.invoke(
            FunctionName='daily-article-dev-scraper',
            InvocationType='RequestResponse',
            LogType='None',
            Payload=json.dumps({
                'date': today_date_str, 
                'request_timestamp': 'timestamp'
            }))

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
