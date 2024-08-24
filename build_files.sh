echo "Building files..."
mkdir -p static

# Install Python packages
echo "Installing Python packages..."
pip3 install -r requirements.txt

# Database migrations
echo "Appling database migrations..."
python3.12 manage.py makemigrations
python3.12 manage.py migrate

# Collect static files
echo "Collecting static files..."
python3.12 manage.py collectstatic --noinput
