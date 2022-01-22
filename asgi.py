from app import app
from hypercorn.asyncio import serve
from hypercorn.config import Config

if __name__ == "__main__":

    config = Config.from_mapping(bind=["unix:app.sock"], umask=7)
    app.loop.run_until_complete(serve(app, config))
