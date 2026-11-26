#!/bin/sh
exec python3 "$(dirname -- "$0")/gnome-scroll/manage.py" flick "$@"
