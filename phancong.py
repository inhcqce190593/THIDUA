from flask import Flask, render_template, request, redirect, session, url_for
from functools import wraps
import pymysql

# Khởi tạo Flask app
app = Flask(__name__)
app.secret_key = 'secret123'  # Khóa bảo mật session

# Cấu hình kết nối cơ sở dữ liệu MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'phancong_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Hàm kết nối đến cơ sở dữ liệu MySQL
def get_db_connection():
    return pymysql.connect(**db_config)

# Decorator kiểm tra người dùng đã đăng nhập hay chưa
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))  # Nếu chưa đăng nhập thì chuyển hướng đến trang login
        return f(*args, **kwargs)
    return decorated_function

# Trang gốc, chuyển hướng đến /home
@app.route('/')
def root():
    return redirect(url_for('home'))

# Trang đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            # Đăng nhập thành công, lưu session
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('home'))
        return render_template('login.html', error="Sai tài khoản hoặc mật khẩu")
    return render_template('login.html')

# Trang chính (home)
@app.route('/home')
@login_required
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)
