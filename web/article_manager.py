from datetime import datetime, timedelta
import pymongo
import subprocess
import json
import hashlib
from aws_gateway import AWS_Pref_DB

def getTitleHash(title):
  '''
  Get the SHA hashed string for the given article title,
  after removing leading and tailing whitespace and convert to lower case
  @param title - title string
  @return SHA hashed string 
  '''
  return hashlib.sha256(title.encode().strip().lower()).hexdigest()

class ArticleDB:
  # Manager an datebase of full article data
  # schema: date -> dict{key=hashed_title_string, value=article}
  # article={'title':string, 'text':string, 'url':string, 'date'='yyyy/mm/dd'}
  def __init__(self, collection):
    '''
    collection - a mongo db collection to store articles
    '''
    self.DATE_FORMAT = "%Y-%m-%d"
    self.collection = collection

  def hasDateEntry(self, date):
    '''
    @param date - artcile publish date string ("yyyy-mm-dd")
    @return boolean - if this date entry is in the collection
    '''
    assert (isinstance(date, str)), "date is not a valid string or datetime object!"

    if self.collection.find({"date": date}).count() == 0:
        return False
    return True
  
  def insertArticle(self, date, article):
    '''
    @param date - artcile publish date string ("yyyy-mm-dd")
    @param list of articles 
            -> {'title': string, 'text': string, 'date': 'yyyy-mm-dd', 'url': url}
    '''
    assert (isinstance(date, str)), "date is not a valid string or datetime object!"

    self.insertListOfArticles(date, [article])

  def insertListOfArticles(self, date, article_list):
    '''
    @param date - artcile publish date string ("yyyy-mm-dd")
    @param list of articles 
            -> {'title': string, 'text': string, 'date': 'yyyy-mm-dd', 'url': url}
    '''
    assert (isinstance(date, str)), "date is not a valid string or datetime object!"

    if (self.hasDateEntry(date)):
      article_dict = self.collection.find_one({"date": date})["articles"]
      for article in article_list:
        article_dict[getTitleHash(article['title'])] = article

      self.collection.update_one(
        {"date": date}, 
        {"$set": {"articles": article_dict}})
    else:
      article_dict = {}
      for article in article_list:
        article_dict[getTitleHash(article['title'])] = article

      self.collection.insert({
        "date": date,
        "articles": article_dict
      })

  def getArticleListForDate(self, date):
    '''
    @param date - artcile publish date string ("yyyy-mm-dd")
    @return list of articles 
            -> {'title': string, 'text': string, 'date': 'yyyy-mm-dd', 'url': url}
    '''
    assert (isinstance(date, str)), "date is not a valid string!"

    if (self.hasDateEntry(date)):
      article_dict = self.collection.find_one({"date": date})["articles"]
      return [article for title, article in article_dict.items()]
    else:
      return []

  def getArticleByTitle(self, title, date=None):
    '''
    Get a full article object by its title
    @param title - article title string
    @return article - {'title': string, 'text': string, 'date': 'yyyy-mm-dd', 'url': url}
    '''
    hashed_title = getTitleHash(title)
    
    if date != None:
      return self.collection.find_one({"date": date})["articles"][hashed_title]
    else:
      for doc in self.collection.find({}):
        if hashed_title in doc["articles"]:
          return doc["articles"][hashed_title]



class TCArticleCrawler:
  
  def __init__(self, save_path="/workspace/PersonalNewsFeed/web/tcData"):
    self.FILENAME_PREFIX = "techcrunch_"
    self.save_path = save_path
    return

  def crawlOnDate(self, specific_date, filename=None):
    '''
    @param specific_date - a string for artcile publish date ("yyyy-mm-dd")
    @return list of dict - representing the article crawled from techcrunch 
                           published on the given date
    '''
    if (filename is None):
      filename = '/workspace/PersonalNewsFeed/web/tcData' + '/' + self.FILENAME_PREFIX + specific_date + ".json"

    # clear all content of this file, if exists
    with open(filename, "w") as f: f.close

    subprocess.check_output(['scrapy', 'crawl', "techcrunch", "-o", filename, 
                              "-a", "date="+specific_date])
    
    article_list = json.load(open(filename, 'r'))
    return article_list

  def crawlInDateRange(self, start_date, end_date):
    '''
    @param start_date - a string for artcile publish date ("yyyy-mm-dd"), inclusive
    @param end_date - a string for artcile publish date ("yyyy-mm-dd"), inclusive
    @return list of dict - representing the article crawled from techcrunch 
                           published within the given date period
    '''
    if (filename is None):
      filename = self.save_path + '/' + start_date + "_to_" + end_date + ".json"

    # clear all content of this file, if exists
    with open(filename, "w") as f: f.close

    subprocess.check_output(['scrapy', 'crawl', "techcrunch", "-o", filename, 
                              "-a", "start="+start_date, "-a", "end="+end_date])

    article_list = json.load(open(filename, 'r'))
    return article_list

class TCArticleManager:
  def __init__(self):
    self.mongoClient = pymongo.MongoClient("mongodb://localhost:27017/")
    self.article_db = ArticleDB(self.mongoClient["TC-Article"]["techcrunch"])
    # self.user_pref_db = ArticlePreferenceDB(self.mongoClient["UserData"]["preference"])
    self.user_pref_db = AWS_Pref_DB()
    self.article_crawler = TCArticleCrawler()
    return


  def retrieve_articles(self, date, full_content=False):
    '''
    @function - retrieve articles published on date, 
                load from database if entry exist, 
                otherwise get from web crawler and back fill into datebase
    @param date - a datetime string for when the articles are published
    @return - a list of article dict
    '''
    article_list = []
    if self.article_db.hasDateEntry(date):
        article_list = self.article_db.getArticleListForDate(date)
    else:
        article_list = self.article_crawler.crawlOnDate(date)
        self.article_db.insertListOfArticles(date, article_list)

    if not full_content:
      for article in article_list:
        article.pop("text", None)

    return article_list


  def fetch_today_articles(self):
    '''
    @function - retrieve articles published today 
    '''
    return self.retrieve_articles(datetime.today().strftime('%Y-%m-%d'))
    

  def get_full_article(self, title, date=None):
    '''
    Get full article data
    @param title - article title
    '''
    return self.article_db.getArticleByTitle(title, date)


  # User labeled article preferences related opeations

  def get_user_likes(self, user_id):
    '''
    Get list of user liked articles
    @param user_id - user id
    '''
    return self.user_pref_db.get_articles_by_preference(user_id, 'like')


  def get_user_dislikes(self, user_id):
    '''
    Get list of user disliked articles
    @param user_id - user id
    '''
    return self.user_pref_db.get_articles_by_preference(user_id, 'dislike')


  def get_user_uncertains(self, user_id):
    '''
    Get list of user uncertain articles
    @param user_id - user id
    '''
    return self.user_pref_db.get_articles_by_preference(user_id, 'uncertain')


  def record_liked_article(self, user_id, article):
    '''
    Store the user liked article in database

    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''

    print("user [{}] liked [{}]".format(user_id, article['title']))
    article['article_id'] = getTitleHash(article['title'])
    self.user_pref_db.record_single_preference(user_id, article, 'like')


  def record_dislike_article(self, user_id, article):
    '''
    Store the user disliked article in database
    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''

    print("user [{}] disliked [{}]".format(user_id, article['title']))
    article['article_id'] = getTitleHash(article['title'])
    self.user_pref_db.record_single_preference(user_id, article, 'dislike')


  def record_uncertain_article(self, user_id, article):
    '''
    Store the user uncertain article in database
    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''
    print("user [{}] is uncertain about [{}]".format(user_id, article['title']))
    article['article_id'] = getTitleHash(article['title'])
    self.user_pref_db.record_single_preference(user_id, article, 'uncertain')

    

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
  
  articleDb = ArticleDB(pymongo.MongoClient("mongodb://localhost:27017/")["TC-Article"]["techcrunch"])
  dynamoDbHelper_1 = AWS_Pref_DB('MyArticlePreferenceTable')
  dynamoDbHelper_2 = AWS_Pref_DB('UserArticlePreferenceTable')

  article_list = dynamoDbHelper_1.get_user_likes("ruizeng")
  for article in article_list:
    print(str(article))
    dynamoDbHelper_2.put_article_preference("ruizeng", article, preference='like')


  
  
