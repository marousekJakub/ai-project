#!/usr/bin/env python

from crawler import LyricsDb
from features import BagOfWordsReducedFeatures, LyricatorFeatures, Doc2VecFeatures
from sklearn.linear_model import LinearRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC, LinearSVC
from sklearn.neighbors import KNeighborsClassifier
from random import random
from time import time
import pdb

g_features = {
    'lyricator': LyricatorFeatures,
    'bag_of_words': BagOfWordsReducedFeatures,
    'doc2vec': Doc2VecFeatures,
}
g_classifiers = {
    'linear': LinearRegression,
    'bayes': GaussianNB,
    'svc': SVC,
    'linear_svc': LinearSVC,
    'knn': KNeighborsClassifier,
}

def load_all_lyrics():
    db = LyricsDb('db.sqlite3')
    lyrics = []
    genres = []
    genres2num = {}
    i = 0
    for genre in db.get_genres():
        l = db.get_lyrics_for_genre(genre)
        lyrics.extend(l)
        genres.extend(len(l) * [genre])
        genres2num[genre] = i
        i += 1
        
    return lyrics, genres, genres2num

g_lyrics, g_genres, g_genre2num = load_all_lyrics()

def split_train_test(lyrics, genres):
    assert len(lyrics) == len(genres)
    train_lyrics = []
    train_genres = []
    test_lyrics = []
    test_genres = []
    for i in range(len(lyrics)):
        if random() < 0.8:
            lyr = train_lyrics
            gen = train_genres
        else:
            lyr = test_lyrics
            gen = test_genres
        lyr.append(lyrics[i])
        gen.append(genres[i])
    
    return train_lyrics, train_genres, test_lyrics, test_genres



def test(features_class, classifier_class):
    train_lyrics, train_genres, test_lyrics, test_genres = split_train_test(g_lyrics, g_genres)

    time_start = time()
    # print("making features")
    feature_maker = features_class(train_lyrics)
    train_features = list(map(lambda text: feature_maker.get_features(text), train_lyrics))
    time_features = time()

    # print("fitting classifier")
    classifier = classifier_class()
    classifier.fit(train_features, list(map(lambda gen: g_genre2num[gen], train_genres)))
    time_train = time()

    num_good = 0
    num_bad = 0
    for i in range(len(test_lyrics)):
        lyrics = test_lyrics[i]
        good_genre_num = g_genre2num[test_genres[i]]
        predicted_genre_num = int(classifier.predict([ feature_maker.get_features(lyrics) ]))
        if good_genre_num == predicted_genre_num:
            num_good += 1
        else:
            num_bad += 1
    time_predict = time()

    return num_good / (num_good + num_bad), int(time_features - time_start), int(time_train - time_features), int(time_predict - time_features)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("usage: %s lyricator|bag_of_words|doc2vec linear|bayes|svc|linear_svc|knn" % sys.argv[0])
        sys.exit(1)
    
    feature_class = g_features[sys.argv[1]]
    classifier_class = g_classifiers[sys.argv[2]]
    accuracy, time_make_features, time_training, time_prediction = test(feature_class, classifier_class)
    print("accuracy: %d" % accuracy)
    print("time to make features: %d" % time_make_features)
    print("time of training: %d" % time_training)
    print("time of prediction: %d" % time_prediction)