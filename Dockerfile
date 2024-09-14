# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables to prevent Python from writing pyc files and to ensure output is unbuffered
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Create and set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app/

# Run database migrations and collect static files
RUN python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py collectstatic --noinput

# Expose port 8000 for the Django application
EXPOSE 8000

# Define the command to run the application
CMD ["gunicorn", "yugen.wsgi:application", "--bind", "0.0.0.0:8000"]
