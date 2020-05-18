import logging
from funding_bot.bot.runner import runner


if __name__ == "__main__":
    logging.basicConfig(
        filename="log.log",
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("FundingBot")
    logger.info("Start Funding Bot")
    runner(logger)
