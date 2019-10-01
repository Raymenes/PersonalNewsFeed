import boto3
import botocore
import logging
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

import os
os.environ['aws_default_region'] = 'us-west-1'
boto3.setup_default_session(region_name='us-west-1')

### https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html
class AWS_S3_Helper:
    def __init__(self):
        self.s3 = boto3.resource('s3')
        self.s3_client = boto3.client('s3')

    def set_s3_bucket_name(self, bucket_name):
        self.s3_bucket_name = bucket_name

    def has_s3_object(self, obj_key, bucket_name=None):
        if bucket_name is None:
            bucket_name = self.s3_bucket_name
        try:
            self.s3.Object(bucket_name, obj_key).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise
        else:
            # The object does exist.
            return True

    def put_s3_object(self, file_name, obj_key=None, bucket_name=None):
    ### https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#client
        if bucket_name is None:
            bucket_name = self.s3_bucket_name
        if obj_key is None:
            obj_key = file_name

        try:
            response = self.s3_client.upload_file(file_name, bucket_name, obj_key)
            logging.info(response)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def get_s3_object(self, obj_key, file_name=None, bucket_name=None):
        if bucket_name is None:
            bucket_name = self.s3_bucket_name
        if file_name is None:
            file_name = obj_key
        response = self.s3_client.download_file(bucket_name, obj_key, file_name)
        logging.info(response)


class AWS_Pref_DB:
    def __init__(self, table_name='MyArticlePreferenceTable', region_name='us-east-1'):
        self.table = boto3.resource('dynamodb').Table(table_name)

    def record_single_preference(self, user_id, article, preference):
        '''
        Get single article preference for suer
        @ user_id - user id
        @ article - {'title': {}, 'date': {}, 'article_id': {}}
        @ preference - 'like', 'dislike', 'uncertain'
        '''
        self.put_article_preference(user_id, article, preference)

    def record_preference(self, user_id, liked_article, dislike_article, uncertain_article):
        '''
        Record user liked article
        @param liked_article - {'title'=string, 'url'=string, 'date'='yyyy/mm/dd'}
        '''
        liked_articles = [liked_article] if liked_article else []
        dislike_articles = [dislike_article] if dislike_article else []
        uncertain_articles = [uncertain_article] if uncertain_article else []
        self.record_preference_list(user_id, liked_articles, dislike_articles, uncertain_articles)

    def record_preference_list(self, user_id, liked_articles, dislike_articles, uncertain_articles):
        article_list = []
        for article in liked_articles:
            article_list.append({
                'user_id': user_id,
                'article_id': article['article_id'],
                'title': article['title'], 
                'date': article['date'],
                'preference': 'like'})
        for article in dislike_articles:
            article_list.append({
                'user_id': user_id,
                'article_id': article['article_id'],
                'title': article['title'], 
                'date': article['date'],
                'preference': 'dislike'})
        for article in uncertain_articles:
            article_list.append({
                'user_id': user_id,
                'article_id': article['article_id'],
                'title': article['title'], 
                'date': article['date'],
                'preference': 'uncertain'})
        with self.table.batch_writer() as batch:
            for article in article_list:
                batch.put_item(Item=article)

    def get_all_articles(self, user_id):
        '''
        Get user article preferences
        @ user_id - user id
        @ return - {'like': {}, 'dislike': {}, 'uncertain': {}}
        '''
        result = {'like':{}, 'dislike':{}, 'uncertain':{}}

        response = self.table.query(KeyConditionExpression=Key('user_id').eq(user_id))

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            # request failure
            return result
        if len(response['Items']) == 0:
            # no entry
            return result

        for item in response['Items']:
            article_metadata = {'title': item['title'], 
                                'date': item['date'], 
                                'article_id': item['article_id'],
                                'url': item['url']}

            if item['preference'] == 'like':
                result['like'][item['article_id']] = article_metadata
            elif item['preference'] == 'dislike':
                result['dislike'][item['article_id']] = article_metadata
            elif item['preference'] == 'uncertain':
                result['uncertain'][item['article_id']] = article_metadata
        
        return result
    
    def get_articles_by_preference(self, user_id, preference):
        '''
        Return a list of user labeled articles of specified type
        @param user_id - user id
        @return - list of articles -> {'title': str, 'date': 'yyyy-mm-dd', 'url': str, 'article_id' = str}
        '''
        result = []
        response = self.table.query(KeyConditionExpression=Key('user_id').eq(user_id))

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            # request failure
            return result
        if len(response['Items']) == 0:
            # no entry
            return result

        result = [item for item in response['Items'] if item['preference'] == preference]
        return result
    
    def put_article_preference(self, user_id, article, preference):
        assert article['article_id'] is not None
        assert article['title'] is not None
        assert article['date'] is not None

        item = {'user_id': user_id, 
                'article_id': article['article_id'], 
                'title': article['title'],
                'date': article['date'],
                'preference': preference}

        if 'url' in article:
            item['url'] = article['url']

        self.table.put_item(Item=item)


class AWS_Article_DB:
    def __init__(self, table_name='ArticleMetadata', region_name='us-east-1'):
        self.table = boto3.resource('dynamodb', region_name=region_name).Table(table_name)

    def put_single_article(self, article):
        self.validate_article(article)
        item = {'article_id': article['article_id'], 
                'title': article['title'],
                'date': article['date'],
                'url': article['url']}
        self.table.put_item(Item=item)

    def put_articles(self, article_list):
        print("putting " + str(len(article_list)) + " articles into dynamodb")
        for article in article_list:
            self.validate_article(article)
        with self.table.batch_writer() as batch:
            for article in article_list:
                item = {'article_id': article['article_id'], 
                        'title': article['title'],
                        'date': article['date'],
                        'url': article['url']}
                batch.put_item(Item=item)

    def get_articles_by_date(self, date):
        '''
        @ date - date string of formate yyyy/MM/dd
        '''
        response = self.table.query(KeyConditionExpression=Key('date').eq(date))
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            print("Error retrieving articles from dynamodb for date = {}".format(date))
            return []
        if len(response['Items']) == 0:
            print("Empty entry from dynamodb for date = {}".format(date))
            return []
        return [article for article in response['Items']]

    def get_article_by_id(self, article_id):
        response = self.table.query(IndexName='article_id-index',
                        KeyConditionExpression=Key('article_id').eq(article_id))
        
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            return []
        if len(response['Items']) == 0:
            return []
        return response['Items'][0]

    def validate_article(self, article):
        assert article['article_id'] is not None
        assert article['date'] is not None
        assert article['title'] is not None
        assert article['url'] is not None

if __name__ == '__main__':
    # sample_file = "/workspace/PersonalNewsFeed/web/tcData/"
    # aws_gateway = AWS_S3_Helper()
    # aws_gateway.set_s3_bucket_name('ruizeng-cloud-bucket')
    # # aws_gateway.get_s3_object("Original_Doge_meme.jpg", "doge.jpg")
    # # aws_gateway.put_s3_object(file_name="app.py")
    
    # print("S3 has obj [{}] is [{}]".format(
    #     "Original_Doge_meme.jpg", 
    #     aws_gateway.has_s3_object("Original_Doge_meme.jpg")))


    # dynamoDbHelper = AWS_Pref_DB()
    # preferences = dynamoDbHelper.get_user_preferences("min")
    # print(preferences)


    articleDb = AWS_Article_DB()
    article_list = articleDb.get_articles_by_date("2019/01/01")
    article = articleDb.get_article_by_id(
        "000ad338197c71935c5e3edc003334b06bcf5008272d2e038778ee4b3ffd1f26")
    print(article)
