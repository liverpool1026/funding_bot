from setuptools import setup

setup(
    name="funding_bot",
    version="1.1.0",
    description="Handle automatic funding on Bitfinex",
    url="https://github.com/liverpool1026/funding_bot",
    author="Kevin Hwa",
    author_email="liverpool1026.bne@gmail.com",
    packages=["funding_bot"],
    include_package_data=True,
    install_requires=["requests", "tabulate", "mypy", "boto3", "click"],
    entry_points={"console_scripts": ["funding_bot=funding_bot.cli:main"]},
)
