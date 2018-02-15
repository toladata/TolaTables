FROM python:2.7

COPY . /code
WORKDIR /code

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install nginx -y

ADD docker/etc/nginx/nginx.conf /etc/nginx/nginx.conf

RUN pip install -r requirements/base.txt

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate; nginx; python manage.py runserver --insecure 127.0.0.1:8888"]
