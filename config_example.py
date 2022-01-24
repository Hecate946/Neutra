# Rename file to "config.py"

# Base endpoint for website
BASE_WEB_URL = "http://localhost:3000/"  # https://neutrabot.com/

# Support server invite
SUPPORT = "https://discord.gg/H2qTG4yxqb"

# Discord embed color, default navy blue
EMBED_COLOR = 661538

# Prefix to use when no custom prefixes are set
DEFAULT_PREFIX = "-"

# List of user_ids that own the bot
OWNERS = [708584008065351681]

# List of user_ids that can see global bot data
ADMINS = [782479134436753428, 766973396944551968]

# Start by: "python starter.py"
class PRODUCTION:
    """
    Production: This mode runs all "bug-free" features.
    This is the only mode that posts stats to the website
    and that has full webhook functionality (avs, icons, etc..)
    """

    # Bot token for production bot.
    token = "https://discord.com/developers/applications/"

    class POSTGRES:
        user = "postgres"  # Postgres username, defualt "postgres"
        password = "WUACK"  # Postgres password
        host = "localhost"  # Postgres host IP, default "localhost"
        port = 5432  # Postgres port, leave 5432 for default
        name = "Neutra"  # Database name
        uri = f"postgres://{user}:{password}@{host}:{port}/{name}"


# Start by: "python starter.py tester"
class TESTER:
    """
    Tester: This is a second bot meant to run on vps with production bot.
    This includes the music module. Runs without webhooks.
    """

    # Bot token for tester bot.
    token = "https://discord.com/developers/applications/"

    class POSTGRES:
        user = "postgres"  # Postgres username, defualt "postgres"
        password = "WUACK"  # Postgres password
        host = "localhost"  # Postgres host IP, default "localhost"
        port = 5432  # Postgres port, leave 5432 for default
        name = "Tester"  # Database name
        uri = f"postgres://{user}:{password}@{host}:{port}/{name}"


# Start by: "python starter.py dev"
class DEVELOPMENT:
    """
    Development: This is a third bot meant to run on local machine.
    Currently has largely the same functionality as tester mode.
    """

    # Bot token for development bot.
    token = "https://discord.com/developers/applications/"

    class POSTGRES:
        user = "postgres"
        password = "CySD191540"
        host = "168.119.185.159"
        port = 5432
        name = "Development"
        uri = f"postgres://{user}:{password}@{host}:{port}/{name}"


class DISCORD:
    token = PRODUCTION.token  # Leave as is
    client_id = "806953546372087818"  # Client ID of production bot as a string
    client_secret = "WUACK"  # Client secret of production bot.

    # Enter this url on discord dev portal (app -> oauth2 > add redirect)
    redirect_uri = BASE_WEB_URL + "discord/login"


class SPOTIFY:
    """Create app here: https://developer.spotify.com/dashboard/applications"""

    client_id = "Spotify app client id"
    client_secret = "Spotify app client secret"

    # Enter this url on spotify dashboard (app -> edit settings > add redirect uri)
    redirect_uri = BASE_WEB_URL + "spotify/connect"


class EMAIL:
    # Turn this setting on: https://myaccount.google.com/lesssecureapps
    password = "Gmail password"
    address = "Bot gmail account"


class KEYS:
    bitly = "https://bitly.com"  # Go get key from here
    timezonedb = "https://timezonedb.com"  # Go get key from here
    github = "https://github.com/settings/tokens"
    lyrics = "not even implemented in bot"


class LISTING_SITES:
    dbotsgg = "ignore this"
    topgg = "ignore this"


class WEBHOOKS:  # Run tester or dev mode to do without these
    class AVATARS:
        channel_id = 800000000000000000
        webhook_id = 800000000000000000
        token = "WUACK"

    class ERRORS:
        channel_id = 800000000000000000
        webhook_id = 800000000000000000
        token = "WUACK"

    class ICONS:
        channel_id = 800000000000000000
        webhook_id = 800000000000000000
        token = "WUACK"

    class LOGGING:
        channel_id = 800000000000000000
        webhook_id = 800000000000000000
        token = "WUACK"

    class TESTING:
        channel_id = 800000000000000000
        webhook_id = 800000000000000000
        token = "WUACK"
