from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Cấu hình MySQL (bạn có thể chỉnh lại nếu cần)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'phancong_db'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM accounts WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            session['username'] = user['username']
            session['lop'] = user['lop']
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Sai tài khoản hoặc mật khẩu")
    return render_template('login.html')

@app.route('/home')
@login_required
def home():
    lop_hien_tai = session.get('lop')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM phan_cong WHERE lop_truc = %s", (lop_hien_tai,))
    phan_cong = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('home.html', phan_cong=phan_cong, lop=lop_hien_tai, username=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
