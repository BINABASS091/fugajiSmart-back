"""
Setup script for monitoring and logging configuration.
"""
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories for logs and monitoring."""
    base_dir = Path(__file__).parent
    dirs_to_create = [
        base_dir / 'logs',
        base_dir / 'metrics',
    ]
    
    for directory in dirs_to_create:
        try:
            directory.mkdir(exist_ok=True)
            logger.info(f"Created directory: {directory}")
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")

def setup_logging_config():
    """Generate logging configuration."""
    config = """# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/debug.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose'
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'logs/error.log',
            'formatter': 'verbose'
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
"""
    return config

def main():
    """Main setup function."""
    logger.info("Starting monitoring setup...")
    
    # Create necessary directories
    setup_directories()
    
    # Generate logging config
    logging_config = setup_logging_config()
    
    # Write to a separate logging config file
    with open('logging_config.py', 'w') as f:
        f.write(logging_config)
    
    logger.info("Monitoring setup completed successfully!")
    logger.info("Next steps:")
    logger.info("1. Update your Django settings to import the logging configuration")
    logger.info("2. Configure your web server to expose the metrics endpoint")
    logger.info("3. Set up log rotation and monitoring for the log files")

if __name__ == "__main__":
    main()
