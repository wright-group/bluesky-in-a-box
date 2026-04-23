FROM debian:trixie

# python
RUN apt update
RUN apt install git -y
RUN apt install librdkafka-dev -y
RUN apt install python3-pip -y
RUN apt install python3-venv -y

COPY ./startup.py ./startup.py
COPY ./user_group_permissions.yaml ./user_group_permissions.yaml
COPY ./requirements.txt /requirements.txt

# Create a virtual environment
RUN python3 -m venv /opt/venv

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
RUN python3 -m pip install -r requirements.txt

RUN qserver-list-plans-devices --startup-script startup.py
