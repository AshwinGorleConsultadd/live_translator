import logging
import os
from datetime import datetime

def setup_logging():
    """Set up logging configuration for the translator application."""
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create timestamp for log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"translator_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Create specific loggers for each module
    loggers = {
        'audio_capture': logging.getLogger('audio_capture'),
        'translation': logging.getLogger('translation'),
        'tts': logging.getLogger('tts'),
        'audio_output': logging.getLogger('audio_output'),
        'main': logging.getLogger('main')
    }
    
    return loggers

def get_logger(module_name):
    """Get a logger for a specific module."""
    return logging.getLogger(module_name)
