import re
import nltk
from nltk.corpus import wordnet, stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.stem.wordnet import WordNetLemmatizer

nltk_cache_dir = './tmp/'
nltk.download('averaged_perceptron_tagger', download_dir=nltk_cache_dir)
nltk.download('wordnet', download_dir=nltk_cache_dir)
nltk.download('stopwords', download_dir=nltk_cache_dir)
nltk.download('punkt', download_dir=nltk_cache_dir)
nltk.data.path.append(nltk_cache_dir)


lemmatizer = WordNetLemmatizer()
# excluding some useful words from stop words list
excluding = ['against', 'not', 'don', "don't",'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't",
             'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 
             'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't",'shouldn', "shouldn't", 'wasn',
            "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"]
stop_words = [word for word in stopwords.words('english') if word not in excluding]


# strip non-alphanumeric-characters-at-the-beginning-or-end of the word
# '--apple+' -> 'apple'
def strip_nonalnum_re(word):
    return re.sub(r"^\W+|\W+$", "", word)


def get_sentences_for_article(article):
    '''
    @param article - dict = {'title': str, 'text': str}
    @return - list of str = sentences, 1st would be article title
    '''
    sentence_list = [article['title']]
    # this gives us a list of sentences
    sentence_list += nltk.sent_tokenize(article['text'])
    return sentence_list


# convert each sentence into a list of words, and lemmatize them
# https://www.machinelearningplus.com/nlp/lemmatization-examples-python/
def lemmatize_sentence_v2(sentence, pos_tagging=True, remove_stopword=True):
    '''
    given a sentence, return a list of lemmatized words
    this lemmatization use word pos tagging and also removes punctuations

    @return - list of str = word breakdowns in given sentence
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

    sentence = sentence.lower()
    filtered_word_list = []
    
    if pos_tagging:
        word_list = nltk.pos_tag(nltk.word_tokenize(sentence))
        for word, tag in word_list:
            # remove punctuations like ',' '.' '"'
            word = strip_nonalnum_re(word)

            if remove_stopword and (word in stop_words):
                continue
            if word.isnumeric() or len(word) < 2:
                continue
            filtered_word_list.append(lemmatizer.lemmatize(word, convert_pos_tag(tag)))
    else:
        word_list = nltk.word_tokenize(sentence)
        for word in word_list:
            word = strip_nonalnum_re(word)
            if remove_stopword and (word in stop_words):
                continue
            if word.isnumeric() or len(word) < 2:
                continue
            filtered_word_list.append(lemmatizer.lemmatize(word))
    
    return filtered_word_list


def get_word_breakdowns_for_article(article):
    sentences = get_sentences_for_article(article)
    sentence_words = []
    for sent in sentences:
        sentence_words.append(lemmatize_sentence_v2(sent))
    return sentence_words


def get_word_breakdowns_for_article_list(article_list):
    sentences = []
    sentence_words = []
    for article in article_list:
        sentences += get_sentences_for_article(article)
    for sent in sentences:
        sentence_words.append(lemmatize_sentence_v2(sent))
    return sentence_words