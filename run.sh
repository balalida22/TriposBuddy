#!/bin/bash -e
cd /home/tz387/public_html/TriposBuddy
. venv/bin/activate
mkdir -p /home/tz387/logs
exec gunicorn \
    --workers 2 \
    --bind unix:/home/tz387/public_html/TriposBuddy/web.sock \
    --log-file /home/tz387/logs/triposbuddy.log \
    passenger_wsgi:application
