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