from datetime import datetime, timedelta
import pymongo
import subprocess
import json
import hashlib

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

class ArticlePreferenceDB:
  # Manage an datebase of user prefered article meta data
  # schema: uid -> {'LIKE' -> article_dict, 'DISLIKE' -> article_dict}
  # article_dict={key=hashed_title_string, value=article}
  # article={'title':string, 'url':string, 'date'='yyyy/mm/dd'}

  def __init__(self, collection):
    '''
    @param collection - a mongo db collection to store user article preference
    '''
    self.collection = collection


  def has_user(self, user_id):
    return self.collection.find({"uid": user_id}).count() != 0


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
    '''
    Record user liked articles
    @param liked_articles - a list of user liked articles
    @param dislike_articles - a list of user disliked articles
    article = {'title'=string, 'url'=string, 'date'='yyyy/mm/dd'}
    '''
    user_preferences = self.get_user_preferences(user_id)
    like_article_dict = user_preferences['like'] if 'like' in user_preferences else {}
    dislike_article_dict = user_preferences['dislike'] if 'dislike' in user_preferences else {}
    uncertain_article_dict = user_preferences['uncertain'] if 'uncertain' in user_preferences else {}

    #make sure user doesn't have the same article across different categories
    all_articles = liked_articles + dislike_articles + uncertain_articles
    all_hashed_titles = [getTitleHash(article['title']) for article in all_articles]

    for key in all_hashed_titles:
      if key in like_article_dict:
        del like_article_dict[key]
      elif key in dislike_article_dict:
        del dislike_article_dict[key]
      elif key in uncertain_article_dict:
        del uncertain_article_dict[key]
    
    # store articles into correct entry
    for article in liked_articles:
      key = getTitleHash(article['title'])
      like_article_dict[key] = article
    for article in dislike_articles:
      key = getTitleHash(article['title'])
      dislike_article_dict[key] = article
    for article in uncertain_articles:
      uncertain_article_dict[key] = article
    
    self.collection.update_one(
      {'uid': user_id}, 
      {"$set": {'like': like_article_dict, 
                'dislike': dislike_article_dict, 
                'uncertain': uncertain_article_dict}}, 
      upsert=True)


  def get_user_preferences(self, user_id):
    '''
    Get user article preferences
    @ user_id - user id
    @ return - {'like': {}, 'dislike': {}}
    '''
    if not self.has_user(user_id):
      return {}
    else:
      return self.collection.find_one({'uid': user_id})


  def get_user_likes(self, user_id):
    '''
    Return a list of user liked articles
    @param user_id - user id
    @return - list of articles -> {'title': string, 'date': 'yyyy-mm-dd'}
    '''
    likes_dict = self.get_user_preferences(user_id)['like']
    return [article for key, article in likes_dict.items()]


  def get_user_dislikes(self, user_id):
    '''
    Return a list of user disliked articles
    @param user_id - user id
    @return - list of articles -> {'title': string, 'date': 'yyyy-mm-dd'}
    '''
    dislikes_dict = self.get_user_preferences(user_id)['dislike']
    return [article for key, article in dislikes_dict.items()]


  def get_user_uncertains(self, user_id):
    '''
    Return a list of user uncertain articles
    @param user_id - user id
    @return - list of articles -> {'title': string, 'date': 'yyyy-mm-dd'}
    '''
    uncertain_dict = self.get_user_preferences(user_id)['uncertain']
    return [article for key, article in uncertain_dict.items()]

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
    self.user_pref_db = ArticlePreferenceDB(self.mongoClient["UserData"]["preference"])
    self.article_crawler = TCArticleCrawler()
    return


  def retrieve_articles(self, date, full_content=False, ):
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
    

  def record_liked_article(self, user_id, article):
    '''
    Store the user liked article in database

    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''

    print("user [{}] liked [{}]".format(user_id, article['title']))
    self.user_pref_db.record_preference(user_id, liked_article=article, dislike_article=None, uncertain_article=None)


  def record_dislike_article(self, user_id, article):
    '''
    Store the user disliked article in database
    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''

    print("user [{}] disliked [{}]".format(user_id, article['title']))
    self.user_pref_db.record_preference(user_id, liked_article=None, dislike_article=article, uncertain_article=None)


  def record_uncertain_article(self, user_id, article):
    '''
    Store the user uncertain article in database
    @param user_id - user id
    @param article - {'title': string, 'date': 'yyyy-mm-dd'}
    '''
    print("user [{}] is uncertain about [{}]".format(user_id, article['title']))
    self.user_pref_db.record_preference(user_id, liked_article=None, dislike_article=None, uncertain_article=article)


  def has_user(self, user_id):
    return self.user_pref_db.has_user(user_id)


  def get_full_article(self, title, date=None):
    '''
    Get full article data
    @param title - article title
    '''
    return self.article_db.getArticleByTitle(title, date)


  def get_user_likes(self, user_id):
    '''
    Get list of user liked articles
    @param user_id - user id
    '''
    if self.user_pref_db.has_user(user_id):
      return self.user_pref_db.get_user_likes(user_id)
    else:
      return []


  def get_user_dislikes(self, user_id):
    '''
    Get list of user disliked articles
    @param user_id - user id
    '''
    if self.user_pref_db.has_user(user_id):
      return self.user_pref_db.get_user_dislikes(user_id)
    else:
      return []


  def get_user_uncertains(self, user_id):
    '''
    Get list of user uncertain articles
    @param user_id - user id
    '''
    if self.user_pref_db.has_user(user_id):
      return self.user_pref_db.get_user_uncertains(user_id)
    else:
      return []
    

## this is for debugging
## to manually run mongodb on local host:
## brew install mongodb
## mongod --config /usr/local/etc/mongod.conf

# basic syntax: https://www.w3schools.com/python/python_classes.asp
# official documentation: http://api.mongodb.com/python/current/tutorial.html
# shell command: https://dzone.com/articles/top-10-most-common-commands-for-beginners
if __name__ == '__main__':
  article_manager = TCArticleManager()
  startDate = datetime.strptime('2016-01-01', "%Y-%m-%d")
  endDate = datetime.strptime('2018-01-01', "%Y-%m-%d")

  article_dict = {}

  while startDate <= endDate:
      dateStr = startDate.strftime("%Y-%m-%d")
      article_manager.retrieve_articles(dateStr)
      startDate += timedelta(days=1)

  
  
