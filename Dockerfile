FROM python:3.11-slim

# Install deps
RUN pip install websockets aiohttp

# Copy your server code
WORKDIR /app
COPY main.py .

# Run the WebSocket server
CMD ["python", "main.py"]
