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
# Trong app8.py
# ... (các hàm khác) ...

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
            session['role'] = user['role']
            session['lop'] = user.get('lop', 'N/A') # Lấy lớp nếu có
            session['tuan'] = user.get('tuan', 'N/A') # Lấy tuần của người dùng
            session['lop_truc'] = user.get('lop_truc', 'N/A') # Lấy lop_truc của người dùng
            
            flash(f"Chào mừng {user['username']}! Bạn đã đăng nhập thành công.", 'success')
            if user['role'] == 'admin':
                return redirect(url_for('home'))
            elif user['role'] == 'user':
                return redirect(url_for('user')) # Chuyển hướng đến trang user
            elif user['role'] == 'viewer':
                return redirect(url_for('viewer'))
            else:
                flash("Vai trò không hợp lệ.", 'error')
                return redirect(url_for('login'))
        
        flash("Sai tài khoản hoặc mật khẩu.", 'error')
        return render_template('login.html', error="Sai tài khoản hoặc mật khẩu")
    
    return render_template('login.html')

# ... (các hàm khác) ...
# Trang chính
@app.route('/home', methods=['GET', 'POST'])
@login_required # Yêu cầu đăng nhập để truy cập
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Xử lý chọn tuần (cho phép mọi người dùng đã đăng nhập)
    # Admin có thể set tuần cho các tài khoản, user có tuần riêng
    if request.method == 'POST' and 'set_week' in request.form:
        if session.get('role') == 'admin':
            selected_week = request.form.get('week_select')
            session['tuan'] = selected_week # Admin có thể thay đổi tuần hiển thị
            flash(f"Tuần đã được đặt thành {selected_week}.", 'info')
            return redirect(url_for('home'))
        else:
            flash("Bạn không có quyền thay đổi tuần hiển thị.", 'error')
            return redirect(url_for('home'))

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

    # Lấy dữ liệu học tập và vi phạm nội quy (dành cho admin, hiện tất cả)
    study_data = []
    rules_data = []
    if session.get('role') == 'admin':
        cursor.execute("SELECT * FROM study_data")
        study_data = cursor.fetchall()

        cursor.execute("SELECT * FROM rules_data")
        rules_data = cursor.fetchall()

    cursor.close()
    conn.close()

    # Lấy lớp trực và tuần từ session (nếu có)
    lop = session.get('lop', 'Không xác định')
    tuan = session.get('tuan', 'Chưa thiết lập')
    lop_truc = session.get('lop_truc', 'Chưa thiết lập')


    return render_template('home.html', study_data=study_data, rules_data=rules_data, lop=lop, tuan=tuan, lop_truc=lop_truc)

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
# Trong app8.py

# ... (các import và cấu hình khác) ...

# Trang người dùng (chỉ người dùng role 'user' mới xem được)
# Trong app8.py
# ...

# Trang người dùng (chỉ người dùng role 'user' mới xem được)
@app.route('/user', methods=['GET']) # Đảm bảo phương thức GET được chấp nhận
@login_required
def user():
    if session.get('role') != 'user':
        flash("Bạn không có quyền truy cập trang người dùng.", 'error')
        return redirect(url_for('home'))

    user_lop = session.get('lop')
    user_tuan_hien_tai = session.get('tuan') # Tuần hiện tại của tài khoản người dùng

    # Lấy tuần mà người dùng muốn xem tổng kết từ query parameter (mặc định là tuần hiện tại của lớp)
    selected_tuan_tong_ket = request.args.get('tong_ket_tuan', type=str)
    
    user_lop_truc = session.get('lop_truc')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Lấy thông tin user hiện tại để kiểm tra trạng thái tổng kết
    cursor.execute("SELECT trangthai FROM accounts WHERE username = %s", (session['username'],))
    account_status = cursor.fetchone()
    trangthai_tongket = account_status['trangthai'] if account_status else 'No'

    # Lấy dữ liệu học tập và nội quy chỉ của lớp và tuần của user
    study_data = []
    rules_data = []
    tong_ket_data = [] # Biến để lưu dữ liệu tổng kết

    # Lấy tất cả các tuần mà lớp của user có dữ liệu trong bang_tong_ket để populate dropdown
    available_weeks_for_lop = []
    if user_lop:
        cursor.execute("SELECT DISTINCT tuan FROM bang_tong_ket WHERE lop = %s ORDER BY tuan ASC", (user_lop,))
        available_weeks_for_lop = [row['tuan'] for row in cursor.fetchall()]
        
        # Nếu chưa có selected_tuan_tong_ket, gán nó là tuần hiện tại của tài khoản hoặc tuần đầu tiên có dữ liệu của lớp
        if not selected_tuan_tong_ket and user_tuan_hien_tai in available_weeks_for_lop:
            selected_tuan_tong_ket = user_tuan_hien_tai
        elif not selected_tuan_tong_ket and available_weeks_for_lop:
            selected_tuan_tong_ket = available_weeks_for_lop[0] # Chọn tuần đầu tiên nếu tuần hiện tại không có dữ liệu tổng kết

    if user_lop and user_tuan_hien_tai: # Điều kiện để hiển thị dữ liệu học tập và nội quy theo tuần hiện tại của user
        cursor.execute("SELECT * FROM study_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan_hien_tai))
        study_data = cursor.fetchall()

        cursor.execute("SELECT * FROM rules_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan_hien_tai))
        rules_data = cursor.fetchall()
    else:
        flash("Thông tin lớp hoặc tuần của tài khoản bạn chưa được thiết lập. Vui lòng liên hệ quản trị viên.", 'info')

    # Lấy dữ liệu tổng kết cho lớp của người dùng theo tuần được chọn (selected_tuan_tong_ket)
    if user_lop and selected_tuan_tong_ket:
        cursor.execute("""
            SELECT * FROM bang_tong_ket 
            WHERE lop = %s AND tuan = %s
            ORDER BY tong_diem_chung DESC
        """, (user_lop, selected_tuan_tong_ket))
        tong_ket_data = cursor.fetchall()
        
        # Nếu có dữ liệu tổng kết, tính xếp hạng cho tuần đó
        if tong_ket_data:
            # Lấy tất cả các lớp trong cùng tuần để tính xếp hạng chính xác
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
                
                # Tìm và cập nhật xếp hạng cho lớp của user trong tong_ket_data
                for user_item in tong_ket_data: # tong_ket_data chỉ chứa dữ liệu của 1 lớp
                    if user_item['lop'] == user_lop: # Điều kiện này luôn đúng nếu tong_ket_data không rỗng
                        user_item['xep_hang'] = item['xep_hang'] # Lấy xếp hạng của lớp hiện tại
                        break
    else:
        flash("Không có thông tin lớp hoặc tuần để hiển thị dữ liệu tổng kết.", 'info')


    cursor.close()
    conn.close()
    
    return render_template('user.html', 
                           study_data=study_data, 
                           rules_data=rules_data, 
                           lop=user_lop, 
                           tuan=user_tuan_hien_tai, # Tuần hiện tại của tài khoản
                           lop_truc=user_lop_truc, 
                           trangthai_tongket=trangthai_tongket,
                           tong_ket_data=tong_ket_data, # Dữ liệu tổng kết cho lớp và tuần được chọn
                           selected_tuan_tong_ket=selected_tuan_tong_ket, # Tuần đang được hiển thị trong bảng tổng kết
                           available_weeks_for_lop=available_weeks_for_lop) # Các tuần có dữ liệu tổng kết cho lớp này
# Trang viewer (role viewer)
@app.route('/viewer')
@login_required
def viewer():
    if session.get('role') != 'viewer':
        flash("Bạn không có quyền truy cập trang xem.", 'error')
        return redirect(url_for('home')) # Hoặc redirect đến trang login

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
    # Cả admin và user đều có thể xem học tập
    if session.get('role') not in ['admin', 'user', 'viewer']: # Viewer cũng có thể xem
        flash("Bạn không có quyền truy cập vào mục Học Tập.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    data = []
    user_role = session.get('role')
    
    if user_role == 'admin':
        cursor.execute("SELECT * FROM study_data")
        data = cursor.fetchall()
    elif user_role in ['user', 'viewer']:
        user_lop = session.get('lop')
        user_tuan = session.get('tuan')
        if user_lop and user_tuan:
            cursor.execute("SELECT * FROM study_data WHERE lop = %s AND tuan = %s", (user_lop, user_tuan))
            data = cursor.fetchall()
        else:
            flash("Không có thông tin lớp hoặc tuần để hiển thị dữ liệu học tập.", 'info')

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

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy thông tin lớp và tuần của người dùng hiện tại
    user_lop = session.get('lop', '')
    user_tuan = session.get('tuan', '')
    
    # Chỉ cho user nhập nếu lớp và tuần đã được gán
    if session.get('role') == 'user' and (not user_lop or not user_tuan):
        flash("Bạn cần được gán lớp và tuần trước khi thêm dữ liệu học tập.", 'error')
        conn.close()
        return redirect(url_for('user'))

    if request.method == 'POST':
        # Đối với user, lấy tuần và lớp từ session; đối với admin, cho phép nhập
        if session.get('role') == 'admin':
            tuan = request.form['tuan'].strip()
            lop = request.form['lop'].strip()
        else: # role is 'user'
            tuan = user_tuan
            lop = user_lop

        gio_a = int(request.form['gio_a'] or 0)
        gio_b = int(request.form['gio_b'] or 0)
        gio_c = int(request.form['gio_c'] or 0)
        gio_d = int(request.form['gio_d'] or 0)
        dat_kieu_mau = request.form['dat_kieu_mau']

        # Tính tổng điểm học tập
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
@app.route('/noi_quy')
@login_required
def noi_quy():
    # Cả admin và user đều có thể xem nội quy
    if session.get('role') not in ['admin', 'user', 'viewer']: # Viewer cũng có thể xem
        flash("Bạn không có quyền truy cập vào mục Nội Quy.", 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
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

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy thông tin lớp và tuần của người dùng hiện tại
    user_lop = session.get('lop', '')
    user_tuan = session.get('tuan', '')

    # Chỉ cho user nhập nếu lớp và tuần đã được gán
    if session.get('role') == 'user' and (not user_lop or not user_tuan):
        flash("Bạn cần được gán lớp và tuần trước khi thêm dữ liệu vi phạm nội quy.", 'error')
        conn.close()
        return redirect(url_for('user'))

    if request.method == 'POST':
        # Đối với user, lấy tuần và lớp từ session; đối với admin, cho phép nhập
        if session.get('role') == 'admin':
            tuan = request.form['tuan'].strip()
            lop = request.form['lop'].strip()
        else: # role is 'user'
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
# Trong app8.py
# ...

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
        # Logic tính toán lại tổng kết đã có ở đây và đã đúng
        # ... (không thay đổi phần này) ...
        
        flash("Tổng kết điểm đã được cập nhật.", 'success')
        return redirect(url_for('tong_ket'))

    # Handle GET request (and after POST redirect)
    selected_tuan = request.args.get('tuan', type=str) # Lấy tuần được chọn từ query parameter

    # Lấy tất cả các tuần duy nhất từ bang_tong_ket để điền vào dropdown
    cursor.execute("SELECT DISTINCT tuan FROM bang_tong_ket ORDER BY tuan ASC")
    available_weeks = [row['tuan'] for row in cursor.fetchall()]

    # Lấy dữ liệu tổng kết dựa trên tuần được chọn hoặc tất cả các tuần
    if selected_tuan:
        cursor.execute("SELECT * FROM bang_tong_ket WHERE tuan = %s ORDER BY tong_diem_chung DESC", (selected_tuan,))
    else:
        # Nếu không có tuần nào được chọn, hiển thị tất cả các tuần, sắp xếp theo tuần và điểm
        cursor.execute("SELECT * FROM bang_tong_ket ORDER BY tuan ASC, tong_diem_chung DESC")
    data = cursor.fetchall()

    # Logic tính xếp hạng theo từng tuần cho dữ liệu được hiển thị
    ranked_data = []
    grouped_data = {}
    for item in data:
        if item['tuan'] not in grouped_data:
            grouped_data[item['tuan']] = []
        grouped_data[item['tuan']].append(item)
    
    for tuan_key in sorted(grouped_data.keys()):
        current_week_data = sorted(grouped_data[tuan_key], key=lambda x: x['tong_diem_chung'], reverse=True)
        current_rank = 1
        prev_diem = None
        for i, item in enumerate(current_week_data):
            if i > 0 and item['tong_diem_chung'] < prev_diem:
                current_rank = i + 1
            item['xep_hang'] = current_rank
            prev_diem = item['tong_diem_chung']
            ranked_data.append(item)

    cursor.close()
    conn.close()
    
    # Render template tong_ket.html
    return render_template('tong_ket.html', data=ranked_data, available_weeks=available_weeks, selected_tuan=selected_tuan)
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
        INSERT INTO accounts (Name, username, password, role, lop, tuan, Capquanli, trangthai)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (input_name, input_username, input_password,
                              input_role, input_lop, input_tuan, input_capquanli, 'No')) # Thêm cột trangthai mặc định là 'No'

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
            input_trangthai = request.form.get('trangthai', 'No') # Lấy trạng thái từ form, mặc định 'No'

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
            SET Name = %s, username = %s, password = %s, role = %s, lop = %s, tuan = %s, Capquanli = %s, lop_truc = %s, trangthai = %s
            WHERE id = %s
            """
            cursor.execute(sql, (input_name, input_username, input_password,
                                 input_role, input_lop, input_tuan_edit, input_capquanli, input_lop_truc, input_trangthai, account_id))
            conn.commit()
            flash(f"Cập nhật tài khoản '{input_username}' thành công!", 'success')
            return redirect(url_for('index', tuan=selected_tuan)) 

        else: # GET request để hiển thị form chỉnh sửa
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

        # Cập nhật cột 'tuan' cho tất cả tài khoản
        sql_update_tuan = "UPDATE accounts SET tuan = %s"
        cursor.execute(sql_update_tuan, (new_tuan,))
        
        # Cập nhật cột 'trangthai' thành 'No' cho tất cả tài khoản
        sql_update_trangthai = "UPDATE accounts SET trangthai = 'No'"
        cursor.execute(sql_update_trangthai)

        conn.commit()
        flash(f"Đã cập nhật tất cả tài khoản sang Tuần {new_tuan} và đặt trạng thái tổng kết về 'No' thành công!", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi cập nhật tuần hàng loạt hoặc trạng thái: {err}", 'error')
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

# @app.route('/view_schedule')
# @login_required # Đảm bảo đã đăng nhập
# def view_schedule():
#     # Mọi người dùng đã đăng nhập có thể xem lịch
#     data = get_all_schedule()
#     return render_template('view_schedule.html', schedules=data)

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

# Endpoint để user tổng kết
@app.route('/user_tong_ket', methods=['POST'])
@login_required
def user_tong_ket():
    if session.get('role') != 'user':
        flash("Bạn không có quyền thực hiện thao tác này.", 'error')
        return redirect(url_for('user'))

    user_username = session.get('username')
    user_tuan = session.get('tuan')

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Kiểm tra trạng thái tổng kết của user cho tuần hiện tại
        cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", (user_username, user_tuan))
        current_status = cursor.fetchone()

        if current_status and current_status[0] == 'Yes':
            flash(f"Bạn đã tổng kết cho Tuần {user_tuan} rồi. Không thể tổng kết lại.", 'warning')
        else:
            # Cập nhật trạng thái tổng kết thành 'Yes'
            cursor.execute("UPDATE accounts SET trangthai = 'Yes' WHERE username = %s AND tuan = %s", (user_username, user_tuan))
            conn.commit()
            flash(f"Bạn đã tổng kết thành công cho Tuần {user_tuan}!", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi tổng kết: {err}", 'error')
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    return redirect(url_for('user'))


# Khởi chạy Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)