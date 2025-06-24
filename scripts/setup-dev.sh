#!/bin/bash

echo "🚀 Setting up MarketEntropy development environment..."

# Check if Python 3.11+ is installed
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
if [[ $(echo "$python_version < 3.11" | bc) -eq 1 ]]; then
    echo "❌ Python 3.11+ required. Current version: $python_version"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install development tools
pip install pytest pytest-cov black isort flake8

# Setup pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
EOF

pip install pre-commit
pre-commit install

# Setup frontend
echo "📦 Setting up frontend..."
cd frontend
npm install
cd ..

# Start infrastructure services
echo "🐳 Starting infrastructure services..."
docker-compose up -d redis timescaledb

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Initialize database
echo "🗄️ Initializing database..."
python -c "
import asyncio
from market_entropy.core.database import init_db
asyncio.run(init_db())
print('Database initialized successfully!')
"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Database
DB_PASSWORD=dev_password_123
DATABASE_URL=postgresql://entropy_user:dev_password_123@localhost:5432/marketentropy

# Redis
REDIS_URL=redis://localhost:6379

# API Keys (get free key from https://www.alphavantage.co/support/#api-key)
ALPHA_VANTAGE_API_KEY=demo

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG
EOF
    echo "⚠️  Please update the ALPHA_VANTAGE_API_KEY in .env file"
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🚀 Quick start commands:"
echo "  source venv/bin/activate"
echo "  uvicorn market_entropy.api.main:app --reload"
echo "  cd frontend && npm start"
echo ""
echo "📊 Services:"
echo "  Dashboard: http://localhost:3000"
echo "  API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"