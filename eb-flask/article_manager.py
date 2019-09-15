from datetime import datetime, timedelta
import pymongo
import subprocess
import json
import hashlib
from functools import lru_cache
from aws_gateway import AWS_Pref_DB, AWS_Article_DB
import article_crawler

def getTitleHash(title):
  '''
  Get the SHA hashed string for the given article title,
  after removing leading and tailing whitespace and convert to lower case
  @param title - title string
  @return SHA hashed string 
  '''
  return hashlib.sha256(title.encode().strip().lower()).hexdigest()

class TCArticleManager:
  def __init__(self):
    self.article_db = AWS_Article_DB()
    self.user_pref_db = AWS_Pref_DB()
    # self.article_crawler = TCArticleCrawler()
    return

  # https://docs.python.org/3/library/functools.html
  # https://www.programcreek.com/python/example/29697/functools.lru_cache
  @lru_cache(maxsize=15)
  def retrieve_articles(self, date, full_content=False):
    '''
    @function - retrieve articles published on date, 
                load from database if entry exist, 
                otherwise get from web crawler and back fill into datebase
    @param date - a datetime string for when the articles are published
    @return - a list of article dict
    '''
    date = date.replace("-", "/")
    print("getting article by date: " + date)
    article_list = self.article_db.get_articles_by_date(date)

    if article_list is None or len(article_list) == 0:
      # no entry in dynamodb, crawl from tc website instead
      article_list = article_crawler.fetch_articles_with_lambda(date.replace("/", "-"))
      for article in article_list:
        article['article_id'] = getTitleHash(article['title'])

    if not full_content:
      for article in article_list:
        if 'text' in article:
          article.pop("text", None)

    return article_list


  def fetch_today_articles(self):
    '''
    @function - retrieve articles published today 
    '''
    return self.retrieve_articles(datetime.today().strftime('%Y-%m-%d'))
    

  def get_full_article(self, title):
    '''
    Get full article data
    @param title - article title
    '''
    article_id = getTitleHash(title)
    return self.article_db.get_article_by_id(title)


  # User labeled article preferences related opeations
  @lru_cache(maxsize=5)
  def get_user_likes(self, user_id):
    '''
    Get list of user liked articles
    @param user_id - user id
    '''
    print("getting user [{}] liked article from db".format(user_id))
    return self.user_pref_db.get_articles_by_preference(user_id, 'like')


  @lru_cache(maxsize=5)
  def get_user_dislikes(self, user_id):
    '''
    Get list of user disliked articles
    @param user_id - user id
    '''
    print("getting user [{}] disliked article from db".format(user_id))
    return self.user_pref_db.get_articles_by_preference(user_id, 'dislike')


  @lru_cache(maxsize=5)
  def get_user_uncertains(self, user_id):
    '''
    Get list of user uncertain articles
    @param user_id - user id
    '''
    print("getting user [{}] uncertained article from db".format(user_id))
    return self.user_pref_db.get_articles_by_preference(user_id, 'uncertain')


  def record_liked_article(self, user_id, article):
    '''
    Store the user liked article in database

    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''
    # clear cache upon preference write update
    self.clear_user_pref_cache('like')
    self.clear_user_pref_cache(article['prev_label'])

    print("user [{}] liked [{}]".format(user_id, article['title']))
    article['article_id'] = getTitleHash(article['title'])
    self.user_pref_db.record_single_preference(user_id, article, 'like')


  def record_dislike_article(self, user_id, article):
    '''
    Store the user disliked article in database
    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''
    self.clear_user_pref_cache('dislike')
    self.clear_user_pref_cache(article['prev_label'])

    print("user [{}] disliked [{}]".format(user_id, article['title']))
    article['article_id'] = getTitleHash(article['title'])
    self.user_pref_db.record_single_preference(user_id, article, 'dislike')


  def record_uncertain_article(self, user_id, article):
    '''
    Store the user uncertain article in database
    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''
    self.clear_user_pref_cache('uncertain')
    self.clear_user_pref_cache(article['prev_label'])

    print("user [{}] is uncertain about [{}]".format(user_id, article['title']))
    article['article_id'] = getTitleHash(article['title'])
    self.user_pref_db.record_single_preference(user_id, article, 'uncertain')


  def clear_user_pref_cache(self, preference):
    if preference == 'like':
      self.get_user_likes.cache_clear()
    elif preference == 'dislike':
      self.get_user_dislikes.cache_clear()
    elif preference == 'uncertain':
      self.get_user_uncertains.cache_clear()

    

## this is for debugging
## to manually run mongodb on local host:
## brew install mongodb
## mongod --config /usr/local/etc/mongod.conf

# basic syntax: https://www.w3schools.com/python/python_classes.asp
# official documentation: http://api.mongodb.com/python/current/tutorial.html
# shell command: https://dzone.com/articles/top-10-most-common-commands-for-beginners
if __name__ == '__main__':
  article_manager = TCArticleManager()
  # startDate = datetime.strptime('2016-01-01', "%Y-%m-%d")
  # endDate = datetime.strptime('2018-01-01', "%Y-%m-%d")

  # article_dict = {}

  # while startDate <= endDate:
  #     dateStr = startDate.strftime("%Y-%m-%d")
  #     article_manager.retrieve_articles(dateStr)
  #     startDate += timedelta(days=1)
  


  # articleDb = ArticleDB(pymongo.MongoClient("mongodb://localhost:27017/")["TC-Article"]["techcrunch"])
  # dynamoDbHelper_1 = AWS_Pref_DB('MyArticlePreferenceTable')
  # dynamoDbHelper_2 = AWS_Pref_DB('UserArticlePreferenceTable')

  # article_list = dynamoDbHelper_1.get_user_likes("ruizeng")
  # for article in article_list:
  #   print(str(article))
  #   dynamoDbHelper_2.put_article_preference("ruizeng", article, preference='like')
  import time

  aws_article_db = AWS_Article_DB()
  mongo_article_collection = pymongo.MongoClient("mongodb://localhost:27017/")["TC-Article"]["techcrunch"]
  docs = mongo_article_collection.find({})
  print(type(docs))
  # print(len(docs))
  count = 0
  for doc in docs:
    date = doc['date']
    article_dict = doc["articles"]
    article_list = [article for title, article in article_dict.items()]
    for article in article_list:
      article['article_id'] = getTitleHash(article['title'])
    time.sleep(1)
    aws_article_db.put_articles(article_list)
    count += 1
    print(count)
