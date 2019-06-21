#%%
import sys
sys.path.append('/workspace/PersonalNewsFeed/web')

from article_manager import TCArticleCrawler, ArticleDB, TCArticleManager
from datetime import datetime, timedelta

# Import necessary nlp preprocessing module
import re
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


article_manager = TCArticleManager()

# method to get source data - a list of articles
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

# method to convert article objects into text corpus
def get_text_corpus_from_articles(article_list):
    # Get corpus as a list of string = article text
    corpus = []
    for article in article_list:
        corpus.append(article['text'])
    return corpus
    
# method to convert text corpus to list of sentences
def get_sentences_from_corpus(corpus):
    # convert list of article/paragraph into a list of sentences
    sentence_list = []
    for paragraph in corpus:
        # this gives us a list of sentences in the paragraph
        sent_text = nltk.sent_tokenize(paragraph) 
        sentence_list += sent_text
    return sentence_list

#%%
# Step 2: 

lemmatizer = WordNetLemmatizer()
stop = stopwords.words('english')

# excluding some useful words from stop words list
excluding = ['against', 'not', 'don', "don't",'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't",
             'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 
             'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't",'shouldn', "shouldn't", 'wasn',
            "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"]

stop_words = [word for word in stop if word not in excluding]


# strip non-alphanumeric-characters-at-the-beginning-or-end of the word
# '--apple+' -> 'apple'
def strip_nonalnum_re(word):
    return re.sub(r"^\W+|\W+$", "", word)


# Step 3: Define text corpus preprocessing functions
def lemmatize_sentence_v1(sentence):
    '''
    given a string of sentence, return the lemmatized version of it
    lemmatization here is without word pos tagging
    also remove stop words
    '''
    filtered_sentence=[]
    sentence = sentence.lower()
    for w in word_tokenize(sentence):
        # Check if it is not numeric and its length>2 and not in stop words
        if (not w.isnumeric()) and (len(w)>2) and (w not in stop_words):  
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
    sentence = sentence.lower()
    word_list = nltk.pos_tag(nltk.word_tokenize(sentence))
    for word, tag in word_list:
        # remove punctuations like ',' '.' '"'
        if (not word.isnumeric()) and (len(word)>=2):
            word = strip_nonalnum_re(word)
            filtered_sentence.append(lemmatizer.lemmatize(word, convert_pos_tag(tag)))
            
    return filtered_sentence

# simplest way to get list of word from a sentence string, 
# simple lemmatization and stripping off any punctuations
# no removing of stop words
def lemmatize_sentence_v0(sentence):
    words = []
    for w in word_tokenize(sentence):
        # only remove the punctuations
        if (len(w) > 1) or (w.isalnum()):
            words.append(w)
    return words

    
#%%
article_list = get_articles_for_date_range('2018-01-01', '2019-06-18')
corpuses = get_text_corpus_from_articles(article_list)
sentences = get_sentences_from_corpus(corpuses)

#%%
sentence_words = []
for sent in sentences:
    sentence_words.append(lemmatize_sentence_v2(sent))


#%%
for word_list in sentence_words:
    for i, word in enumerate(word_list):
        word_list[i] = word.decode("utf-8") 
#%%
# https://datascience.stackexchange.com/questions/10695/how-to-initialize-a-new-word2vec-model-with-pre-trained-model-weights
# https://radimrehurek.com/gensim/models/word2vec.html
from gensim.models import Word2Vec
from sklearn.decomposition import PCA
from matplotlib import pyplot

# train a word2vec model based on the techcrunch data

model_1 = Word2Vec(sentences=sentence_words, size=300, min_count=2)

# #%%
# # fit a 2d PCA model to the vectors
# X = model_1[model_1.wv.vocab]
# pca = PCA(n_components=2)
# result = pca.fit_transform(X)



#%%
print(len(model_1.wv.vocab))
print('\n')
print(model_1.predict_output_word(['apple']))
print('\n')
print(model_1.predict_output_word(['google']))
print('\n')
print(model_1.predict_output_word(['car']))


#%%

#%%
from gensim.models import KeyedVectors

model_2 = Word2Vec(size=300, min_count=2)
model_2.build_vocab(sentence_words)
total_examples = model_2.corpus_count
google_wv = KeyedVectors.load_word2vec_format('/workspace/PersonalNewsFeed/web/GoogleNews-vectors-negative300.bin', binary=True)
model_2.build_vocab([list(google_wv.vocab.keys())], update=True)
model_2.intersect_word2vec_format("/workspace/PersonalNewsFeed/web/GoogleNews-vectors-negative300.bin", binary=True, lockf=1.0)
model_2.train(sentence_words, total_examples=total_examples, epochs=model_2.epochs)


#%%
print(len(model_2.wv.vocab))
print('\n')
print(model_2.predict_output_word(['apple']))
print('\n')
print(model_2.predict_output_word(['google']))
print('\n')
print(model_2.predict_output_word(['car']))

#%%
print(model_2.wv.similarity('apple', 'banana'))
print(model_1.wv.similarity('apple', 'banana'))

#%%
