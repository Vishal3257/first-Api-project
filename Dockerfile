FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /code/

# Expose port 7860 (Hugging Face binds to this port automatically)
EXPOSE 7860

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "myproject.wsgi:application"]