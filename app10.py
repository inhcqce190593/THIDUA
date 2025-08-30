from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, send_file
from functools import wraps
import mysql.connector
import random
import string
import pandas as pd
from io import BytesIO
from collections import defaultdict
from fpdf import FPDF

# Khởi tạo Flask app
app = Flask(__name__)
app.secret_key = 'secret123'  # Khóa bảo mật session. Hãy dùng một khóa mạnh hơn trong môi trường production!

# Hàm kết nối đến cơ sở dữ liệu MySQL cho các bảng chung
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='test', # Database chứa info_data, study_data, rules_data, bang_tong_ket
        charset='utf8mb4' # Thêm charset để hỗ trợ tiếng Việt tốt hơn
    )

# Cấu hình cơ sở dữ liệu cho bảng phan_cong
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # để trống nếu không có mật khẩu
    'database': 'test', # Sửa thành 'test' để đồng nhất
    'charset': 'utf8mb4'
}

# Cấu hình cơ sở dữ liệu cho bảng accounts
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'test',
    'charset': 'utf8mb4'
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
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM phan_cong ORDER BY khoi, tuan')
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

# Hàm tạo mật khẩu ngẫu nhiên theo định dạng DDD@DDD
def generate_specific_password():
    part1 = ''.join(random.choices(string.digits, k=3))
    part2 = ''.join(random.choices(string.digits, k=3))
    return f"{part1}@{part2}"

# Hàm cập nhật lop_truc từ bảng phan_cong_truc
def update_lop_truc_data():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Kiểm tra dữ liệu trong phan_cong_truc
        cursor.execute("SELECT COUNT(*) FROM phan_cong_truc")
        count = cursor.fetchone()[0]
        if count == 0:
            return "❌ Không có dữ liệu trong bảng phan_cong_truc để cập nhật."

        sql_query = """
        UPDATE accounts AS a
        JOIN phan_cong_truc AS pct ON a.tuan = pct.tuan AND a.lop = pct.lop
        SET a.lop_truc = pct.lop_truc
        """
        cursor.execute(sql_query)
        conn.commit()
        print(f"Updated {cursor.rowcount} records in accounts with lop_truc.")  # Debug
        return f"✅ Đã cập nhật {cursor.rowcount} bản ghi 'Lớp Trực'."
    except mysql.connector.Error as err:
        print(f"Error updating lop_truc: {err}")  # Debug
        return f"❌ Lỗi cập nhật 'Lớp Trực': {err}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# Decorator kiểm tra người dùng đã đăng nhập hay chưa
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Trang gốc, chuyển hướng đến /home
@app.route('/')
def root():
    return render_template('welcome.html')

# Trang đăng nhập
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
            session['Name'] = user['Name']
            session['role'] = user['role']
            session['lop'] = user.get('lop', 'N/A')
            session['tuan'] = user.get('tuan', 'N/A')
            session['lop_truc'] = user.get('lop_truc', 'N/A')
            
            flash(f"Chào mừng {user['username']}! Bạn đã đăng nhập thành công.", 'success')
            if user['role'] == 'admin':
                return redirect(url_for('home'))
            elif user['role'] == 'user':
                return redirect(url_for('user'))
            elif user['role'] == 'viewer':
                return redirect(url_for('viewer'))
            else:
                flash("Vai trò không hợp lệ.", 'error')
                return redirect(url_for('login'))
        
        flash("Sai tài khoản hoặc mật khẩu.", 'error')
        return render_template('login.html', error="Sai tài khoản hoặc mật khẩu")
    
    return render_template('login.html')

# Trang chính
@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST' and 'set_week' in request.form:
        if session.get('role') == 'admin':
            selected_week = request.form.get('week_select')
            session['tuan'] = selected_week
            flash(f"Tuần đã được đặt thành {selected_week}.", 'info')
            return redirect(url_for('home'))
        else:
            flash("Bạn không có quyền thay đổi tuần hiển thị.", 'error')
            return redirect(url_for('home'))

    if request.method == 'POST' and ('delete_data' in request.form or 'update_data' in request.form):
        if session.get('role') != 'admin':
            flash("Bạn không có quyền thực hiện thao tác này.", 'error')
            return redirect(url_for('home'))
        
        data_id = request.form.get('data_id')
        data_type = request.form.get('data_type')

        if 'delete_data' in request.form:
            if data_type == 'study':
                cursor.execute("DELETE FROM study_data WHERE id = %s", (data_id,))
                flash(f"Đã xóa dữ liệu học tập ID {data_id}.", 'success')
            elif data_type == 'rules':
                cursor.execute("DELETE FROM rules_data WHERE id = %s", (data_id,))
                flash(f"Đã xóa dữ liệu nội quy ID {data_id}.", 'success')
            conn.commit()

        elif 'update_data' in request.form:
            if data_type == 'study':
                return redirect(url_for('update_study_data', data_id=data_id))
            elif data_type == 'rules':
                return redirect(url_for('update_rules_data', data_id=data_id))

    study_data = []
    rules_data = []
    if session.get('role') == 'admin':
        cursor.execute("SELECT * FROM study_data")
        study_data = cursor.fetchall()

        cursor.execute("SELECT * FROM rules_data")
        rules_data = cursor.fetchall()

    cursor.close()
    conn.close()

    lop = session.get('lop', 'Không xác định')
    tuan = session.get('tuan', 'Chưa thiết lập')
    lop_truc = session.get('lop_truc', 'Chưa thiết lập')

    # Get available weeks and classes for export filter
    conn_filter = get_db_connection()
    cursor_filter = conn_filter.cursor()
    
    cursor_filter.execute("SELECT DISTINCT tuan FROM bang_tong_ket UNION SELECT DISTINCT tuan FROM study_data UNION SELECT DISTINCT tuan FROM rules_data ORDER BY tuan ASC")
    available_export_weeks = [row[0] for row in cursor_filter.fetchall()]
    
    cursor_filter.execute("SELECT DISTINCT lop FROM bang_tong_ket UNION SELECT DISTINCT lop FROM study_data UNION SELECT DISTINCT lop FROM rules_data ORDER BY lop ASC")
    available_export_classes = [row[0] for row in cursor_filter.fetchall()]
    
    cursor_filter.close()
    conn_filter.close()

    return render_template('home.html', study_data=study_data, rules_data=rules_data, lop=lop, tuan=tuan, lop_truc=lop_truc,
                           available_export_weeks=available_export_weeks, available_export_classes=available_export_classes)

# Đăng xuất, xóa session
@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", 'info')
    return redirect(url_for('login'))

# Trang admin, xem danh sách người dùng (info_data)
@app.route('/admin')
@login_required
def admin():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang admin.", 'error')
        return redirect(url_for('home'))

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
    if session.get('role') != 'admin':
        flash("Bạn không có quyền thêm dữ liệu.", 'error')
        return redirect(url_for('home'))

    name = request.form['name'].strip()
    email = request.form['email'].strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO info_data (name, email) VALUES (%s, %s)", (name, email))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Đã thêm dữ liệu thành công.", 'success')
    return redirect(url_for('admin'))

# Chỉnh sửa thông tin trong bảng info_data
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền chỉnh sửa dữ liệu.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        cursor.execute("UPDATE info_data SET name=%s, email=%s WHERE id=%s", (name, email, id))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Đã cập nhật ID {id} thành công.", 'success')
        return redirect(url_for('admin'))

    cursor.execute("SELECT * FROM info_data WHERE id=%s", (id,))
    user_info = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user_info:
        flash("Không tìm thấy dữ liệu để chỉnh sửa.", 'error')
        return redirect(url_for('admin'))
    return render_template('edit.html', user=user_info)

# Xóa bản ghi trong bảng info_data
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền xóa dữ liệu.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM info_data WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Đã xóa dữ liệu ID {id} thành công.", 'success')
    return redirect(url_for('admin'))

# Trang người dùng (chỉ người dùng role 'user' mới xem được)
@app.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    if session.get('role') != 'user':
        flash("Bạn không có quyền truy cập trang người dùng.", 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        data_id = request.form.get('data_id')
        data_type = request.form.get('data_type')

        # Kiểm tra trạng thái tổng kết trước khi thực hiện xóa hoặc sửa
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", 
                       (session['username'], session.get('tuan')))
        account_status = cursor.fetchone()
        trangthai_tongket = account_status['trangthai'] if account_status else 'Chưa tổng kết'

        if trangthai_tongket == 'Đã tổng kết':
            flash("Không thể chỉnh sửa hoặc xóa dữ liệu vì tuần này đã được tổng kết.", 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('user'))

        if 'delete_data' in request.form:
            if data_type == 'study':
                cursor.execute("DELETE FROM study_data WHERE id = %s", (data_id,))
                flash(f"Đã xóa dữ liệu học tập ID {data_id}.", 'success')
            elif data_type == 'rules':
                cursor.execute("DELETE FROM rules_data WHERE id = %s", (data_id,))
                flash(f"Đã xóa dữ liệu nội quy ID {data_id}.", 'success')
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('user'))

        elif 'update_data' in request.form:
            if data_type == 'study':
                return redirect(url_for('update_study_data', data_id=data_id))
            elif data_type == 'rules':
                return redirect(url_for('update_rules_data', data_id=data_id))

    user_lop = session.get('lop')
    user_tuan_hien_tai = session.get('tuan')
    selected_tuan_tong_ket = request.args.get('tong_ket_tuan', type=str)
    user_lop_truc = session.get('lop_truc')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", 
                   (session['username'], user_tuan_hien_tai))
    account_status = cursor.fetchone()
    trangthai_tongket = account_status['trangthai'] if account_status else 'Chưa tổng kết'

    study_data = []
    rules_data = []
    tong_ket_data = []
    available_weeks_for_lop = []

    if user_lop:
        cursor.execute("SELECT DISTINCT tuan FROM bang_tong_ket WHERE lop = %s ORDER BY tuan ASC", (user_lop,))
        available_weeks_for_lop = [row['tuan'] for row in cursor.fetchall()]

        if not selected_tuan_tong_ket and user_tuan_hien_tai in available_weeks_for_lop:
            selected_tuan_tong_ket = user_tuan_hien_tai
        elif not selected_tuan_tong_ket and available_weeks_for_lop:
            selected_tuan_tong_ket = available_weeks_for_lop[0]

    if user_lop and user_tuan_hien_tai:
        cursor.execute("SELECT * FROM study_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan_hien_tai))
        study_data = cursor.fetchall()

        cursor.execute("SELECT * FROM rules_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan_hien_tai))
        rules_data = cursor.fetchall()
    else:
        flash("Thông tin lớp hoặc tuần của tài khoản bạn chưa được thiết lập. Vui lòng liên hệ quản trị viên.", 'info')

    if user_lop and selected_tuan_tong_ket:
        cursor.execute("""
            SELECT * FROM bang_tong_ket 
            WHERE lop = %s AND tuan = %s
            ORDER BY tong_diem_chung DESC
        """, (user_lop, selected_tuan_tong_ket))
        tong_ket_data = cursor.fetchall()

        if tong_ket_data:
            cursor.execute("""
                SELECT * FROM bang_tong_ket
                WHERE tuan = %s
                ORDER BY tong_diem_chung DESC
            """, (selected_tuan_tong_ket,))
            all_data_for_selected_tuan = cursor.fetchall()

            current_rank = 1
            prev_diem = None
            for i, item in enumerate(all_data_for_selected_tuan):
                if i > 0 and item['tong_diem_chung'] < prev_diem:
                    current_rank = i + 1
                item['xep_hang'] = current_rank
                prev_diem = item['tong_diem_chung']

                for user_item in tong_ket_data:
                    if user_item['lop'] == user_lop:
                        user_item['xep_hang'] = item['xep_hang']
                        break
    else:
        flash("Không có thông tin lớp hoặc tuần để hiển thị dữ liệu tổng kết.", 'info')

    cursor.close()
    conn.close()

    return render_template('user.html',
                           study_data=study_data,
                           rules_data=rules_data,
                           lop=user_lop,
                           tuan=user_tuan_hien_tai,
                           lop_truc=user_lop_truc,
                           trangthai_tongket=trangthai_tongket,
                           tong_ket_data=tong_ket_data,
                           selected_tuan_tong_ket=selected_tuan_tong_ket,
                           available_weeks_for_lop=available_weeks_for_lop)
# Trang viewer (role viewer)
@app.route('/viewer')
@login_required
def viewer():
    if session.get('role') != 'viewer':
        flash("Bạn không có quyền truy cập trang xem.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    user_lop = session.get('lop')
    user_tuan = session.get('tuan')
    user_lop_truc = session.get('lop_truc')

    study_data = []
    rules_data = []

    if user_lop and user_tuan:
        cursor.execute("SELECT * FROM study_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan))
        study_data = cursor.fetchall()

        cursor.execute("SELECT * FROM rules_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan))
        rules_data = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('viewer.html', 
                           study_data=study_data, 
                           rules_data=rules_data, 
                           lop=user_lop, 
                           tuan=user_tuan, 
                           lop_truc=user_lop_truc)

# Trang Học Tập (study_data)
@app.route('/hoc_tap')
@login_required
def hoc_tap():
    if session.get('role') not in ['admin', 'user', 'viewer']:
        flash("Bạn không có quyền truy cập vào mục Học Tập.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    data = []
    user_role = session.get('role')
    
    available_weeks = []
    available_lops = []
    cursor.execute("SELECT DISTINCT tuan FROM study_data ORDER BY tuan ASC")
    available_weeks = [row['tuan'] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT lop FROM study_data ORDER BY lop ASC")
    available_lops = [row['lop'] for row in cursor.fetchall()]

    selected_tuan = request.args.get('tuan', type=str)
    selected_lop = request.args.get('lop', type=str)

    query = "SELECT * FROM study_data WHERE 1=1"
    query_params = []

    if user_role == 'admin':
        if selected_tuan:
            query += " AND tuan = %s"
            query_params.append(selected_tuan)
        if selected_lop:
            query += " AND lop = %s"
            query_params.append(selected_lop)
    elif user_role in ['user', 'viewer']:
        user_lop = session.get('lop')
        user_tuan = session.get('tuan')
        if user_lop and user_tuan:
            query += " AND lop = %s AND tuan = %s"
            query_params.append(user_lop)
            query_params.append(user_tuan)
        else:
            flash("Không có thông tin lớp hoặc tuần để hiển thị dữ liệu học tập.", 'info')
            
    query += " ORDER BY tuan DESC, lop ASC"
    
    cursor.execute(query, tuple(query_params))
    data = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('hoc_tap.html', data=data, available_weeks=available_weeks, available_lops=available_lops, selected_tuan=selected_tuan, selected_lop=selected_lop)

@app.route('/delete_hoc_tap_entry/<int:entry_id>', methods=['POST'])
@login_required
def delete_hoc_tap_entry(entry_id):
    user_role = session.get('role')
    current_class_id = session.get('lop')

    if user_role not in ['admin', 'user']:
        return jsonify({'status': 'error', 'message': 'Bạn không có quyền thực hiện hành động này.'}), 403

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT lop, tuan FROM study_data WHERE id = %s", (entry_id,))
        entry_info = cursor.fetchone()

        if not entry_info:
            return jsonify({'status': 'error', 'message': 'Dữ liệu không tồn tại.'}), 404
        
        entry_lop = entry_info['lop']
        entry_tuan = entry_info['tuan']

        cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", 
                      (session.get('username'), entry_tuan))
        account_status = cursor.fetchone()
        if account_status and account_status['trangthai'] == 'Đã tổng kết':
            return jsonify({'status': 'error', 'message': 'Không thể xóa dữ liệu vì tuần này đã được tổng kết.'}), 403

        if user_role == 'user' and entry_lop != current_class_id:
            return jsonify({'status': 'error', 'message': 'Bạn không có quyền xóa dữ liệu của lớp khác.'}), 403

        cursor.execute("DELETE FROM study_data WHERE id = %s", (entry_id,))
        conn.commit()
        flash("Đã xóa dữ liệu học tập thành công.", 'success')
        return jsonify({'status': 'success', 'message': 'Đã xóa dữ liệu học tập thành công.'}), 200
    except mysql.connector.Error as err:
        flash(f"Lỗi khi xóa dữ liệu học tập: {err}", 'error')
        print(f"Error deleting study data entry: {err}")
        return jsonify({'status': 'error', 'message': f'Lỗi khi xóa dữ liệu học tập: {err}'}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# Thêm dữ liệu học tập
@app.route('/add_hoc_tap', methods=['GET', 'POST'])
@login_required
def add_hoc_tap():
    if session.get('role') not in ['admin', 'user']:
        flash("Bạn không có quyền thêm dữ liệu học tập.", 'error')
        return redirect(url_for('hoc_tap'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    user_lop = session.get('lop', '')
    user_tuan = session.get('tuan', '')

    if session.get('role') == 'user' and (not user_lop or not user_tuan):
        flash("Bạn cần được gán lớp và tuần trước khi thêm dữ liệu học tập.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('user'))

    # Kiểm tra trạng thái tổng kết
    cursor.execute("SELECT trangthai FROM bang_tong_ket WHERE lop = %s AND tuan = %s", 
               (user_lop, user_tuan))


    status_row = cursor.fetchone()
    if status_row and status_row['trangthai'] == 'Đã tổng kết':
        flash("Tuần này đã được tổng kết. Bạn không thể thêm dữ liệu học tập.", 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('hoc_tap'))

    if request.method == 'POST':
        if session.get('role') == 'admin':
            tuan = request.form['tuan'].strip()
            lop = request.form['lop'].strip()
        else:
            tuan = user_tuan
            lop = user_lop

        gio_a = int(request.form['gio_a'] or 0)
        gio_b = int(request.form['gio_b'] or 0)
        gio_c = int(request.form['gio_c'] or 0)
        gio_d = int(request.form['gio_d'] or 0)
        dat_kieu_mau = request.form['dat_kieu_mau']

        tong_diem = gio_a * 5 + gio_b * -5 + gio_c * -15 + gio_d * -25
        tong_diem += 5 if dat_kieu_mau == "Yes" else -10

        try:
            cursor.execute("""
                INSERT INTO study_data 
                (tuan, lop, gio_a, gio_b, gio_c, gio_d, dat_kieu_mau, tong_diem)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (tuan, lop, gio_a, gio_b, gio_c, gio_d, dat_kieu_mau, tong_diem))
            conn.commit()
            flash("Đã thêm dữ liệu học tập thành công.", 'success')
        except mysql.connector.Error as err:
            flash(f"Lỗi khi thêm dữ liệu học tập: {err}", 'error')
            print(f"Error: {err}")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('hoc_tap'))

    cursor.close()
    conn.close()
    return render_template('add_hoc_tap.html', user_lop=user_lop, user_tuan=user_tuan, role=session.get('role'))

# Trang Nội Quy
@app.route('/noi_quy', methods=['GET', 'POST'])
@login_required
def noi_quy():
    if session.get('role') not in ['admin', 'user', 'viewer']:
        flash("Bạn không có quyền truy cập vào mục Nội Quy.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 👉 Xử lý POST (XÓA hoặc CHỈNH SỬA)
    if request.method == 'POST':
        data_id = request.form.get('data_id')
        data_type = request.form.get('data_type')  # ví dụ: 'rules'

        # Nếu là nút XÓA
        if 'delete_data' in request.form:
            if session.get('role') != 'admin':
                flash("Chỉ quản trị viên mới có quyền xóa dữ liệu.", 'error')
            else:
                try:
                    cursor.execute("DELETE FROM rules_data WHERE id = %s", (data_id,))
                    conn.commit()
                    flash("Đã xóa dữ liệu thành công.", 'success')
                except Exception as e:
                    flash(f"Lỗi khi xóa dữ liệu: {e}", 'error')

        # Nếu là nút SỬA (gợi ý chuyển hướng đến trang chỉnh sửa riêng)
        elif 'update_data' in request.form:
            return redirect(url_for('edit_noi_quy', rule_id=data_id))  # bạn cần tạo route edit_noi_quy nếu muốn chỉnh sửa

    # 👉 Dữ liệu để hiển thị
    data = []
    user_role = session.get('role')

    if user_role == 'admin':
        cursor.execute("SELECT * FROM rules_data")
        data = cursor.fetchall()
    elif user_role in ['user', 'viewer']:
        user_lop = session.get('lop')
        user_tuan = session.get('tuan')
        if user_lop and user_tuan:
            cursor.execute("SELECT * FROM rules_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan))
            data = cursor.fetchall()
        else:
            flash("Không có thông tin lớp hoặc tuần để hiển thị dữ liệu nội quy.", 'info')

    # Trạng thái tổng kết (dùng để disable nút xóa/sửa)
    trangthai_tongket = 'Chưa tổng kết'
    if session.get('role') in ['user', 'viewer']:
        cursor.execute("SELECT trangthai FROM bang_tong_ket WHERE lop = %s AND tuan = %s", (session.get('lop'), session.get('tuan')))
        result = cursor.fetchone()
        if result:
            trangthai_tongket = result['trangthai']

    cursor.close()
    conn.close()

    return render_template('noi_quy.html', data=data, trangthai_tongket=trangthai_tongket,
                           lop=session.get('lop'), tuan=session.get('tuan'),
                           lop_truc=session.get('lop_truc'))  # gửi thêm thông tin sang modal
@app.route('/edit_noi_quy/<int:rule_id>', methods=['GET', 'POST'])
@login_required
def edit_noi_quy(rule_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy dữ liệu theo ID
    cursor.execute("SELECT * FROM rules_data WHERE id = %s", (rule_id,))
    rule = cursor.fetchone()

    if not rule:
        flash("Không tìm thấy dữ liệu nội quy.", "error")
        return redirect(url_for('noi_quy'))

    if request.method == 'POST':
        # Lấy dữ liệu từ form
        tuan = request.form['tuan']
        lop = request.form['lop']
        vi_pham = request.form['vi_pham']
        diem_tru = int(request.form['diem_tru'] or 0)
        so_luot = int(request.form['so_luot'] or 0)
        hoc_sinh = request.form['hoc_sinh']
        tong_diem = diem_tru * so_luot

        try:
            cursor.execute("""
                UPDATE rules_data
                SET tuan=%s, lop=%s, noi_dung_vi_pham=%s, diem_tru=%s, so_luot_vi_pham=%s,
                    ten_hoc_sinh_vi_pham=%s, tong_diem_vi_pham=%s
                WHERE id=%s
            """, (tuan, lop, vi_pham, diem_tru, so_luot, hoc_sinh, tong_diem, rule_id))
            conn.commit()
            flash("Cập nhật nội quy thành công!", "success")
            return redirect(url_for('noi_quy'))
        except Exception as e:
            flash(f"Lỗi khi cập nhật: {e}", "error")

    cursor.close()
    conn.close()
    return render_template('edit_noi_quy.html', rule=rule)

# Thêm dữ liệu vi phạm nội quy
@app.route('/add_noi_quy', methods=['GET', 'POST'])
@login_required
def add_noi_quy():
    if session.get('role') not in ['admin', 'user']:
        flash("Bạn không có quyền thêm dữ liệu vi phạm nội quy.", 'error')
        return redirect(url_for('noi_quy'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    user_lop = session.get('lop', '')
    user_tuan = session.get('tuan', '')

    if session.get('role') == 'user' and (not user_lop or not user_tuan):
        flash("Bạn cần được gán lớp và tuần trước khi thêm dữ liệu vi phạm nội quy.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('user'))

    # ✅ Dùng đúng biến đã khai báo
    cursor.execute("SELECT trangthai FROM bang_tong_ket WHERE lop = %s AND tuan = %s", 
                   (user_lop, user_tuan))

    status_row = cursor.fetchone()
    if status_row and status_row['trangthai'] == 'Đã tổng kết':
        flash("Tuần này đã được tổng kết. Bạn không thể thêm dữ liệu vi phạm nội quy.", 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('noi_quy'))

    if request.method == 'POST':
        if session.get('role') == 'admin':
            tuan = request.form['tuan'].strip()
            lop = request.form['lop'].strip()
        else:
            tuan = user_tuan
            lop = user_lop

        noi_dung_vi_pham = request.form['vi_pham'].strip()
        diem_tru = int(request.form['diem_tru'] or 0)
        so_luot_vi_pham = int(request.form['so_luot'] or 0)
        ten_hoc_sinh_vi_pham = request.form['hoc_sinh'].strip()
        tong_diem_vi_pham = diem_tru * so_luot_vi_pham

        try:
            cursor.execute("""
                INSERT INTO rules_data 
                (tuan, lop, noi_dung_vi_pham, diem_tru, tong_diem_vi_pham, so_luot_vi_pham, ten_hoc_sinh_vi_pham)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (tuan, lop, noi_dung_vi_pham, diem_tru, tong_diem_vi_pham, so_luot_vi_pham, ten_hoc_sinh_vi_pham))
            conn.commit()
            flash("Đã thêm dữ liệu vi phạm nội quy thành công.", 'success')
        except mysql.connector.Error as err:
            flash(f"Lỗi khi thêm dữ liệu vi phạm nội quy: {err}", 'error')
            print(f"Error: {err}")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('noi_quy'))

    cursor.close()
    conn.close()
    return render_template('add_noi_quy.html', user_lop=user_lop, user_tuan=user_tuan, role=session.get('role'))

# Tổng kết điểm học tập và nội quy -> bảng bang_tong_ket

@app.route('/tong_ket', methods=['GET', 'POST'])
@login_required
def tong_ket():
    if session.get('role') != 'admin':
        flash("Chỉ admin mới được tổng kết.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST' and 'recalculate' in request.form:
        cursor.execute("TRUNCATE TABLE bang_tong_ket")
        conn.commit()

        cursor.execute("SELECT DISTINCT tuan, lop FROM study_data UNION SELECT DISTINCT tuan, lop FROM rules_data")
        unique_weeks_lops = cursor.fetchall()

        if not unique_weeks_lops:
            flash("Không có dữ liệu trong study_data hoặc rules_data để tổng kết.", 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('tong_ket'))

        print(f"Unique weeks and classes: {unique_weeks_lops}")  # Debug

        for entry in unique_weeks_lops:
            tuan = entry['tuan']
            lop = entry['lop']

            cursor.execute("SELECT SUM(tong_diem) as total_study_points FROM study_data WHERE tuan = %s AND lop = %s", (tuan, lop))
            study_result = cursor.fetchone()
            total_study_points = study_result['total_study_points'] if study_result and study_result['total_study_points'] is not None else 0
            print(f"Study points for {tuan}, {lop}: {total_study_points}")  # Debug

            cursor.execute("SELECT SUM(tong_diem_vi_pham) as total_rules_points FROM rules_data WHERE tuan = %s AND lop = %s", (tuan, lop))
            rules_result = cursor.fetchone()
            total_rules_points = rules_result['total_rules_points'] if rules_result and rules_result['total_rules_points'] is not None else 0
            print(f"Rules points for {tuan}, {lop}: {total_rules_points}")  # Debug

            tong_diem_chung = total_study_points + total_rules_points

            cursor.execute("""
                INSERT INTO bang_tong_ket (tuan, lop, tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung, trangthai)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    tong_diem_hoc_tap = %s, 
                    tong_diem_noi_quy = %s, 
                    tong_diem_chung = %s,
                    trangthai = %s
            """, (
                tuan, lop, total_study_points, total_rules_points, tong_diem_chung, 'Chưa tổng kết',
                total_study_points, total_rules_points, tong_diem_chung, 'Chưa tổng kết'
            ))

        flash("Tổng kết điểm đã được cập nhật.", 'success')
        return redirect(url_for('tong_ket'))

    selected_tuan = request.args.get('tuan', type=str)

    cursor.execute("SELECT DISTINCT tuan FROM bang_tong_ket ORDER BY tuan ASC")
    available_weeks = [row['tuan'] for row in cursor.fetchall()]

    if selected_tuan:
        cursor.execute("SELECT * FROM bang_tong_ket WHERE tuan = %s ORDER BY tong_diem_chung DESC", (selected_tuan,))
    else:
        cursor.execute("SELECT * FROM bang_tong_ket ORDER BY tuan ASC, tong_diem_chung DESC")
    data = cursor.fetchall()

    if not data:
        flash("Không có dữ liệu tổng kết để hiển thị.", 'warning')
        cursor.close()
        conn.close()
        return render_template('tong_ket.html', data=[], available_weeks=available_weeks, selected_tuan=selected_tuan)

    ranked_data = []
    grouped_data = defaultdict(list)
    for item in data:
        grouped_data[item['tuan']].append(item)

    for tuan_key in sorted(grouped_data.keys()):
        current_week_data = sorted(grouped_data[tuan_key], key=lambda x: x['tong_diem_chung'], reverse=True)
        current_rank = 1
        same_rank_count = 1
        prev_diem = None

        for i, item in enumerate(current_week_data):
            if i == 0:
                item['xep_hang'] = current_rank
            else:
                if item['tong_diem_chung'] < prev_diem:
                    current_rank += same_rank_count
                    same_rank_count = 1
                else:
                    same_rank_count += 1
                item['xep_hang'] = current_rank
            prev_diem = item['tong_diem_chung']
            ranked_data.append(item)

    cursor.close()
    conn.close()
    
    return render_template('tong_ket.html', data=ranked_data, available_weeks=available_weeks, selected_tuan=selected_tuan)
# Route xuất báo cáo tổng kết ra Excel
@app.route('/export_summary', methods=['GET'])
@login_required
def export_summary():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền xuất dữ liệu này.", 'error')
        return redirect(url_for('home'))

    selected_tuan = request.args.get('export_tuan', type=str)
    selected_lop = request.args.get('export_lop', type=str)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SET SESSION group_concat_max_len = 10000;")

        query = """
            SELECT 
                btk.tuan,
                btk.lop,
                btk.tong_diem_hoc_tap,
                btk.tong_diem_noi_quy,
                btk.tong_diem_chung,
                GROUP_CONCAT(DISTINCT rd.ten_hoc_sinh_vi_pham SEPARATOR '; ') AS ten_hoc_sinh_vi_pham,
                GROUP_CONCAT(DISTINCT CONCAT(rd.noi_dung_vi_pham, ' (', rd.diem_tru, ' điểm, ', rd.so_luot_vi_pham, ' lượt)') SEPARATOR '; ') AS chi_tiet_vi_pham
            FROM 
                bang_tong_ket btk
            LEFT JOIN 
                rules_data rd ON btk.lop = rd.lop AND btk.tuan = rd.tuan
        """
        params = []
        conditions = []

        if selected_tuan:
            conditions.append("btk.tuan = %s")
            params.append(selected_tuan)
        if selected_lop:
            conditions.append("btk.lop = %s")
            params.append(selected_lop)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " GROUP BY btk.tuan, btk.lop ORDER BY btk.tuan, btk.lop"

        cursor.execute(query, tuple(params))
        summary_data = cursor.fetchall()

        if not summary_data:
            flash("Không tìm thấy dữ liệu tổng kết theo tuần và lớp đã chọn để xuất báo cáo.", 'warning')
            return redirect(url_for('home'))

        print(f"Summary data: {summary_data}")  # Debug
        df = pd.DataFrame(summary_data)
        
        if selected_tuan:
            df['xep_hang'] = df['tong_diem_chung'].rank(method='min', ascending=False).astype(int)
        else:
            df['xep_hang'] = df.groupby('tuan')['tong_diem_chung'].rank(method='min', ascending=False).astype(int)

        df = df[['tuan', 'lop', 'tong_diem_hoc_tap', 'tong_diem_noi_quy', 'tong_diem_chung', 'xep_hang', 'ten_hoc_sinh_vi_pham', 'chi_tiet_vi_pham']]
        df = df.rename(columns={
            'tuan': 'Tuần',
            'lop': 'Lớp',
            'tong_diem_hoc_tap': 'Tổng Điểm Học Tập',
            'tong_diem_noi_quy': 'Tổng Điểm Nội Quy',
            'tong_diem_chung': 'Tổng Điểm Chung',
            'xep_hang': 'Xếp Hạng',
            'ten_hoc_sinh_vi_pham': 'Tên Học Sinh Vi Phạm',
            'chi_tiet_vi_pham': 'Chi Tiết Vi Phạm Nội Quy'
        })

        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Tổng Kết Vi Phạm')
        writer.close()
        output.seek(0)

        filename = f"Tong_Ket_Vi_Pham_{selected_lop or 'TatCaLop'}_Tuan{selected_tuan or 'TatCaTuan'}.xlsx"
        return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi truy vấn dữ liệu từ cơ sở dữ liệu: {err}", 'error')
        print(f"Database Error: {err}")
        return redirect(url_for('home'))
    except Exception as e:
        flash(f"Lỗi không xác định khi xuất báo cáo Excel: {e}", 'error')
        print(f"General Error: {e}")
        return redirect(url_for('home'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# Route xuất báo cáo học tập ra PDF
@app.route('/export_hoc_tap_pdf', methods=['GET'])
@login_required
def export_hoc_tap_pdf():
    if session.get('role') not in ['admin', 'user', 'viewer']:
        flash("Bạn không có quyền xuất báo cáo này.", 'error')
        return redirect(url_for('hoc_tap'))

    selected_tuan = request.args.get('tuan', type=str)
    selected_lop = request.args.get('lop', type=str)

    if not selected_tuan or not selected_lop:
        flash("Vui lòng chọn Tuần và Lớp để xuất báo cáo PDF.", 'warning')
        return redirect(url_for('hoc_tap'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM study_data WHERE tuan = %s AND lop = %s ORDER BY id ASC"
    cursor.execute(query, (selected_tuan, selected_lop))
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    if not data:
        flash(f"Không có dữ liệu học tập cho Tuần {selected_tuan} và Lớp {selected_lop} để xuất báo cáo PDF.", 'warning')
        return redirect(url_for('hoc_tap', tuan=selected_tuan, lop=selected_lop))

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('DejaVuSans', '', 'DejaVuSansCondensed.ttf', uni=True)
    pdf.set_font('DejaVuSans', '', 12)

    pdf.cell(0, 10, f"BÁO CÁO HỌC TẬP - Tuần {selected_tuan} - Lớp {selected_lop}", 0, 1, 'C')
    pdf.ln(5)

    headers = ["Tuần", "Lớp", "Giờ A", "Giờ B", "Giờ C", "Giờ D", "Đạt Kiểu Mẫu", "Tổng Điểm"]
    col_widths = [15, 15, 15, 15, 15, 15, 30, 20]

    pdf.set_font('DejaVuSans', '', 10)
    pdf.set_fill_color(200, 220, 255)
    for i, header in enumerate(headers):
        if i < len(col_widths):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C', 1)
    pdf.ln()

    pdf.set_font('DejaVuSans', '', 9)
    for row in data:
        pdf.cell(col_widths[0], 10, str(row.get('tuan', '')), 1, 0, 'C')
        pdf.cell(col_widths[1], 10, str(row.get('lop', '')), 1, 0, 'C')
        pdf.cell(col_widths[2], 10, str(row.get('gio_a', 0)), 1, 0, 'C')
        pdf.cell(col_widths[3], 10, str(row.get('gio_b', 0)), 1, 0, 'C')
        pdf.cell(col_widths[4], 10, str(row.get('gio_c', 0)), 1, 0, 'C')
        pdf.cell(col_widths[5], 10, str(row.get('gio_d', 0)), 1, 0, 'C')
        pdf.cell(col_widths[6], 10, str(row.get('dat_kieu_mau', '')), 1, 0, 'C')
        pdf.cell(col_widths[7], 10, str(row.get('tong_diem', 0)), 1, 0, 'C')
        pdf.ln()

    pdf_output = pdf.output(dest='S').encode('latin-1')
    return send_file(BytesIO(pdf_output), mimetype='application/pdf', as_attachment=True, download_name=f"BaoCaoHocTap_Tuan_{selected_tuan}_Lop_{selected_lop}.pdf")

# Gán tuần cho lớp (admin sử dụng)
@app.route('/assign_tuan', methods=['GET', 'POST'])
@login_required
def assign_tuan():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền phân công.", 'error')
        return redirect(url_for('home'))

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
        flash(f"Đã gán tuần {tuan} cho lớp {lop} thành công.", 'success')
        return redirect(url_for('assign_tuan'))
    return render_template('assign_tuan.html')


@app.route('/index', methods=['GET'])
@login_required
def index():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang quản lý tài khoản.", 'error')
        return redirect(url_for('home'))

    accounts = []
    conn = None
    selected_tuan = request.args.get('tuan', type=int)

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        sql_query = "SELECT id, Name, username, password, role, lop, tuan, Capquanli, lop_truc, trangthai FROM accounts"
        query_params = []

        if selected_tuan is not None:
            sql_query += " WHERE tuan = %s"
            query_params.append(selected_tuan)
        
        sql_query += " ORDER BY id DESC"

        cursor.execute(sql_query, tuple(query_params))
        accounts = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Lỗi khi đọc dữ liệu từ DB: {err}")
        flash(f"Lỗi khi tải danh sách tài khoản: {err}", 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('insert_account.html', accounts=accounts, selected_tuan=selected_tuan)

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
    cursor.execute("DELETE FROM phan_cong_truc WHERE khoi=%s AND lop=%s", (khoi, lop))
    for tuan, lop_truc in enumerate(phan_cong, start=1):
        cursor.execute("INSERT INTO phan_cong_truc (khoi, lop, tuan, lop_truc) VALUES (%s, %s, %s, %s)",
                       (khoi, lop, tuan, lop_truc))
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/insert_account', methods=['GET'])
@login_required
def insert_account_form():
    if 'username' not in session or session['role'] != 'admin':
        flash("Bạn không có quyền truy cập trang này.", 'error')
        return redirect(url_for('login'))
    
    return render_template('insert_account.html')

@app.route('/add_account', methods=['POST'])
@login_required
def add_account():
    if 'username' not in session or session['role'] != 'admin':
        flash("Bạn không có quyền thực hiện hành động này.", 'error')
        return redirect(url_for('login'))

    input_tuan = request.form.get('current_tuan_for_add', type=int) or 1
    
    input_name = request.form['name']
    input_username = request.form['username']
    input_lop = request.form['lop']
    input_capquanli = request.form['Capquanli']
    
    input_password = generate_specific_password()
    input_role = input_capquanli

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        sql = """
        INSERT INTO accounts (Name, username, password, role, lop, tuan, Capquanli, trangthai)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (input_name, input_username, input_password,
                              input_role, input_lop, input_tuan, input_capquanli, 'Chưa tổng kết'))

        conn.commit()
        flash(f"Thêm tài khoản thành công! Tên người dùng: **{input_username}**, Mật khẩu: **{input_password}**, Tuần: **{input_tuan}**", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi thêm tài khoản: {err}", 'error')
        print(f"Error: {err}")

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return redirect(url_for('index', tuan=input_tuan if input_tuan != 1 else None))

@app.route('/toggle_status/<int:account_id>', methods=['POST'])
@login_required
def toggle_status(account_id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền thay đổi trạng thái tài khoản.", 'error')
        return redirect(url_for('index'))

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT trangthai FROM accounts WHERE id = %s", (account_id,))
        result = cursor.fetchone()
        if result:
            current_status = result[0]
            new_status = 'Đã tổng kết' if current_status == 'Đã tổng kết' else 'Đã tổng kết'
            cursor.execute("UPDATE accounts SET trangthai = %s WHERE id = %s", (new_status, account_id))
            conn.commit()
            flash("Trạng thái đã được cập nhật!", "success")
        else:
            flash("Không tìm thấy tài khoản.", "error")

    except mysql.connector.Error as err:
        flash(f"Lỗi cơ sở dữ liệu: {err}", 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return redirect(url_for('index'))

@app.route('/edit_account/<int:account_id>', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền chỉnh sửa tài khoản.", 'error')
        return redirect(url_for('index'))

    conn = None
    account_to_edit = None
    accounts = []
    selected_tuan = request.args.get('tuan', type=int)

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        sql_query = "SELECT id, Name, username, password, role, lop, tuan, Capquanli, lop_truc, trangthai FROM accounts"
        query_params = []
        if selected_tuan is not None:
            sql_query += " WHERE tuan = %s"
            query_params.append(selected_tuan)
        sql_query += " ORDER BY id DESC"

        cursor.execute(sql_query, tuple(query_params))
        accounts = cursor.fetchall()

        if request.method == 'POST':
            input_name = request.form['name']
            input_username = request.form['username']
            input_lop = request.form['lop']
            input_capquanli = request.form['Capquanli']
            input_tuan_edit = request.form.get('tuan_edit', type=int)
            input_lop_truc = request.form.get('lop_truc', '')
            input_trangthai = request.form.get('trangthai', 'Chưa tổng kết')

            cursor.execute("SELECT password FROM accounts WHERE id = %s", (account_id,))
            old_password_row = cursor.fetchone()
            if old_password_row:
                input_password = old_password_row['password']
            else:
                flash("Không tìm thấy tài khoản để cập nhật.", 'error')
                return redirect(url_for('index', tuan=selected_tuan))

            input_role = input_capquanli

            sql = """
            UPDATE accounts
            SET Name = %s, username = %s, password = %s, role = %s, lop = %s, tuan = %s, Capquanli = %s, lop_truc = %s, trangthai = %s
            WHERE id = %s
            """
            cursor.execute(sql, (input_name, input_username, input_password,
                                 input_role, input_lop, input_tuan_edit, input_capquanli, input_lop_truc, input_trangthai, account_id))
            conn.commit()
            flash(f"Cập nhật tài khoản '{input_username}' thành công!", 'success')
            return redirect(url_for('index', tuan=selected_tuan))

        else:
            sql_select_edit = "SELECT id, Name, username, password, role, lop, tuan, Capquanli, lop_truc, trangthai FROM accounts WHERE id = %s"
            cursor.execute(sql_select_edit, (account_id,))
            account_to_edit = cursor.fetchone()

            if not account_to_edit:
                flash("Không tìm thấy tài khoản để chỉnh sửa.", 'error')
                return redirect(url_for('index', tuan=selected_tuan))

    except mysql.connector.Error as err:
        flash(f"Lỗi cơ sở dữ liệu: {err}", 'error')
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return render_template('insert_account.html', account_to_edit=account_to_edit, accounts=accounts, selected_tuan=selected_tuan)

@app.route('/delete_account/<int:account_id>')
@login_required
def delete_account(account_id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền xóa tài khoản.", 'error')
        return redirect(url_for('index'))

    conn = None
    selected_tuan = request.args.get('tuan', type=int)

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
        conn.commit()
        flash(f"Xóa tài khoản ID {account_id} thành công!", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi xóa tài khoản: {err}", 'error')
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return redirect(url_for('index', tuan=selected_tuan))

@app.route('/set_all_tuan', methods=['POST'])
@login_required
def set_all_tuan():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền thực hiện thao tác này.", 'error')
        return redirect(url_for('index'))

    new_tuan = request.form.get('new_tuan_value', type=int)
    
    if new_tuan is None or not (1 <= new_tuan <= 40):
        flash("Giá trị tuần không hợp lệ. Vui lòng chọn tuần từ 1 đến 40.", 'error')
        return redirect(url_for('index'))

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        sql_update_tuan = "UPDATE accounts SET tuan = %s"
        cursor.execute(sql_update_tuan, (new_tuan,))
        
        sql_update_trangthai = "UPDATE accounts SET trangthai = 'Chưa tổng kết'"
        cursor.execute(sql_update_trangthai)

        conn.commit()
        flash(f"Đã cập nhật tất cả tài khoản sang Tuần {new_tuan} và đặt trạng thái tổng kết về 'Chưa tổng kết' thành công!", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi cập nhật tuần hàng loạt hoặc trạng thái: {err}", 'error')
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('index', tuan=new_tuan))

@app.route('/update_lop_truc', methods=['POST'])
@login_required
def update_lop_truc_route():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền cập nhật lớp trực.", 'error')
        return redirect(url_for('index'))

    message = update_lop_truc_data()
    flash(message)
    return redirect(url_for('index'))

@app.route('/save_schedule', methods=['POST'])
@login_required
def save_schedule():
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện hành động này.'}), 403

    data = request.get_json()
    try:
        insert_schedule(data)
        return jsonify({'message': 'Đã lưu vào SQL thành công!'}), 200
    except Exception as e:
        return jsonify({'message': f'Lỗi khi lưu lịch: {str(e)}'}), 500

@app.route('/update_schedule', methods=['POST'])
@login_required
def update_schedule_route():
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện hành động này.'}), 403

    data = request.get_json()
    try:
        update_schedule(data)
        return jsonify({'message': 'Đã cập nhật phân công thành công!'}), 200
    except Exception as e:
        return jsonify({'message': f'Lỗi khi cập nhật lịch: {str(e)}'}), 500

@app.route('/clear_all', methods=['POST'])
@login_required
def clear_all_route():
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện hành động này.'}), 403

    try:
        clear_all_schedule()
        return jsonify({'message': 'Đã xóa tất cả phân công trong cơ sở dữ liệu!'}), 200
    except Exception as e:
        return jsonify({'message': f'Lỗi khi xóa lịch: {str(e)}'}), 500

@app.route('/api/get_class_summary_status', methods=['GET'])
@login_required
def get_class_summary_status():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT MAX(tuan) AS latest_tuan FROM bang_tong_ket")
        result = cursor.fetchone()
        latest_tuan = result['latest_tuan']

        if not latest_tuan:
            return jsonify({'class_statuses': [], 'current_week': None, 'message': 'Không có dữ liệu tổng kết nào để hiển thị trạng thái lớp.'}), 200

        cursor.execute("SELECT DISTINCT lop FROM bang_tong_ket WHERE tuan = %s", (latest_tuan,))
        duty_classes_raw = cursor.fetchall()
        duty_classes = [row['lop'] for row in duty_classes_raw]

        cursor.execute("SELECT username, trangthai FROM accounts WHERE tuan = %s", (latest_tuan,))
        user_statuses = {row['username']: row['trangthai'] for row in cursor.fetchall()}

        cursor.execute("SELECT username, lop FROM info_data")
        user_classes = {row['username']: row['lop'] for row in cursor.fetchall()}

        class_summary_data = []
        for duty_class in duty_classes:
            has_summarized = False
            for username, user_class in user_classes.items():
                if user_class == duty_class and user_statuses.get(username) == 'Đã tổng kết':
                    has_summarized = True
                    break
            
            status_text = 'Đã tổng kết' if has_summarized else 'Chưa tổng kết'
            class_summary_data.append({
                'lop': duty_class,
                'status': status_text,
                'tuan': latest_tuan
            })
        
        class_summary_data.sort(key=lambda x: x['lop'])

        return jsonify({'class_statuses': class_summary_data, 'current_week': latest_tuan})

    except mysql.connector.Error as err:
        print(f"Lỗi MySQL khi lấy trạng thái tổng kết lớp: {err}")
        return jsonify({'error': f'Lỗi khi lấy trạng thái tổng kết lớp: {str(err)}'}), 500
    except Exception as e:
        print(f"Lỗi không xác định khi lấy trạng thái tổng kết lớp: {e}")
        return jsonify({'error': f'Lỗi không xác định: {str(e)}'}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/user_tong_ket', methods=['POST'])
@login_required
def user_tong_ket():
    if session.get('role') != 'user':
        flash("Bạn không có quyền thực hiện thao tác này.", 'error')
        return redirect(url_for('home'))

    user_username = session.get('username')
    user_lop = session.get('lop')
    user_tuan = session.get('tuan')

    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True, buffered=True)

        # Kiểm tra nếu đã tổng kết thì không cho tổng kết lại
        cursor.execute("SELECT trangthai FROM bang_tong_ket WHERE lop = %s AND tuan = %s", (user_lop, user_tuan))
        existing_summary = cursor.fetchone()

        if existing_summary and existing_summary['trangthai'] == 'Đã tổng kết':
            flash(f"Tuần {user_tuan} đã được tổng kết. Bạn không thể tổng kết lại.", 'warning')
            return redirect(url_for('home'))

        # Tính lại dữ liệu từ gốc
        cursor.execute("SELECT SUM(tong_diem) as study FROM study_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan))
        result_study = cursor.fetchone()
        tong_diem_hoc_tap = result_study['study'] if result_study and result_study['study'] is not None else 0

        cursor.execute("SELECT SUM(tong_diem_vi_pham) as rules FROM rules_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan))
        result_rules = cursor.fetchone()
        tong_diem_noi_quy = result_rules['rules'] if result_rules and result_rules['rules'] is not None else 0

        tong_diem_chung = tong_diem_hoc_tap + tong_diem_noi_quy

        # Ghi dữ liệu tổng kết
        cursor.execute("""
            INSERT INTO bang_tong_ket 
            (tuan, lop, tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung, trangthai)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                tong_diem_hoc_tap = %s, 
                tong_diem_noi_quy = %s, 
                tong_diem_chung = %s,
                trangthai = %s
        """, (
            user_tuan, user_lop, tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung, 'Đã tổng kết',
            tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung, 'Đã tổng kết'
        ))

        # Cập nhật trạng thái trong accounts
        cursor.execute("""
            UPDATE accounts 
            SET trangthai = 'Đã tổng kết'
            WHERE username = %s AND tuan = %s
        """, (user_username, user_tuan))

        conn.commit()
        flash(f"Đã tổng kết thành công cho lớp {user_lop} – Tuần {user_tuan}.", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi tổng kết: {err}", 'error')
        print(f"[MySQL Error] {err}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('home'))


@app.route('/get_accounts_status', methods=['GET'])
@login_required
def get_accounts_status():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Bạn không có quyền xem thông tin này.'}), 403

    conn = None
    accounts_data = []
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT username, lop_truc, trangthai, tuan FROM accounts")
        accounts_data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error fetching accounts status: {err}")
        return jsonify({'error': f"Lỗi khi lấy dữ liệu tài khoản: {err}"}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return jsonify({'accounts': accounts_data})

@app.route('/reset_account_status', methods=['POST'])
@login_required
def reset_account_status():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền thực hiện thao tác này.", 'error')
        return redirect(url_for('home'))

    data = request.get_json()
    username_to_reset = data.get('username')
    tuan_to_reset = data.get('tuan')

    if not username_to_reset or not tuan_to_reset:
        return jsonify({'error': 'Thiếu thông tin người dùng hoặc tuần.'}), 400

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("UPDATE accounts SET trangthai = 'Chưa tổng kết' WHERE username = %s AND tuan = %s", (username_to_reset, tuan_to_reset))
        conn.commit()
        return jsonify({'message': f"Đã đặt lại trạng thái cho {username_to_reset} Tuần {tuan_to_reset} thành 'Chưa tổng kết'."}), 200
    except mysql.connector.Error as err:
        print(f"Error resetting account status: {err}")
        return jsonify({'error': f"Lỗi khi đặt lại trạng thái: {err}"}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/phancong", methods=["GET", "POST"])
@login_required
def phancong_index():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập tính năng phân công.", 'error')
        return redirect(url_for('home'))

    result = []
    if request.method == "POST":
        khoi = request.form.get("khoi", "10")
        so_lop = int(request.form.get("so_lop", 20))
        so_tuan = int(request.form.get("so_tuan", 21))
        danh_sach_lop = [f"{khoi}A{i}" for i in range(1, so_lop + 1)]
        print(f"Phân công: khoi={khoi}, so_lop={so_lop}, so_tuan={so_tuan}, danh_sach_lop={danh_sach_lop}")  # Debug

        for i in range(so_lop):
            lop_hien_tai = danh_sach_lop[i]
            phan_cong = []
            j = 1
            while len(phan_cong) < so_tuan:
                index = (i + j) % so_lop
                lop_truc = danh_sach_lop[index]
                if lop_truc != lop_hien_tai:
                    phan_cong.append(lop_truc)
                j += 1
            print(f"Lớp {lop_hien_tai}: {phan_cong}")  # Debug
            save_phancong(khoi, lop_hien_tai, phan_cong)
            result.append({
                "khoi": khoi,
                "lop": lop_hien_tai,
                "phan_cong": phan_cong
            })
        update_lop_truc_data()  # Cập nhật lop_truc sau khi phân công
        flash("Phân công trực lớp và cập nhật tài khoản thành công!", 'success')
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT khoi, lop, tuan, lop_truc FROM phan_cong_truc ORDER BY lop, tuan")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        tmp = defaultdict(lambda: {"phan_cong": []})
        for khoi, lop, tuan, lop_truc in rows:
            tmp[lop]["khoi"] = khoi
            tmp[lop]["lop"] = lop
            tmp[lop]["phan_cong"].append(lop_truc)

        for lop, data in tmp.items():
            result.append(data)

    return render_template("testphancong.html", result=result)

@app.route('/clear_phancong_data', methods=['POST'])
@login_required
def clear_phancong_data():
    if session.get('role') != 'admin':
        return jsonify({'status': 'error', 'message': 'Bạn không có quyền thực hiện hành động này.'}), 403

    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE phan_cong_truc")
        conn.commit()
        flash("Đã xóa toàn bộ dữ liệu phân công trực thành công.", 'success')
        return jsonify({'status': 'success', 'message': 'Đã xóa toàn bộ dữ liệu phân công trực thành công.'}), 200
    except mysql.connector.Error as err:
        flash(f"Lỗi khi xóa dữ liệu phân công trực: {err}", 'error')
        print(f"Error clearing phancong_truc: {err}")
        return jsonify({'status': 'error', 'message': f'Lỗi khi xóa dữ liệu: {err}'}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/edit_rule', methods=['POST'])
@login_required
def edit_rule():
    rule_id = request.form['id']
    new_content = request.form['content']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rules_data SET content=%s WHERE id=%s", (new_content, rule_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify(success=True)

@app.route('/delete_rule', methods=['POST'])
@login_required
def delete_rule():
    if session.get('role') not in ['admin', 'user']:
        flash("Bạn không có quyền xóa dữ liệu nội quy.", 'error')
        return jsonify({'status': 'error', 'message': 'Bạn không có quyền xóa dữ liệu nội quy.'}), 403

    rule_id = request.form['id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT tuan FROM rules_data WHERE id = %s", (rule_id,))
    rule_info = cursor.fetchone()
    if not rule_info:
        cursor.close()
        conn.close()
        return jsonify({'status': 'error', 'message': 'Dữ liệu nội quy không tồn tại.'}), 404

    cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", 
                   (session.get('username'), rule_info['tuan']))
    account_status = cursor.fetchone()
    if account_status and account_status['trangthai'] == 'Đã tổng kết':
        flash("Không thể xóa dữ liệu nội quy vì tuần này đã được tổng kết.", 'error')
        cursor.close()
        conn.close()
        return jsonify({'status': 'error', 'message': 'Không thể xóa dữ liệu nội quy vì tuần này đã được tổng kết.'}), 403

    cursor.execute("DELETE FROM rules_data WHERE id=%s", (rule_id,))
    conn.commit()
    flash("Đã xóa dữ liệu nội quy thành công.", 'success')
    cursor.close()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Đã xóa dữ liệu nội quy thành công.'})

@app.route('/update_study_data/<int:data_id>', methods=['GET', 'POST'])
@login_required
def update_study_data(data_id):
    if session.get('role') != 'user':
        flash("Bạn không có quyền chỉnh sửa dữ liệu học tập.", 'error')
        return redirect(url_for('user'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", 
                   (session.get('username'), session.get('tuan')))
    account_status = cursor.fetchone()
    if account_status and account_status['trangthai'] == 'Đã tổng kết':
        flash("Không thể chỉnh sửa dữ liệu học tập vì tuần này đã được tổng kết.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('user'))

    if request.method == 'POST':
        gio_a = int(request.form.get('gio_a') or 0)
        gio_b = int(request.form.get('gio_b') or 0)
        gio_c = int(request.form.get('gio_c') or 0)
        gio_d = int(request.form.get('gio_d') or 0)
        dat_kieu_mau = request.form.get('dat_kieu_mau', 'No')

        tong_diem = gio_a * 5 + gio_b * -5 + gio_c * -15 + gio_d * -25
        tong_diem += 5 if dat_kieu_mau == 'Yes' else -10

        cursor.execute("""
            UPDATE study_data SET gio_a=%s, gio_b=%s, gio_c=%s, gio_d=%s,
            dat_kieu_mau=%s, tong_diem=%s WHERE id=%s
        """, (gio_a, gio_b, gio_c, gio_d, dat_kieu_mau, tong_diem, data_id))
        conn.commit()
        flash("Đã cập nhật dữ liệu học tập thành công.", 'success')
        cursor.close()
        conn.close()
        return redirect(url_for('user'))

    cursor.execute("SELECT * FROM study_data WHERE id = %s", (data_id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    if not data:
        flash("Không tìm thấy dữ liệu học tập để cập nhật.", 'error')
        return redirect(url_for('user'))

    return render_template('update_study.html', data=data)

@app.route('/update_rules_data/<int:data_id>', methods=['GET', 'POST'])
@login_required
def update_rules_data(data_id):
    if session.get('role') != 'user':
        flash("Bạn không có quyền chỉnh sửa dữ liệu nội quy.", 'error')
        return redirect(url_for('user'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", 
                   (session.get('username'), session.get('tuan')))
    account_status = cursor.fetchone()
    if account_status and account_status['trangthai'] == 'Đã tổng kết':
        flash("Không thể chỉnh sửa dữ liệu nội quy vì tuần này đã được tổng kết.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('user'))

    if request.method == 'POST':
        noi_dung_vi_pham = request.form.get('noi_dung_vi_pham')
        diem_tru = int(request.form.get('diem_tru') or 0)
        so_luot = int(request.form.get('so_luot_vi_pham') or 0)
        ten_hoc_sinh = request.form.get('ten_hoc_sinh_vi_pham')
        tong_diem = diem_tru * so_luot

        cursor.execute("""
            UPDATE rules_data SET noi_dung_vi_pham=%s, diem_tru=%s,
            so_luot_vi_pham=%s, tong_diem_vi_pham=%s, ten_hoc_sinh_vi_pham=%s
            WHERE id=%s
        """, (noi_dung_vi_pham, diem_tru, so_luot, tong_diem, ten_hoc_sinh, data_id))
        conn.commit()
        flash("Đã cập nhật dữ liệu nội quy thành công.", 'success')
        cursor.close()
        conn.close()
        return redirect(url_for('user'))

    cursor.execute("SELECT * FROM rules_data WHERE id = %s", (data_id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    if not data:
        flash("Không tìm thấy dữ liệu nội quy để cập nhật.", 'error')
        return redirect(url_for('user'))

    return render_template('update_rules.html', data=data)
@app.route('/toggle_tong_ket/<lop>/<tuan>', methods=['POST'])
@login_required
def toggle_tong_ket(lop, tuan):
    if session.get('role') != 'admin':
        abort(403)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy trạng thái hiện tại
    cursor.execute("SELECT trangthai FROM bang_tong_ket WHERE lop = %s AND tuan = %s", (lop, tuan))
    row = cursor.fetchone()

    if not row:
        flash(f"Không tìm thấy bản ghi tổng kết của {lop} – Tuần {tuan}", 'error')
    else:
        new_status = 'Chưa tổng kết' if row['trangthai'] == 'Đã tổng kết' else 'Đã tổng kết'

        # Cập nhật bang_tong_ket
        cursor.execute("UPDATE bang_tong_ket SET trangthai = %s WHERE lop = %s AND tuan = %s", (new_status, lop, tuan))

        # Cập nhật luôn accounts (nếu bạn vẫn dùng accounts.trangthai để hiển thị nhanh)
        cursor.execute("UPDATE accounts SET trangthai = %s WHERE lop = %s AND tuan = %s", (new_status, lop, tuan))

        conn.commit()
        flash(f"Đã cập nhật trạng thái tổng kết của {lop} – Tuần {tuan} thành: {new_status}", 'success')

    cursor.close()
    conn.close()
    return redirect(url_for('admin'))
@app.route('/toggle_tong_ket_status', methods=['POST'])
@login_required
def toggle_tong_ket_status():
    if session.get('role') != 'admin':
        abort(403)

    lop = request.form.get('lop')
    tuan = request.form.get('tuan')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)  # ✅ buffer nếu cần nhiều truy vấn

    # ✅ BẮT BUỘC: đọc kết quả trước khi thực hiện truy vấn khác
    cursor.execute("SELECT trangthai FROM bang_tong_ket WHERE lop = %s AND tuan = %s", (lop, tuan))
    result = cursor.fetchone()

    if result:
        # ✅ Đọc xong mới được xóa
        cursor.execute("DELETE FROM bang_tong_ket WHERE lop = %s AND tuan = %s", (lop, tuan))
        cursor.execute("UPDATE accounts SET trangthai = 'Chưa tổng kết' WHERE lop = %s AND tuan = %s", (lop, tuan))
        conn.commit()
        flash(f"Đã tổng kết lại lớp {lop} – Tuần {tuan}. Dữ liệu đã bị xoá.", 'success')
    else:
        flash(f"Không có dữ liệu để tổng kết lại.", 'info')

    cursor.close()
    conn.close()

    return redirect(url_for('tong_ket', tuan=tuan))

if __name__ == '__main__':
    create_table()  # Tạo bảng phan_cong_truc nếu chưa tồn tại
    app.run(host='0.0.0.0', port=5000, debug=True)