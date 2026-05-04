import logging
import os
from datetime import datetime

# Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure basic logger
log_filename = f"logs/robot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

def get_logger(name):
    return logging.getLogger(name)
