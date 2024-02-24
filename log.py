import logging

logger = logging.getLogger('dog_detect')
logger.setLevel(logging.DEBUG)

def log_to_console(level):

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    ch = logging.StreamHandler()

    if level == 1:
        ch.setLevel(logging.INFO)
    else:
        ch.setLevel(logging.DEBUG)

    ch.setFormatter(formatter)

    logger.addHandler(ch)

def log_to_file(filename, level=2):
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    ch = logging.FileHandler(filename, mode='a')

    if level == 1:
        ch.setLevel(logging.INFO)
    else:
        ch.setLevel(logging.DEBUG)

    ch.setFormatter(formatter)

    logger.addHandler(ch)
