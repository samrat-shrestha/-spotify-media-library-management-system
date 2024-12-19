# spotify-media-library-management-system

Generates similar songs based on your current top tracks and adds them to your Spotify playlist.
Automatically creates and updates a playlist with your current top tracks on Spotify.

## Prerequisites

- Python 3.8 or higher
- A Spotify account
- [Registered Spotify Application](https://developer.spotify.com/dashboard)

## Setup

1. **Clone the repository**   ```bash
   git clone <your-repository-url>
   cd <repository-name>   ```

2. **Create and activate a virtual environment**   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate   ```

3. **Install dependencies**   ```bash
   pip install -r requirements.txt   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory with the following variables:   ```
   FLASK_SECRET_KEY=your_secret_key_here
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIFY_REDIRECT_URI=http://localhost:5000/redirect
   OPENAI_API_KEY=your_openai_key
   PORT=5000   ```

6. **Configure Spotify Application**
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new application
   - Add `http://localhost:5000/redirect` to the Redirect URIs in your Spotify app settings
   - Copy your Client ID and Client Secret to the `.env` file

## Running the Application

1. **Start the Flask server**   ```bash
   python app.py   ```

2. **Access the application**
   - Open your web browser and go to `http://localhost:5000`
   - Log in with your Spotify account
   - The application will automatically create/update a playlist called "Saved Top Tracks Weekly"
   - Generating songs is on '/generate' endpoint `http://localhost:5000/generate`

## Features

- Creates a playlist of your top tracks if it doesn't exist
- Updates the playlist weekly with your current top tracks
- Clears previous tracks before adding new ones to prevent duplicates
- Secure authentication using Spotify OAuth
- Generated similar songs based on your top tracks list.

## Environment Variables

- `FLASK_SECRET_KEY`: Secret key for Flask sessions
- `SPOTIFY_CLIENT_ID`: Your Spotify application client ID
- `SPOTIFY_CLIENT_SECRET`: Your Spotify application client secret
- `SPOTIFY_REDIRECT_URI`: The redirect URI (default: http://localhost:5000/redirect)
- `OPENAI_API_KEY`: OPENAI API key for connecting with OPENAI
- `PORT`: The port number for the Flask server (default: 5000)
