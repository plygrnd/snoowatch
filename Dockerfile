FROM python:3

COPY requirements.txt ./

RUN pip3 install pipenv
RUN pipenv install

COPY ./tinkerbell ./tinkerbell
