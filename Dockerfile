FROM python:3.11-slim

# Install deps
RUN pip install websockets

# Copy your server code
WORKDIR /app
COPY test_ws_server.py .

# Run the WebSocket server
CMD ["python", "test_ws_server.py"]
