from flask import Flask, request, render_template, redirect, url_for, make_response, send_from_directory, jsonify, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

from pymongo import MongoClient
from datetime import datetime, timedelta
from article_manager import TCArticleCrawler, ArticleDB, TCArticleManager

import subprocess
import json
from random import randint

app = Flask(__name__)
app.config['SECRET_KEY'] = "maomao is the best"

article_manager = TCArticleManager()

headers = {'Content-Type': 'text/html'}

@app.route('/', methods=['GET','POST'])
def hello_world():
    # Handle get today tc articles button
    form = CrawlTCForm()
    if form.validate_on_submit():
        date = form.date_field.data
        return redirect(url_for('display_techcrunch_articles', date=date))

    # Handle simple user login
    if request.method == 'POST':
        print(request)
        print(request.form)
        action = request.form.get('action')
        if action.lower() == 'login' and request.form.get('uid'):
            session['uid'] = request.form.get('uid')
        elif action.lower() == 'logout':
            session.pop('uid', None)
    
    return make_response(render_template('index.html', form=form, session=session), 200, headers)

@app.route('/Techcrunch/<date>/<diff>', methods=['GET'])
@app.route('/Techcrunch/<date>', methods=['GET','POST'])
def display_techcrunch_articles(date, diff=None):
    if date.lower() == 'today':
        date = datetime.today().strftime("%Y-%m-%d")
        return redirect(url_for('display_techcrunch_articles', date=date, diff=diff))
    
    if diff:
        dateObj = datetime.strptime(date, "%Y-%m-%d")
        if diff.lower() == 'prev':
            dateObj -= timedelta(days=1)
        elif diff.lower() == 'next':
            dateObj += timedelta(days=1)
        elif diff.lower() == 'rand':
            oldestDateObj = datetime.strptime("2018-01-01", "%Y-%m-%d")
            todayObj = datetime.today()
            delta = todayObj - oldestDateObj
            dateObj = oldestDateObj + timedelta(days=randint(0, delta.days))
        date = dateObj.strftime("%Y-%m-%d")
        return redirect(url_for('display_techcrunch_articles', date=date, diff=None))
    
    article_list = []

    if request.method == 'POST':
        article_list = json.loads(request.form.get('article_list').replace("\'", "\""))
        title = request.form.get('title').lower().strip()
        action = request.form.get('action').lower().strip()
        date = request.form.get('date')
        
        #validate required fields present
        if title and action and ('uid' in session):
            uid = session['uid']
            article = {'title': title, 'date': date}
            article_list = [item for item in article_list if item['title'].lower().strip() != title]
            if action == 'like':
                article_manager.record_liked_article(user_id=uid, article=article)
            elif action == 'dislike':
                article_manager.record_dislike_article(user_id=uid, article=article)
            elif action == 'uncertain':
                article_manager.record_uncertain_article(user_id=uid, article=article)
    else:
        article_list = article_manager.retrieve_articles(date)

    # add extra info if article has been labeled by user
    if 'uid' in session:
        uid = session['uid']
        user_likes = set([article['title'] for article in article_manager.get_user_likes(uid)])
        user_dislikes = set([article['title'] for article in article_manager.get_user_dislikes(uid)])
        user_uncertains = set([article['title'] for article in article_manager.get_user_uncertains(uid)])

        for article in article_list:
            article['label'] = ''
            title = article['title'].strip().lower()
            if title in user_likes:
                article['label'] = 'like'
            elif title in user_dislikes:
                article['label'] = 'dislike'
            elif title in user_uncertains:
                article['label'] = 'uncertain'

    return make_response(
        render_template(
            'daily_news_summary.html',
            dateStr=date,
            article_list=article_list,
            session=session
            ), 
        200, headers)

@app.route('/User/<uid>/<prefType>', methods=['GET','POST'])
def display_user_likes(uid, prefType):
    if not article_manager.has_user(uid):
        return "No user [{}] found".format(uid)
    else:
        article_list = []
        if prefType.lower() == 'like':
            article_list = article_manager.get_user_likes(uid)
        elif prefType.lower() == 'dislike':
            article_list = article_manager.get_user_dislikes(uid)
        elif prefType.lower() == 'uncertain':
            article_list = article_manager.get_user_uncertains(uid)

        article_list.sort(key=lambda article: article['date'])
        return make_response(
            render_template(
                'user_preference.html',
                uid=uid,
                pref_type=prefType,
                article_list=article_list
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



