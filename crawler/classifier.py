#!/usr/bin/env python

from crawler import LyricsDb
from features import BagOfWordsReducedFeatures50, BagOfWordsReducedFeatures100, BagOfWordsReducedFeatures200, LyricatorFeatures, Doc2VecFeatures50, Doc2VecFeatures100, Doc2VecFeatures200
from sklearn.linear_model import LinearRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC, LinearSVC
from sklearn.neighbors import KNeighborsClassifier
from random import random
from time import time
import pdb

g_features = {
    'lyricator': LyricatorFeatures,
    'bag_of_words_50': BagOfWordsReducedFeatures50,
    'bag_of_words_100': BagOfWordsReducedFeatures100,
    'bag_of_words_200': BagOfWordsReducedFeatures200,
    'doc2vec_50': Doc2VecFeatures50,
    'doc2vec_100': Doc2VecFeatures100,
    'doc2vec_200': Doc2VecFeatures200,
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
    num2genre = []
    i = 0
    for genre in db.get_genres():
        l = db.get_lyrics_for_genre(genre)
        lyrics.extend(l)
        genres.extend(len(l) * [genre])
        genres2num[genre] = i
        num2genre.append(genre)
        i += 1
        
    return lyrics, genres, genres2num, num2genre

g_lyrics, g_genres, g_genre2num, g_num2genre = load_all_lyrics()

def split_train_test(lyrics, genres):
    assert len(lyrics) == len(genres)
    train_lyrics = []
    train_genres = []
    test_lyrics = []
    test_genres = []
    for i in range(len(lyrics)):
        r = random()
        if r < 0.8:
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
    good_predict_matrix = {}
    for i in range(len(test_lyrics)):
        lyrics = test_lyrics[i]
        good_genre_num = g_genre2num[test_genres[i]]
        predicted_genre_num = int(classifier.predict([ feature_maker.get_features(lyrics) ]))
        good_genre = test_genres[i]
        predicted_genre = g_num2genre[predicted_genre_num] if 0 <= predicted_genre_num < len(g_num2genre) else "out-of-range"
        if good_genre_num == predicted_genre_num:
            num_good += 1
        else:
            num_bad += 1
        
        key = (good_genre, predicted_genre)
        if key in good_predict_matrix:
            good_predict_matrix[key] += 1
        else:
            good_predict_matrix[key] = 1

    time_predict = time()
    for key in good_predict_matrix.keys():
        good_predict_matrix[key]  /=  num_good + num_bad
    return num_good / (num_good + num_bad), int(time_features - time_start), int(time_train - time_features), int(time_predict - time_features), good_predict_matrix

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("usage: %s %s %s" % (sys.argv[0], "|".join(g_features.keys()), "|".join(g_classifiers.keys())))
        sys.exit(1)
    
    feature_class = g_features[sys.argv[1]]
    classifier_class = g_classifiers[sys.argv[2]]
    accuracy, time_make_features, time_training, time_prediction, good_predict_matrix = test(feature_class, classifier_class)
    print("accuracy: %f" % accuracy)
    print("time to make features: %d" % time_make_features)
    print("time of training: %d" % time_training)
    print("time of prediction: %d" % time_prediction)
    print("good-predict matrix:")
    for key, value in good_predict_matrix.items():
        good, predicted = key
        print("  good=%s predicted=%s: %f" % (good, predicted, value))
