import json
import click


@click.command()
@click.argument("mode", default="production")
def main(mode):
    """Launches the bot."""

    block = "#" * (len(mode) + 19)
    startmsg = f"{block}\n## Running {mode.capitalize()} Mode ## \n{block}"
    click.echo(startmsg)
    if mode.lower() == "tester":
        mode = "tester"
    else:
        mode = "production"

    if mode == "tester":
        with open("./config_test.json", "r", encoding="utf-8") as fp:
            configuration = json.load(fp)
        with open("./config.json", "w", encoding="utf-8") as fp:
            json.dump(configuration, fp, indent=2)

    else:
        with open("./config_prod.json", "r", encoding="utf-8") as fp:
            configuration = json.load(fp)
        with open("./config.json", "w", encoding="utf-8") as fp:
            json.dump(configuration, fp, indent=2)

    from core import bot

    # run the application ...
    bot.run(mode=mode)


if __name__ == "__main__":
    main()
