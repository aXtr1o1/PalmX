#!/bin/sh
echo "Checking for Knowledge Index..."
python3 -m app.backend.retrieval.build_index

echo "Starting PalmX Backend..."
exec uvicorn app.backend.main:app --host 0.0.0.0 --port 8000
