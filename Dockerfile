FROM registry.git.zoodroom.com/basket/fertilizer:latest

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
    && apk del .build-deps \
    && apk add --no-cache libstdc++

COPY . /src
WORKDIR /src

RUN python setup.py install

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD grpc_health_probe -addr=127.0.0.1:9000 || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["mango"]