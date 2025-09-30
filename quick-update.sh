#!/bin/bash

# Quick deployment script for updates
# Use this for rapid updates without full deployment

set -e

BOT_DIR="/opt/telegram-bot"
BACKUP_DIR="$HOME/bot-backups"

echo "🔄 Quick Update for VB International Bot"

# Create backup
mkdir -p $BACKUP_DIR
BACKUP_FILE="$BACKUP_DIR/bot-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
echo "📦 Creating backup..."
sudo tar -czf $BACKUP_FILE -C /opt telegram-bot

# Navigate to bot directory
cd $BOT_DIR

# Stop current bot
echo "⏸️ Stopping current bot..."
sudo docker-compose down

# Update files (assuming they're already uploaded)
echo "📝 Updating files..."
# Files should already be updated via scp or git

# Rebuild and start
echo "🔨 Rebuilding container..."
sudo docker-compose build --no-cache

echo "🚀 Starting updated bot..."
sudo docker-compose up -d

# Wait for startup
sleep 10

# Check status
if sudo docker-compose ps | grep -q "Up"; then
    echo "✅ Bot updated successfully!"
    echo "📊 Container status:"
    sudo docker-compose ps
    echo ""
    echo "📝 To view logs: sudo docker-compose logs -f"
else
    echo "❌ Update failed. Checking logs..."
    sudo docker-compose logs
    
    echo "🔙 Restoring from backup..."
    cd /
    sudo tar -xzf $BACKUP_FILE
    cd $BOT_DIR
    sudo docker-compose up -d
    
    echo "⚠️ Restored from backup. Check the issue and try again."
fi

echo "🏁 Update process completed"