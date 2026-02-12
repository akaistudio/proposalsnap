FROM python:3.11-slim

# Install Node.js
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies
COPY package.json .
RUN npm install --production

# Copy app
COPY . .

# Create directories
RUN mkdir -p uploads outputs

EXPOSE 5000
ENV PORT=5000
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --timeout 120
