# Use lightweight Python image
FROM python:3.11

# Set working directory
WORKDIR /app

# Prevent Python from buffering logs
ENV PYTHONUNBUFFERED=1

# Copy requirements first
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy full project
COPY . .

# Expose Flask port
EXPOSE 5000

# Start the app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
