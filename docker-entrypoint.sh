#!/bin/sh

if ! [[ -z "$REDIS_HOST" ]] && ! [[ -z "$REDIS_PORT" ]]
then
    until nc -z ${REDIS_HOST} ${REDIS_PORT}; do
        echo "$(date) - waiting for redis..."
        sleep 1
    done
else
    echo "\$REDIS_HOST & \$REDIS_PORT is not set"
    exit 1
fi

if ! [[ -z "$MONGO_HOST" ]] && ! [[ -z "$MONGO_PORT" ]]
then
    until nc -z ${MONGO_HOST} ${MONGO_PORT}; do
        echo "$(date) - waiting for mongoDB..."
        sleep 1
    done
else
    echo "\$MONGO_HOST & \$MONGO_PORT is not set"
    exit 1
fi

exec "$@"