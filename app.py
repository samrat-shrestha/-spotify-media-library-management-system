import os
import time
from typing import Dict, Optional
from functools import wraps

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect
from dotenv import load_dotenv
import logging
from openai import OpenAI
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'
app.secret_key = os.getenv('FLASK_SECRET_KEY')
TOKEN_INFO = 'token_info'

# Spotify Configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
SPOTIFY_SCOPE = 'user-library-read user-top-read playlist-modify-public playlist-modify-private'

#OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token_info = get_token()
            if not token_info:
                logger.warning("User not logged in, redirecting to login")
                return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Error in login check: {str(e)}")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def login():
    try:
        auth_url = create_spotify_oauth().get_authorize_url()
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return "An error occurred during login", 500

@app.route('/redirect')
def redirect_page():
    try:
        session.clear()
        code = request.args.get('code')
        token_info = create_spotify_oauth().get_access_token(code)
        session[TOKEN_INFO] = token_info
        return redirect(url_for('save_playlist', _external=True))
    except Exception as e:
        logger.error(f"Error during redirect: {str(e)}")
        return "An error occurred during authentication", 500

@app.route('/savePlaylist')
@login_required
def save_playlist():
    try:
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])
        
        user_id = sp.current_user()['id']
        playlist_id = get_or_create_playlist(sp, user_id)
        
        if not playlist_id:
            return "Failed to create/find playlist", 500

        update_playlist_tracks(sp, user_id, playlist_id)
        return "Songs Added in Playlist", 200
    
    except Exception as e:
        logger.error(f"Error saving playlist: {str(e)}")
        return "An error occurred while saving the playlist", 500

def get_or_create_playlist(sp: spotipy.Spotify, user_id: str) -> Optional[str]:
    """Get existing playlist ID or create new one."""
    try:
        current_playlists = sp.current_user_playlists()['items']
        for playlist in current_playlists:
            if playlist['name'] == "Saved Top Tracks Weekly":
                return playlist['id']

        # Create new playlist if not found
        new_playlist = sp.user_playlist_create(
            user_id,
            'Saved Top Tracks Weekly',
            public=True,
            description="Weekly updated playlist of my top tracks"
        )
        return new_playlist['id']
    except Exception as e:
        logger.error(f"Error in get_or_create_playlist: {str(e)}")
        return None

def update_playlist_tracks(sp: spotipy.Spotify, user_id: str, playlist_id: str) -> None:
    """Update playlist with current top tracks."""
    try:
        # Clear existing tracks
        sp.playlist_replace_items(playlist_id, [])
        
        # Get and add new tracks
        current_user_top_tracks = sp.current_user_top_tracks()['items']
        song_uris = [song['uri'] for song in current_user_top_tracks]
        sp.user_playlist_add_tracks(user_id, playlist_id, song_uris)
    except Exception as e:
        logger.error(f"Error in update_playlist_tracks: {str(e)}")
        raise

@app.route('/logout')
def logout():
    try:
        session.clear()
        return "Successfully logged out", 200
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return "An error occurred during logout", 500
    
@app.route('/generate')
def generate():
    try:
        # Get Spotify tracks
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])
        
        # Fetch user's top tracks
        top_tracks = sp.current_user_top_tracks(limit=20)['items']
        
        # Create a formatted list of track and artist information
        tracks_info = []
        for track in top_tracks:
            artists = ", ".join([artist['name'] for artist in track['artists']])
            track_info = f"{track['name']} by {artists}"
            tracks_info.append(track_info)
        
        # Format tracks for OpenAI prompt
        tracks_string = "\n".join(tracks_info)
        
        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful music expert analyzing someone's top tracks. You must respond only with valid JSON containing song recommendations in the format: [{'song': 'Song Name', 'artist': 'Artist Name'}, ...]. Do not include any additional text or markdown formatting."},
                {"role": "user", "content": f"Based on these tracks, generate 10 song recommendations:\n\n{tracks_string}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Extract the response
        ai_response = response.choices[0].message.content
        
        # Parse the JSON response
        recommended_songs = json.loads(ai_response)
        
        # Get current user's playlists
        current_user_id = sp.current_user()['id']
        playlists = sp.current_user_playlists()
        playlist_id = None
        
        # Check if "Similar Songs Weekly" already exists
        for playlist in playlists['items']:
            if playlist['name'] == "Similar Songs Weekly":
                playlist_id = playlist['id']
                break
        
        # print("PLAYLIST:",playlist_id)
        # Create new playlist if it doesn't exist
        if not playlist_id:
            playlist = sp.user_playlist_create(
                user=current_user_id,
                name="Similar Songs Weekly",
                public=True,
                description="AI-generated recommendations based on your top tracks"
            )
            playlist_id = playlist['id']
            playlist_url = playlist['external_urls']['spotify']
        else:
            playlist = sp.playlist(playlist_id)
            playlist_url = playlist['external_urls']['spotify']
            sp.playlist_replace_items(playlist_id, [])
        
        # Search and add each recommended song
        track_uris = []
        for index, song in enumerate(recommended_songs, 1):
            search_query = f"track:{song['song']} artist:{song['artist']}"
            logger.info(f"[{index}/10] Searching for: {song['song']} by {song['artist']}")
            
            search_results = sp.search(q=search_query, type='track', limit=1)
            
            if search_results['tracks']['items']:
                track_uri = search_results['tracks']['items'][0]['uri']
                track_name = search_results['tracks']['items'][0]['name']
                artist_name = search_results['tracks']['items'][0]['artists'][0]['name']
                track_uris.append(track_uri)
                logger.info(f"✓ Found track: {track_name} by {artist_name}")
            else:
                logger.warning(f"✗ Could not find: {song['song']} by {song['artist']}")
        
        # Add all found tracks to the playlist
        if track_uris:
            logger.info(f"Adding {len(track_uris)} tracks to playlist 'Similar Songs Weekly'")
            sp.playlist_add_items(playlist_id, track_uris)
            logger.info("Successfully added tracks to playlist")
        else:
            logger.warning("No tracks were found to add to the playlist")
        
        return {
            "similar_songs": ai_response,
            "playlist_id": playlist_id,
            "playlist_url": playlist_url
        }, 200
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing AI response: {str(e)}")
        return "Invalid response format from AI", 500
    except Exception as e:
        logger.error(f"Error generating track list: {str(e)}")
        return "An error occurred while generating track list", 500

def get_token() -> Optional[Dict]:
    """Get and refresh token if necessary."""
    try:
        token_info = session.get(TOKEN_INFO, None)
        if not token_info:
            return None

        now = int(time.time())
        is_expired = token_info['expires_at'] - now < 60
        
        if is_expired:
            spotify_oauth = create_spotify_oauth()
            token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
            session[TOKEN_INFO] = token_info
        
        return token_info
    except Exception as e:
        logger.error(f"Error in get_token: {str(e)}")
        return None

def create_spotify_oauth() -> SpotifyOAuth:
    """Create SpotifyOAuth instance."""
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=url_for(SPOTIFY_REDIRECT_URI, _external=True),
        scope=SPOTIFY_SCOPE
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
