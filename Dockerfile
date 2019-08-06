FROM python:3.6-alpine

LABEL MAINTAINER="Sayyed Alireza Hoseini <alireza.hosseini@zoodroom.com>"

RUN apk add --update --no-cache netcat-openbsd

COPY requirements.txt /src/requirements.txt

RUN set -ex \
    && apk add --no-cache --update --virtual .build-deps \
        g++ \
        make \
        git \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r /src/requirements.txt \
    && apk del .build-deps

RUN apk add libstdc++

COPY . /src
WORKDIR /src

RUN python setup.py install

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["mango"]