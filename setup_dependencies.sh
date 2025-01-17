#!/bin/bash

# Exit on error
set -e

# Function to show dialog
show_dialog() {
    osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\""
}

# Show start dialog
show_dialog "WebCrawler will now install required dependencies. Click OK to continue."

echo "Installing dependencies..."

# Install Homebrew if not present
if ! command -v brew &> /dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Install Python if not present
brew install python@3.11

# Install pip packages
pip3 install --upgrade pip
pip3 install PyQt6 requests psutil crawl4ai asyncio aiohttp playwright

# Install Playwright browser
python3 -m playwright install chromium

# Show completion dialog
show_dialog "Dependencies installation complete! You can now use WebCrawler."
