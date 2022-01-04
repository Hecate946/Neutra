from urllib.parse import urlencode
import time
from config import DISCORD
from core import bot as client

class CONSTANTS:
    API_URL = "https://discord.com/api"
    AUTH_URL = "https://discord.com/api/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"
    SCOPES = [
        "guilds",
        "guilds.join",
        "identify",
    ]


class Oauth:
    API_URL = "https://discord.com/api"
    AUTH_URL = "https://discord.com/api/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"

    def __init__(self, scope=None):
        self.client_id = DISCORD.client_id
        self.client_secret = DISCORD.client_secret
        self.redirect_uri = DISCORD.redirect_uri
        self.scope = " ".join(CONSTANTS.SCOPES)

    def get_auth_url(self, scope=None):
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope or self.scope,
            "prompt": "none", # "consent" to force them to agree again
        }
        query_params = urlencode(params)
        return "%s?%s" % (self.AUTH_URL, query_params)

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
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        token_info = await client.post(
            CONSTANTS.TOKEN_URL, data=params, headers=self.headers, res_method="json"
        )
        if not token_info.get("refresh_token"):
            # Didn't get new refresh token.
            # Old one is still valid.
            token_info["refresh_token"] = refresh_token

        return token_info

    async def request_access_token(self, code):
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "scope": self.scope,
            "code": code,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        token_info = await client.post(
            CONSTANTS.TOKEN_URL, data=params, headers=headers, res_method="json"
        )
        return token_info

    async def get_user_data(self, access_token):

        headers = {"Authorization": f"Bearer {access_token}"}

        user_data = await client.get(
            url=self.API_URL + "/users/@me", headers=headers, res_method="json"
        )
        return user_data



oauth = Oauth()