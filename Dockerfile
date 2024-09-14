# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables to prevent Python from writing pyc files and to ensure output is unbuffered
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create and set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app/

# Copy the entry point script into the container
COPY entrypoint.sh /app/

# Make the entry point script executable
RUN chmod +x /app/entrypoint.sh

# Expose port 8000 for the Django application
EXPOSE 8000

# Use the entry point script
ENTRYPOINT ["/app/entrypoint.sh"]
