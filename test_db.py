import mysql.connector

cfg = {
    'host': '127.0.0.1',
    'port': 3306,  # hoặc 3307 nếu Laragon dùng 3307
    'user': 'root',
    'password': '',
    'database': 'test'
}

conn = mysql.connector.connect(**cfg)
cur = conn.cursor()
cur.execute("SHOW TABLES;")
print(cur.fetchall())
conn.close()
