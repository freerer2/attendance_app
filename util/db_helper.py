import psycopg2.extras
from psycopg2 import pool
from contextlib import contextmanager
import atexit

from os import getenv
from dotenv import load_dotenv
load_dotenv()


class DBHelper:
    def __init__(self):
        self._connection_pool = None

    def initialize_connection_pool(self):
        self._connection_pool = pool.ThreadedConnectionPool(1,10,dbname=getenv('PGDATABASE')
                                                            , user=getenv('PGUSER')
                                                            , password=getenv('PGPASSWORD')
                                                            , host=getenv('PGHOST')
                                                            , port=getenv('PGPORT', 5432))

    @contextmanager
    def get_resource_rdb(self, autocommit=True):
        if self._connection_pool is None:
            self.initialize_connection_pool()

        conn = self._connection_pool.getconn()
        conn.autocommit = autocommit
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            yield cursor, conn
        finally:
            cursor.close()
            self._connection_pool.putconn(conn)

    def shutdown_connection_pool(self):
        if self._connection_pool is not None:
            self._connection_pool.closeall()

    def getconn(self, autocommit=True):
        if self._connection_pool is None:
            self.initialize_connection_pool()

        conn = self._connection_pool.getconn()
        conn.autocommit = autocommit
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        return cursor, conn

    def putconn(self, cursor, conn):
        cursor.close()
        self._connection_pool.putconn(conn)


db_helper = DBHelper()


@atexit.register
def shutdown_connection_pool():
    db_helper.shutdown_connection_pool()