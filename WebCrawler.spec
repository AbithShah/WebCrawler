# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import crawl4ai

crawl4ai_path = os.path.dirname(crawl4ai.__file__)
js_snippet_path = os.path.join(crawl4ai_path, 'js_snippet')

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),
        *collect_data_files('playwright_stealth'),
        *collect_data_files('crawl4ai'),
        (js_snippet_path, 'crawl4ai/js_snippet')
    ],
    hiddenimports=[
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtCore.Qt',
        'fake_http_header',
        'fake_http_header.data',
        'playwright_stealth',
        'aiohttp',
        'asyncio',
        'xml.etree.ElementTree',
        'psutil',
        'requests',
        'playwright',
        'playwright.async_api',
        'crawl4ai'
    ],
    excludes=['playwright.driver.package.browsers'],
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WebCrawler',
    debug=False,  # Changed to False for production
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False  # Changed to False to hide console
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WebCrawler'
)

app = BUNDLE(
    coll,
    name='WebCrawler.app',
    icon='assets/icon.icns',
    bundle_identifier='com.webcrawler.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '10.13.0',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleDisplayName': 'WebCrawler',
        'CFBundleName': 'WebCrawler',
        'NSHumanReadableCopyright': 'Copyright © 2025',
        'LSEnvironment': {
            'PLAYWRIGHT_BROWSERS_PATH': '~/Library/Caches/ms-playwright'
        },
        # macOS Permissions and Capabilities
        'NSAppleEventsUsageDescription': 'Allow keyboard input and automation',
        'NSPasteboardUsageDescription': 'Allow copy and paste operations',
        'NSDownloadsFolderUsageDescription': 'Allow saving files',
        'NSDesktopFolderUsageDescription': 'Allow access to Desktop',
        'NSDocumentsFolderUsageDescription': 'Allow access to Documents',
        # Application Services
        'NSServices': [],
        'UTExportedTypeDeclarations': [],
        'UTImportedTypeDeclarations': [],
        # Additional required capabilities
        'LSRequiresNativeExecution': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        'NSRequiresAquaSystemAppearance': False,
    }
)
