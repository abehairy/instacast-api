# start_server.sh

# Activate the virtual environment
source .venv/bin/activate

# Start the FastAPI server
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
