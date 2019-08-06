#!/bin/sh

until nc -z ${REDIS_HOST} ${REDIS_PORT}; do
    echo "$(date) - waiting for redis..."
    sleep 1
done

exec "$@"