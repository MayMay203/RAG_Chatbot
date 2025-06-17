# Base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set workdir
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Expose the port (not strictly needed for Render, but nice for clarity)
EXPOSE 8000

# Run the app
CMD gunicorn rag_chatbot.wsgi:application --bind 0.0.0.0:$PORT
