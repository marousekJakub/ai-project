import execnet

class LyricatorFeatures:
    def __init__(self):
        pass
    
    def get_features(self, lyrics):
        feats = self.call_python_version('2.7', 'lyricator', 'run_emotuslite', (" ".join(lyrics),))
        assert len(feats) == 3
        return list(enumerate(feats))

    def call_python_version(self, Version, Module, Function, ArgumentList):
        gw      = execnet.makegateway("popen//python=python%s" % Version)
        channel = gw.remote_exec("""
            from %s import %s as the_function
            channel.send(the_function(*channel.receive()))
        """ % (Module, Function))
        channel.send(ArgumentList)
        return channel.receive()


