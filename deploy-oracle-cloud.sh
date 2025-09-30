#!/bin/bash

# Oracle Cloud deployment script for Telegram Bot
# This script sets up the bot on Oracle Cloud Infrastructure

set -e

echo "🚀 Starting Oracle Cloud deployment for VB International Bot..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (recommended for initial setup)
if [[ $EUID -eq 0 ]]; then
   print_warning "Running as root. This is fine for initial setup."
fi

# Update system packages
print_status "Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    print_status "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    print_success "Docker installed successfully"
else
    print_success "Docker is already installed"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    print_status "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose installed successfully"
else
    print_success "Docker Compose is already installed"
fi

# Install Git if not present
if ! command -v git &> /dev/null; then
    print_status "Installing Git..."
    sudo apt-get install -y git
    print_success "Git installed successfully"
else
    print_success "Git is already installed"
fi

# Install other useful tools
print_status "Installing additional tools..."
sudo apt-get install -y \
    curl \
    wget \
    unzip \
    htop \
    nano \
    traceroute \
    whois \
    iputils-ping

# Create bot directory
BOT_DIR="/opt/telegram-bot"
print_status "Creating bot directory at $BOT_DIR..."
sudo mkdir -p $BOT_DIR
sudo chown -R $USER:$USER $BOT_DIR

# Navigate to bot directory
cd $BOT_DIR

# Check if bot files exist
if [ ! -f "bot.py" ]; then
    print_warning "Bot files not found. You need to upload your bot files to $BOT_DIR"
    print_status "Expected files: bot.py, locate_ip.py, requirements.txt, Dockerfile, docker-compose.yml, .env"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating template..."
    cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
BOT_NAME=VB_International_BOT
DEBUG=False

# Optional: Add other environment variables
# LOG_LEVEL=INFO
EOF
    print_warning "Please edit .env file with your actual bot token: nano .env"
    exit 1
fi

# Create logs directory
mkdir -p logs
chmod 755 logs

# Build and start the bot
print_status "Building Docker image..."
docker-compose build

print_status "Starting the bot..."
docker-compose up -d

# Wait a moment for startup
sleep 5

# Check if bot is running
if docker-compose ps | grep -q "Up"; then
    print_success "Bot is running successfully!"
    print_status "Container status:"
    docker-compose ps
else
    print_error "Bot failed to start. Checking logs..."
    docker-compose logs
    exit 1
fi

# Create systemd service for auto-restart
print_status "Creating systemd service for auto-restart..."
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null << EOF
[Unit]
Description=VB International Telegram Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$BOT_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service

print_success "Systemd service created and started"

# Configure firewall (Oracle Cloud uses iptables)
print_status "Configuring firewall..."
# Allow SSH (port 22)
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
# Allow established connections
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# Allow loopback
sudo iptables -A INPUT -i lo -j ACCEPT
# Drop other incoming connections (default policy)
sudo iptables -P INPUT DROP

# Save iptables rules
sudo sh -c "iptables-save > /etc/iptables.rules"

# Create script to restore iptables on boot
sudo tee /etc/rc.local > /dev/null << 'EOF'
#!/bin/bash
iptables-restore < /etc/iptables.rules
exit 0
EOF
sudo chmod +x /etc/rc.local

print_success "Firewall configured"

# Setup log rotation
print_status "Setting up log rotation..."
sudo tee /etc/logrotate.d/telegram-bot > /dev/null << EOF
$BOT_DIR/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

# Create monitoring script
print_status "Creating monitoring script..."
tee $BOT_DIR/monitor.sh > /dev/null << 'EOF'
#!/bin/bash

# Simple monitoring script for the Telegram Bot
BOT_DIR="/opt/telegram-bot"
cd $BOT_DIR

# Check if container is running
if ! docker-compose ps | grep -q "Up"; then
    echo "$(date): Bot container is down. Restarting..." >> logs/monitor.log
    docker-compose up -d
    sleep 10
    
    # Check again
    if docker-compose ps | grep -q "Up"; then
        echo "$(date): Bot successfully restarted" >> logs/monitor.log
    else
        echo "$(date): Failed to restart bot. Manual intervention required." >> logs/monitor.log
    fi
else
    echo "$(date): Bot is running normally" >> logs/monitor.log
fi

# Clean old logs (keep last 100 lines)
if [ -f logs/monitor.log ]; then
    tail -n 100 logs/monitor.log > logs/monitor.log.tmp
    mv logs/monitor.log.tmp logs/monitor.log
fi
EOF

chmod +x $BOT_DIR/monitor.sh

# Add monitoring to crontab
print_status "Setting up automatic monitoring..."
(crontab -l 2>/dev/null; echo "*/5 * * * * $BOT_DIR/monitor.sh") | crontab -

print_success "Monitoring script installed (runs every 5 minutes)"

# Create management aliases
print_status "Creating management aliases..."
tee -a ~/.bashrc > /dev/null << EOF

# Telegram Bot Management Aliases
alias bot-status='cd /opt/telegram-bot && docker-compose ps'
alias bot-logs='cd /opt/telegram-bot && docker-compose logs -f'
alias bot-restart='cd /opt/telegram-bot && docker-compose restart'
alias bot-stop='cd /opt/telegram-bot && docker-compose down'
alias bot-start='cd /opt/telegram-bot && docker-compose up -d'
alias bot-update='cd /opt/telegram-bot && git pull && docker-compose build && docker-compose up -d'
alias bot-dir='cd /opt/telegram-bot'
EOF

# Display final information
echo ""
print_success "🎉 Oracle Cloud deployment completed successfully!"
echo ""
print_status "Bot Information:"
echo "  📂 Bot Directory: $BOT_DIR"
echo "  🐳 Container Status: $(docker-compose ps --format 'table {{.Service}}\t{{.Status}}')"
echo "  📝 Log Location: $BOT_DIR/logs/"
echo ""
print_status "Useful Commands:"
echo "  bot-status    - Check bot status"
echo "  bot-logs      - View bot logs"
echo "  bot-restart   - Restart bot"
echo "  bot-stop      - Stop bot"
echo "  bot-start     - Start bot"
echo "  bot-update    - Update bot from git"
echo ""
print_status "Next Steps:"
echo "  1. Make sure your .env file has the correct TELEGRAM_BOT_TOKEN"
echo "  2. Test the bot by sending /start to your Telegram bot"
echo "  3. Monitor logs with: bot-logs"
echo ""
print_warning "Note: Reload your shell to use the new aliases: source ~/.bashrc"
EOF