import html
import os
import secrets
from quart import Quart, request, redirect, url_for, render_template, session
import json
from tabulate import tabulate

from web import client
from web import discord
from web import spotify


app = Quart(__name__)
app.secret_key = secrets.token_urlsafe(64)


@app.route("/")
async def index():
    return await render_template("home.html")


@app.route("/docs")
async def docs():
    return await render_template("docs.html")
    
@app.route("/test")
async def test():

    return redirect(url_for("discord_login"))


@app.route("/discord/login")
async def discord_login():
    code = request.args.get("code")
    user_id = session.get("user_id")

    if user_id:  # User is already logged in:
        ref = session.pop("referrer", None)
        if ref:
            return redirect(ref)
        return "you are already logged in"

    if not code:
        # They were redirected by me, or they visited the endpoint on their own.
        # Send them to discord to get their user_id.
        return redirect(discord.oauth.get_auth_url())

    # User was redirected from discord auth url
    token_info = await discord.oauth.request_access_token(code)

    if not token_info:  # Invalid code or user rejection
        return redirect(discord.oauth.get_auth_url())

    user = await discord.User.from_token(token_info) # Save user
    session["user_id"] = int(user.user_id)

    ref = session.pop("referrer", None)
    if ref:
        return redirect(ref)

    return "logged in to discord"

@app.route("/discord/logout")
async def discord_logout():
    session.pop("user_id", None)

    ref = session.pop("referrer", None)
    if ref:
        return redirect(ref)
    return "logged out of discord"


@app.route("/spotify/connect")
async def spotify_connect():
    code = request.args.get("code")
    user_id = session.get("user_id")

    if not user_id:  # User is not logged in to discord, redirect them back
        session["referrer"] = url_for("spotify_connect") # So they'll send the user back here
        return redirect(url_for("discord_login"))

    # lets check if they're already in the system
    query = """
            SELECT token_info
            FROM spotify_auth
            WHERE user_id = $1
            """
    token_info = await client.cxn.fetchval(query, user_id)
    if token_info:  # They already logged in to spotify
        ref = session.pop("referrer", None)
        if ref:
            return redirect(ref)
        return await render_template("success.html")


    if not code: # Need code, redirect user to spotify
        return redirect(spotify.oauth.get_auth_url())


    # We have a discord user redirected from spotify,


    token_info = await spotify.oauth.request_access_token(code)
    if not token_info:  # Invalid code or user rejection
        return redirect(spotify.oauth.get_auth_url())

    query = """
            INSERT INTO spotify_auth
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET token_info = $2
            WHERE spotify_auth.user_id = $1;
            """
    await client.cxn.execute(query, user_id, json.dumps(token_info))
    ref = session.pop("referrer", None)
    if ref:
        return redirect(ref)
    return await render_template("success.html")


@app.route("/spotify/top/<spotify_type>")
async def spotify_top(spotify_type):
    user_id = session.get("user_id")
    time_range = request.args.get("time_range", "short_term")

    if not user_id:  # User is not logged in to discord, redirect them back
        session["referrer"] = url_for("spotify_top", spotify_type=spotify_type, time_range=time_range) # So they'll send the user back here
        return redirect(url_for("discord_login"))


    user = await spotify.User.load(user_id)


    if spotify_type == "artists":
        data = await user.get_top_artists(time_range=time_range)
        return spotify.formatting.artist_html_table(data, time_range)

    if spotify_type == "tracks":
        data = await user.get_top_tracks(time_range=time_range)
        return spotify.formatting.track_html_table(data, time_range)

@app.route("/spotify/recent")
async def spotify_recent():
    user_id = session.get("user_id")

    if not user_id:  # User is not logged in to discord, redirect them back
        session["referrer"] = url_for("spotify_recent") # So they'll send the user back here
        return redirect(url_for("discord_login"))


    user = await spotify.User.load(user_id)

    data = await user.get_recently_played()
    return spotify.formatting.recent_html_table(data)













    
    return "hi"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, loop=client.loop)
