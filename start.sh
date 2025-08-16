#!/bin/bash
export FLASK_APP=app.py
gunicorn -w 1 -k gthread -b 0.0.0.0:5000 app:app