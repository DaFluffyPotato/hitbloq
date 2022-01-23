import time
import traceback
from datetime import datetime

def error_catch(func, *args, group_id=None, retry=0, retry_delay=0, **kwargs):
    while retry >= 0:
        try:
            func(*args, **kwargs)
            break
        except KeyboardInterrupt:
            raise KeyboardInterrupt()
        except Exception:
            print('error on group:', group_id)

            error = traceback.format_exc()

            error_log_name = 'errors'
            if group_id:
                error_log_name += '_' + group_id

            f = open('logs/' + error_log_name + '.log', 'a')
            error_header = datetime.now().strftime('%d/%m/%Y - %H:%M:%S') + '\n'
            f.write(error_header + error + '\n<---------------->\n')
            f.close()

            retry -= 1
            if retry_delay and retry >= 0:
                time.sleep(retry_delay)
