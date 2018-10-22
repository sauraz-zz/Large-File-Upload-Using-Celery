FROM ubuntu:16.04

MAINTAINER saurav sarkar saurav0988@gmail.com

RUN apt-get update


RUN apt-get install -y supervisor
RUN apt-get install -y  python-pip python-dev build-essential

# Copy the current directory contents into the container at /app
COPY . /app
ENV HOME=/app
WORKDIR /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt
RUN pip install --user requests

EXPOSE 5000


ADD supervisord.conf /etc/supervisor/conf.d/supervisord.conf 

ENTRYPOINT ["/usr/bin/supervisord"]