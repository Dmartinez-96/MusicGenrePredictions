from flask import Flask, redirect, request, session, jsonify, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import pandas as pd
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def get_audio_features_with_retries(sp, track_id, max_retries=10, base_sleep_time=1):
    retries = 0
    while retries < max_retries:
        try:
            audio_features = sp.audio_features(track_id)[0]
            return audio_features
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', base_sleep_time * (2 ** retries)))
                logger.warning(f"Rate limited. Retrying in {retry_after} seconds... (Retry {retries + 1}/{max_retries})")
                time.sleep(retry_after)
                retries += 1
            else:
                logger.error(f"Failed to fetch audio features for track ID {track_id}: {e}")
                break
    logger.error(f"Max retries exceeded for track ID {track_id}")
    return None

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
        'classical': '2AIyLES2xJfPa6EOxmKySl',
        'jazz': '6ylvGA8NeX2CuaeGtwHWDJ',
        'electronic': '2e3dcRuo9uDH6qD3NOGKAL',
        'rap': '041EEjr8FMkWlzbuKnSXYD'
    }
    
    tracks_data = []
    for genre, playlist_id in genre_playlists.items():
        playlist_tracks = sp.playlist_tracks(playlist_id, limit=100)
        
        for item in playlist_tracks['items']:
            track = item['track']
            track_id = track['id']
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            
            # Get audio features with retries
            audio_features = get_audio_features_with_retries(sp, track_id)
            if not audio_features:
                logger.error(f"Skipping track ID {track_id} due to errors")
                continue
            
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
            # Add a delay between requests to manage rate limit
            time.sleep(1)  # Sleep for 1 second between requests
    
    df = pd.DataFrame(tracks_data)
    df.to_csv('tracks_data.csv', index=False)
    
    return jsonify(tracks_data)

if __name__ == '__main__':
    app.run(port=8888)
