#!/bin/bash
echo "Starting Redis and PostgreSQL services..."

# Start Redis
echo "Starting Redis..."
sudo service redis-server start

# Start PostgreSQL
echo "Starting PostgreSQL..."
sudo service postgresql start

# Create database if it doesn't exist
echo "Setting up database..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'csv_reader'" | grep -q 1 || sudo -u postgres createdb csv_reader
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';" 2>/dev/null || echo "Password already set"

echo "Waiting for services to start..."
sleep 5

echo "Services started. You can now run the Django backend and React frontend."
echo ""
echo "To run the backend:"
echo "  cd backend"
echo "  pip install -r requirements.txt"
echo "  python3 manage.py migrate"
echo "  python3 manage.py runserver"
echo ""
echo "To run Celery worker (in another terminal):"
echo "  cd backend"
echo "  celery -A csv_reader_project worker --loglevel=info"
echo ""
echo "To run the frontend:"
echo "  cd frontend"
echo "  npm install"
echo "  npm start"