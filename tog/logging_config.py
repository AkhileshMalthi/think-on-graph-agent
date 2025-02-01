import logging

# Create a logger
logger = logging.getLogger(__name__)
logger.propagate = False

# Set the logging level
logger.setLevel(logging.DEBUG) 

# Create both console and file handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('tog\\tog_logs.log')

console_handler.setLevel(logging.DEBUG)
file_handler.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Add formatter to handlers
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
