import logging
import os
from datetime import datetime
import subprocess
import sys

from .ccp.platform_utils import get_platform_tmp_dir


__version__ = '0.1.0'


# logging.disable(logging.CRITICAL)

logger = logging.getLogger(__name__)

tmp_dir = get_platform_tmp_dir(sys.platform)
logging_directory_path = os.path.join(tmp_dir, 'ccp_logs')
if not os.path.exists(logging_directory_path):
    os.mkdir(logging_directory_path)

now_str = datetime.strftime(datetime.now(), '%Y-%m-%d_%Hh%Mm%Ss')
logging_file_path = os.path.join(
    'ccp',  # logging_directory_path,
    f'ccp-log_{now_str}.txt'
)

logging.basicConfig(
    level=logging.DEBUG,
    filename=logging_file_path,
    filemode='w',
    format='%(asctime)s.%(msecs)03d - %(module)s.%(funcName)s [%(levelname)s]:\n%(message)s',
    datefmt='(%Y-%m-%d) %H:%M:%S',
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(fmt='%(message)s')
console_handler.setFormatter(console_formatter)


logging.getLogger('').addHandler(console_handler)


# ---- CONSOLE ----
MAX_CONSOLE_WIDTH = 200

try:
    terminal_width = min(os.get_terminal_size().columns, MAX_CONSOLE_WIDTH)
except OSError:
    logger.error('Could not find OS terminal size.')
    terminal_width = MAX_CONSOLE_WIDTH

logger.debug('Terminal width set as %d columns.', terminal_width)

