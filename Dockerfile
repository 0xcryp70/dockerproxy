# Dockerfile

FROM python:3.9-slim

# Install Docker CLI
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the application code
COPY app/ /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port (optional)
#EXPOSE 5000

# Run the application
CMD ["python", "app.py"]

