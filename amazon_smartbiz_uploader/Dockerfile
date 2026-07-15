# Use the official Playwright Python image which includes all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the correct playwright browsers (Chromium is usually enough)
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI server
CMD ["bash", "-c", "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"]
