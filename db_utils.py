import mysql.connector
from config import DB_CONFIG, PHAN_CONG_DB_CONFIG

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_db():
    return mysql.connector.connect(**PHAN_CONG_DB_CONFIG)

def create_table():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phan_cong_truc (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            khoi VARCHAR(10) NOT NULL,
            lop VARCHAR(10) NOT NULL,
            tuan INT NOT NULL,
            lop_truc VARCHAR(10) NOT NULL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def insert_schedule(data):
    conn = get_db()
    cursor = conn.cursor()
    for row in data:
        cursor.execute('''
            INSERT INTO phan_cong (khoi, tuan, lop, lop_truc)
            VALUES (%s, %s, %s, %s)
        ''', (row['khoi'], row['tuan'], row['from'], row['to']))
    conn.commit()
    cursor.close()
    conn.close()

def update_schedule(data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE phan_cong
        SET lop = %s, lop_truc = %s
        WHERE khoi = %s AND tuan = %s
    ''', (data['from'], data['to'], data['khoi'], data['tuan']))
    conn.commit()
    cursor.close()
    conn.close()

def clear_all_schedule():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM phan_cong')
    conn.commit()
    cursor.close()
    conn.close()

def save_phancong(khoi, lop, phan_cong):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM phan_cong_truc WHERE khoi=%s AND lop=%s", (khoi, lop))
    for tuan, lop_truc in enumerate(phan_cong, start=1):
        cursor.execute("INSERT INTO phan_cong_truc (khoi, lop, tuan, lop_truc) VALUES (%s, %s, %s, %s)",
                       (khoi, lop, tuan, lop_truc))
    conn.commit()
    cursor.close()
    conn.close()