from urllib.parse import urlencode
import time
import json
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
        "email",
    ]


class Oauth:
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
            "prompt": "none",  # "consent" to force them to agree again
        }
        query_params = urlencode(params)
        return "%s?%s" % (CONSTANTS.AUTH_URL, query_params)

    def validate_token(self, token_info):
        """Checks a token is valid"""
        now = int(time.time())
        return token_info["expires_at"] - now > 60

    async def get_access_token(self, user):
        """Gets the token or creates a new one if expired"""
        if self.validate_token(user.token_info):
            return user.token_info["access_token"]

        user.token_info = await self.refresh_access_token(
            user.user_id, user.token_info.get("refresh_token")
        )

        return user.token_info["access_token"]

    async def refresh_access_token(self, user_id, refresh_token):
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        token_info = await client.post(
            CONSTANTS.TOKEN_URL, data=params, headers=headers, res_method="json"
        )
        token_info["expires_at"] = int(time.time()) + token_info["expires_in"]

        query = """
                INSERT INTO discord_auth
                VALUES ($1, $2)
                ON CONFLICT (user_id)
                DO UPDATE SET token_info = $2
                WHERE discord_auth.user_id = $1;
                """
        await client.cxn.execute(query, user_id, json.dumps(token_info))

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
        token_info["expires_at"] = int(time.time()) + token_info["expires_in"]
        return token_info

    async def identify(self, access_token):

        headers = {"Authorization": f"Bearer {access_token}"}

        user_data = await client.get(
            url=CONSTANTS.API_URL + "/users/@me", headers=headers, res_method="json"
        )
        return user_data


oauth = Oauth()


class User:  # Discord user operations with scopes
    def __init__(self, token_info, user_id):
        self.token_info = token_info
        self.user_id = user_id

    @classmethod
    async def from_id(cls, user_id):
        query = """
                SELECT token_info
                FROM discord_auth
                WHERE user_id = $1;
                """
        token_info = await client.cxn.fetchval(query, int(user_id))

        if token_info:
            token_info = json.loads(token_info)
            return cls(token_info, user_id)

    @classmethod
    async def from_token(cls, token_info):
        user_data = await oauth.identify(token_info.get("access_token"))
        user_id = int(user_data.get("id"))
        query = """
                INSERT INTO discord_auth
                VALUES ($1, $2)
                ON CONFLICT (user_id)
                DO UPDATE SET token_info = $2
                WHERE discord_auth.user_id = $1;
                """
        await client.cxn.execute(query, user_id, json.dumps(token_info))

        return cls(token_info, user_id)

    async def get(self, url, *, access_token=None):
        access_token = access_token or await oauth.get_access_token(self)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        return await client.get(url, headers=headers, res_method="json")

    async def identify(self):
        return await self.get(CONSTANTS.API_URL + "/users/@me")

    async def get_guilds(self):
        return await self.get(CONSTANTS.API_URL + "/users/@me/guilds")

    async def join_guild(self, guild_id):
        access_token = await oauth.get_access_token(self)

        params = {"access_token": access_token}
        headers = {
            "Authorization": f"Bot {DISCORD.token}",
        }
        return await client.put(
            CONSTANTS.API_URL + f"/guilds/{guild_id}/members/{self.user_id}",
            headers=headers,
            json=params,
        )
