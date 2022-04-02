# syntax=docker/dockerfile:1

FROM python:3.9.7

EXPOSE 5000 5001 5002 5003 5004
RUN mkdir -p /app
COPY . /app
WORKDIR /app

RUN pip install Flask \
    && pip install requests \


CMD [ "flask", "run", "--host=127.0.0.1"]

