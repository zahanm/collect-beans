# syntax=docker/dockerfile:1

FROM python:3

WORKDIR /app

RUN curl https://rclone.org/install.sh | bash

COPY requirements.txt .
RUN pip install -r requirements.txt

ENV TZ="America/Los_Angeles"

EXPOSE 5000
ENTRYPOINT [ "flask", "--app", "src/bookkeeper/api", "run", "--port", "5000", "--host", "0.0.0.0" ]
