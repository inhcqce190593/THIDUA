from flask import Flask, render_template, redirect, url_for, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Để sử dụng flash message

# Cấu hình kết nối database
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'database': 'test'
}

def update_lop_truc():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        sql_query = """
        UPDATE accounts AS a
        JOIN phan_cong_truc AS pct ON a.tuan = pct.tuan AND a.lop = pct.lop
        SET a.lop_truc = pct.lop_truc;
        """
        cursor.execute(sql_query)
        conn.commit()
        return f"✅ Đã cập nhật {cursor.rowcount} bản ghi."
    except mysql.connector.Error as err:
        return f"❌ Lỗi cập nhật: {err}"
    finally:
        if conn.is_connected():
            conn.close()

@app.route('/')
def index():
    return render_template('updatedata.html')

@app.route('/update', methods=['POST'])
def update():
    message = update_lop_truc()
    flash(message)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Đổi sang cổng 5001 hoặc bất kỳ cổng nào chưa dùng

