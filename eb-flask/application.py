from flask import Flask, request, render_template, redirect, url_for, make_response, send_from_directory, jsonify, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

from datetime import datetime, timedelta
from article_manager import TCArticleManager
import account_manager

import subprocess
import json

from random import randint

# https://stackoverflow.com/questions/14810795/flask-url-for-generating-http-url-instead-of-https
class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get('HTTP_X_FORWARDED_PROTO')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


# EB looks for an 'application' callable by default.
application = Flask(__name__)
application.wsgi_app = ReverseProxied(application.wsgi_app)
application.config['SECRET_KEY'] = "maomao is the best"

article_manager = TCArticleManager()
web_headers = {'Content-Type': 'text/html'}

# Home page
@application.route('/', methods=['GET','POST'])
def hello_world():
    # class CrawlTCForm(FlaskForm):
    #     '''
    #     simple form object to get date string from user
    #     '''
    #     date_field = StringField("Get articles from specific date (yyyy-mm-dd):")
    #     submit_field = SubmitField("Submit")

    # # Handle get today tc articles button
    # form = CrawlTCForm()
    # if form.validate_on_submit():
    #     date = form.date_field.data
    #     return redirect(url_for('display_techcrunch_articles', date=date))

    # Handle simple user log out
    if request.method == 'POST' and request.form is not None:
        action = request.form.get('action')

        # handle user pick date
        if action.lower() == 'pickdate' and request.form.get('date'):
            date = request.form.get('date')
            return redirect(url_for('display_techcrunch_articles', date=date))

        # handle user logout
        if action.lower() == 'logout' and session.get('uid'):
            print("pop uid from session")
            session.pop('uid', None)
    
    return make_response(render_template('index.html', session=session), 200, web_headers)

@application.route('/Techcrunch/<date>/<diff>', methods=['GET'])
@application.route('/Techcrunch/<date>', methods=['GET','POST'])
def display_techcrunch_articles(date, diff=None):
    if date.lower() == 'today':
        date = datetime.today().strftime("%Y-%m-%d")
        return redirect(url_for('display_techcrunch_articles', date=date, diff=diff))
    
    # handle the case where diff is set, redirect to the actual date
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

    # handle the user like/dislike event
    if request.method == 'POST':
        article_list = json.loads(request.form.get('article_list').replace("\'", "\""))
        title = request.form.get('title').lower().strip()
        action = request.form.get('action').lower().strip()
        prev_label = request.form.get('label').lower().strip()
        date = request.form.get('date')
        
        # validate required fields present
        # action = like/dislike/uncertain
        # uid = user id
        if title and action and ('uid' in session):
            uid = session['uid']
            article = {'title': title, 'date': date, 'prev_label': prev_label}
            print(article)
            if action == 'like':
                article_manager.record_liked_article(user_id=uid, article=article)
            elif action == 'dislike':
                article_manager.record_dislike_article(user_id=uid, article=article)
            elif action == 'uncertain':
                article_manager.record_uncertain_article(user_id=uid, article=article)
    else:
        article_list = article_manager.retrieve_articles(date)

    # render extra info if article has been labeled by user
    # https://stackoverflow.com/questions/40963401/flask-dynamic-data-update-without-reload-page
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
        200, web_headers)

# User preference page
@application.route('/User/<uid>/<prefType>', methods=['GET','POST'])
def display_user_likes(uid, prefType):
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
        200, web_headers)

# Login page  
@application.route('/UserLogin/<type>', methods=['GET','POST'])
def login_signup(type):
    code = request.args.get('code')
    if code != None and len(code) > 0:
        user_info = account_manager.get_user_info(code)
        session['uid'] = user_info['Username']
        return redirect(url_for('hello_world')) 

    return make_response(
        render_template(
            'login.html',
            type=type,
            login_url=account_manager.login_url,
            signup_url=account_manager.signup_url,
            reset_password_url=account_manager.reset_password_url
            ), 
        200, web_headers)

# run the app.
if __name__ == "__main__":
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    application.debug = True
    application.run(ssl_context='adhoc')

