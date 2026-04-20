#!/bin/bash
# ==============================================================
# CloudSave Deployment Script (Ubuntu 22.04 / 24.04 Target)
# ==============================================================

# Exit immediately if a command exits with a non-zero status
set -e

# Prompt for interactive variables required for domain routing
read -p "Enter your live Domain Name (e.g. api.yourdomain.com): " DOMAIN_NAME
read -p "Enter an email for SSL Certbot Notifications: " CERT_EMAIL
read -p "Enter your Gemini API Key (leave blank to skip): " GEMINI_API_KEY

echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "Installing required dependencies (Python 3.12, Nginx, Certbot)..."
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx sqlite3

# Define App Path
APP_DIR="/var/www/cloudsave"

echo "Setting up Application Directory at $APP_DIR..."
sudo mkdir -p /var/www/cloudsave
# Copying existing cloned project root into the live dir
sudo cp -r . /var/www/cloudsave
sudo chown -R $USER:www-data /var/www/cloudsave
sudo chmod -R 775 /var/www/cloudsave

cd $APP_DIR

echo "Generating generic virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing requirements..."
pip3 install -r requirements.txt
pip3 install gunicorn  # Used for daemon clustering

# Generate .env if missing securely
if [ ! -f .env ]; then
    echo "Generating secure .env file..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat <<EOF > .env
JWT_SECRET_KEY=$SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200
# Insert Gemini API here:
GEMINI_API_KEY=${GEMINI_API_KEY:-your_key_here}
EOF
fi

# Ensure directories for storage / db exist globally
mkdir -p storage/saves
touch app.db
chmod 664 app.db
chmod -R 775 storage

echo "Setting up Systemd Service for CloudSave..."
SERVICE_FILE="/etc/systemd/system/cloudsave.service"
sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Gunicorn daemon for CloudSave FastAPI
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
# Using 3 workers, binding directly locally for nginx.
ExecStart=$APP_DIR/venv/bin/gunicorn app.main:app -w 3 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl start cloudsave
sudo systemctl enable cloudsave

echo "Configuring Nginx Reverse Proxy..."
NGINX_CONF="/etc/nginx/sites-available/cloudsave"
sudo bash -c "cat <<EOF > $NGINX_CONF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    # Nginx max upload limit (Increase for giant saves)
    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }
}
EOF"

sudo ln -s /etc/nginx/sites-available/cloudsave /etc/nginx/sites-enabled/ || true
sudo rm /etc/nginx/sites-enabled/default || true

echo "Testing Nginx Config..."
sudo nginx -t

echo "Restarting Nginx..."
sudo systemctl restart nginx

echo "Attempting to provision Let's Encrypt SSL HTTPS..."
sudo certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos -m "$CERT_EMAIL"

echo "=============================================================="
echo "Deployment Complete!"
echo "Your FastAPI CloudSave Backend is now globally accessible at: https://$DOMAIN_NAME"
echo "Check journalctl -u cloudsave to monitor backend logs."
echo "=============================================================="
