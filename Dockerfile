FROM python:3.13-slim

WORKDIR /app

# Install git for patch operations
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY run.sh .
COPY Procfile .
COPY src/ ./src/
COPY data/ ./data/

# Create necessary directories
RUN mkdir -p logs runs

# Make run.sh executable
RUN chmod +x run.sh

# Expose port (Railway sets PORT env var)
EXPOSE 8010

# Run via agentbeats controller
CMD ["agentbeats", "run_ctrl"]
