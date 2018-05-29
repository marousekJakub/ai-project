from crawler import LyricsDb
from features import BagOfWordsReducedFeatures, LyricatorFeatures, Doc2VecFeatures
from sklearn.linear_model import LinearRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC, LinearSVC
from random import random

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
}

def load_all_lyrics():
    db = LyricsDb('db.sqlite3')
    lyrics = []
    genres = []
    for genre in db.get_genres():
        l = db.get_lyrics_for_genre(genre)
        lyrics.extend(l)
        genres.extend(len(l) * [genre])
    return lyrics, genres

g_lyrics, g_genres = load_all_lyrics()

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

    feature_maker = features_class(train_lyrics)
    train_features = list(map(lambda text: feature_maker.get_features(text), train_lyrics))
    classifier = classifier_class()
    classifier.fit(train_features, train_genres)

    num_good = 0
    num_bad = 0
    for i in len(test_lyrics):
        lyrics = test_lyrics[i]
        good_genre = test_genres[i]
        predicted_genre = classifier.predict(feature_maker.get_features(lyrics))
        if good_genre == predicted_genre:
            num_good += 1
        else:
            num_bad += 1

    return num_good / (num_good + num_bad)
