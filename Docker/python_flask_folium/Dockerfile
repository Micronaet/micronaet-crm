# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster

LABEL version="0.1"
LABEL maintaner="Micronaet - Nicola Riolini"
LABEL release-date="2024-10-24"

WORKDIR /micronaet-flask/data/log
WORKDIR /micronaet-flask

ENV data_folder=/micronaet-flask/data
ENV PIP_ROOT_USER_ACTION=ignore
COPY ./app/requirements.txt requirements.txt

# Network need:
# RUN apt install telnet iproute2 iputils-ping procps psmisc

RUN pip3 install --no-cache-dir --upgrade -r requirements.txt
COPY ./app/. ./
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "-p", "5000"]

