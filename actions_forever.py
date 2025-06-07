import time
import os
from getpass import getpass

PYTHON_CMD = 'python3.8'

print('MongoDB requires a password!')
db_password = getpass()

while True:
    # janky password passing to prevent need of password for every restart
    f = open('temppass.txt', 'w')
    f.write(db_password)
    f.close()
    os.system(f'{PYTHON_CMD} actions.py')
    time.sleep(1)
    print('actions rebooted')