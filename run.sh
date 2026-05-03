#!/bin/bash -e
cd /home/tz387/public_html/TriposBuddy
. venv/bin/activate
mkdir -p /home/tz387/logs
exec uwsgi \
    --socket 127.0.0.1:5387 \
    --module passenger_wsgi \
    --callable application \
    --master \
    --processes 2 \
    --logto /home/tz387/logs/triposbuddy.log
