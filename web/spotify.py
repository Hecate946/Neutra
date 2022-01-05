from urllib.parse import urlencode

import base64
import time
import json


from config import SPOTIFY
from web import client


class CONSTANTS:
    WHITE_ICON = "https://cdn.discordapp.com/attachments/872338764276576266/927649624888602624/spotify_white.png"
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
        self.client_id = SPOTIFY.client_id
        self.client_secret = SPOTIFY.client_secret
        self.redirect_uri = SPOTIFY.redirect_uri
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
            "Content-Type": "application/x-www-form-urlencoded",
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

    async def get_access_token(self, user_id, token_info):
        """Gets the token or creates a new one if expired"""
        token_info["expires_at"] = int(time.time()) + token_info["expires_in"]
        if self.validate_token(token_info):
            return token_info["access_token"]

        token_info = await self.refresh_access_token(user_id, token_info.get("refresh_token"))

        return token_info["access_token"]

    async def refresh_access_token(self, user_id, refresh_token):
        params = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        token_info = await client.post(
            CONSTANTS.TOKEN_URL, data=params, headers=self.headers, res_method="json"
        )
        if not token_info.get("refresh_token"):
            # Didn't get new refresh token.
            # Old one is still valid.
            token_info["refresh_token"] = refresh_token

        query = """
                INSERT INTO spotify_auth
                VALUES ($1, $2)
                ON CONFLICT (user_id)
                DO UPDATE SET token_info = $2
                WHERE spotify_auth.user_id = $1;
                """
        await client.cxn.execute(query, user_id, json.dumps(token_info))

        return token_info

    async def request_access_token(self, code):
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        token_info = await client.post(
            CONSTANTS.TOKEN_URL, data=params, headers=self.headers, res_method="json"
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

    async def auth(self):
        access_token = await oauth.get_access_token(self.user_id, self.token_info)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        return headers

    async def get(self, url):
        return await client.get(url, headers=await self.auth())

    async def put(self, url, json=None, res_method=None):
        return await client.put(url, headers=await self.auth(), json=json, res_method=res_method)

    async def get_profile(self):
        return await self.get(CONSTANTS.API_URL + "me")

    async def get_playback_state(self):
        return await self.get(CONSTANTS.API_URL + "me/player")

    async def get_currently_playing(self):
        return await self.get(CONSTANTS.API_URL + "me/player/currently-playing")

    async def get_devices(self):
        return await self.get(CONSTANTS.API_URL + "me/player/devices")

    async def transfer_playback(self, devices, play: bool = False):
        return await self.put(CONSTANTS.API_URL + "me/player", json={"device_ids": devices, "play": play})

    async def get_recently_played(self, limit=50):
        params = {"limit": limit}
        query_params = urlencode(params)
        return await self.get(
            CONSTANTS.API_URL + "me/player/recently-played?" + query_params
        )

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

    async def pause(self):
        return await self.put(CONSTANTS.API_URL + "me/player/pause")

    async def play(self, **kwargs):
        return await self.put(CONSTANTS.API_URL + "me/player/play", json=kwargs)

    async def play(self, **kwargs):
        return await self.put(CONSTANTS.API_URL + "me/player/play", json=kwargs)

    async def skip_to_next(self):
        return await client.post(CONSTANTS.API_URL + "me/player/next", headers=await self.auth(), res_method=None)

    async def skip_to_previous(self):
        return await client.post(CONSTANTS.API_URL + "me/player/previous", headers=await self.auth(), res_method=None)

    async def seek(self, position):
        params = {"position_ms": position * 1000}
        query_params = urlencode(params)
        return await self.put(CONSTANTS.API_URL + "me/player/seek?" + query_params)

    async def repeat(self, option):
        params = {"state": option}
        query_params = urlencode(params)
        return await self.put(CONSTANTS.API_URL + "me/player/repeat?" + query_params)

    async def shuffle(self, option: bool):
        params = {"state": option}
        query_params = urlencode(params)
        return await self.put(CONSTANTS.API_URL + "me/player/shuffle?" + query_params)

    async def volume(self, amount):
        params = {"volume_percent": amount}
        query_params = urlencode(params)
        return await self.put(CONSTANTS.API_URL + "me/player/volume?" + query_params)

    async def enqueue(self, uri):
        params = {"uri": uri}
        query_params = urlencode(params)
        return await client.post(CONSTANTS.API_URL + "me/player/queue?" + query_params, headers=await self.auth(), res_method=None)
