import os
from quart import Quart, request, redirect, url_for
import json

from web import client
from web import discord
from web import spotify


app = Quart(__name__)
app.config["SECRET_KEY"] = os.urandom(64)


@app.route("/")
async def index():
    return """
<meta property="og:title" content="Neutra" />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://neutrabot.com" />
<meta property="og:image" content="https://cdn.discordapp.com/attachments/872338764276576266/927503071242747944/neutra.png" />
<meta property="og:description" content="Hello! I'm Neutra, and I specialize in tracking and moderation. I was designed to collect statistics on servers, users, messages, and more." />
<meta name="theme-color" content="#0A1822">"""

@app.route("/test")
async def test():
    user = await spotify.User.load(708584008065351681)
    a = await user.volume(100)
    #a = await user.play(context_uri="spotify:playlist:6icIkJjrZ8z3TFuctVcfeB", offset={"position": 0})
    return str(a)


@app.route("/discord_login", methods=["GET"])
async def discord_login():
    code = request.args.get("code")

    if code:  # User was redirected from discord auth url
        token_info = await discord.oauth.request_access_token(code)
        user = await discord.User.from_token(token_info) # Save user
        return redirect(spotify.oauth.get_auth_url(user.user_id))
    else:
        # They were redirected by me, or they visited the endpoint on their own.
        # Send them to discord to get their user_id.
        return redirect(discord.oauth.get_auth_url())


@app.route("/spotify_login")
async def spotify_login():
    code = request.args.get("code")
    user_id = request.args.get("state")

    if user_id and code:
        # We have a discord user redirected from spotify,
        # lets check if they're already in the system
        query = """
                SELECT token_info
                FROM spotify_auth
                WHERE user_id = $1
                """
        token_info = await client.cxn.fetchval(query, int(user_id))
        if token_info:
            return "you are already logged in"
        else:
            token_info = await spotify.oauth.request_access_token(code)

            if not token_info.get("access_token"):
                # Invalid code or user denied access
                return "Unable to connect your spotify account."
            query = """
                    INSERT INTO spotify_auth
                    VALUES ($1, $2)
                    ON CONFLICT (user_id)
                    DO UPDATE SET token_info = $2
                    WHERE spotify_auth.user_id = $1;
                    """
            await client.cxn.execute(query, int(user_id), json.dumps(token_info))
            return "successfully logged in"

    else:  # User visited the endpoint on their own. Aka was not redirected.
        # Send them to discord to get their user_id
        return redirect(url_for("discord_login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, loop=client.loop)
