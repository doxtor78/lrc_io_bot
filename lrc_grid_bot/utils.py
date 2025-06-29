import logging
import sys

def setup_logger(level='INFO'):
    """
    Sets up a basic logger to print messages to the console.
    """
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    logger = logging.getLogger('LRCGridBot')
    logger.setLevel(level)
    
    # Prevent adding duplicate handlers if this function is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(log_format)
        logger.addHandler(handler)
        
    return logger

# Example usage:
# from utils import setup_logger
# logger = setup_logger()
# logger.info("This is an info message.")
# logger.error("This is an error message.") 