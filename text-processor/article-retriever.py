#%%
import boto3
import botocore
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

import pprint
pp = pprint.PrettyPrinter(indent=4)

import time
from sys import getsizeof


# config metadata
region_name = 'us-east-1'
article_dynamodb_table_name = 'ArticleMetadata'
article_s3_bucket_name = 'techcrunch-article-set'

s3_client = boto3.client('s3')
comprehend = boto3.client(service_name='comprehend', region_name=region_name)
dynamo_table = boto3.resource('dynamodb', region_name=region_name).Table(article_dynamodb_table_name)

def get_articles_by_date(date_str):
    response = dynamo_table.query(KeyConditionExpression=Key('date').eq(date_str))
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        print("Error retrieving articles from dynamodb for date = {}".format(date_str))
        return []
    if len(response['Items']) == 0:
        print("Empty entry from dynamodb for date = {}".format(date_str))
        return []
    articles = [article for article in response['Items']]

    for article in articles:
        article['text'] = get_article_by_id(article['article_id'])['text']
    return articles

def get_articles_by_ids(ids):
    articles = []
    for article_id in ids:
        response = s3_client.get_object(
            Bucket=article_s3_bucket_name, 
            Key=article_id+'.json')
        article = json.loads(response['Body'].read().decode('utf-8'))
        article['article_id'] = article_id
        articles.append(article)
    return articles

def get_article_by_id(article_id):
    response = s3_client.get_object(
        Bucket=article_s3_bucket_name, 
        Key=article_id+'.json')
    return json.loads(response['Body'].read().decode('utf-8'))

def batch_analyze_articles(articles):
    process_articles = [article for article in articles if len(article['text']) > 0]
    process_texts = [article['text'][:4500] for article in process_articles]
    batches = divide_chunks(process_texts, 25)

    pp.pprint("Total articles to be processed = {}".format(len(process_articles)))
    pp.pprint("Total number of batches = {}".format(len(batches)))

    pp.pprint('Calling DetectSentiment')
    start_time = time.time()

    sentiment_results = {}
    for i in range(0, len(batches)):
        count = i * 25
        response = comprehend.batch_detect_sentiment(
            TextList=batches[i], LanguageCode='en'
        )

        if len(response['ErrorList']) > 0:
            print("Error for detect sentiment in batch {}!".format(i))
            print(response['ErrorList'])

        for sent in response['ResultList']:
            scores = {}
            for key, score in sent['SentimentScore'].items():
                scores[key] = Decimal(score)
            
            sentiment_results[count + sent['Index']] = {
                'Sentiment': sent['Sentiment'], 
                'SentimentScore': scores
            }

    pp.pprint("--- DetectSentiment took {} seconds ---".format(time.time() - start_time))

    pp.pprint('Calling DetectEntities')
    start_time = time.time()

    entities_results = {}
    for i in range(0, len(batches)):
        count = i * 25
        response = comprehend.batch_detect_entities(
            TextList=batches[i], LanguageCode='en'
        )
        
        if len(response['ErrorList']) > 0:
            print("Error for detect entities in batch {}!".format(i))
            print(response['ErrorList'])
        
        for ent in response['ResultList']:
            entity_list = dedup_list([entry['Text'] for entry in ent['Entities']])
            entities_results[count + ent['Index']] = entity_list

    pp.pprint("--- DetectEntities took {} seconds ---".format(time.time() - start_time))

    for i, article in enumerate(process_articles):
        if i in sentiment_results:
            article['Sentiment'] = sentiment_results[i]
        if i in entities_results:
            article['Entities'] = entities_results[i]

    return process_articles

def put_updated_articles(article_list):
    pp.pprint("Writing {} analyzed articles into dynamodb".format(len(article_list)))
    with dynamo_table.batch_writer() as batch:
        for article in article_list:
            item = {'article_id': article['article_id'], 
                    'title': article['title'],
                    'date': article['date'],
                    'url': article['url']}
            if 'Sentiment' in article:
                item['sentiment'] = article['Sentiment']
            if 'Entities' in article:
                item['entities'] = article['Entities']
            batch.put_item(Item=item)

# Functions to truncate text into certain bytes
# Because Comprehend Sentiment api only take max of 5000 bytes
def utf8_lead_byte(b):
    '''A UTF-8 intermediate byte starts with the bits 10xxxxxx.'''
    return (ord(b) & 0xC0) != 0x80

def utf8_byte_truncate(text, max_bytes):
    '''If text[max_bytes] is not a lead byte, back up until a lead byte is
    found and truncate before that character.'''
    utf8 = text.encode('utf8')
    if len(utf8) <= max_bytes:
        return utf8
    i = max_bytes
    while i > 0 and not utf8_lead_byte(utf8[i]):
        i -= 1
    return utf8[:i]

# Helper methods
# Divide a list l into a list of sublist and each one with max size of n
def divide_chunks(l, n):  
    # looping till length l 
    n = max(1, n)
    result = []
    i = 0
    while i < len(l):
        chunk = l[i: i+n]
        result.append(chunk)
        i = i+n
    return result

# Remove duplicate items in a list while keeping the order
def dedup_list(l):
    seen = set()
    seen_add = seen.add
    return [x for x in l if not (x in seen or seen_add(x))]

#%%
if __name__ == '__main__':
    # id = '38054ee2c7f49df83beedaaeb9cefbbcadef221ed83b5e55ce1a488aba64ad09'
    # article = get_article_by_id(id)
    # text = article['text']
    # text_length = len(text)
    # print(text)
    # print(text_length)
    start_time = time.time()


    date = '2019/09/20'
    articles = get_articles_by_date(date)
    
    batch_analyze_articles(articles)

    print("--- %s seconds ---" % (time.time() - start_time))
    

#%%
date = '2019/09/20'
articles = get_articles_by_date(date)


#%%
batch_analyze_articles(articles)

#%%


put_updated_articles(articles)

#%%

test_articles = get_articles_by_ids([
    '0160459551e2d05d37d696dcbfedbe3165b7e6a0a649f97a2d643ea42a9066f4',
    '086b01d02525187dfa7ba55891dfa3adaaf1ccedc7fb1c697c0563bdc04a0de5'
    ])


#%%
