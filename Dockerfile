# Start from Python 3.9-slim base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Create a non-root user and switch to it
RUN useradd theia && \
    chown -R theia:theia /app
USER theia

# Set environment variables
ENV DATABASE_URI=sqlite:///accounts.db
ENV FLASK_APP=service/__init__.py
ENV PYTHONUNBUFFERED=1

# Expose port 8080
EXPOSE 8080

# Set the entry point to run gunicorn
CMD ["gunicorn", "--bind=0.0.0.0:8080", "--log-level=info", "service:app"]