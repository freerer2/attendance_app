import os
from dotenv import load_dotenv

import threading

from util.db_helper import db_helper
from attendance import Attendance

load_dotenv()


if __name__ == '__main__':

    with db_helper.get_resource_rdb() as (cursor, _):
        cursor.execute(os.getenv('DOMAIN_LIST'))
        domain_accnt_list = cursor.fetchall()

    if len(domain_accnt_list) > 0:
        for domain_accnt_data in domain_accnt_list:
            thread = threading.Thread(target=Attendance(domain_accnt_data).run)
            thread.start()
