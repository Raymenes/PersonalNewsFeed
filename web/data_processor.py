#%%
import sys
sys.path.append('/workspace/PersonalNewsFeed/web')

from article_manager import TCArticleCrawler, ArticleDB, TCArticleManager
from datetime import datetime, timedelta

article_manager = TCArticleManager()

def get_articles_for_date_range(startDate, endDate):
    article_list = []
    startDate = datetime.strptime(startDate, "%Y-%m-%d")
    endDate = datetime.strptime(endDate, "%Y-%m-%d")
    currDate = startDate
    while currDate <= endDate:
        dateStr = currDate.strftime("%Y-%m-%d")
        article_list += article_manager.retrieve_articles(dateStr, full_content=True)
        currDate += timedelta(days=1)
    return article_list

# Step 1
# Get corpus as a list of string = article text
corpus = []
article_list = get_articles_for_date_range('2018-01-01', '2019-06-16')
for article in article_list:
        corpus.append(article['text'])
# place the extra space after each '.', to avoid 'sentence1.sentence2'
for i, text in enumerate(corpus):
    corpus[i] = text.replace(".", ". ")
# convert list of article/paragraph into a list of sentences
sentence_list = []
for paragraph in corpus:
    # this gives us a list of sentences in the paragraph
    sent_text = nltk.sent_tokenize(paragraph) 
    sentence_list += sent_text


#%%
# Step 2
# Import necessary nlp preprocessing module
import pandas as pd
import numpy as mp
import matplotlib.pyplot as pyt

import nltk
from nltk.corpus import wordnet, stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.stem.wordnet import WordNetLemmatizer

from sklearn import preprocessing
from sklearn.utils import class_weight

nltk.download('averaged_perceptron_tagger', download_dir='/tmp/')
nltk.download('wordnet', download_dir='/tmp/')
nltk.download('stopwords', download_dir='/tmp/')
nltk.download('punkt', download_dir='/tmp/')
nltk.data.path.append("/tmp")

lemmatizer = WordNetLemmatizer()
stop = stopwords.words('english')

#excluding some useful words from stop words list
excluding = ['against', 'not', 'don', "don't",'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't",
             'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 
             'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't",'shouldn', "shouldn't", 'wasn',
            "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"]

stop_words = [word for word in stop if word not in excluding]

# Step 3: Define text corpus preprocessing functions
def lemmatize_sentence(sentence):
    '''
    given a string of sentence, return the lemmatized version of it
    lemmatization here is without word pos tagging
    '''
    filtered_sentence=[]
    sentence = sentence.lower().replace(".", ". ")
    for w in word_tokenize(sentence):
        # Check if it is not numeric and its length>2 and not in stop words
        if(not w.isnumeric()) and (len(w)>2) and (w not in stop_words):  
            # Stem and add to filtered list
            filtered_sentence.append(lemmatizer.lemmatize(w))
    final_sentence = " ".join(filtered_sentence) #final string of cleaned words
    return final_sentence

# convert each sentence into a list of words, and lemmatize them
# https://www.machinelearningplus.com/nlp/lemmatization-examples-python/
def lemmatize_sentence_v2(sentence):
    '''
    given a sentence, return a list of lemmatized words
    this lemmatization use word pos tagging and also removes punctuations
    '''
    # 
    def convert_pos_tag(tag):
        """Map POS tag to first character lemmatize() accepts"""
        tag = tag[0].upper()
        tag_dict = {"J": wordnet.ADJ,
                    "N": wordnet.NOUN,
                    "V": wordnet.VERB,
                    "R": wordnet.ADV}

        return tag_dict.get(tag, wordnet.NOUN)

    filtered_sentence = []
    word_list = nltk.pos_tag(nltk.word_tokenize(sentence))
    for word, tag in word_list:
        # remove punctuations like ',' '.' '"'
        if len(word) == 1 and (not word.isalnum()):
            pass
        else:
            filtered_sentence.append(lemmatizer.lemmatize(word, convert_pos_tag(tag)))
    return filtered_sentence

#%%
