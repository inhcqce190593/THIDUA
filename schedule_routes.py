from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from collections import defaultdict
from db_utils import get_db, save_phancong, insert_schedule, update_schedule, clear_all_schedule
from auth_routes import login_required, update_lop_truc_data
from config import DB_CONFIG

schedule_bp = Blueprint('schedule', __name__)

@schedule_bp.route('/assign_tuan', methods=['GET', 'POST'])
@login_required
def assign_tuan():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền phân công.", 'error')
        return redirect(url_for('auth.home'))

    if request.method == 'POST':
        lop = request.form['lop'].strip()
        tuan = request.form['tuan'].strip()
        conn = get_db()
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
        return redirect(url_for('schedule.assign_tuan'))
    return render_template('assign_tuan.html')

@schedule_bp.route('/phancong', methods=["GET", "POST"])
@login_required
def phancong_index():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập tính năng phân công.", 'error')
        return redirect(url_for('auth.home'))

    result = []
    if request.method == "POST":
        khoi = request.form.get("khoi", "10")
        so_lop = int(request.form.get("so_lop", 20))
        so_tuan = int(request.form.get("so_tuan", 21))
        danh_sach_lop = [f"{khoi}A{i}" for i in range(1, so_lop + 1)]
        print(f"Phân công: khoi={khoi}, so_lop={so_lop}, so_tuan={so_tuan}, danh_sach_lop={danh_sach_lop}")

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
            print(f"Lớp {lop_hien_tai}: {phan_cong}")
            save_phancong(khoi, lop_hien_tai, phan_cong)
            result.append({
                "khoi": khoi,
                "lop": lop_hien_tai,
                "phan_cong": phan_cong
            })
        update_lop_truc_data()
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

@schedule_bp.route('/clear_phancong_data', methods=['POST'])
@login_required
def clear_phancong_data():
    if session.get('role') != 'admin':
        return jsonify({'status': 'error', 'message': 'Bạn không có quyền thực hiện hành động này.'}), 403

    conn = None
    try:
        conn = get_db()
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

@schedule_bp.route('/save_schedule', methods=['POST'])
@login_required
def save_schedule():
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện.'}), 403

    data = request.get_json()
    try:
        insert_schedule(data)
        return jsonify({'message': 'Đã lưu vào hệ thống thành công!'}), 200
    except Exception as e:
        print(f"Error saving schedule: {e}")
        return jsonify({'message': f'Lỗi khi lưu lịch: {str(e)}'}), 500

@schedule_bp.route('/update_schedule', methods=['POST'])
@login_required
def update_schedule_route():
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện.'}), 403

    data = request.get_json()
    try:
        update_schedule(data)
        return jsonify({'message': 'Đã cập nhật phân công thành công!'}), 200
    except Exception as e:
        print(f"Error updating schedule: {e}")
        return jsonify({'message': f'Lỗi khi cập nhật lịch: {str(e)}'}), 500

@schedule_bp.route('/clear_all', methods=['POST'])
@login_required
def clear_all_route():
    if session.get('role') != 'admin':
        return jsonify({'message': 'Bạn không có quyền thực hiện.'}), 403

    try:
        clear_all_schedule()
        return jsonify({'message': 'Đã xóa tất cả phân công trong cơ sở dữ liệu!'}), 200
    except Exception as e:
        print(f"Error clearing all schedules: {e}")
        return jsonify({'message': f'Lỗi khi xóa lịch: {str(e)}'}), 500