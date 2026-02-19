# Backend

This is the backend for the Remote Control application. It uses FastAPI and `python-uinput` to create a virtual keyboard that can be controlled over a WebSocket.

## Running the backend

1.  Navigate to the `backend` directory.
2.  Create a virtual environment: `python -m venv venv`
3.  Activate the virtual environment: `source venv/bin/activate`
4.  Install the dependencies: `pip install -r requirements.txt`
5.  Run the application: `sudo venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000`

**Note:** The application must be run with `sudo` for `python-uinput` to work.

## Running the tests

1.  Navigate to the `backend` directory.
2.  Install the dependencies (including test dependencies): `pip install -r requirements.txt`
3.  Run the tests: `pytest`
