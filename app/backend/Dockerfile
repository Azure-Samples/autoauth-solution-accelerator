#TODO: Test Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container to /app
WORKDIR /app

ENV PYTHONPATH="/app:$PYTHONPATH"

# Add the current directory contents into the container at /app
COPY src /app/src
COPY app /app/app
COPY requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run app.py when the container launches
CMD ["python3", "app", "backend", "paprocessing", "app.py"]
