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
    article_list = []

    if request.method == 'POST':
        article_list = json.loads(request.form.get('article_list').replace("\'", "\""))
        title = request.form.get('title').lower().strip()
        action = request.form.get('action').lower().strip()
        date = request.form.get('date')
        
        #validate required fields present
        if title and action:
            article = {'title': title, 'date': date}
            article_list = [item for item in article_list if item['title'].lower().strip() != title]
            if action == 'like':
                article_manager.record_liked_article(user_id='rui', article=article)
            elif action == 'dislike':
                article_manager.record_dislike_article(user_id='rui', article=article)
    else:
        article_list = article_manager.retrieve_articles(date)

    return make_response(
        render_template(
            'daily_news_summary.html',
            dateStr=date,
            article_list=article_list
            ), 
        200, headers)

@app.route('/UserLikes/<uid>', methods=['GET','POST'])
def display_user_likes(uid):
    if not article_manager.has_user(uid):
        return "No user [{}] found".format(uid)
    else:
        like_article_list = article_manager.get_user_likes(uid)
        like_article_list.sort(key=lambda article: article['date'])
        return make_response(
            render_template(
                'user_preference.html',
                uid=uid,
                pref_type="liked",
                article_list=like_article_list
                ), 
            200, headers)

@app.route('/UserDislikes/<uid>', methods=['GET','POST'])
def display_user_dislikes(uid):
    if not article_manager.has_user(uid):
        return "No user [{}] found".format(uid)
    else:
        dislike_article_list = article_manager.get_user_dislikes(uid)
        dislike_article_list.sort(key=lambda article: article['date'])
        return make_response(
            render_template(
                'user_preference.html',
                uid=uid,
                pref_type="disliked",
                article_list=dislike_article_list
                ), 
            200, headers)





class CrawlTCForm(FlaskForm):
    '''
    simple form object to get date string from user
    '''
    date_field = StringField("Get articles from specific date(yyyy-mm-dd):")
    submit_field = SubmitField("Submit")

## to manually run mongodb on local host:
## brew install mongodb
## mongod --config /usr/local/etc/mongod.conf
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=4999, debug=True)



