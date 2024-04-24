import logging
import sys


def configure_logger(name=__name__, log_level="DEBUG"):
  """Configures a logger with the specified name, level, and file."""

  logger = logging.getLogger(name)
  logger.propagate = False
  logger.setLevel("CRITICAL")

  # Create a file handler
  fh = logging.StreamHandler(sys.stdout)
  # file_handler = logging.FileHandler(sys.stderr)
  fh.setLevel(log_level)

  # Define a formatter for the log messages
  formatter = logging.Formatter(
    "[%(asctime)s] - %(levelname)s [%(funcName)s]: %(message)s"
    )
  fh.setFormatter(formatter)

  # Add the handler to the logger
  logger.addHandler(fh)

  return logger


# logger = logging.getLogger(__package__)
# logger.setLevel(logging.INFO)

# ch = logging.StreamHandler(sys.stdout)
# ch.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s - %(levelname)s [%(funcName)s]:  %(message)s')
# ch.setFormatter(formatter)
# logger.addHandler(ch)

logger = configure_logger(__name__)