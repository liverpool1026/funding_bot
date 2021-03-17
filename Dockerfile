FROM python:3.6-slim-buster

COPY setup.py setup.py
COPY . . 
RUN python3 -m pip install -e .


CMD [ "funding_bot", "run"]
