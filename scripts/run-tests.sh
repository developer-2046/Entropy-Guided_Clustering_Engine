echo "🧪 Running MarketEntropy test suite..."

# Activate virtual environment
source venv/bin/activate

# Run linting
echo "🔍 Running code quality checks..."
black --check market_entropy/ tests/
isort --check-only market_entropy/ tests/
flake8 market_entropy/ tests/

# Run unit tests
echo "🧪 Running unit tests..."
pytest tests/ -v --cov=market_entropy --cov-report=html --cov-report=term

# Run integration tests (if infrastructure is running)
if docker ps | grep -q redis; then
    echo "🔗 Running integration tests..."
    pytest tests/integration/ -v
else
    echo "⚠️  Skipping integration tests (infrastructure not running)"
fi

echo "✅ Test suite complete!"