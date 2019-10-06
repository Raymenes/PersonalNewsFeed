import os
import subprocess
import json
import hashlib
import boto3
import botocore
from datetime import datetime, timedelta
import scrapy
from scrapy import signals
from scrapy.crawler import CrawlerProcess, Crawler, CrawlerRunner
from scrapy.utils.project import get_project_settings
from scrapy.signalmanager import dispatcher

# https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html
# https://nervous.io/python/aws/lambda/2016/02/17/scipy-pandas-lambda/
# https://stackoverflow.com/questions/36397171/aws-lambda-not-importing-lxml

# How to deploy to aws
# https://serverless.com/blog/serverless-python-packaging/
# $serverless deploy

# config metadata
region_name = 'us-east-1'
article_dynamodb_table_name = 'ArticleMetadata'
article_s3_bucket_name = 'techcrunch-article-set'
success_notification_sns_arn = 'arn:aws:sns:us-east-1:672834257724:Daily-Article-Fetch-Complete-Notification'
test_notification_sns_arn = 'arn:aws:sns:us-east-1:672834257724:Daily-Article-Fetch-Notification-Test'

sns = boto3.client('sns', region_name=region_name)
s3 = boto3.resource('s3')
db = boto3.resource('dynamodb', region_name=region_name)
table = db.Table(article_dynamodb_table_name)
lambda_client = boto3.client('lambda', region_name=region_name)

def getTitleHash(title):
  '''
  Get the SHA hashed string for the given article title,
  after removing leading and tailing whitespace and convert to lower case
  @param title - title string
  @return SHA hashed string 
  '''
  return hashlib.sha256(title.encode().strip().lower()).hexdigest()

class TechCrunchSpider(scrapy.Spider):
    name = "techcrunch"

    def __init__(self, date='', start='', end='', **kwargs):
        if len(date) > 0:
            self.start_date = datetime.strptime(date, '%Y-%m-%d')
            self.end_date = self.start_date
        elif (len(start) > 0 and len(end) > 0):
            self.start_date = datetime.strptime(start, '%Y-%m-%d')
            self.end_date = datetime.strptime(end, '%Y-%m-%d')
        else:
            self.start_date = datetime.today().strftime('%Y-%m-%d')
            self.end_date = self.start_date
        super().__init__(**kwargs)

    def start_requests(self):        
        curr_date = self.start_date
        
        while curr_date <= self.end_date:
            new_request = scrapy.Request(self.generate_url(curr_date))
            new_request.meta["date"] = curr_date
            new_request.meta["page_number"] = 1
            yield new_request
            curr_date += timedelta(days=1)

    def generate_url(self, date, page_number=None):
        url = 'https://techcrunch.com/' + date.strftime("%Y/%m/%d") + "/"
        if page_number:
            url  += "page/" + str(page_number) + "/"
        return url

    def parse(self, response):
        date = response.meta['date']
        page_number = response.meta['page_number']

        # when I access a page number that doesn't exist I get 404
        # I could use the pagination buttons, but this is less work
        if response.status == 200:
            articles = response.xpath('//h2[@class="post-block__title"]/a/@href').extract()
            for url in articles:
                request = scrapy.Request(url,
                                callback=self.parse_article)
                request.meta['date'] = date
                yield request

            url = self.generate_url(date, page_number+1)
            request = scrapy.Request(url,
                            callback=self.parse)
            request.meta['date'] = date
            request.meta['page_number'] = page_number
            yield request

    def parse_article(self, response):
        item = {
            'title': " ".join(response.xpath('//h1/text()').extract()),
            'text': " ".join(response.xpath('//div[starts-with(@class,"article-content")]/p//text()').extract()),
            'date': response.meta['date'].strftime("%Y/%m/%d"),
            'url' : response.url
        }
        yield item

def lambda_handler(event, context):
    # list to collect all items
    items = []
    def add_item(item):
        items.append(item)

    try:
        # crawl article on the given date
        dateStr = None
        try:
            dateStr = os.environ['date']
            datetime.strptime(dateStr, "%Y-%m-%d")
        except (ValueError, KeyError) as err:
            print("[error] cannot parse date from env variable!")
            print(err)
            dateStr = datetime.today().strftime("%Y-%m-%d")

        print("[info] crawling techcrunch articles for datetime = {}".format(dateStr))

        process = CrawlerProcess({
            'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
            'LOG_LEVEL': 'INFO'
        })
        dispatcher.connect(add_item, signal=signals.item_passed)
        process.crawl(TechCrunchSpider, date=dateStr)
        process.start()

        # Print complete message
        print("[info] finished scraping")
        br = '\n'
        complete_message = 'RuiZeng fetched {} articles from Techcrunch for date {}'.format(str(len(items)), dateStr)
        complete_message += br
        complete_message += "Visit https://www.ruizeng.info to express your preference!"
        complete_message += br + br
        for idx, article in enumerate(items):
            title_str = "{}: {}".format(str(idx+1), article['title'])
            link_str = "  - link: {}".format(article['url']) 
            complete_message += title_str + br + link_str + br + br
            print(title_str)

        # Publish to SNS topic (Differentiate test and prod SNS topic)
        topic_arn = success_notification_sns_arn
        if ('test' in event) and (event['test'] is True):
            complete_message = "This is a TEST notification!" + br + br + complete_message
            topic_arn = test_notification_sns_arn
        
        response = sns.publish(
            TopicArn=topic_arn,
            Subject='RuiZeng - Daily Techcrunch Articles',
            Message=complete_message
        )

        # Publish to S3    
        print("putting {} articles into s3".format(str(len(items))))
        for article in items:
            article_id = getTitleHash(article['title'])
            article['article_id'] = article_id
            obj = s3.Object(article_s3_bucket_name, article_id + '.json')
            obj.put(Body=json.dumps(article))

        # Publish to DynamoDb
        print("putting " + str(len(items)) + " articles into dynamodb")
        with table.batch_writer() as batch:
          for article in items:
            item = {'article_id': article['article_id'], 
                    'title': article['title'],
                    'date': article['date'],
                    'url': article['url']}
            batch.put_item(Item=item)

        # Invoke the Article Analyzer Lambda (for Sentiment and Entities)
        print("Invoking daily-article-analyzer lambda func with article_ids")
        lambda_client.invoke(
            FunctionName='daily-article-analyzer',
            InvocationType='Event',
            LogType='None',
            Payload=json.dumps({
                'article_ids': [article['article_id'] for article in items], 
                'request_timestamp': 'timestamp'
            }))

        return {
                'statusCode': 200,
                'body': json.dumps('Successfully fetched {} articles from techcrunch!'.format(str(len(items))))
            }

    except Exception as e:
        # TODO: Publish to another error SNS
        print(e)
        raise e

if __name__ == "__main__":
    lambda_handler({'test': True}, '')