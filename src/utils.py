# This file will contain utility functions.

import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

# Set up logging with both console and daily rotating file
def setup_logging():
    # Create logs directory in AppData/Local/COMRADE
    appdata_local = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
    log_dir = os.path.join(appdata_local, 'COMRADE')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with daily rotation using COMRADE-YYYY-MM-DD.log format
    today = datetime.now().strftime('%Y-%m-%d')
    log_filename = os.path.join(log_dir, f'COMRADE-{today}.log')
    file_handler = TimedRotatingFileHandler(
        log_filename,
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    # Custom namer function to create COMRADE-YYYY-MM-DD.log format
    def custom_namer(default_name):
        # Extract the date from the default name and format it properly
        base_dir = os.path.dirname(default_name)
        # The default name will be something like COMRADE-2025-07-02.log.2025-07-03
        # We want to extract the date and create COMRADE-YYYY-MM-DD.log
        parts = os.path.basename(default_name).split('.')
        if len(parts) >= 2:
            date_part = parts[-1]  # Get the date suffix
            return os.path.join(base_dir, f'COMRADE-{date_part}.log')
        return default_name
    
    file_handler.namer = custom_namer
    root_logger.addHandler(file_handler)

def darken_color(color):
    """Darken a hex color by 20%"""
    color = color.lstrip('#')
    rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    darkened = tuple(int(c * 0.8) for c in rgb)
    return '#%02x%02x%02x' % darkened
