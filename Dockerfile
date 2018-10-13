FROM python:3

COPY Pipfile ./

RUN pip3 install pipenv
RUN pipenv install

COPY ./tinkerbell ./tinkerbell
