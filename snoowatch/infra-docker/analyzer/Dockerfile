FROM python:3.8

RUN pip3 install pipenv

COPY ../../Pipfile* /tmp
COPY ../Snoowatch/* /app

RUN cd /tmp && pipenv lock --requirements  > requirements.txt

RUN pip3 install -r /tmp/requirements.txt

COPY . /tmp/snoowatch

RUN pip3 install /tmp/snoowatch

CMD python3 run.py