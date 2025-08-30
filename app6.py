from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from functools import wraps
import mysql.connector
import random
import string

# Khởi tạo Flask app
app = Flask(__name__)
app.secret_key = 'secret123'  # Khóa bảo mật session. Hãy dùng một khóa mạnh hơn trong môi trường production!

# Hàm kết nối đến cơ sở dữ liệu MySQL cho các bảng chung
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='test' # Database chứa info_data, study_data, rules_data, bang_tong_ket
    )

# Cấu hình cơ sở dữ liệu cho bảng phan_cong
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'phancong_db' # Database cho phan_cong
}

# Cấu hình cơ sở dữ liệu cho bảng accounts (đã dùng DB_CONFIG trong code gốc)
DB_CONFIG = { # Đây là DB_CONFIG cho accounts table
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'test',  # Tên database cho accounts table
    'charset': 'utf8'
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

        sql_query = """
        UPDATE accounts AS a
        JOIN phan_cong_truc AS pct ON a.tuan = pct.tuan AND a.lop = pct.lop
        SET a.lop_truc = pct.lop_truc;
        """
        cursor.execute(sql_query)
        conn.commit()
        return f"✅ Đã cập nhật {cursor.rowcount} bản ghi 'Lớp Trực'."
    except mysql.connector.Error as err:
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
            flash("Bạn cần đăng nhập để truy cập trang này.", 'error')
            return redirect(url_for('login'))  # Nếu chưa đăng nhập thì chuyển hướng đến trang login
        return f(*args, **kwargs)
    return decorated_function

# Trang gốc, chuyển hướng đến /home
@app.route('/')
def root():
    # Có thể chuyển hướng trực tiếp đến login nếu chưa đăng nhập, hoặc home nếu đã đăng nhập
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

# Trang đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        conn = get_db_connection() # Sử dụng get_db_connection vì bảng accounts nằm trong database 'test'
        cursor = conn.cursor(dictionary=True)
        # Lưu ý: Mật khẩu không nên lưu plaintext, hãy sử dụng hashing (bcrypt)
        cursor.execute("SELECT * FROM accounts WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            # Đăng nhập thành công, lưu session
            session['username'] = user['username']
            session['role'] = user['role']
            session['lop'] = user.get('lop', 'N/A') # Lấy lớp nếu có

            flash(f"Chào mừng {user['username']}! Bạn đã đăng nhập thành công.", 'success')
            # Chuyển hướng theo vai trò (hoặc chung về home rồi xử lý phân quyền trên đó)
            if user['role'] == 'admin':
                return redirect(url_for('home')) # Admin có thể xem tất cả
            elif user['role'] == 'user':
                return redirect(url_for('user')) # User có trang riêng
            elif user['role'] == 'viewer':
                return redirect(url_for('viewer')) # Viewer có trang riêng
            else:
                flash("Vai trò không hợp lệ.", 'error')
                return redirect(url_for('login')) # Chuyển hướng lại trang đăng nhập
        
        flash("Sai tài khoản hoặc mật khẩu.", 'error')
        return render_template('login.html', error="Sai tài khoản hoặc mật khẩu")
    
    return render_template('login.html')

# Trang chính
@app.route('/home', methods=['GET', 'POST'])
@login_required # Yêu cầu đăng nhập để truy cập
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Xử lý chọn tuần (cho phép mọi người dùng đã đăng nhập)
    if request.method == 'POST' and 'set_week' in request.form:
        selected_week = request.form.get('week_select')
        session['tuan'] = selected_week
        flash(f"Tuần đã được đặt thành {selected_week}.", 'info')
        return redirect(url_for('home')) # Chuyển hướng lại để hiển thị tuần mới

    # Xử lý xóa/cập nhật dữ liệu (chỉ admin)
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

# Đăng xuất, xóa session
@app.route('/logout')
@login_required # Đảm bảo đã đăng nhập mới có thể logout
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", 'info')
    return redirect(url_for('login')) # Chuyển hướng về trang đăng nhập

# Trang admin, xem danh sách người dùng (info_data)
@app.route('/admin')
@login_required
def admin():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang admin.", 'error')
        return redirect(url_for('home')) # Hoặc redirect đến trang login nếu không có quyền

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
    user_info = cursor.fetchone() # Đổi tên biến để tránh trùng với 'user' trong session
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
@app.route('/user')
@login_required
def user():
    if session.get('role') != 'user':
        flash("Bạn không có quyền truy cập trang người dùng.", 'error')
        return redirect(url_for('home')) # Hoặc redirect đến trang login

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM info_data") # Lấy dữ liệu info_data cho trang user
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('user.html', data=data)

# Trang viewer (role viewer)
@app.route('/viewer')
@login_required
def viewer():
    if session.get('role') != 'viewer':
        flash("Bạn không có quyền truy cập trang xem.", 'error')
        return redirect(url_for('home')) # Hoặc redirect đến trang login

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM info_data") # Lấy dữ liệu info_data cho trang viewer
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('viewer.html', data=data)

# Trang Học Tập (study_data)
@app.route('/hoc_tap')
@login_required
def hoc_tap():
    # Cả admin và user đều có thể xem học tập
    if session.get('role') not in ['admin', 'user', 'viewer']: # Viewer cũng có thể xem
        flash("Bạn không có quyền truy cập vào mục Học Tập.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM study_data")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('hoc_tap.html', data=data)

# Thêm dữ liệu học tập
@app.route('/add_hoc_tap', methods=['GET', 'POST'])
@login_required
def add_hoc_tap():
    if session.get('role') not in ['admin', 'user']: # Chỉ admin và user mới có thể thêm
        flash("Bạn không có quyền thêm dữ liệu học tập.", 'error')
        return redirect(url_for('hoc_tap'))

    if request.method == 'POST':
        tuan = request.form['tuan'].strip()
        selected_tuan = request.args.get('tuan', type=int) 
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
        flash("Đã thêm dữ liệu học tập thành công.", 'success')
        return redirect(url_for('hoc_tap'))
    return render_template('add_hoc_tap.html')

# Trang Nội Quy
@app.route('/noi_quy')
@login_required
def noi_quy():
    # Cả admin và user đều có thể xem nội quy
    if session.get('role') not in ['admin', 'user', 'viewer']: # Viewer cũng có thể xem
        flash("Bạn không có quyền truy cập vào mục Nội Quy.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM rules_data")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('noi_quy.html', data=data)

# Thêm dữ liệu vi phạm nội quy
@app.route('/add_noi_quy', methods=['GET', 'POST'])
@login_required
def add_noi_quy():
    if session.get('role') not in ['admin', 'user']: # Chỉ admin và user mới có thể thêm
        flash("Bạn không có quyền thêm dữ liệu vi phạm nội quy.", 'error')
        return redirect(url_for('noi_quy'))

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
        flash("Đã thêm dữ liệu vi phạm nội quy thành công.", 'success')
        return redirect(url_for('noi_quy'))
    return render_template('add_noi_quy.html')

# Tổng kết điểm học tập và nội quy -> bảng bang_tong_ket
@app.route('/tong_ket')
@login_required
def tong_ket():
    if session.get('role') != 'admin':
        flash("Chỉ admin mới được tổng kết.", 'error')
        return redirect(url_for('home'))

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
        tuan_key = item['tuan']
        if tuan_key not in rank_by_tuan:
            rank_by_tuan[tuan_key] = 1
            item['xep_hang'] = 1
            rank_by_tuan[f'{tuan_key}_prev_diem'] = item['tong_diem_chung']
        else:
            prev_diem = rank_by_tuan[f'{tuan_key}_prev_diem']
            if item['tong_diem_chung'] == prev_diem:
                item['xep_hang'] = rank_by_tuan[tuan_key]
            else:
                rank_by_tuan[tuan_key] += 1
                item['xep_hang'] = rank_by_tuan[tuan_key]
            rank_by_tuan[f'{tuan_key}_prev_diem'] = item['tong_diem_chung']

    cursor.close()
    conn.close()
    flash("Tổng kết điểm đã được cập nhật.", 'success')
    return render_template('tong_ket.html', data=data)

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
        return redirect(url_for('assign_tuan')) # Redirect lại trang gán tuần
    return render_template('assign_tuan.html')  # Cần tạo file HTML cho việc phân công


@app.route('/index', methods=['GET']) # Đổi tên thành '/index' cho tiện
@login_required
def index():
    # Chỉ admin mới có quyền xem trang quản lý tài khoản này
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang quản lý tài khoản.", 'error')
        return redirect(url_for('home'))

    accounts = []
    conn = None
    selected_tuan = request.args.get('tuan', type=int) 

    try:
        conn = mysql.connector.connect(**DB_CONFIG) # Sử dụng DB_CONFIG cho accounts table
        cursor = conn.cursor(dictionary=True)

        sql_query = "SELECT id, Name, username, password, role, lop, tuan, Capquanli, lop_truc FROM accounts"
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

    # Lưu ý: 'insert_account.html' được dùng làm trang hiển thị danh sách tài khoản, 
    # bạn nên xem xét đổi tên hoặc tạo một template riêng cho việc hiển thị danh sách.
    return render_template('insert_account.html', accounts=accounts, selected_tuan=selected_tuan)

# @app.route('/add_account', methods=['POST'])
# Hàm này đã được định nghĩa lại ở dưới, tôi sẽ bỏ comment ở đây.

@app.route('/insert_account', methods=['GET'])
@login_required # Đảm bảo đã đăng nhập
def insert_account_form():
    # Kiểm tra quyền hạn, chỉ admin mới được cấp quyền
    if 'username' not in session or session['role'] != 'admin':
        flash("Bạn không có quyền truy cập trang này.", 'error')
        return redirect(url_for('login'))
    
    # Render template chứa form thêm tài khoản
    return render_template('insert_account.html') # Tạo file này ở bước 2

@app.route('/add_account', methods=['POST'])
@login_required # Đảm bảo đã đăng nhập
def add_account():
    # Kiểm tra quyền hạn, chỉ admin mới được cấp quyền
    if 'username' not in session or session['role'] != 'admin':
        flash("Bạn không có quyền thực hiện hành động này.", 'error')
        return redirect(url_for('login'))

    # Lấy tuần hiện tại, mặc định là 1 nếu không có
    input_tuan = request.form.get('current_tuan_for_add', type=int) or 1
    
    input_name = request.form['name']
    input_username = request.form['username']
    input_lop = request.form['lop']
    input_capquanli = request.form['Capquanli'] # Tên trường trong form phải khớp
    
    input_password = generate_specific_password() # Đảm bảo hàm này được định nghĩa
    input_role = input_capquanli # Gán role bằng Capquanli từ form

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG) # Đảm bảo DB_CONFIG được định nghĩa
        cursor = conn.cursor()

        sql = """
        INSERT INTO accounts (Name, username, password, role, lop, tuan, Capquanli)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (input_name, input_username, input_password,
                              input_role, input_lop, input_tuan, input_capquanli))

        conn.commit()
        flash(f"Thêm tài khoản thành công! Tên người dùng: **{input_username}**, Mật khẩu: **{input_password}**, Tuần: **{input_tuan}**", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi thêm tài khoản: {err}", 'error')
        print(f"Error: {err}") # In lỗi ra console để debug

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    # Chuyển hướng về trang chính hoặc trang quản lý tài khoản sau khi thêm
    return redirect(url_for('index', tuan=input_tuan if input_tuan != 1 else None))


@app.route('/edit_account/<int:account_id>', methods=['GET', 'POST'])
@login_required # Đảm bảo đã đăng nhập
def edit_account(account_id):
    # Chỉ admin mới được sửa tài khoản
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

        sql_query = "SELECT id, Name, username, password, role, lop, tuan, Capquanli, lop_truc FROM accounts"
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

            # Lấy mật khẩu cũ (không thay đổi mật khẩu khi sửa trừ khi có form riêng)
            cursor.execute("SELECT password FROM accounts WHERE id = %s", (account_id,))
            old_password_row = cursor.fetchone()
            if old_password_row:
                input_password = old_password_row['password']
            else:
                flash("Không tìm thấy tài khoản để cập nhật.", 'error')
                return redirect(url_for('index', tuan=selected_tuan))

            input_role = input_capquanli # role được gán bằng Capquanli

            sql = """
            UPDATE accounts
            SET Name = %s, username = %s, password = %s, role = %s, lop = %s, tuan = %s, Capquanli = %s, lop_truc = %s
            WHERE id = %s
            """
            cursor.execute(sql, (input_name, input_username, input_password,
                                 input_role, input_lop, input_tuan_edit, input_capquanli, input_lop_truc, account_id))
            conn.commit()
            flash(f"Cập nhật tài khoản '{input_username}' thành công!", 'success')
            return redirect(url_for('index', tuan=selected_tuan)) 

        else: # GET request để hiển thị form chỉnh sửa
            sql_select_edit = "SELECT id, Name, username, password, role, lop, tuan, Capquanli, lop_truc FROM accounts WHERE id = %s"
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
@login_required # Đảm bảo đã đăng nhập
def delete_account(account_id):
    # Chỉ admin mới được xóa tài khoản
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
@login_required # Đảm bảo đã đăng nhập
def set_all_tuan():
    # Chỉ admin mới được thay đổi tuần hàng loạt
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

        sql = "UPDATE accounts SET tuan = %s"
        cursor.execute(sql, (new_tuan,))
        conn.commit()
        flash(f"Đã cập nhật tất cả tài khoản sang Tuần {new_tuan} thành công!", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi cập nhật tuần hàng loạt: {err}", 'error')
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('index', tuan=new_tuan))

@app.route('/update_lop_truc', methods=['POST'])
@login_required # Đảm bảo đã đăng nhập
def update_lop_truc_route():
    # Chỉ admin mới được cập nhật lớp trực
    if session.get('role') != 'admin':
        flash("Bạn không có quyền cập nhật lớp trực.", 'error')
        return redirect(url_for('index'))

    message = update_lop_truc_data()
    flash(message)
    return redirect(url_for('index'))

@app.route('/view_schedule')
@login_required # Đảm bảo đã đăng nhập
def view_schedule():
    # Mọi người dùng đã đăng nhập có thể xem lịch
    data = get_all_schedule()
    return render_template('view_schedule.html', schedules=data)

@app.route('/save_schedule', methods=['POST'])
@login_required # Đảm bảo đã đăng nhập
def save_schedule():
    # Chỉ admin mới có quyền lưu lịch
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện hành động này.'}), 403 # Forbidden

    data = request.get_json()
    try:
        insert_schedule(data)
        return jsonify({'message': 'Đã lưu vào SQL thành công!'}), 200
    except Exception as e:
        return jsonify({'message': f'Lỗi khi lưu lịch: {str(e)}'}), 500

@app.route('/update_schedule', methods=['POST'])
@login_required # Đảm bảo đã đăng nhập
def update_schedule_route():
    # Chỉ admin mới có quyền cập nhật lịch
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện hành động này.'}), 403

    data = request.get_json()
    try:
        update_schedule(data)
        return jsonify({'message': 'Đã cập nhật phân công thành công!'}), 200
    except Exception as e:
        return jsonify({'message': f'Lỗi khi cập nhật lịch: {str(e)}'}), 500

@app.route('/clear_all', methods=['POST'])
@login_required # Đảm bảo đã đăng nhập
def clear_all_route():
    # Chỉ admin mới có quyền xóa tất cả lịch
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện hành động này.'}), 403

    try:
        clear_all_schedule()
        return jsonify({'message': 'Đã xóa tất cả phân công trong cơ sở dữ liệu!'}), 200
    except Exception as e:
        return jsonify({'message': f'Lỗi khi xóa lịch: {str(e)}'}), 500

# Khởi chạy Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)