# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 user
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and change ownership
COPY --chown=user:user . .

# Pre-create writable directories with correct ownership
RUN mkdir -p uploads web/data models && chown -R user:user uploads web/data models

# Switch to non-root user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Expose the port the app runs on (Hugging Face Spaces default is 7860)
EXPOSE 7860

# Run main.py when the container launches
CMD ["python", "main.py"]
