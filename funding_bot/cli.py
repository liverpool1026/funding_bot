import os
import sys
import click
import logging
import pkg_resources

from funding_bot.bot.runner import runner

dir_path = os.path.dirname(os.path.realpath(__file__))


@click.group()
def cli():
    funding_bot = click.style("funding_bot", fg="cyan", bold=True)
    version = pkg_resources.get_distribution('funding_bot').version
    click.echo(funding_bot + " " + version)


@click.command()
def run():
    logging.basicConfig(
        filename=f"{dir_path}/log.log",
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("FundingBot")
    logger.info("Start Funding Bot")
    runner(logger)


cli.add_command(run)


def main():
    cli(sys.argv[1:])


if __name__ == "__main__":
    main()
