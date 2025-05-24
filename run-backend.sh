#!/bin/bash
echo "Starting Django backend..."
cd backend
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver