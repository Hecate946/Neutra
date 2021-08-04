import os
import json
import click


@click.command()
@click.argument("mode", default="production")
def main(mode):
    """Launches the bot."""
    mode = mode.lower()

    if not os.path.exists("./config.json"):
        mode = "setup"
    else:
        with open("./config.json", "r", encoding="utf-8") as fp:
            conf = json.load(fp)

    if mode == "setup":
        from settings import setup

        setup.start()
    elif mode == "tester":
        tester = True
        token = conf["tester"]
    else:
        tester = False
        token = conf["token"]

    from core import bot

    block = "#" * (len(mode) + 19)
    startmsg = f"{block}\n## Running {mode.capitalize()} Mode ## \n{block}"
    click.echo(startmsg)
    # run the application ...
    bot.run(token=token, tester=tester)


if __name__ == "__main__":
    main()
