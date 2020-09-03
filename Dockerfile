FROM ubuntu:20.04
LABEL maintainer="glentner@purdue.edu"


RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y \
    build-essential \
    python3-dev python3-pip python3-setuptools

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --force-yes \
    postgresql-12 postgresql-client-12 postgresql-contrib-12

RUN mkdir -p /app
COPY . /app

RUN python3 -m pip install /app
