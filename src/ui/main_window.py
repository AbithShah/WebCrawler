import sys
import os
import asyncio
import psutil
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLineEdit, QPushButton, QLabel,
    QProgressBar, QSpinBox, QFileDialog, QMessageBox,
    QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime
from PyQt6.QtGui import QKeyEvent, QKeySequence
from typing import Optional
from src.crawler import WebCrawler, CrawlProgress

class CrawlerThread(QThread):
    progress_updated = pyqtSignal(CrawlProgress)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, crawler: WebCrawler, mode: str, url: str, max_concurrent: int = 5):
        super().__init__()
        self.crawler = crawler
        self.mode = mode
        self.url = url
        self.max_concurrent = max_concurrent
        self._is_running = False
        self.loop = None

    def run(self):
        try:
            self._is_running = True
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            if self.mode == "single":
                result = self.loop.run_until_complete(
                    self.crawler.crawl_single_page(self.url)
                )
                if self._is_running:
                    self.finished.emit({"result": result})
            else:
                results = self.loop.run_until_complete(
                    self.crawler.crawl_sitemap(self.url, self.max_concurrent)
                )
                if self._is_running:
                    self.finished.emit(results)
            
        except Exception as e:
            print(f"Error in crawler thread: {str(e)}")
            if self._is_running:
                self.error.emit(str(e))
        finally:
            self._is_running = False
            if self.loop and self.loop.is_running():
                self.loop.close()

    def stop(self):
        self._is_running = False
        if self.loop and self.loop.is_running():
            self.loop.stop()

class LineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebCrawler")
        self.setMinimumSize(800, 600)
        
        # Initialize timer for progress tracking
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_elapsed_time)
        self.start_time = None

        # Initialize variables
        self.crawler_thread: Optional[CrawlerThread] = None
        self.crawler = WebCrawler(self.update_progress)
        self.crawled_content = {}
        
        # Set the window style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                margin: 20px;
                padding: 0px;
            }
            QTabBar::tab {
                background-color: transparent;
                padding: 12px 30px;
                color: #666666;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                min-width: 180px;
                margin-right: 20px;  /* Add space between tabs */
                position: static;   /* Prevent animation */
            }
            QTabBar::tab:selected {
                background-color: white;
                border: 1px solid black;
                color: black;
            }
            QTabWidget::tab-bar {
                left: 20px;
                position: absolute;
            }
            /* Disable animations */
            QTabBar::tab:hover {
                position: static;
            }
            QTabWidget::tab-bar {
                position: static;
            }
            QTabWidget::pane {
                top: 0px;
            }
        """)
        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs)
        
        # Set up the UI
        self.setup_ui()
        
    def setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Add tabs
        self.setup_single_page_tab()
        self.setup_multi_page_tab()
        
    def setup_single_page_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # URL input
        url_layout = QHBoxLayout()
        self.single_url_input = LineEdit()
        self.single_url_input.setPlaceholderText("Enter URL...")
        self.single_url_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
                color: #000000;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #000000;
            }
        """)
        self.single_url_input.setMinimumHeight(40)
        url_layout.addWidget(self.single_url_input)
        layout.addLayout(url_layout)
        
        # Status section
        status_layout = QVBoxLayout()
        status_layout.setSpacing(15)
        
        status_header = QLabel("Status")
        status_header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #000000;
            }
        """)
        status_layout.addWidget(status_header)
        
        # Status text
        self.single_status_label = QLabel("Status: Ready to crawl")
        self.single_status_label.setStyleSheet("color: #000000;")
        status_layout.addWidget(self.single_status_label)
        
        self.single_time_label = QLabel("Time Elapsed: 0:00")
        self.single_time_label.setStyleSheet("color: #000000;")
        status_layout.addWidget(self.single_time_label)
        
        self.single_memory_label = QLabel("Memory Usage: 0 MB")
        self.single_memory_label.setStyleSheet("color: #000000;")
        status_layout.addWidget(self.single_memory_label)
        
        # Progress bar
        self.single_progress_bar = QProgressBar()
        self.single_progress_bar.setTextVisible(True)
        self.single_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.single_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                text-align: center;
                height: 20px;
                color: #000000;
                padding: 0px;
                background-color: #f5f5f5;
            }
            QProgressBar::chunk {
                background-color: black;
                border-radius: 3px;
            }
        """)
        self.single_progress_bar.setFormat("%p%")
        status_layout.addWidget(self.single_progress_bar)
        
        # Success message
        self.single_success_label = QLabel("✓ Crawling completed successfully!")
        self.single_success_label.setStyleSheet("color: #4CAF50;")
        self.single_success_label.hide()
        status_layout.addWidget(self.single_success_label)
        
        layout.addLayout(status_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.single_start_button = QPushButton("Start")
        self.single_stop_button = QPushButton("Stop")
        self.single_export_button = QPushButton("Export")
        
        button_style = """
            QPushButton {
                padding: 12px 30px;
                border-radius: 4px;
                font-size: 14px;
                border: 1px solid black;
                color: black;
                background-color: white;
            }
            QPushButton:disabled {
                border-color: #cccccc;
                color: #999999;
            }
        """
        
        self.single_start_button.setStyleSheet(button_style + """
            background-color: black;
            color: white;
            border: none;
        """)
        self.single_stop_button.setStyleSheet(button_style)
        self.single_export_button.setStyleSheet(button_style)
        
        self.single_start_button.clicked.connect(lambda: self.start_crawling("single"))
        self.single_stop_button.clicked.connect(self.stop_crawling)
        self.single_export_button.clicked.connect(self.export_results)
        
        self.single_stop_button.setEnabled(False)
        self.single_export_button.setEnabled(False)
        
        button_layout.addWidget(self.single_start_button)
        button_layout.addWidget(self.single_stop_button)
        button_layout.addStretch()
        button_layout.addWidget(self.single_export_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.tabs.addTab(tab, "Single Page Crawler")

    def setup_multi_page_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # URL input with auto-sitemap functionality
        url_layout = QHBoxLayout()
        self.sitemap_url_input = LineEdit()
        self.sitemap_url_input.setPlaceholderText("Enter website URL (sitemap.xml will be appended automatically)")
        self.sitemap_url_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
                color: #000000;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #000000;
            }
        """)
        self.sitemap_url_input.setMinimumHeight(40)
        self.sitemap_url_input.textChanged.connect(self.handle_sitemap_url_change)
        url_layout.addWidget(self.sitemap_url_input)
        layout.addLayout(url_layout)
        
        # Max concurrent setting
        concurrent_layout = QHBoxLayout()
        concurrent_label = QLabel("Max Concurrent Crawls:")
        concurrent_label.setStyleSheet("color: #000000; font-size: 14px;")
        self.max_concurrent_input = QSpinBox()
        self.max_concurrent_input.setRange(1, 20)
        self.max_concurrent_input.setValue(5)
        self.max_concurrent_input.setFixedWidth(100)
        self.max_concurrent_input.setStyleSheet("""
            QSpinBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                color: #000000;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                border: none;
                background: #000000;
                width: 16px;
                border-radius: 2px;
                margin: 1px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #333333;
            }
            QSpinBox::up-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 5px solid white;
            }
            QSpinBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
            }
        """)
        concurrent_layout.addWidget(concurrent_label)
        concurrent_layout.addWidget(self.max_concurrent_input)
        concurrent_layout.addStretch()
        layout.addLayout(concurrent_layout)
        
        # Status section
        status_layout = QVBoxLayout()
        status_layout.setSpacing(15)
        
        status_header = QLabel("Status")
        status_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #000000;")
        status_layout.addWidget(status_header)
        
        self.sitemap_status_label = QLabel("Status: Ready to crawl")
        self.sitemap_status_label.setStyleSheet("color: #000000;")
        status_layout.addWidget(self.sitemap_status_label)
        
        self.sitemap_time_label = QLabel("Time Elapsed: 0:00")
        self.sitemap_time_label.setStyleSheet("color: #000000;")
        status_layout.addWidget(self.sitemap_time_label)
        
        self.sitemap_memory_label = QLabel("Memory Usage: 0 MB")
        self.sitemap_memory_label.setStyleSheet("color: #000000;")
        status_layout.addWidget(self.sitemap_memory_label)
        
        # Progress bar
        self.sitemap_progress_bar = QProgressBar()
        self.sitemap_progress_bar.setTextVisible(True)
        self.sitemap_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sitemap_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                text-align: center;
                height: 20px;
                color: #000000;
                padding: 0px;
                background-color: #f5f5f5;
            }
            QProgressBar::chunk {
                background-color: black;
                border-radius: 3px;
            }
        """)
        self.sitemap_progress_bar.setFormat("%p%")
        status_layout.addWidget(self.sitemap_progress_bar)
        
        self.sitemap_progress_details = QLabel("Pages Crawled: 0/0")
        self.sitemap_progress_details.setStyleSheet("color: #000000;")
        status_layout.addWidget(self.sitemap_progress_details)
        
        # Success message
        self.sitemap_success_label = QLabel("✓ Crawling completed successfully!")
        self.sitemap_success_label.setStyleSheet("color: #4CAF50;")
        self.sitemap_success_label.hide()
        status_layout.addWidget(self.sitemap_success_label)
        
        layout.addLayout(status_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.sitemap_start_button = QPushButton("Start")
        self.sitemap_stop_button = QPushButton("Stop")
        self.sitemap_export_button = QPushButton("Export")
        
        button_style = """
            QPushButton {
                padding: 12px 30px;
                border-radius: 4px;
                font-size: 14px;
                border: 1px solid black;
                color: black;
                background-color: white;
            }
            QPushButton:disabled {
                border-color: #cccccc;
                color: #999999;
            }
        """
        
        self.sitemap_start_button.setStyleSheet(button_style + """
            background-color: black;
            color: white;
            border: none;
        """)
        self.sitemap_stop_button.setStyleSheet(button_style)
        self.sitemap_export_button.setStyleSheet(button_style)
        
        self.sitemap_start_button.clicked.connect(lambda: self.start_crawling("sitemap"))
        self.sitemap_stop_button.clicked.connect(self.stop_crawling)
        self.sitemap_export_button.clicked.connect(self.export_results)
        
        self.sitemap_stop_button.setEnabled(False)
        self.sitemap_export_button.setEnabled(False)
        
        button_layout.addWidget(self.sitemap_start_button)
        button_layout.addWidget(self.sitemap_stop_button)
        button_layout.addStretch()
        button_layout.addWidget(self.sitemap_export_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.tabs.addTab(tab, "Multi-Page Crawler")

    def handle_sitemap_url_change(self, url: str):
        """Automatically handle sitemap URL formatting"""
        try:
            # Remove any existing sitemap.xml from the URL
            url = url.replace('/sitemap.xml', '')
            # Remove trailing slash if exists
            url = url.rstrip('/')
            # Only auto-append sitemap.xml if a valid URL is entered
            if url and ('http://' in url or 'https://' in url):
                # Add sitemap.xml to the URL
                formatted_url = f"{url}/sitemap.xml"
                # Only update if different to avoid infinite loop
                if formatted_url != self.sitemap_url_input.text():
                    self.sitemap_url_input.setText(formatted_url)
        except Exception as e:
            print(f"Error formatting sitemap URL: {e}")

    def safe_update_ui(self, func):
        """Safely execute UI updates"""
        try:
            print("safe_update_ui called")
            QTimer.singleShot(10, lambda: self._execute_update(func))  # Reduced from 100 to 10ms
            print("Update scheduled with 10ms delay")
        except Exception as e:
            print(f"Error in safe_update_ui: {str(e)}")

    def _execute_update(self, func):
        """Execute the update and log any errors"""
        try:
            print("\n=== Executing UI Update ===")
            print("Starting UI update execution")
            func()
            
            # Add specific progress bar value check
            current_tab = self.tabs.currentIndex()
            if current_tab == 1:  # Sitemap tab
                current_value = self.sitemap_progress_bar.value()
                current_text = self.sitemap_progress_details.text()
                print(f"Progress bar value: {current_value}")
                print(f"Progress details text: {current_text}")
            
            print("UI update completed successfully")
            
        except Exception as e:
            print(f"Error executing UI update: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")

    def update_progress(self, progress: CrawlProgress):
        try:
            print("\n=== Progress Update Debug ===")
            print(f"Pages Crawled: {progress.pages_crawled}/{progress.total_pages}")
            print(f"Status: {progress.status}")
            print(f"Memory: {progress.memory_usage:.1f} MB")
            
            # Direct updates for progress-related UI
            if self.tabs.currentIndex() == 1:  # Sitemap tab
                # Update progress bar directly
                if progress.total_pages > 0:
                    percentage = min(100, int((progress.pages_crawled / progress.total_pages) * 100))
                    self.sitemap_progress_bar.setValue(percentage)
                    self.sitemap_progress_details.setText(f"Pages Crawled: {progress.pages_crawled}/{progress.total_pages}")
                    print(f"Set progress bar to {percentage}% and updated text")
            
            # Use safe update for non-progress UI elements
            def update_other_ui():
                try:
                    if self.tabs.currentIndex() == 1:  # Sitemap tab
                        self.sitemap_status_label.setText(f"Status: {progress.status}")
                        self.sitemap_memory_label.setText(f"Memory Usage: {progress.memory_usage:.1f} MB")
                        
                        if progress.is_complete:
                            self.sitemap_export_button.setEnabled(True)
                except Exception as e:
                    print(f"Error in update_other_ui: {str(e)}")
            
            self.safe_update_ui(update_other_ui)
            
        except Exception as e:
            print(f"Error in update_progress: {str(e)}")

    def start_crawling(self, mode: str):
        try:
            if self.crawler_thread and self.crawler_thread.isRunning():
                print("Crawler already running")
                return
                
            print(f"Starting {mode} crawl...")
            
            if mode == "single":
                url = self.single_url_input.text().strip()
                if not url:
                    QMessageBox.warning(self, "Error", "Please enter a URL")
                    return
                print(f"Single page URL: {url}")
                self.single_progress_bar.setValue(0)
                self.single_start_button.setEnabled(False)
                self.single_stop_button.setEnabled(True)
                self.single_export_button.setEnabled(False)
                self.single_success_label.hide()
            else:
                url = self.sitemap_url_input.text().strip()
                if not url:
                    QMessageBox.warning(self, "Error", "Please enter a sitemap URL")
                    return
                print(f"Sitemap URL: {url}")
                self.sitemap_progress_bar.setValue(0)
                self.sitemap_start_button.setEnabled(False)
                self.sitemap_stop_button.setEnabled(True)
                self.sitemap_export_button.setEnabled(False)
                self.sitemap_success_label.hide()
            
            self.start_time = QDateTime.currentDateTime()
            self.timer.start(1000)  # Update every second
            
            self.crawler_thread = CrawlerThread(
                self.crawler, 
                mode, 
                url, 
                self.max_concurrent_input.value()
            )
            self.crawler_thread.progress_updated.connect(self.update_progress)
            self.crawler_thread.finished.connect(self.crawling_finished)
            self.crawler_thread.error.connect(self.crawling_error)
            self.crawler_thread.start()
            
        except Exception as e:
            print(f"Error in start_crawling: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start crawler: {str(e)}")
            self.reset_ui_state(mode)

    def stop_crawling(self):
        try:
            print("Stopping crawler...")
            if self.crawler_thread and self.crawler_thread.isRunning():
                self.crawler_thread.terminate()
                self.crawler_thread.wait()
                
                current_tab = self.tabs.currentIndex()
                if current_tab == 0:  # Single page tab
                    self.single_stop_button.setEnabled(False)
                    self.single_start_button.setEnabled(True)
                    if self.crawled_content.get("result"):
                        self.single_export_button.setEnabled(True)
                else:  # Sitemap tab
                    self.sitemap_stop_button.setEnabled(False)
                    self.sitemap_start_button.setEnabled(True)
                    if self.crawled_content:
                        self.sitemap_export_button.setEnabled(True)
                
                self.timer.stop()
                
                # Show message about partial export
                if self.crawled_content:
                    pages = len(self.crawled_content) if isinstance(self.crawled_content, dict) else 0
                    QMessageBox.information(self, "Stopped", 
                        f"Crawler stopped. {pages} pages were crawled.\nYou can export the collected content.")
                
        except Exception as e:
            print(f"Error in stop_crawling: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to stop crawler: {str(e)}")

    def reset_ui_state(self, mode: str):
        """Reset UI elements to their initial state"""
        if mode == "single":
            self.single_start_button.setEnabled(True)
            self.single_stop_button.setEnabled(False)
            self.single_export_button.setEnabled(False)
            self.single_progress_bar.setValue(0)
            self.single_status_label.setText("Status: Ready")
            self.single_memory_label.setText("Memory Usage: 0 MB")
            self.single_time_label.setText("Time Elapsed: 0:00")
        else:
            self.sitemap_start_button.setEnabled(True)
            self.sitemap_stop_button.setEnabled(False)
            self.sitemap_export_button.setEnabled(False)
            self.sitemap_progress_bar.setValue(0)
            self.sitemap_status_label.setText("Status: Ready")
            self.sitemap_memory_label.setText("Memory Usage: 0 MB")
            self.sitemap_time_label.setText("Time Elapsed: 0:00")
            self.sitemap_progress_details.setText("Pages Crawled: 0/0")

    def update_elapsed_time(self):
        """Update elapsed time and memory usage in UI"""
        if self.start_time:
            current_time = QDateTime.currentDateTime()
            elapsed = self.start_time.secsTo(current_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # Update memory usage
            memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            
            current_tab = self.tabs.currentIndex()
            if current_tab == 0:  # Single page tab
                self.single_time_label.setText(f"Time Elapsed: {time_str}")
                self.single_memory_label.setText(f"Memory Usage: {memory_mb:.1f} MB")
            else:  # Sitemap tab
                self.sitemap_time_label.setText(f"Time Elapsed: {time_str}")
                self.sitemap_memory_label.setText(f"Memory Usage: {memory_mb:.1f} MB")

    def crawling_finished(self, results: dict):
        try:
            print("Crawling finished successfully")
            self.crawled_content = results
            current_tab = self.tabs.currentIndex()
            
            if current_tab == 0:  # Single page tab
                if results.get("result"):
                    self.single_export_button.setEnabled(True)
                    self.single_success_label.show()
                else:
                    self.single_status_label.setText("Status: No content retrieved")
                self.single_stop_button.setEnabled(False)
                self.single_start_button.setEnabled(True)
            else:  # Sitemap tab
                if results:
                    self.sitemap_export_button.setEnabled(True)
                    self.sitemap_success_label.show()
                    print(f"Successfully crawled {len(results)} pages")
                else:
                    self.sitemap_status_label.setText("Status: No content retrieved")
                self.sitemap_stop_button.setEnabled(False)
                self.sitemap_start_button.setEnabled(True)
            
            self.timer.stop()
            message = f"Crawling completed successfully!\nPages crawled: {len(results)}"
            QMessageBox.information(self, "Success", message)
            
        except Exception as e:
            print(f"Error in crawling_finished: {str(e)}")
            self.crawling_error(str(e))

    def crawling_error(self, error_message: str):
        print(f"Crawling error: {error_message}")
        self.timer.stop()  # Stop timer on error
        QMessageBox.critical(self, "Error", f"An error occurred during crawling:\n{error_message}")
        current_tab = self.tabs.currentIndex()
        self.reset_ui_state("single" if current_tab == 0 else "sitemap")

    def export_results(self):
        try:
            if not self.crawled_content:
                QMessageBox.warning(self, "Error", "No content to export")
                return
            
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Save Content",
                "",
                "Text Files (*.txt)"
            )
            
            if filepath:
                if not filepath.endswith('.txt'):
                    filepath += '.txt'
                
                content = ""
                if isinstance(self.crawled_content, dict):
                    if "result" in self.crawled_content:  # Single page result
                        content = self.crawled_content["result"]
                    else:  # Sitemap results
                        for url, page_content in self.crawled_content.items():
                            content += f"\n\n=== {url} ===\n\n{page_content}"
                
                success = self.crawler.export_to_txt(content, filepath)
                if success:
                    QMessageBox.information(self, "Success", 
                        f"Content exported successfully to:\n{filepath}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to export content")
                    
        except Exception as e:
            print(f"Error in export_results: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export results: {str(e)}")