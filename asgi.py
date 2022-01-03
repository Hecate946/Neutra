from app import app
from web import client
from hypercorn.asyncio import serve
from hypercorn.config import Config

if __name__ == "__main__":

    config = Config.from_mapping(bind=["unix:app.sock"], umask=7)
    client.loop.run_until_complete(serve(app, config))
