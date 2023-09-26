FROM python:slim

RUN useradd microblog 

WORKDIR /home/microblog

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN /bin/bash -c "source venv/bin/activate"
RUN pip install -r requirements.txt
RUN pip install gunicorn pymongo cryptography

COPY app app
COPY microblog.py config.py  __init__.py ./


ENV FLASK_APP microblog.py
ENV MONGODB_URI="mongodb://mongoserver-container:27017/microblog"



COPY .env .env


EXPOSE 8000
WORKDIR /home
CMD  ["gunicorn","-w 4","-b 0.0.0.0:8000", "microblog.microblog:app"]

