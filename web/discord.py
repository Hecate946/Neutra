from urllib.parse import urlencode

from web import client
from web import secrets

class CONSTANTS:
    API_URL = "https://discord.com/api"
    AUTH_URL = "https://discord.com/api/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"
    SCOPES = [
        "guilds",
        "guilds.members.read",
        "identify",
    ]
class Oauth:
    API_URL = "https://discord.com/api"
    AUTH_URL = "https://discord.com/api/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"
    def __init__(self, scope=None):
        self.client_id = secrets.DISCORD.client_id
        self.client_secret = secrets.DISCORD.client_secret
        self.redirect_uri = secrets.DISCORD.redirect_uri
        self.scope = " ".join(CONSTANTS.SCOPES)


    def get_auth_url(self, scope=None):
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope or self.scope,
        }
        query_params = urlencode(params)
        return "%s?%s" % (self.AUTH_URL, query_params)

    async def get_access_token(self, code):
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "scope": self.scope,
            "code": code,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = await client.post(url=self.TOKEN_URL, data=payload, headers=headers)
        print(data)
        return data.get("access_token")

    async def get_user_data(self, access_token):

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        user_data = await client.get(url=self.API_URL + "/users/@me", headers=headers)
        return user_data

oauth = Oauth()