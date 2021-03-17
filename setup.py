from setuptools import setup

setup(
    name="funding-bot",
    version="2.4.1",
    description="Handle automatic funding on Bitfinex",
    url="https://github.com/liverpool1026/funding_bot",
    author="Kevin Hwa",
    author_email="liverpool1026.bne@gmail.com",
    packages=["funding_bot"],
    include_package_data=True,
    install_requires=["requests", "tabulate", "mypy", "boto3", "click", "sentry-sdk"],
    entry_points={"console_scripts": ["funding_bot=funding_bot.cli:main"]},
)
