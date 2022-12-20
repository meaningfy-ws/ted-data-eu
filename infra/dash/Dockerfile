FROM python:3.8.10-slim-buster

# set working directory in container
WORKDIR /usr/src/app

# Copy and install packages
COPY requirements.txt /

RUN apt-get update
RUN apt-get install git -y

RUN pip install --upgrade pip
RUN pip install -r /requirements.txt

# Copy app folder to app folder in container
COPY /dash /usr/src/app/
COPY /sparql_queries /usr/src/app/sparql_queries

# Changing to non-root user
RUN useradd -m appUser
USER appUser

# Run locally on port 8050
EXPOSE 8050
CMD gunicorn -b 0.0.0.0:8050 app:server