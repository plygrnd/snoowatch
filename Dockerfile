FROM python:3.8-slim

RUN pip3 install pipenv

COPY Pipfile /tmp
COPY snoowatch/ /app/snoowatch
COPY bin/run_snoowatch.py /app

RUN cd /tmp && pipenv lock --requirements  > requirements.txt

RUN pip3 install -r /tmp/requirements.txt

COPY . /tmp/snoowatch

RUN pip3 install /tmp/snoowatch

WORKDIR /app
ENTRYPOINT ["/usr/local/bin/python3", "/app/run_snoowatch.py"]