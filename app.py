import secrets
from quart import Quart, request, redirect, url_for, render_template, session
import json

from web import client
from web import discord
from web import spotify

from config import SUPPORT


app = Quart(__name__)
app.secret_key = secrets.token_urlsafe(64)


@app.route("/")
async def home():
    return await render_template("home.html")


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

    user = await discord.User.from_token(token_info)  # Save user
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


@app.route("/spotify")
async def _spotify():
    return await render_template("spotify.html")


@app.route("/spotify/connect")
async def spotify_connect():
    code = request.args.get("code")
    user_id = session.get("user_id")

    if not user_id:  # User is not logged in to discord, redirect them back
        session["referrer"] = url_for(
            "spotify_connect"
        )  # So they'll send the user back here
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

    if not code:  # Need code, redirect user to spotify
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


@app.route("/spotify/recent")
async def spotify_recent():
    user_id = session.get("user_id")

    if not user_id:  # User is not logged in to discord, redirect them back
        session["referrer"] = url_for(
            "spotify_recent"
        )  # So they'll send the user back here
        return redirect(url_for("discord_login"))

    user = await spotify.User.load(user_id)

    data = await user.get_recently_played()
    tracks = spotify.formatting.recent_tracks(data)
    caption = spotify.formatting.get_caption("recents")
    return await render_template("spotify/tables.html", data=tracks, caption=caption)


@app.route("/spotify/top/<spotify_type>")
async def spotify_top(spotify_type):
    user_id = session.get("user_id")
    time_range = request.args.get("time_range", "short_term")

    if not user_id:  # User is not logged in to discord, redirect them back
        session["referrer"] = url_for(
            "spotify_top", spotify_type=spotify_type, time_range=time_range
        )  # So they'll send the user back here
        return redirect(url_for("discord_login"))

    user = await spotify.User.load(user_id)

    if spotify_type == "artists":
        data = await user.get_top_artists(time_range=time_range)
        artists = spotify.formatting.top_artists(data)
        caption = spotify.formatting.get_caption("artists", time_range)
        return await render_template(
            "spotify/tables.html", artist=True, data=artists, caption=caption
        )

    if spotify_type == "tracks":
        data = await user.get_top_tracks(time_range=time_range)
        tracks = spotify.formatting.top_tracks(data)
        caption = spotify.formatting.get_caption("tracks", time_range)
        return await render_template(
            "spotify/tables.html", data=tracks, caption=caption
        )

    if spotify_type == "genres":
        data = await user.get_top_genres(time_range=time_range)
        genres = spotify.formatting.top_genres(data)
        caption = spotify.formatting.get_caption("genres", time_range)
        return await render_template(
            "spotify/tables.html", genre=True, data=genres, caption=caption
        )


@app.route("/docs")
async def docs():
    return await render_template("docs.html")


@app.route("/docs/<cog>")
async def cog_docs(cog):
    return await render_template(f"docs/{cog}.html")


@app.route("/support")
async def support():
    return redirect(SUPPORT)


@app.route("/invite")
async def invite():
    return redirect(discord.oauth.get_auth_url(invite=True))


STATS = {"retard": "hi"}


@app.route("/live_stats", methods=["GET", "POST"])
async def live_stats():
    text = await request.json
    global STATS
    STATS = text
    return "hi"


@app.route("/_stuff")
async def background_process():
    from quart import jsonify

    return jsonify(result=json.dumps(STATS))


# allow both GET and POST requests
@app.route("/s", methods=["GET"])
async def retard():

    return await render_template("s.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, loop=client.loop)
