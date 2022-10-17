# syntax=docker/dockerfile:1

FROM python:3

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 5005
ENTRYPOINT [ "flask", "--app", "src/bookkeeper/api", "run", "--port", "5005", "--host", "0.0.0.0" ]
