from flask import Flask, render_template, request
import mysql.connector

app = Flask(__name__)

# Cấu hình MySQL (thay đổi theo cấu hình của bạn)
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "your_password",
    "database": "test"  # database chính (bên ngoài)
}

# Nếu trong hệ thống MySQL của bạn, 'test' là database chính, còn 'test' bên trong là schema hoặc namespace,
# bạn có thể cần thêm phần tiền tố cho bảng, hoặc truy vấn đúng cú pháp.


def get_db():
    conn = mysql.connector.connect(**db_config)
    return conn

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

def save_phancong(khoi, lop, phan_cong):
    conn = get_db()
    cursor = conn.cursor()
    # Xóa dữ liệu cũ của lớp này trước
    cursor.execute("DELETE FROM phan_cong_truc WHERE khoi=%s AND lop=%s", (khoi, lop))
    # Thêm mới phân công
    for tuan, lop_truc in enumerate(phan_cong, start=1):
        cursor.execute("INSERT INTO phan_cong_truc (khoi, lop, tuan, lop_truc) VALUES (%s, %s, %s, %s)",
                       (khoi, lop, tuan, lop_truc))
    conn.commit()
    cursor.close()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    result = []
    if request.method == "POST":
        khoi = request.form.get("khoi", "10")
        so_lop = int(request.form.get("so_lop", 20))
        so_tuan = int(request.form.get("so_tuan", 21))
        danh_sach_lop = [f"{khoi}A{i}" for i in range(1, so_lop + 1)]

        for i in range(so_lop):
            lop_hien_tai = danh_sach_lop[i]
            phan_cong = []
            j = 1
            while len(phan_cong) < so_tuan:
                index = (i + j) % so_lop
                lop_truc = danh_sach_lop[index]
                # Tuần 20 và 21, lớp tự trực không phải lớp mình
                # Nếu tuần 20 (tuan == 20) lớp trực không phải lớp mình (đã logic sẵn)
                # Bạn có thể tùy chỉnh nếu cần
                if lop_truc != lop_hien_tai:
                    phan_cong.append(lop_truc)
                j += 1
            save_phancong(khoi, lop_hien_tai, phan_cong)
            result.append({
                "khoi": khoi,
                "lop": lop_hien_tai,
                "phan_cong": phan_cong
            })
    else:
        # Load dữ liệu từ DB khi GET
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT khoi, lop, tuan, lop_truc FROM phan_cong_truc ORDER BY lop, tuan")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        from collections import defaultdict
        tmp = defaultdict(lambda: {"phan_cong": []})
        for khoi, lop, tuan, lop_truc in rows:
            tmp[lop]["khoi"] = khoi
            tmp[lop]["lop"] = lop
            tmp[lop]["phan_cong"].append(lop_truc)

        for lop, data in tmp.items():
            result.append(data)

    return render_template("testphancong.html", result=result)


if __name__ == "__main__":
    create_table()
    app.run(debug=True)
