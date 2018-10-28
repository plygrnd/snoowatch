FROM nginx:latest

COPY default.conf /etc/nginx/conf.d/default.conf
COPY wait-for-it.sh /usr/local/bin

RUN chmod +x /usr/local/bin/wait-for-it.sh
