# RENAME THIS FILE TO "secrets.py"
BASE_WEB_URL = "http://localhost:3000/" # YOUR REDIRECT URI

class DISCORD(object):
    # Go here: https://discord.com/developers/applications
    # Go to the oauth tab and copy the client ID and client secret
    # Then add a redirect uri. Ex: http://localhost:3000/discord_login
    client_id = "DISCORD CLIENT ID HERE" # Same as bot ID
    client_secret = "DISCORD CLIENT SECRET HERE"
    redirect_uri = BASE_WEB_URL + "discord_login"

class SPOTIFY(object):
    # Make an app here: https://developer.spotify.com/dashboard/login
    # Add the client secret and client ID here.
    # Then click "edit settings" and add a redirect uri. Ex: http://localhost:3000/spotify_login
    client_id = "SPOTIFY CLIENT ID HERE"
    client_secret = "SPOTIFY CLIENT SECRET HERE"
    redirect_uri = BASE_WEB_URL + "spotify_login"

class POSTGRES(object):
    # Use same database as bot
    user = "postgres"
    password = "your database password"
    host = "your host IP or localhost"
    port = 5432 # Default port number
    name = "your database name"
    uri = f"postgres://{user}:{password}@{host}:{port}/{name}"