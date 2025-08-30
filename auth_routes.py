from flask import Blueprint, render_template, request, redirect, session, url_for, flash, jsonify
from functools import wraps
import mysql.connector
import random
import string
from config import DB_CONFIG
from db_utils import get_db_connection

auth_bp = Blueprint('auth', __name__)

def generate_specific_password():
    part1 = ''.join(random.choices(string.digits, k=3))
    part2 = ''.join(random.choices(string.digits, k=3))
    return f"{part1}@{part2}"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Bạn cần đăng nhập để truy cập trang này.", 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/')
def root():
    if 'username' in session:
        return redirect(url_for('auth.home'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
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
                return redirect(url_for('auth.home'))
            elif user['role'] == 'user':
                return redirect(url_for('auth.user'))
            elif user['role'] == 'viewer':
                return redirect(url_for('auth.viewer'))
            else:
                flash("Vai trò không hợp lệ.", 'error')
                return redirect(url_for('auth.login'))
        
        flash("Sai tài khoản hoặc mật khẩu.", 'error')
        return render_template('login.html', error="Sai tài khoản hoặc mật khẩu")
    
    return render_template('login.html')

@auth_bp.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST' and 'set_week' in request.form:
        if session.get('role') == 'admin':
            selected_week = request.form.get('week_select')
            session['tuan'] = selected_week
            flash(f"Tuần đã được đặt thành {selected_week}.", 'info')
            return redirect(url_for('auth.home'))
        else:
            flash("Bạn không có quyền thay đổi tuần hiển thị.", 'error')
            return redirect(url_for('auth.home'))

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

@auth_bp.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/admin')
@login_required
def admin():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang admin.", 'error')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM info_data")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin.html', data=data)

@auth_bp.route('/add', methods=['POST'])
@login_required
def add():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền thêm dữ liệu.", 'error')
        return redirect(url_for('auth.home'))

    name = request.form['name'].strip()
    email = request.form['email'].strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO info_data (name, email) VALUES (%s, %s)", (name, email))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Đã thêm dữ liệu thành công.", 'success')
    return redirect(url_for('auth.admin'))

@auth_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền chỉnh sửa dữ liệu.", 'error')
        return redirect(url_for('auth.home'))

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
        return redirect(url_for('auth.admin'))

    cursor.execute("SELECT * FROM info_data WHERE id=%s", (id,))
    user_info = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user_info:
        flash("Không tìm thấy dữ liệu để chỉnh sửa.", 'error')
        return redirect(url_for('auth.admin'))
    return render_template('edit.html', user=user_info)

@auth_bp.route('/delete/<int:id>')
@login_required
def delete(id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền xóa dữ liệu.", 'error')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM info_data WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Đã xóa dữ liệu ID {id} thành công.", 'success')
    return redirect(url_for('auth.admin'))

@auth_bp.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    if session.get('role') != 'user':
        flash("Bạn không có quyền truy cập trang người dùng.", 'error')
        return redirect(url_for('auth.home'))

    user_lop = session.get('lop')
    user_tuan_hien_tai = session.get('tuan')
    selected_tuan_tong_ket = request.args.get('tong_ket_tuan', type=str)
    user_lop_truc = session.get('lop_truc')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT trangthai FROM accounts WHERE username = %s", (session['username'],))
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

@auth_bp.route('/viewer')
@login_required
def viewer():
    if session.get('role') != 'viewer':
        flash("Bạn không có quyền truy cập trang xem.", 'error')
        return redirect(url_for('auth.home'))

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

@auth_bp.route('/index', methods=['GET'])
@login_required
def index():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang quản lý tài khoản.", 'error')
        return redirect(url_for('auth.home'))

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

@auth_bp.route('/insert_account', methods=['GET'])
@login_required
def insert_account_form():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang này.", 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('insert_account.html')

@auth_bp.route('/add_account', methods=['POST'])
@login_required
def add_account():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền thực hiện hành động này.", 'error')
        return redirect(url_for('auth.login'))

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

    return redirect(url_for('auth.index', tuan=input_tuan if input_tuan != 1 else None))

@auth_bp.route('/toggle_status/<int:account_id>', methods=['POST'])
@login_required
def toggle_status(account_id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền thay đổi trạng thái tài khoản.", 'error')
        return redirect(url_for('auth.index'))

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT trangthai FROM accounts WHERE id = %s", (account_id,))
        result = cursor.fetchone()
        if result:
            new_status = 'Đã tổng kết'
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

    return redirect(url_for('auth.index'))

@auth_bp.route('/edit_account/<int:account_id>', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền chỉnh sửa tài khoản.", 'error')
        return redirect(url_for('auth.index'))

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
                return redirect(url_for('auth.index', tuan=selected_tuan))

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
            return redirect(url_for('auth.index', tuan=selected_tuan))

        else:
            sql_select_edit = "SELECT id, Name, username, password, role, lop, tuan, Capquanli, lop_truc, trangthai FROM accounts WHERE id = %s"
            cursor.execute(sql_select_edit, (account_id,))
            account_to_edit = cursor.fetchone()

            if not account_to_edit:
                flash("Không tìm thấy tài khoản để chỉnh sửa.", 'error')
                return redirect(url_for('auth.index', tuan=selected_tuan))

    except mysql.connector.Error as err:
        flash(f"Lỗi cơ sở dữ liệu: {err}", 'error')
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return render_template('insert_account.html', account_to_edit=account_to_edit, accounts=accounts, selected_tuan=selected_tuan)

@auth_bp.route('/delete_account/<int:account_id>')
@login_required
def delete_account(account_id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền xóa tài khoản.", 'error')
        return redirect(url_for('auth.index'))

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

    return redirect(url_for('auth.index', tuan=selected_tuan))

@auth_bp.route('/set_all_tuan', methods=['POST'])
@login_required
def set_all_tuan():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền thực hiện thao tác này.", 'error')
        return redirect(url_for('auth.index'))

    new_tuan = request.form.get('new_tuan_value', type=int)
    
    if new_tuan is None or not (1 <= new_tuan <= 40):
        flash("Giá trị tuần không hợp lệ. Vui lòng chọn tuần từ 1 đến 40.", 'error')
        return redirect(url_for('auth.index'))

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
    
    return redirect(url_for('auth.index', tuan=new_tuan))

@auth_bp.route('/update_lop_truc', methods=['POST'])
@login_required
def update_lop_truc_route():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền cập nhật lớp trực.", 'error')
        return redirect(url_for('auth.index'))

    message = update_lop_truc_data()
    flash(message)
    return redirect(url_for('auth.index'))

def update_lop_truc_data():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

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
        return f"✅ Đã cập nhật {cursor.rowcount} bản ghi 'Lớp Trực'."
    except mysql.connector.Error as err:
        print(f"Error updating lop_truc: {err}")
        return f"❌ Lỗi cập nhật 'Lớp Trực': {err}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()