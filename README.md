# Welcome to Funding Bot

A funding bot written in python3.6 that can automatically lend out money and earn interest on Bitfinex.

Annualised ROI over 294 days (17-05-2020 ~ 06-03-2021):
- USD : 16.74%
- ETH : 2.27%

![image](https://user-images.githubusercontent.com/29122286/110626592-a7a7f780-81ec-11eb-8348-b480a9d5301a.png)

Current supported currencies

- USD
- BTC
- ETH

# How to run

## Pull pre-built docker container

Pull Docker Container
```
docker pull hawkvine/funding-bot:version (i.e. docker pull hawkvine/funding-bot:2.5.0)
```

Obtain a copy of the config and modify it (Template: funding_bot/funding_bot/myconfig_template.py)

Run Docker Container
```
docker run -v absolute_path_to_config_file:/funding_bot/configs/myconfig.py hawkvine/funding-bot:version
```

Check out https://hub.docker.com/r/hawkvine/funding-bot/tags?page=1&ordering=last_updated for available versions. (Latest Stable: 2.5.0)

## Run the code directly

Install
```
git clone https://github.com/liverpool1026/funding_bot
cd funding_bot
pip install -e .  (Requires python3.6)
```

Config Setting
```
cp funding_bot/funding_bot/myconfig_template.py funding_bot/funding_bot/myconfig.py
vim funding_bot/funding_bot/myconfig.py
```

Run
```
funding_bot run
```

## Build Custom Docker Container Locally

Pull Source Code
```
git clone https://github.com/liverpool1026/funding_bot
cd funding_bot
```

Config Setting
```
cp funding_bot/funding_bot/myconfig_template.py funding_bot/funding_bot/myconfig.py
vim funding_bot/funding_bot/myconfig.py
```

Build Container
```
docker build --tag funding_bot .
```

Run Container
```
docker run funding_bot
```

# Integration

Currently supports
- Telegram Notification
- Sentry Error Integration
- AWS DynamoDB

Example DynamoDB Structure
![image](https://user-images.githubusercontent.com/29122286/111640383-e28ed880-8847-11eb-8e2c-cc30eb12c02f.png)


### Support or Contact

