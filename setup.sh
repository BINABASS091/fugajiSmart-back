#!/bin/bash

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set environment variables
export DJANGO_SETTINGS_MODULE=config.settings
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env <<EOL
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgres://postgres:postgres@localhost:5432/cohort_kuku
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
EOL
    echo ".env file created. Please update it with your actual configuration."
fi

# Run database migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser..."
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

# Set superuser password
echo "Setting superuser password..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user = User.objects.get(username='admin')
    user.set_password('admin')
    user.save()
    print('Superuser created/updated successfully')
except Exception as e:
    print(f'Error creating/updating superuser: {e}')"

echo "Setup complete! Run 'source venv/bin/activate' to activate the virtual environment."
