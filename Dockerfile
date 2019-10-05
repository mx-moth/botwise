FROM python:3.7-alpine

WORKDIR /opt/botwise
ADD requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/opt/botwise/questions.sql
ENV PEERWISE_SCHEDULE=@daily

ADD botwise.py botwise.py
ADD Readme.rst Readme.rst
ADD LICENSE LICENSE

CMD ["python3", "botwise.py"]
