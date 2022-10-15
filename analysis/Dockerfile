# syntax=docker/dockerfile:1

FROM python:3

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

ENTRYPOINT [ "fava", "--host=0.0.0.0", "/data/main.beancount" ]
EXPOSE 5000
