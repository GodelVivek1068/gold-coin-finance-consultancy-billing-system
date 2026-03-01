# Use lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Prevent Python from buffering logs
ENV PYTHONUNBUFFERED=1

# Copy requirements first (better layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Railway injects $PORT — default to 8080
ENV PORT=8080

# Expose port
EXPOSE 8080

# Start the app — init_db() runs automatically at module load
CMD gunicorn -w 2 -b 0.0.0.0:$PORT app:app
