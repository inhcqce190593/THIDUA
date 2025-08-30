from flask import Flask, render_template, request, redirect, session, url_for
from functools import wraps
import mysql.connector

# Khởi tạo Flask app
app = Flask(__name__)
app.secret_key = 'secret123'  # Khóa bảo mật session

# Hàm kết nối đến cơ sở dữ liệu MySQL
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='test'
    )




db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Mặc định XAMPP
    'database': 'phancong_db'
}

def insert_schedule(data):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    for row in data:
        khoi = row['khoi']
        tuan = row['tuan']
        lop = row['from']
        lop_truc = row['to']
        cursor.execute('''
            INSERT INTO phan_cong (khoi, tuan, lop, lop_truc)
            VALUES (%s, %s, %s, %s)
        ''', (khoi, tuan, lop, lop_truc))
    conn.commit()
    cursor.close()
    conn.close()

def update_schedule(data):
    conn = mysql.connector.connect(**db_config)
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
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM phan_cong')
    conn.commit()
    cursor.close()
    conn.close()

def get_all_schedule():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)  # dictionary=True để trả về dict
    cursor.execute('SELECT * FROM phan_cong ORDER BY khoi, tuan')
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results










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
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username'].strip()
#         password = request.form['password'].strip()
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute("SELECT * FROM accounts WHERE username=%s AND password=%s", (username, password))
#         user = cursor.fetchone()
#         cursor.close()
#         conn.close()

#         if user:
#             # Đăng nhập thành công, lưu session
#             session['username'] = user['username']
#             session['role'] = user['role']
#             return redirect(url_for('home'))
#         return render_template('login.html', error="Sai tài khoản hoặc mật khẩu")
#     return render_template('login.html')

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
            # Đăng nhập thành công, lưu session
            session['username'] = user['username']
            session['role'] = user['role']
            
            # Chuyển hướng theo vai trò
            if user['role'] == 'admin':
                return redirect(url_for('home'))
            elif user['role'] == 'user':
                return redirect(url_for('user'))
            elif user['role'] == 'viewer':
                return redirect(url_for('viewer'))
            else:
                return "Role không hợp lệ"
        
        return render_template('login.html', error="Sai tài khoản hoặc mật khẩu")
    
    return render_template('login.html')





# Trang chính
# @app.route('/home', methods=['GET', 'POST'])
# @login_required
# def home():
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)

#     if request.method == 'POST':
#         data_id = request.form.get('data_id')
#         data_type = request.form.get('data_type')

#         if 'delete_data' in request.form:
#             if data_type == 'study':
#                 cursor.execute("DELETE FROM study_data WHERE id = %s", (data_id,))
#             elif data_type == 'rules':
#                 cursor.execute("DELETE FROM rules_data WHERE id = %s", (data_id,))
#             conn.commit()

#         elif 'update_data' in request.form:
#             # Chuyển hướng đến trang cập nhật dữ liệu (tùy từng loại)
#             if data_type == 'study':
#                 return redirect(url_for('update_study_data', data_id=data_id))
#             elif data_type == 'rules':
#                 return redirect(url_for('update_rules_data', data_id=data_id))

#     # Lấy dữ liệu học tập
#     cursor.execute("SELECT * FROM study_data")
#     study_data = cursor.fetchall()

#     # Lấy dữ liệu vi phạm nội quy
#     cursor.execute("SELECT * FROM rules_data")
#     rules_data = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return render_template('home.html', study_data=study_data, rules_data=rules_data)






@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Xử lý chọn tuần
    if request.method == 'POST':
        # Nếu thiết lập tuần
        if 'set_week' in request.form:
            selected_week = request.form.get('week_select')
            session['tuan'] = selected_week

        # Nếu xóa/cập nhật dữ liệu
        else:
            data_id = request.form.get('data_id')
            data_type = request.form.get('data_type')

            if 'delete_data' in request.form:
                if data_type == 'study':
                    cursor.execute("DELETE FROM study_data WHERE id = %s", (data_id,))
                elif data_type == 'rules':
                    cursor.execute("DELETE FROM rules_data WHERE id = %s", (data_id,))
                conn.commit()

            elif 'update_data' in request.form:
                if data_type == 'study':
                    return redirect(url_for('update_study_data', data_id=data_id))
                elif data_type == 'rules':
                    return redirect(url_for('update_rules_data', data_id=data_id))

    # Lấy dữ liệu học tập
    cursor.execute("SELECT * FROM study_data")
    study_data = cursor.fetchall()

    # Lấy dữ liệu vi phạm nội quy
    cursor.execute("SELECT * FROM rules_data")
    rules_data = cursor.fetchall()

    cursor.close()
    conn.close()

    # Lấy lớp trực và tuần từ session (nếu có)
    lop = session.get('lop', 'Không xác định')
    tuan = session.get('tuan', 'Chưa thiết lập')

    return render_template('home.html', study_data=study_data, rules_data=rules_data, lop=lop, tuan=tuan)




# # Đăng xuất, xóa session
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Trang admin, xem danh sách người dùng (info_data)
@app.route('/admin')
@login_required
def admin():
    if session.get('role') != 'admin':
        return "Bạn không có quyền truy cập trang admin."

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM info_data")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin.html', data=data)

# Thêm dữ liệu vào bảng info_data
@app.route('/add', methods=['POST'])
@login_required
def add():
    if session.get('role') == 'admin':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO info_data (name, email) VALUES (%s, %s)", (name, email))
        conn.commit()
        cursor.close()
        conn.close()
    return redirect('/admin')

# Chỉnh sửa thông tin trong bảng info_data
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if session.get('role') != 'admin':
        return "Bạn không có quyền chỉnh sửa dữ liệu."

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        cursor.execute("UPDATE info_data SET name=%s, email=%s WHERE id=%s", (name, email, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/admin')

    cursor.execute("SELECT * FROM info_data WHERE id=%s", (id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('edit.html', user=user)

# Xóa bản ghi trong bảng info_data
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    if session.get('role') == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM info_data WHERE id=%s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
    return redirect('/admin')

# Trang người dùng (chỉ người dùng role 'user' mới xem được)
@app.route('/user')
@login_required
def user():
    if session.get('role') != 'user':
        return "Bạn không có quyền truy cập trang người dùng."

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM info_data")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('user.html', data=data)

# Trang viewer (role viewer)
@app.route('/viewer')
@login_required
def viewer():
    if session.get('role') != 'viewer':
        return "Bạn không có quyền truy cập trang xem."

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM info_data")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('viewer.html', data=data)

# Trang Học Tập (study_data)
@app.route('/hoc_tap')
@login_required
def hoc_tap():
    if session.get('role') in ['admin', 'user']:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM study_data")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('hoc_tap.html', data=data)
    return "Bạn không có quyền truy cập vào mục Học Tập."

# Thêm dữ liệu học tập
@app.route('/add_hoc_tap', methods=['GET', 'POST'])
@login_required
def add_hoc_tap():
    if request.method == 'POST':
        tuan = request.form['tuan'].strip()
        lop = request.form['lop'].strip()
        gio_a = int(request.form['gio_a'] or 0)
        gio_b = int(request.form['gio_b'] or 0)
        gio_c = int(request.form['gio_c'] or 0)
        gio_d = int(request.form['gio_d'] or 0)
        dat_kieu_mau = request.form['dat_kieu_mau']

        # Tính tổng điểm học tập
        tong_diem = gio_a * 5 + gio_b * -5 + gio_c * -15 + gio_d * -25
        tong_diem += 5 if dat_kieu_mau == "Yes" else -10

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO study_data 
            (tuan, lop, gio_a, gio_b, gio_c, gio_d, dat_kieu_mau, tong_diem)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (tuan, lop, gio_a, gio_b, gio_c, gio_d, dat_kieu_mau, tong_diem))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/hoc_tap')
    return render_template('add_hoc_tap.html')

# Trang Nội Quy
@app.route('/noi_quy')
@login_required
def noi_quy():
    if session.get('role') in ['admin', 'user']:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM rules_data")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('noi_quy.html', data=data)
    return "Bạn không có quyền truy cập vào mục Nội Quy."

# Thêm dữ liệu vi phạm nội quy
@app.route('/add_noi_quy', methods=['GET', 'POST'])
@login_required
def add_noi_quy():
    if request.method == 'POST':
        tuan = request.form['tuan'].strip()
        lop = request.form['lop'].strip()
        noi_dung_vi_pham = request.form['vi_pham'].strip()
        diem_tru = int(request.form['diem_tru'] or 0)
        so_luot_vi_pham = int(request.form['so_luot'] or 0)
        ten_hoc_sinh_vi_pham = request.form['hoc_sinh'].strip()
        tong_diem_vi_pham = diem_tru * so_luot_vi_pham

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rules_data 
            (tuan, lop, noi_dung_vi_pham, diem_tru, tong_diem_vi_pham, so_luot_vi_pham, ten_hoc_sinh_vi_pham)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (tuan, lop, noi_dung_vi_pham, diem_tru, tong_diem_vi_pham, so_luot_vi_pham, ten_hoc_sinh_vi_pham))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/noi_quy')
    return render_template('add_noi_quy.html')

# Tổng kết điểm học tập và nội quy -> bảng bang_tong_ket
@app.route('/tong_ket')
@login_required
def tong_ket():
    if session.get('role') != 'admin':
        return "Chỉ admin mới được tổng kết."

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy danh sách tất cả tuần - lớp có trong study_data và rules_data
    cursor.execute("""
        SELECT DISTINCT tuan, lop FROM (
            SELECT tuan, lop FROM study_data
            UNION
            SELECT tuan, lop FROM rules_data
        ) AS combined
    """)
    rows = cursor.fetchall()

    # Xóa dữ liệu cũ (nếu muốn làm mới hoàn toàn)
    cursor.execute("DELETE FROM bang_tong_ket")
    conn.commit()

    for row in rows:
        tuan = row['tuan']
        lop = row['lop']

        # Tổng điểm học tập
        cursor.execute("SELECT SUM(tong_diem) as diem_ht FROM study_data WHERE tuan=%s AND lop=%s", (tuan, lop))
        diem_ht = cursor.fetchone()['diem_ht'] or 0

        # Tổng điểm vi phạm
        cursor.execute("SELECT SUM(tong_diem_vi_pham) as diem_nq FROM rules_data WHERE tuan=%s AND lop=%s", (tuan, lop))
        diem_nq = cursor.fetchone()['diem_nq'] or 0

        # Tính tổng điểm chung (học tập + nội quy)
        tong_diem = diem_ht + diem_nq

        # Chèn vào bảng tổng kết
        cursor.execute("""
            INSERT INTO bang_tong_ket (tuan, lop, tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung)
            VALUES (%s, %s, %s, %s, %s)
        """, (tuan, lop, diem_ht, diem_nq, tong_diem))

    conn.commit()

    # Lấy dữ liệu tổng kết, sắp xếp theo tuần ASC, tổng điểm DESC
    cursor.execute("SELECT * FROM bang_tong_ket ORDER BY tuan ASC, tong_diem_chung DESC")
    data = cursor.fetchall()

    # Tính rank thủ công theo từng tuần
    rank_by_tuan = {}
    for item in data:
        tuan = item['tuan']
        if tuan not in rank_by_tuan:
            rank_by_tuan[tuan] = 1
            item['xep_hang'] = 1
        else:
            # Nếu điểm bằng điểm của người trước thì rank bằng nhau
            prev = rank_by_tuan[tuan+'_prev_diem']
            if item['tong_diem_chung'] == prev:
                item['xep_hang'] = rank_by_tuan[tuan]
            else:
                rank_by_tuan[tuan] += 1
                item['xep_hang'] = rank_by_tuan[tuan]
        rank_by_tuan[tuan+'_prev_diem'] = item['tong_diem_chung']

    cursor.close()
    conn.close()

    return render_template('tong_ket.html', data=data)




# Gán tuần cho lớp (admin sử dụng)
@app.route('/assign_tuan', methods=['GET', 'POST'])
@login_required
def assign_tuan():
    if session.get('role') != 'admin':
        return "Bạn không có quyền phân công."

    if request.method == 'POST':
        lop = request.form['lop'].strip()
        tuan = request.form['tuan'].strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO week_assignment (lop, tuan)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE tuan=%s
        """, (lop, tuan, tuan))
        conn.commit()
        cursor.close()
        conn.close()
    return render_template('assign_tuan.html')  # Cần tạo file HTML cho việc phân công


@app.route('/')
def root_redirect():
    return redirect('/index.html')

@app.route('/index.html')
def index():
    return render_template('index.html')

@app.route('/view_schedule')
def view_schedule():
    data = get_all_schedule()
    return render_template('view_schedule.html', schedules=data)

@app.route('/save_schedule', methods=['POST'])
def save_schedule():
    data = request.get_json()
    insert_schedule(data)
    return jsonify({'message': 'Đã lưu vào SQL thành công!'}), 200

@app.route('/update_schedule', methods=['POST'])
def update_schedule_route():
    data = request.get_json()
    update_schedule(data)
    return jsonify({'message': 'Đã cập nhật phân công thành công!'}), 200

@app.route('/clear_all', methods=['POST'])
def clear_all_route():
    clear_all_schedule()
    return jsonify({'message': 'Đã xóa tất cả phân công trong cơ sở dữ liệu!'}), 200



# Khởi chạy Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
