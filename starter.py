import json
import click


@click.command()
@click.argument("mode", default="production")
def main(mode):
    """Launches the bot."""

    if mode == "tester":
        with open("./config_test.json", "r", encoding="utf-8") as fp:
            configuration = json.load(fp)
        with open("./config.json", "w", encoding="utf-8") as fp:
            json.dump(configuration, fp, indent=2)

    elif mode == "watcher":
        with open("./config_watch.json", "r", encoding="utf-8") as fp:
            configuration = json.load(fp)
        with open("./config.json", "w", encoding="utf-8") as fp:
            json.dump(configuration, fp, indent=2)

    else:
        mode = "production"
        with open("./config_prod.json", "r", encoding="utf-8") as fp:
            configuration = json.load(fp)
        with open("./config.json", "w", encoding="utf-8") as fp:
            json.dump(configuration, fp, indent=2)

    from core import bot
    block = "#" * (len(mode) + 19)
    startmsg = f"{block}\n## Running {mode.capitalize()} Mode ## \n{block}"
    click.echo(startmsg)
    # run the application ...
    bot.run(mode=mode)


if __name__ == "__main__":
    main()
