import mysql.connector

# Kết nối vào DB chứa bảng 'accounts'
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='test',  # Chứa bảng accounts
    charset='utf8mb4'
)

cursor = conn.cursor()

# Truy vấn cập nhật lop_truc từ bảng phancong_db.phan_cong
update_query = """
UPDATE accounts AS a
JOIN phancong_db.phan_cong AS p ON a.lop = p.lop AND a.tuan = p.tuan
SET a.lop_truc = p.lop_truc
"""

cursor.execute(update_query)
conn.commit()

print("✅ Đã cập nhật thành công cột lop_truc trong bảng accounts.")

cursor.close()
conn.close()
