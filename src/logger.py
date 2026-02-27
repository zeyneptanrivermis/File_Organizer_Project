import logging
import os

def get_logger(name="file_organizer"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        fh = logging.FileHandler(os.path.join(log_dir, "app.log"), encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger
