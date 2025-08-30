from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import random
import string

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # Cần có secret key khi sử dụng flash messages

# Cấu hình cơ sở dữ liệu
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'test',
    'charset': 'utf8'
}

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


@app.route('/', methods=['GET'])
def index():
    """Renders the form to add a new account and displays existing accounts, optionally filtered by 'tuan'."""
    accounts = []
    conn = None
    selected_tuan = request.args.get('tuan', type=int) # Lấy giá trị 'tuan' từ URL, mặc định là None nếu không có

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        sql_query = "SELECT id, Name, username, password, role, lop, tuan, Capquanli, lop_truc FROM accounts"
        query_params = []

        if selected_tuan is not None: # Nếu có tham số tuần, thì lọc
              sql_query += " WHERE tuan = %s"
              query_params.append(selected_tuan)
        
        sql_query += " ORDER BY id DESC" # Sắp xếp để dễ nhìn

        cursor.execute(sql_query, tuple(query_params))
        accounts = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Lỗi khi đọc dữ liệu từ DB: {err}")
        flash(f"Lỗi khi tải danh sách tài khoản: {err}", 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    # Truyền danh sách tài khoản và tuần đã chọn vào template
    return render_template('insert_account.html', accounts=accounts, selected_tuan=selected_tuan)


@app.route('/add_account', methods=['POST'])
def add_account():
    """Handles the form submission and inserts data into the database."""
    input_tuan = request.form.get('current_tuan_for_add', type=int) or 1
    
    input_name = request.form['name']
    input_username = request.form['username']
    input_lop = request.form['lop']
    input_capquanli = request.form['Capquanli']
    # 'lop_truc' sẽ không được thêm vào đây, sẽ được cập nhật sau bằng hàm update_lop_truc_data

    input_password = generate_specific_password()
    input_role = input_capquanli

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        sql = """
        INSERT INTO accounts (Name, username, password, role, lop, tuan, Capquanli)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (input_name, input_username, input_password,
                             input_role, input_lop, input_tuan, input_capquanli))

        conn.commit()
        flash(f"Thêm tài khoản thành công! Tên người dùng: {input_username}, Mật khẩu: {input_password}, Tuần: {input_tuan}", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi thêm tài khoản: {err}", 'error')
        print(f"Error: {err}")

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return redirect(url_for('index', tuan=input_tuan if input_tuan != 1 else None))


@app.route('/edit_account/<int:account_id>', methods=['GET', 'POST'])
def edit_account(account_id):
    conn = None
    account_to_edit = None
    accounts = []
    selected_tuan = request.args.get('tuan', type=int) # Lấy tuần của bộ lọc nếu có

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
            input_lop_truc = request.form.get('lop_truc', '') # Lấy giá trị lop_truc nếu có

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
            SET Name = %s, username = %s, password = %s, role = %s, lop = %s, tuan = %s, Capquanli = %s, lop_truc = %s
            WHERE id = %s
            """
            cursor.execute(sql, (input_name, input_username, input_password,
                                 input_role, input_lop, input_tuan_edit, input_capquanli, input_lop_truc, account_id))
            conn.commit()
            flash(f"Cập nhật tài khoản '{input_username}' thành công!", 'success')
            return redirect(url_for('index', tuan=selected_tuan)) # Chuyển hướng và giữ lại filter

        else:
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
def delete_account(account_id):
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
def set_all_tuan():
    """Cập nhật cột 'tuan' cho TẤT CẢ các tài khoản hiện có."""
    new_tuan = request.form.get('new_tuan_value', type=int)
    
    if new_tuan is None or not (1 <= new_tuan <= 40):
        flash("Giá trị tuần không hợp lệ. Vui lòng chọn tuần từ 1 đến 40.", 'error')
        return redirect(url_for('index')) # Quan trọng: Phải return ở đây nếu giá trị không hợp lệ

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Câu lệnh UPDATE tất cả các bản ghi
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
    
    # Chuyển hướng về trang chính và hiển thị bảng với tuần vừa được cài đặt
    return redirect(url_for('index', tuan=new_tuan))

@app.route('/update_lop_truc', methods=['POST'])
def update_lop_truc_route():
    """Route để xử lý yêu cầu cập nhật lop_truc."""
    message = update_lop_truc_data() # Gọi hàm xử lý cập nhật
    flash(message) # Hiển thị thông báo
    return redirect(url_for('index')) # Chuyển hướng về trang chính

if __name__ == '__main__':
    app.run(debug=True) # Để debug dễ dàng, có thể bỏ debug=True khi triển khai thật