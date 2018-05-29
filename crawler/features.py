import execnet
import stop_words
from gensim import corpora, models
from gensim.models.doc2vec import TaggedDocument

g_stop_words = set(stop_words.get_stop_words('en'))
def filter_stop_words(texts):
    filter_text = lambda text: list(filter(lambda w: w not in g_stop_words, text))
    return list(map(filter_text, texts))

class LyricatorFeatures:
    def __init__(self, texts):
        pass
    
    def get_features(self, lyrics):
        feats = self.call_python_version('2.7', 'lyricator', 'run_emotuslite', (" ".join(lyrics),))
        if len(feats) == 0:
            feats = [0, 0, 0]
        return list(enumerate(feats))

    def call_python_version(self, Version, Module, Function, ArgumentList):
        gw      = execnet.makegateway("popen//python=python%s" % Version)
        channel = gw.remote_exec("""
            from %s import %s as the_function
            channel.send(the_function(*channel.receive()))
        """ % (Module, Function))
        channel.send(ArgumentList)
        return channel.receive()


class BagOfWordsFeatures:
    def __init__(self, texts):
        ''' texts: list of lists of words '''
        self._stop_words = set(stop_words.get_stop_words('en'))
        self._dictionary = corpora.Dictionary(filter_stop_words(texts))
        self._corpus = list(map(lambda text: self._dictionary.doc2bow(text), texts))
        self._if_idf = models.TfidfModel(self._corpus)
    
    def get_features(self, lyrics):
        ''' lyrics: list of words '''

        f = self._if_idf[ self._dictionary.doc2bow(lyrics) ]
        assert len(f) > 0
        return f

class BagOfWordsReducedFeatures:
    def __init__(self, texts):
        self._bow = BagOfWordsFeatures(texts)
        self._lsi = models.LsiModel(self._bow._if_idf[self._bow._corpus], num_topics=100)
    
    def get_features(self, lyrics):
        return self._lsi[self._bow.get_features(lyrics)]
    

class Doc2VecFeatures:
    def __init__(self, texts):
        texts = filter_stop_words(texts)
        self._model = models.Doc2Vec(list(map(lambda pair: TaggedDocument(pair[1], (pair[0],) ), enumerate(texts))))
    
    def get_features(self, lyrics):
        lyrics = list(filter(lambda word: word in self._model.wv, lyrics))
        avg = sum(map(lambda word: self._model.wv[word], lyrics)) / len(lyrics)
        return list(enumerate(list(avg)))

if __name__ == '__main__':
    import crawler
    db = crawler.LyricsDb('db.sqlite3')
    lyr = db.get_lyrics_for_genre('metal')
