# syntax=docker/dockerfile:1

FROM python:3

COPY requirements.txt .
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "/src/main.py" ]
