import pymysql

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'phancong_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**db_config)
