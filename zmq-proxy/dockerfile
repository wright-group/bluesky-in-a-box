FROM python:3.10-bullseye
COPY ./requirements.txt ./
RUN python3 -m pip install -r requirements.txt
CMD ["bluesky-0MQ-proxy", "5567", "5568"]



