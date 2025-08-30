import mysql.connector

# Kết nối MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",           # Tài khoản mặc định XAMPP
    password="",           # Mật khẩu thường để trống nếu dùng XAMPP
    database="test"        # Tên database của bạn
)

cursor = conn.cursor()

# Cập nhật lop_truc trong bảng accounts từ bảng phancong dựa trên lop và tuan
update_query = """
UPDATE accounts AS a
JOIN phancong AS p ON a.lop = p.lop AND a.tuan = p.tuan
SET a.lop_truc = p.lop_truc
"""

cursor.execute(update_query)
conn.commit()

print("Đã cập nhật xong cột lop_truc trong bảng accounts.")

# Đóng kết nối
cursor.close()
conn.close()
