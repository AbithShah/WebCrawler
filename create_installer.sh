#!/bin/bash

# Clean previous builds first
rm -rf build dist

# Build the app
pyinstaller WebCrawler.spec

# Create the DMG
create-dmg \
  --volname "WebCrawler Installer" \
  --volicon "assets/icon.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "WebCrawler.app" 200 190 \
  --hide-extension "WebCrawler.app" \
  --app-drop-link 600 185 \
  "dist/WebCrawler_Installer.dmg" \
  "dist/WebCrawler.app"
