# Use official Playwright image with Python + Chromium pre-installed
FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

# Set working directory
WORKDIR /code

# Install pip dependencies
COPY requirements.txt .
RUN pip install psycopg2-binary
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Make entrypoint executable
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Start the app
CMD ["/entrypoint.sh"]
