#!/bin/bash
echo "Starting Redis and PostgreSQL services..."
PROC_PATH="/home/reader_speeder/csv-reader-app"
echo "Running the Python tests"
python3 "${PROC_PATH}/backend/csv_processor/test/test_file_processor.py"

