# Install Python packages
pip3 install -r requirements.txt

# Collect static files
python3.12 manage.py collectstatic --noinput
