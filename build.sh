#!/bin/bash

# Build script for Vercel
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput
