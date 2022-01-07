import sys
import json
from re import match


def start():
    config = {}
    msg = "Hello! My name is Neutra, and I'm a moderation bot made by Hecate#3523\n"
    msg += "I'm going to walk you through a few steps to get started.\n"
    msg += "Firstly, we'll be creating a file names config.json that will hold all my secrets.\n"
    msg += "In order to run, I'll need a bot token. Visit this link: https://discord.com/developers/applications\n"
    msg += "then click on 'create an application'\n"
    msg += "Next, you'll need to give me a name.\n"
    msg += "I'd appreciate if you name me Neutra... but if you don't I guess I'll get used to it :((\n"
    msg += "After creating an application, click on the 'bot' tab, and select the copy token option.\n"
    msg += "This token is extremely important, do not share it with anyone for any reason.\n"
    print(msg)
    token = input("Once you've copied the token, enter it here: ")
    while len(token) < 15:
        print("That does not look like a valid token.")
        token = input("Once you've copied the token, enter it here: ")
    msg = "Next, assuming you've configured postgresql, you have to enter my connection URI.\n"
    msg += "If you haven't setup postgres, here's a link to their homepage where you should get started.\n"
    msg += "https://www.postgresql.org/\n"
    msg += "Back to the connection URI, it should look like this: postgres://user:password@host:post/dbname\n"
    msg += "substitute the 'user' with your postgres user, the password with your configured password,\n"
    msg += "the host with either an IP address or 'localhost', the port number (usually 5432) and finally, the database name."
    print(msg)
    postgres = input("Enter the postgres connection URI here: ")
    some_trash_regex = "postgres://.*:.*@.*:.*/.*"
    while not match(some_trash_regex, postgres):
        print("That does not look like a valid postgres URI.")
        postgres = input("Enter the postgres connection URI here: ")
    msg = "You're almost done. Now its time to enter a color for all my embeds. It should be a hex code.\n"
    msg += "As an example, aqua blue is 29f4ff\n"
    msg += "If you're not sure which color you want, I love this color: 0A1822"
    print(msg)
    embed = input("Enter my embed color code: ")
    while len(embed) != 6:
        print(
            "That does not seem like a valid hex code. It should be 6 digits in hexadecimal."
        )
        embed = input("Enter my embed color code: ")
        try:
            test = int(embed, 16)
        except:
            embed = "the while loop will run again because it couldnt convert"
    msg = (
        "Alrighty, now you have to enter your discord ID, registering you as an owner."
    )
    print(msg)
    owners = input("Enter your discord ID here: ")
    while len(owners) > 20 or len(owners) < 16:
        print(
            "That does not seem like a valid discord ID. Enable developer mode and right click on your avatar to find your ID."
        )
        owners = input("Enter your discord ID here: ")
        try:
            stuff = [int(owners)]
        except:
            owners = "This wont be a valid discord id, so the while loop runs again"
    prefix = input(
        "Great job! All set now. Just enter what prefix you want me to use as default, and you're done: "
    )
    print("Done! Run the bot again to start")
    print("Feel free to harass Hecate#3523 if you have issues.")

    config["admins"] = []
    config["avchan"] = None
    config["bitly"] = None
    config["botlog"] = None
    config["embed"] = int(embed, 16)
    config["github"] = "https://github.com/Hecate946/Neutra"
    config["gtoken"] = None
    config["owners"] = [int(owners)]
    config["postgres"] = postgres
    config["prefix"] = prefix
    config["support"] = "https://discord.gg/947ramn"
    config["tester"] = token
    config["timezonedb"] = None
    config["token"] = token
    with open("./config.json", "w", encoding="utf-8") as fp:
        json.dump(config, fp, indent=2)

    sys.exit(0)
