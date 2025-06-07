import time

import os

PYTHON_CMD = 'python3.8'

while True:
    os.system(f'{PYTHON_CMD} actions.py')
    time.sleep(1)
    print('actions rebooted')