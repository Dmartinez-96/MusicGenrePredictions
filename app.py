from flask import Flask, redirect, request, session, jsonify, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import librosa
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

SPOTIPY_CLIENT_ID = 'PUT YOUR SPOTIFY CLIENT ID HERE'
SPOTIPY_CLIENT_SECRET = 'PUT YOUR SPOTIFY CLIENT SCRET HERE'
SPOTIPY_REDIRECT_URI = 'http://localhost:8888/callback'

os.environ['SPOTIPY_CLIENT_ID'] = SPOTIPY_CLIENT_ID
os.environ['SPOTIPY_CLIENT_SECRET'] = SPOTIPY_CLIENT_SECRET
os.environ['SPOTIPY_REDIRECT_URI'] = SPOTIPY_REDIRECT_URI

sp_oauth = SpotifyOAuth(scope="playlist-read-private user-library-read")

@app.route('/')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect('/getTopTracks')

@app.route('/getTopTracks')
def get_track():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    genre_playlists = {
        'pop': '1WH6WVBwPBz35ZbWsgCpgr',
        'rock': '7DgPQwzEoUVfQYBiMLER9Z',
        'hip-hop': '02okEcUQXHe2sS5ajE9XG0',
        'country': '2Hi4RV1DJHHiSDcwYFFKeR',
        'metal': '1yMlpNGEpIVUIilZlrbdS0',
        'classical': '2AIyLES2xJfPa6EOxmKySl'
    }
    
    tracks_data = []
    for genre, playlist_id in genre_playlists.items():
        playlist_tracks = sp.playlist_tracks(playlist_id, limit=100)
        
        for item in playlist_tracks['items']:
            track = item['track']
            track_id = track['id']
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            
            # Get audio features
            audio_features = sp.audio_features(track_id)[0]
            
            track_data = {
                'genre': genre,
                'track_id': track_id,
                'track_name': track_name,
                'artist_name': artist_name,
                'tempo': audio_features['tempo'],
                'danceability': audio_features['danceability'],
                'energy': audio_features['energy'],
                'acousticness': audio_features['acousticness'],
                'duration_ms': audio_features['duration_ms'],
                'instrumentalness': audio_features['instrumentalness'],
                'liveness': audio_features['liveness'],
                'loudness': audio_features['loudness'],
                'mode': audio_features['mode'],
                'speechiness': audio_features['speechiness'],
                'time_signature': audio_features['time_signature'],
                'valence': audio_features['valence']
            }
            tracks_data.append(track_data)
    df = pd.DataFrame(tracks_data)
    df.to_csv('tracks_data.csv', index=False)
    
    return jsonify(tracks_data)

if __name__ == '__main__':
    app.run(port=8888)
    