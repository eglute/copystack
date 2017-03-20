import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

logger = logging.getLogger('copystack')
logger.setLevel(logging.DEBUG)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# swift_logger = logging.getLogger('swiftclient')
# swift_logger.setLevel(logging.DEBUG)

