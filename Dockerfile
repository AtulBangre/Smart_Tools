# Use the official Playwright Python image which includes all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the correct playwright browsers (Chromium is usually enough)
RUN playwright install chromium

# Copy the entire project
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI server from the correct directory
CMD ["bash", "-c", "cd amazon_smartbiz_uploader/backend && uvicorn main:app --host 0.0.0.0 --port 8000"]
