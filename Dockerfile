FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scrape_fbtv_streams.py .
COPY app.py .

# Expose port
EXPOSE 8080

# Run app
CMD ["python", "app.py"]
