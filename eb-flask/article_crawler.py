# 1. Invoke lambda function daily-article-dev-scraper
# 2. poll from SQS to get the fetch complete notification
# 3. get articles from dynamodb, which are populated by lambda func in step 1

import boto3
import json
import time
from aws_gateway import AWS_Article_DB

sqs_arn = 'arn:aws:sqs:us-east-1:672834257724:daily-article-scrapper-complete-message'
lambda_func_name = 'daily-article-dev-scraper'
lambda_client = boto3.client('lambda', region_name='us-east-1')
article_db = AWS_Article_DB()

current_milli_time = lambda: int(round(time.time() * 1000))

def fetch_articles_with_lambda(date_str):
    start_time = current_milli_time()

    update_response = lambda_client.update_function_configuration(
        FunctionName='daily-article-dev-scraper',
        Environment={
            'Variables': {
                'date': date_str
            }
        })

    invoke_response = lambda_client.invoke(
            FunctionName=lambda_func_name,
            InvocationType='RequestResponse',
            LogType='None',
            Payload=json.dumps({
                'date': date_str, 
                'request_timestamp': 'timestamp',
                'test': True,
                'SQS': sqs_arn
            }))

    end_time = current_milli_time()

    print(invoke_response)
    response_json = json.loads(invoke_response['Payload'].read().decode("utf-8"))
    print(response_json)

    if invoke_response['StatusCode'] is 200:
        print("successfully fetched tc articles using lambda {}".format(lambda_func_name))
        print("operation took {} ms".format(end_time - start_time))
        # now get articles from dynamodb
        article_list = article_db.get_articles_by_date(date_str.replace("-", "/"))
        print("retrieved {} articles from dynamodb.".format(str(len(article_list))))
        for idx, article in enumerate(article_list):
            print("{}: {}".format(str(idx+1), article['title']))

    return article_list
    

if __name__ == "__main__":
    fetch_articles_with_lambda('2019-09-08')

    