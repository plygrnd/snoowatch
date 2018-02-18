FROM python:3

COPY ../requirements.txt ./

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY

ENV AWS_ACCESS_KEY_ID $AWS_ACCESS_KEY_ID
ENV AWS_SECRET_ACCESS_KEY $AWS_SECRET_ACCESS_KEY

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /root/.aws

RUN echo '[profile tinkerbell]\n\
region = eu-west-1\n\
output = json'\
>> /root/.aws/config

RUN echo [tinkerbell] >> /root/.aws/credentials

RUN echo $AWS_ACCESS_KEY_ID >> /root/.aws/credentials
RUN echo $AWS_SECRET_ACCESS_KEY >> /root/.aws/credentials

COPY ../tinkerbell ./tinkerbell