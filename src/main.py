import sys
import os
import logging
from datetime import datetime

# Set up logging in the project directory
project_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(os.path.dirname(project_dir), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"webscout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('WebScout')

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

try:
    logger.info("Starting application")
    from PyQt6.QtWidgets import QApplication
    logger.info("Successfully imported QApplication")
    from src.ui.main_window import MainWindow
    logger.info("Successfully imported MainWindow")

    def main():
        try:
            logger.info("Initializing QApplication")
            app = QApplication(sys.argv)
            app.setStyle('Fusion')
            
            logger.info("Creating MainWindow")
            window = MainWindow()
            
            logger.info("Showing MainWindow")
            window.show()
            
            logger.info("Entering application main loop")
            sys.exit(app.exec())
            
        except Exception as e:
            logger.error(f"Error in main: {str(e)}", exc_info=True)
            raise

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}", exc_info=True)
            sys.exit(1)

except Exception as e:
    logger.error(f"Import error: {str(e)}", exc_info=True)
    sys.exit(1)
