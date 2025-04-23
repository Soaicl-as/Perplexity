import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    
    # Selenium settings
    HEADLESS = os.environ.get('HEADLESS', 'True').lower() == 'true'
    
    # Instagram settings
    DEFAULT_MIN_DELAY = 30  # seconds
    DEFAULT_MAX_DELAY = 60  # seconds
    MAX_EXTRACTION_COUNT = 1000
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
