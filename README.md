# CSV Reader App

A full-stack application for uploading CSV files and converting them to pandas DataFrames.

## Structure
- `backend/` - Django REST API
- `frontend/` - React application

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Features
- Upload CSV files from React frontend
- Process CSV files in Django backend
- Convert CSV to pandas DataFrame
- Return DataFrame info to frontend