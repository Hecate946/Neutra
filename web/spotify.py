from urllib.parse import urlencode

import base64
import time
import json


from web import secrets
from web import client

class CONSTANTS:
    API_URL = "https://api.spotify.com/v1/"
    AUTH_URL = "https://accounts.spotify.com/authorize"
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    SCOPES = [
        # Spotify connect
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        # Users
        "user-read-private",
        # Follow
        "user-follow-modify",
        "user-follow-read",
        # Library
        "user-library-modify",
        "user-library-read",
        # Listening history
        "user-read-playback-position",
        "user-top-read",
        "user-read-recently-played",
        # Playlists
        "playlist-modify-private",
        "playlist-read-collaborative",
        "playlist-read-private",
        "playlist-modify-public",
    ]


class Oauth:
    def __init__(self, scope=None):
        self.client_id = secrets.SPOTIFY.client_id
        self.client_secret = secrets.SPOTIFY.client_secret
        self.redirect_uri = secrets.SPOTIFY.redirect_uri
        self.scope = " ".join(CONSTANTS.SCOPES)

    @property
    def headers(self):
        """
        Return proper headers for all token requests
        """
        auth_header = base64.b64encode(
            (self.client_id + ":" + self.client_secret).encode("ascii")
        )
        return {
            "Authorization": "Basic %s" % auth_header.decode("ascii"),
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def get_auth_url(self, state):
        """
        Return an authorization url to get an access code
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": " ".join(CONSTANTS.SCOPES),
            # "show_dialog": True
        }
        constructed = urlencode(params)
        return "%s?%s" % (CONSTANTS.AUTH_URL, constructed)

    def validate_token(self, token_info):
        """Checks a token is valid"""
        now = int(time.time())
        return token_info["expires_at"] - now < 60

    async def get_access_token(self, token_info):
        """Gets the token or creates a new one if expired"""
        token_info["expires_at"] = int(time.time()) + token_info["expires_in"]
        if self.validate_token(token_info):
            return token_info["access_token"]

        token_info = await self.refresh_access_token(token_info.get("refresh_token"))

        return token_info["access_token"]

    async def refresh_access_token(self, refresh_token):
        params = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        token_info = await client.post(
            CONSTANTS.TOKEN_URL,
            data=params,
            headers=self.headers,
        )
        if not token_info.get("refresh_token"):
            # Didn't get new refresh token.
            # Old one is still valid.
            token_info["refresh_token"] = refresh_token

        return token_info

    async def request_access_token(self, code):
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        token_info = await client.post(
            CONSTANTS.TOKEN_URL,
            data=params,
            headers=self.headers,
        )
        return token_info

oauth = Oauth()

class User:  # Spotify user w discord user_id
    def __init__(self, user_id, token_info):
        self.user_id = user_id
        self.token_info = token_info

    @classmethod
    async def load(cls, user_id):
        query = """
                SELECT token_info
                FROM spotify_auth
                WHERE user_id = $1;
                """
        token_info = await client.cxn.fetchval(query, int(user_id))

        if token_info:
            token_info = json.loads(token_info)

        return cls(user_id, token_info)

    async def get(self, url):
        access_token = await oauth.get_access_token(self.token_info)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        return await client.get(url, headers=headers)

    async def get_profile(self):
        return await self.get(CONSTANTS.API_URL + "me")
        
    async def get_currently_playing(self):
        return await self.get(CONSTANTS.API_URL + "me/player/currently-playing")

    async def get_recently_played(self, limit=50):
        params = {"limit": limit}
        query_params = urlencode(params)
        return await self.get(CONSTANTS.API_URL + "me/player/recently-played?" + query_params)

    async def get_top_tracks(self, limit=50, time_range="long_term"): 
        params = {"limit": limit, "time_range": time_range}
        query_params = urlencode(params)
        return await self.get(CONSTANTS.API_URL + "me/top/tracks?" + query_params)

    async def get_top_artists(self, limit=50, time_range="long_term"):
        params = {"limit": limit, "time_range": time_range}
        query_params = urlencode(params)
        return await self.get(CONSTANTS.API_URL + "me/top/artists?" + query_params)

    async def get_top_albums(self, limit=50):
        params = {"limit": limit}
        query_params = urlencode(params)
        return await self.get(CONSTANTS.API_URL + "me/albums?" + query_params)