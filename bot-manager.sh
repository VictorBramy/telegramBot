#!/bin/bash

# Bot Management Interface
# Simple CLI tool for managing the Telegram Bot

BOT_DIR="/opt/telegram-bot"
SCRIPT_NAME="VB International Bot Manager"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Function to print header
print_header() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     ${WHITE}VB International Bot Manager     ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    echo ""
}

# Function to show bot status
show_status() {
    print_header
    echo -e "${CYAN}📊 Bot Status:${NC}"
    echo ""
    
    cd $BOT_DIR 2>/dev/null || {
        echo -e "${RED}❌ Bot directory not found: $BOT_DIR${NC}"
        return 1
    }
    
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Bot is RUNNING${NC}"
        echo ""
        docker-compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
    else
        echo -e "${RED}❌ Bot is STOPPED${NC}"
        echo ""
        docker-compose ps
    fi
    
    echo ""
    echo -e "${YELLOW}📝 Recent logs (last 10 lines):${NC}"
    docker-compose logs --tail=10
}

# Function to start bot
start_bot() {
    print_header
    echo -e "${YELLOW}🚀 Starting bot...${NC}"
    
    cd $BOT_DIR
    docker-compose up -d
    
    sleep 3
    
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Bot started successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to start bot${NC}"
    fi
}

# Function to stop bot
stop_bot() {
    print_header
    echo -e "${YELLOW}⏹️ Stopping bot...${NC}"
    
    cd $BOT_DIR
    docker-compose down
    
    echo -e "${GREEN}✅ Bot stopped${NC}"
}

# Function to restart bot
restart_bot() {
    print_header
    echo -e "${YELLOW}🔄 Restarting bot...${NC}"
    
    cd $BOT_DIR
    docker-compose restart
    
    sleep 3
    
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Bot restarted successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to restart bot${NC}"
    fi
}

# Function to view logs
view_logs() {
    print_header
    echo -e "${CYAN}📝 Bot Logs (Press Ctrl+C to exit):${NC}"
    echo ""
    
    cd $BOT_DIR
    docker-compose logs -f --tail=50
}

# Function to update bot
update_bot() {
    print_header
    echo -e "${YELLOW}🔨 Updating bot...${NC}"
    
    # Create backup first
    BACKUP_DIR="$HOME/bot-backups"
    mkdir -p $BACKUP_DIR
    BACKUP_FILE="$BACKUP_DIR/bot-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    echo "📦 Creating backup..."
    sudo tar -czf $BACKUP_FILE -C /opt telegram-bot
    echo "✅ Backup created: $BACKUP_FILE"
    
    cd $BOT_DIR
    
    echo "⏹️ Stopping bot..."
    docker-compose down
    
    echo "🔨 Rebuilding container..."
    docker-compose build --no-cache
    
    echo "🚀 Starting updated bot..."
    docker-compose up -d
    
    sleep 5
    
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Bot updated successfully!${NC}"
    else
        echo -e "${RED}❌ Update failed${NC}"
    fi
}

# Function to show system info
show_system_info() {
    print_header
    echo -e "${CYAN}💻 System Information:${NC}"
    echo ""
    
    echo -e "${YELLOW}🖥️ System:${NC}"
    uname -a
    echo ""
    
    echo -e "${YELLOW}💾 Memory Usage:${NC}"
    free -h
    echo ""
    
    echo -e "${YELLOW}💽 Disk Usage:${NC}"
    df -h / | tail -1
    echo ""
    
    echo -e "${YELLOW}🐳 Docker Info:${NC}"
    docker version --format 'Client: {{.Client.Version}} | Server: {{.Server.Version}}'
    echo ""
    
    echo -e "${YELLOW}📊 Container Stats:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

# Function to backup bot
backup_bot() {
    print_header
    echo -e "${YELLOW}📦 Creating backup...${NC}"
    
    BACKUP_DIR="$HOME/bot-backups"
    mkdir -p $BACKUP_DIR
    BACKUP_FILE="$BACKUP_DIR/bot-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    sudo tar -czf $BACKUP_FILE -C /opt telegram-bot
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup created successfully!${NC}"
        echo "📁 Location: $BACKUP_FILE"
        echo "📏 Size: $(ls -lh $BACKUP_FILE | awk '{print $5}')"
    else
        echo -e "${RED}❌ Backup failed${NC}"
    fi
}

# Main menu
show_menu() {
    print_header
    echo -e "${CYAN}Choose an option:${NC}"
    echo ""
    echo -e "${WHITE}1)${NC} 📊 Show Status"
    echo -e "${WHITE}2)${NC} 🚀 Start Bot"
    echo -e "${WHITE}3)${NC} ⏹️  Stop Bot"
    echo -e "${WHITE}4)${NC} 🔄 Restart Bot"
    echo -e "${WHITE}5)${NC} 📝 View Logs"
    echo -e "${WHITE}6)${NC} 🔨 Update Bot"
    echo -e "${WHITE}7)${NC} 💻 System Info"
    echo -e "${WHITE}8)${NC} 📦 Create Backup"
    echo -e "${WHITE}9)${NC} 🚪 Exit"
    echo ""
    echo -n -e "${YELLOW}Enter your choice [1-9]: ${NC}"
}

# Main loop
while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            show_status
            echo ""
            read -p "Press Enter to continue..."
            ;;
        2)
            start_bot
            sleep 2
            ;;
        3)
            stop_bot
            sleep 2
            ;;
        4)
            restart_bot
            sleep 2
            ;;
        5)
            view_logs
            ;;
        6)
            update_bot
            echo ""
            read -p "Press Enter to continue..."
            ;;
        7)
            show_system_info
            echo ""
            read -p "Press Enter to continue..."
            ;;
        8)
            backup_bot
            echo ""
            read -p "Press Enter to continue..."
            ;;
        9)
            print_header
            echo -e "${GREEN}👋 Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid option. Please try again.${NC}"
            sleep 1
            ;;
    esac
done