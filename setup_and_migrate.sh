#!/bin/bash

# Exit on error
set -e

echo "🚀 Setting up the project..."

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python -m venv venv
fi

# Activate the virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt

# Set environment variables
export DJANGO_SETTINGS_MODULE=config.settings
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run migrations
echo "🔄 Running migrations..."
python manage.py migrate

echo "✅ Setup complete! You can now start the development server with:"
echo "   cd /home/kilimanjaro/Desktop/cohort-kuku/backend"
echo "   source venv/bin/activate"
echo "   python manage.py runserver"

# Keep the virtual environment activated
/bin/bash
