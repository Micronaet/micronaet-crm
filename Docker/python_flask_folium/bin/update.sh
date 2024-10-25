#!/bin/bash
# Run this batch in folder where Dockerfile is!

# Parameters:
mkdir -p /root/docker/data/log
data_folder=/root/docker/data
# package_folder=`realpath ../excel_writer`

# Update from git:
git pull
# Save credential:
# git config --global credential.helper store

# Stop, delete container, remove image:
docker stop micronaet-flask
docker rm micronaet-flask
docker rmi python-flask

# Create new image from Dockerfile:
docker build --tag python-flask .

# Restart new container:
docker run -d -p 5000:5000 -p 5001:5001 --name=micronaet-flask --hostname=flask -v `pwd`/app:/micronaet-flask -v ${data_folder}:/micronaet-flask/data --restart=always python-flask

# Show started container:
docker ps -a
