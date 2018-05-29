#!/usr/bin/python3

import requests
from lxml import html
from urllib.parse import urljoin
import re
from logging import warning, error, info, debug
import logging
import sqlite3
from gwa_spotify_api import SpotifyAPI
import os

def get_tree(url):
    try:
        debug('Getting url %s', url)
        rq = requests.get(url, headers={ 'User-Agent': 'Mo4) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/65.0.3325.181 Chrome/65.0.3325.181'})
        assert rq.ok
        return html.fromstring(rq.content)
    except Exception as e:
        error('Cannot get url %s: %s', url, e)

def map_text(elements):
    return list(map(lambda x: x.text_content(), elements))

def musicbrains_get_artists(genre):
    tr = get_tree('https://musicbrainz.org/tag/%s/artist' % genre)
    return map_text(tr.xpath('//h2/following-sibling::ul//a/bdi'))

def azlyrics_get_artist_urls(artist):
    tr = get_tree('https://search.azlyrics.com/search.php?q=%s' % artist)
    return list(tr.xpath('//div[@class="panel"][1]/table//a/@href'))

def azlyrics_get_lyrics_urls(artist_url):
    tr = get_tree(artist_url)
    href_rel = tr.xpath('//div[@id="listAlbum"]//a/@href')
    return list(map(lambda x: urljoin(artist_url, x), href_rel))

def azlyrics_get_lyrics(lyrics_url):
    tr = get_tree(lyrics_url)
    name = tr.xpath('//div[@class="ringtone"]/following-sibling::b')[0].text_content()[1:-1]
    lyrics = tr.xpath('//div[@class="ringtone"]/following-sibling::div')[0].text_content()
    return (name, lyrics)

g_spotify_client_id = '8bffc1073b7749f8852dfa53237a4017'
g_spotify_client_secret = '4a9bb562ee8d40e9a85b3bd893b6bda3'
os.environ['SPOTIFY_CLIENT_ID'] = g_spotify_client_id
os.environ['SPOTIFY_CLIENT_SECRET'] = g_spotify_client_secret
g_spotify = SpotifyAPI()

def spotify_get_popular_songs(artist):
    
    # 1. search for artists by name
    ax = g_spotify.get('search', { 'q': artist, 'type': 'artist' })
    ax = ax['artists']['items']
    if len(ax) == 0:
        return None

    max_followers = max(map(lambda x: x['followers']['total'], ax))
    max_artist_id = None
    for x in ax:
        if x['followers']['total'] == max_followers:
            max_artist_id = x['id']
    if max_artist_id is None:
        return None
    
    # 2. get the tracks
    params = { 'country': 'us' }
    top = g_spotify.get('artists/%s/top-tracks' % max_artist_id, params)
    return list(map(lambda x: x['name'], top['tracks']))

g_token = 'GFG-NUbg5JKgbEWv8ecGLZhAcdz-FI_PfnIbYohvqmTdMHHn_PXxh8eKKrOPxbDm'

def genius_get_lyrics_path(artist, song):
    full_search = genius_get_lyrics_path2(artist, song)
    if full_search is not None:
        return full_search
    
    # sometimes, the song contains a note behind the '-' characted, like 'Fullmoon - remastered 2007'
    # if the search did not succeed, try it without the note
    idx = song.rfind('-')
    if idx != -1:
        return genius_get_lyrics_path2(artist, song[:idx])

def genius_get_lyrics_path2(artist, song):
    headers = { 'Authorization': 'Bearer %s' % g_token }
    songs_found = requests.get('https://api.genius.com/search', { 'q': artist+' '+song } , headers=headers).json()
    for hit in songs_found['response']['hits']:
        if hit['type'] == 'song' and hit['result']['primary_artist']['name'].lower() == artist.lower():
            return hit['result']['path']

def genius_get_lyrics(path):
    tr = get_tree('https://www.genius.com%s' % path)
    return tr.xpath('//div[@class="lyrics"]')[0].text_content()

g_re_music = re.compile(r'(^|\n)\s*Music:[^\n]*(\n|$)')
g_re_words = re.compile(r'(^|\n)\s*Words:[^\n]*(\n|$)')
g_re_notes = re.compile(r'\[[^]]*\]')
g_re_chars = re.compile(r'[^\w\s\'-]')
g_re_spaces = re.compile(r'\s+')
g_re_spaces_begin = re.compile(r'^\s+')
g_re_spaces_end = re.compile(r'\s+$')

def preprocess_lyrics(text):
    text = g_re_music.sub('', text)
    text = g_re_words.sub('', text)
    text = g_re_notes.sub('', text)
    text = g_re_chars.sub('', text)
    text = g_re_spaces_begin.sub('', text)
    text = g_re_spaces_end.sub('', text)
    text = g_re_spaces.sub(' ', text)
    return text.lower()


### LYRICS DATABASE ###

class LyricsDb:
    def __init__(self, file):
        self.conn = sqlite3.connect(file)
        self.cursor = self.conn.cursor()

    def create_database(self):
        self.conn.execute('''
            CREATE TABLE genres (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                parent_id INTEGER DEFAULT NULL
            )''')
        self.conn.execute('''
            CREATE TABLE artists (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                genre_id INTEGER NOT NULL
            )
        ''')
        self.conn.execute('''
            CREATE TABLE songs (
                id INTEGER PRIMARY KEY,
                artist_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                lyrics TEXT NOT NULL
            )
        ''')
    
    def drop_database(self):
        for t in ('genres', 'artists', 'songs'):
            self.conn.execute('DROP TABLE IF EXISTS %s' % t)
    
    def insert_genre(self, name, parent_id):
        self.cursor.execute('INSERT INTO genres (name, parent_id) VALUES (?, ?)', (name, parent_id))
        genre_id = self.cursor.lastrowid
        if parent_id is None:
            self.cursor.execute('UPDATE genres SET parent_id = ? WHERE id = ?', (genre_id, genre_id))
        return genre_id
    
    def insert_artist(self, name, genre_id):
        self.cursor.execute('INSERT INTO artists (name, genre_id) VALUES (?, ?)', (name, genre_id))
        return self.cursor.lastrowid
    
    def insert_song(self, name, lyrics, artist_id):
        self.cursor.execute('INSERT INTO songs (name, lyrics, artist_id) VALUES (?, ?, ?)', (name, lyrics, artist_id))
        return self.cursor.lastrowid
    
    def save(self):
        self.conn.commit()
    
    def sample_data(self):
        self.drop_database()
        self.create_database()
        metal = self.insert_genre('metal', None)
        power = self.insert_genre('power metal', metal)
        thrash = self.insert_genre('thrash metal', metal)

        zeppelin = self.insert_artist('Led Zeppelin', metal)
        sonata = self.insert_artist('Sonata Arctica', power)
        metallica = self.insert_artist('Metallica', thrash)

        self.insert_song('Stairway to Heaven', "there's a lady who's sure all glitters is gold and she's buying a stairway to heaven", zeppelin)
        self.insert_song('Nothing Else Matters', "so close no matter how far couldn't be much more from the heart", metallica)
        self.insert_song('Tallulah', "Remember when we used to look how sun set far away'", sonata)
        self.save()

    def get_artists(self):
        query = 'SELECT artists.id, artists.name, g1.name AS genre, g2.name AS parent_genre FROM artists JOIN genres g1 ON artists.genre_id = g1.id LEFT JOIN genres g2 ON g1.parent_id = g2.id'
        return list(self.cursor.execute(query))
    
    def get_genres(self):
        query = 'SELECT name FROM genres'
        return list(map(lambda x: x[0], self.cursor.execute(query)))
    
    def get_lyrics_for_genre(self, genre_name):
        query = 'SELECT lyrics FROM songs WHERE artist_id IN (SELECT id FROM artists WHERE genre_id IN (SELECT id FROM genres WHERE name = ?))'
        return list(map(lambda x: x[0].split(), self.cursor.execute(query, (genre_name,))))
    
    def get_songs(self):
        query = '''SELECT songs.id, songs.name AS song_name, artists.name AS artist_name, songs.lyrics, g1.name AS genre, g2.name AS parent_genre
            FROM songs
            JOIN artists ON artists.id = songs.artist_id
            JOIN genres g1 ON g1.id = artists.genre_id
            JOIN genres g2 ON g2.id = g1.parent_id
        '''
        return list(self.cursor.execute(query))
    
    def dump_lyrics(self, genre):
        query = 'SELECT lyrics FROM songs WHERE artist_id IN (SELECT id FROM artists WHERE genre_id IN (SELECT id FROM genres WHERE name=?))'
        lyrics = list(self.cursor.execute(query, (genre,)))
        return '\n'.join(list(map(lambda x: x[0], lyrics)))


### CRAWLING ###

# get list of artists, filter then so each one appears only at one genre
# and get the lyrics so one genre has no more than <limit> bands and for one
# band, no more than <limit> lyrics is selected
# save everything to the database
def crawle_genres(db: LyricsDb, genres, limit_lyrics_for_genre, limit_lyrics_for_artist):
    # db.drop_database()
    # db.create_database()
    artists_by_genre = get_singlegenre_artists(genres, limit_lyrics_for_genre)
    for genre in genres:
        genre_id = db.insert_genre(genre, None)
        for artist in artists_by_genre[genre]:

            songs = get_songs_for_artist(artist, limit_lyrics_for_artist)
            if len(songs) > 0:
                info('Inserting data of artist %s (%s)', artist, genre)
                artist_id = db.insert_artist(artist, genre_id)
                for (song_name, song_lyrics) in songs:
                    info('Inserting song %s', song_name)
                    db.insert_song(song_name, song_lyrics, artist_id)
                db.save()
            else:
                info('Artist %s not inserted', artist)

# for each genre in the list of genres, return <limit> artists which appear only for this genre
def get_singlegenre_artists(genres, limit):
    ag = {}
    a = {}
    for genre in genres:
        ag[genre] = musicbrains_get_artists(genre)
        for artist in ag[genre]:
            a.setdefault(artist, 0)
            a[artist] += 1
    
    filtered_ag = {}
    for genre in genres:
        filtered_ag[genre] = []
        for artist in ag[genre]:
            if a[artist] == 1 and len(filtered_ag[genre]) < limit:
                filtered_ag[genre].append(artist)
    
    return filtered_ag

# for a given artist, randomly select not more than <limit> songs and return their names and preprocessed lyrics
def get_songs_for_artist(artist, limit):
    info('Getting songs for artist %s' % artist)
    top_songs = spotify_get_popular_songs(artist)
    if top_songs is None:
        warning('Could not find popular songs for artist %s', artist)
        return []
    
    lyr_songs = []
    for song in top_songs:
        if len(lyr_songs) >= limit:
            break

        info('Getting lyrics for %s (%s)' % (song, artist))
        lyr_path = genius_get_lyrics_path(artist, song)
        if lyr_path is None:
            warning('Could not find lyrics for %s (%s)' % (song, artist))
            continue
        lyrics = preprocess_lyrics(genius_get_lyrics(lyr_path))
        lyr_songs.append((song, lyrics))
    return lyr_songs

if __name__ == '__main__':
   db = LyricsDb('db.sqlite3')
