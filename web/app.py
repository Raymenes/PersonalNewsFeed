from flask import Flask, request, render_template, redirect, url_for, make_response, send_from_directory, jsonify, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

from pymongo import MongoClient
from datetime import datetime, timedelta
from article_manager import TCArticleCrawler, ArticleDB, TCArticleManager

import subprocess
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = "maomao is the best"

# # Mongo db initialization
# mongoClient = MongoClient("mongodb://localhost:27017/")
# db = mongoClient["TC-Article"]
# collection = db["techcrunch"]

# # article helper class
# article_db = ArticleDB(collection)
# article_crawler = TCArticleCrawler()
article_manager = TCArticleManager()

headers = {'Content-Type': 'text/html'}

@app.route('/', methods=['GET','POST'])
def hello_world():
    form = CrawlTCForm()
    if form.validate_on_submit():
        date = form.date_field.data
        return redirect(url_for('display_techcrunch_articles', date=date))

    return make_response(render_template('index.html', form=form), 200, headers)

@app.route('/Techcrunch/<date>', methods=['GET','POST'])
def display_techcrunch_articles(date):
    if date.lower() == 'today':
        date = datetime.today().strftime("%Y-%m-%d")
    article_list = article_manager.retrieve_articles(date)

    for article in article_list:
        interest_form = ArticleInterestForm()
        article['form'] = interest_form

    return make_response(
        render_template(
            'daily_news_summary.html',
            dateStr=date,
            article_list=article_list
            ), 
        200, headers)

# @app.context_processor
# def utility_processor():
#     def like_techcrunch_article(article):
#             article_manager.record_liked_article(article)
#     return dict(like_techcrunch_article=like_techcrunch_article)

@app.route('/like_techcrunch_article', methods=['POST'])
def like_techcrunch_article():
    title = request.form.get('title')
    date = request.form.get('date')
    action = request.form.get('action')
    print(title)
    print(date)
    print(action)
    article = {'title': title, 'date': date}

    if action.lower() == 'like':
        article_manager.record_liked_article(user_id='rui', article=article)
    elif action.lower() == 'dislike':
        article_manager.record_dislike_article(user_id='rui', article=article)
    
    return redirect(url_for('display_techcrunch_articles', date=date))

class CrawlTCForm(FlaskForm):
    '''
    simple form object to get date string from user
    '''
    date_field = StringField("Get articles from specific date(yyyy-mm-dd):")
    submit_field = SubmitField("Submit")

class ArticleInterestForm(FlaskForm):
    '''
    form for user to select interested or not
    '''
    like_btn = SubmitField("Like")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=4999, debug=True)



