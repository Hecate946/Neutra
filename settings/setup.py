import sys
import json


def start():
    config = {}
    msg = "Hello! My name is Snowbot, and I'm a moderation bot made by Hecate#3523\n"
    msg += "I'm going to walk you through a few steps to get started.\n"
    msg += "Firstly, we'll be creating a file names config.json that will hold all my secrets.\n"
    msg += "In order to run, I'll need a bot token. Visit this link: https://discord.com/developers/applications\n"
    msg += "then click on 'create an application'\nNext, you'll need to give me a name."
    msg += "I'd appreciate if you name me Snowbot... but if you don't I guess I'll get used to it :((\n"
    msg += "After creating an application, click on the 'bot' tab, and select the copy token option.\n"
    msg += "This token is extremely important, do not share it with anyone for any reason.\n"
    print(msg)
    token = input("Once you've copied the token, enter it here: ")
    config["token"] = token
    config["tester"] = token
    msg = "Next, assuming you've configured postgresql, you have to enter my connection URI.\n"
    msg += "If you haven't setup postgres, here's a link to their homepage where you should get started.\n"
    msg += "https://www.postgresql.org/\n"
    msg += "Back to the connection URI, it should look like this: postgres://user:password@host:post/dbname\n"
    msg += "substitude the 'user' with your postgres user, the password with your configured password,\n"
    msg += "the host with either an IP address or 'localhost', the port number (usually 5432) and finally, the database name."
    print(msg)
    postgres = input("Enter the postgres connection URI here: ")
    config["postgres"] = postgres
    msg = "Next, you should create a 'home' discord server where the bot will reside.\n"
    msg += "To copy discord IDs, you need to go into your discord settings, under appearances, and turn on developer mode.\n"
    msg += "After turning on developer mode, simply right click on your server's icon and copy the ID."
    print(msg)
    home = input("Paste that copied ID here: ")
    config["home"] = int(home)
    msg = "You're almost done. Now its time to enter a color for all my embeds. It should be a decimalized hex code.\n"
    msg += "If you're not sure which color you want, I love this color: 661538"
    print(msg)
    embed = input("Enter my embed color code: ")
    config["embed"] = int(embed)
    msg = (
        "Alrighty, now you have to enter your discord ID, registering you as an owner."
    )
    print(msg)
    owners = input("Enter your discord ID here: ")
    config["owners"] = [int(owners)]
    prefix = input(
        "Great job! All set now. Just enter what prefix you want me to use as default, and you're done: "
    )
    config["prefix"] = prefix

    config["botlog"] = None
    config["avchan"] = None
    config["github"] = "https://github.com/Hecate946/Snowbot"
    config["support"] = "https://discord.gg/947ramn"
    config["bitly"] = None
    config["timezonedb"] = None
    config["admins"] = []
    with open("./config.json", "w", encoding="utf-8") as fp:
        json.dump(config, fp, indent=2)

    sys.exit(0)
