import os
import time
from dotenv import load_dotenv
from util.db_helper import db_helper

load_dotenv()

# cursor, conn = db_helper.getconn()


class Log(object):

    def __init__(self, attendance_id, attendance_account_id):
        self.attendance_id = attendance_id
        self.attendance_account_id = attendance_account_id

    def print(self, msg):
        with db_helper.get_resource_rdb() as (cursor, _):
            attendance_id = str(self.attendance_id)
            attendance_account_id = str(self.attendance_account_id)
            cursor.execute(os.getenv('INSERT_LOG'), (attendance_id,attendance_account_id,attendance_id,attendance_account_id,msg,))

        log_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
        print(f"{log_time} : [{attendance_id}, {attendance_account_id}] : {msg}")

    # def print(self, msg):
    #     attendance_id = str(self.attendance_id)
    #     attendance_account_id = str(self.attendance_account_id)
    #     cursor.execute(os.getenv('INSERT_LOG'), (attendance_id, attendance_account_id, attendance_id, attendance_account_id, msg,))
    #     print(f"[{attendance_id}, {attendance_account_id}] : {msg}")


# @atexit.register
# def shutdown_connection_pool():
#     log = Log(0, "None")
#     log.print("로그 커넥션 반환")
#     db_helper.putconn(cursor, conn)
