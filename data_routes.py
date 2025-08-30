from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from io import BytesIO
import mysql.connector
import pandas as pd
from fpdf import FPDF
from db_utils import get_db_connection
from auth_routes import login_required

data_bp = Blueprint('data', __name__)

@data_bp.route('/hoc_tap')
@login_required
def hoc_tap():
    if session.get('role') not in ['admin', 'user', 'viewer']:
        flash("Bạn không có quyền truy cập vào mục Học Tập.", 'error')
        return redirect(url_for('auth.home'))

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

@data_bp.route('/delete_hoc_tap_entry/<int:entry_id>', methods=['POST'])
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

@data_bp.route('/add_hoc_tap', methods=['GET', 'POST'])
@login_required
def add_hoc_tap():
    if session.get('role') not in ['admin', 'user']:
        flash("Bạn không có quyền thêm dữ liệu học tập.", 'error')
        return redirect(url_for('data.hoc_tap'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    user_lop = session.get('lop', '')
    user_tuan = session.get('tuan', '')
    
    if session.get('role') == 'user' and (not user_lop or not user_tuan):
        flash("Bạn cần được gán lớp và tuần trước khi thêm dữ liệu học tập.", 'error')
        conn.close()
        return redirect(url_for('auth.user'))

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
        return redirect(url_for('data.hoc_tap'))
    
    cursor.close()
    conn.close()
    return render_template('add_hoc_tap.html', user_lop=user_lop, user_tuan=user_tuan, role=session.get('role'))

@data_bp.route('/noi_quy')
@login_required
def noi_quy():
    if session.get('role') not in ['admin', 'user', 'viewer']:
        flash("Bạn không có quyền truy cập vào mục Nội Quy.", 'error')
        return redirect(url_for('auth.home'))

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

@data_bp.route('/add_noi_quy', methods=['GET', 'POST'])
@login_required
def add_noi_quy():
    if session.get('role') not in ['admin', 'user']:
        flash("Bạn không có quyền thêm dữ liệu vi phạm nội quy.", 'error')
        return redirect(url_for('data.noi_quy'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    user_lop = session.get('lop', '')
    user_tuan = session.get('tuan', '')

    if session.get('role') == 'user' and (not user_lop or not user_tuan):
        flash("Bạn cần được gán lớp và tuần trước khi thêm dữ liệu vi phạm nội quy.", 'error')
        conn.close()
        return redirect(url_for('auth.user'))

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
        return redirect(url_for('data.noi_quy'))
    
    cursor.close()
    conn.close()
    return render_template('add_noi_quy.html', user_lop=user_lop, user_tuan=user_tuan, role=session.get('role'))

@data_bp.route('/tong_ket', methods=['GET', 'POST'])
@login_required
def tong_ket():
    if session.get('role') != 'admin':
        flash("Chỉ admin mới được tổng kết.", 'error')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST' and 'recalculate' in request.form:
        cursor.execute("TRUNCATE TABLE bang_tong_ket")
        conn.commit()

        cursor.execute("SELECT DISTINCT tuan, lop FROM study_data UNION SELECT DISTINCT tuan, lop FROM rules_data")
        unique_weeks_lops = cursor.fetchall()

        for entry in unique_weeks_lops:
            tuan = entry['tuan']
            lop = entry['lop']

            cursor.execute("SELECT SUM(tong_diem) as total_study_points FROM study_data WHERE tuan = %s AND lop = %s", (tuan, lop))
            study_result = cursor.fetchone()
            total_study_points = study_result['total_study_points'] if study_result and study_result['total_study_points'] is not None else 0

            cursor.execute("SELECT SUM(tong_diem_vi_pham) as total_rules_points FROM rules_data WHERE tuan = %s AND lop = %s", (tuan, lop))
            rules_result = cursor.fetchone()
            total_rules_points = rules_result['total_rules_points'] if rules_result and rules_result['total_rules_points'] is not None else 0

            tong_diem_chung = total_study_points + total_rules_points

            cursor.execute("""
                INSERT INTO bang_tong_ket (tuan, lop, tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                tong_diem_hoc_tap = %s, 
                tong_diem_noi_quy = %s, 
                tong_diem_chung = %s
            """, (tuan, lop, total_study_points, total_rules_points, tong_diem_chung,
                  total_study_points, total_rules_points, tong_diem_chung))
            conn.commit()
        
        flash("Tổng kết điểm đã được cập nhật.", 'success')
        return redirect(url_for('data.tong_ket'))

    selected_tuan = request.args.get('tuan', type=str)

    cursor.execute("SELECT DISTINCT tuan FROM bang_tong_ket ORDER BY tuan ASC")
    available_weeks = [row['tuan'] for row in cursor.fetchall()]

    if selected_tuan:
        cursor.execute("SELECT * FROM bang_tong_ket WHERE tuan = %s ORDER BY tong_diem_chung DESC", (selected_tuan,))
    else:
        cursor.execute("SELECT * FROM bang_tong_ket ORDER BY tuan ASC, tong_diem_chung DESC")
    data = cursor.fetchall()

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
    
    return render_template('tong_ket.html', data=ranked_data, available_weeks=available_weeks, selected_tuan=selected_tuan)

@data_bp.route('/export_summary', methods=['GET'])
@login_required
def export_summary():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền xuất dữ liệu này.", 'error')
        return redirect(url_for('auth.home'))

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
            return redirect(url_for('auth.home'))

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
        return redirect(url_for('auth.home'))
    except Exception as e:
        flash(f"Lỗi không xác định khi xuất báo cáo Excel: {e}", 'error')
        print(f"General Error: {e}")
        return redirect(url_for('auth.home'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@data_bp.route('/export_hoc_tap_pdf', methods=['GET'])
@login_required
def export_hoc_tap_pdf():
    if session.get('role') not in ['admin', 'user', 'viewer']:
        flash("Bạn không có quyền xuất báo cáo này.", 'error')
        return redirect(url_for('data.hoc_tap'))

    selected_tuan = request.args.get('tuan', type=str)
    selected_lop = request.args.get('lop', type=str)

    if not selected_tuan or not selected_lop:
        flash("Vui lòng chọn Tuần và Lớp để xuất báo cáo PDF.", 'warning')
        return redirect(url_for('data.hoc_tap'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM study_data WHERE tuan = %s AND lop = %s ORDER BY id ASC"
    cursor.execute(query, (selected_tuan, selected_lop))
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    if not data:
        flash(f"Không có dữ liệu học tập cho Tuần {selected_tuan} và Lớp {selected_lop} để xuất báo cáo PDF.", 'warning')
        return redirect(url_for('data.hoc_tap', tuan=selected_tuan, lop=selected_lop))

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

@data_bp.route('/edit_rule', methods=['POST'])
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

@data_bp.route('/delete_rule', methods=['POST'])
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

@data_bp.route('/update_study_data/<int:data_id>', methods=['GET', 'POST'])
@login_required
def update_study_data(data_id):
    if session.get('role') != 'user':
        flash("Bạn không có quyền chỉnh sửa dữ liệu học tập.", 'error')
        return redirect(url_for('auth.user'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", 
                   (session.get('username'), session.get('tuan')))
    account_status = cursor.fetchone()
    if account_status and account_status['trangthai'] == 'Đã tổng kết':
        flash("Không thể chỉnh sửa dữ liệu học tập vì tuần này đã được tổng kết.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('auth.user'))

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
        return redirect(url_for('auth.user'))

    cursor.execute("SELECT * FROM study_data WHERE id = %s", (data_id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    if not data:
        flash("Không tìm thấy dữ liệu học tập để cập nhật.", 'error')
        return redirect(url_for('auth.user'))

    return render_template('update_study.html', data=data)

@data_bp.route('/update_rules_data/<int:data_id>', methods=['GET', 'POST'])
@login_required
def update_rules_data(data_id):
    if session.get('role') != 'user':
        flash("Bạn không có quyền chỉnh sửa dữ liệu nội quy.", 'error')
        return redirect(url_for('auth.user'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", 
                   (session.get('username'), session.get('tuan')))
    account_status = cursor.fetchone()
    if account_status and account_status['trangthai'] == 'Đã tổng kết':
        flash("Không thể chỉnh sửa dữ liệu nội quy vì tuần này đã được tổng kết.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('auth.user'))

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
        return redirect(url_for('auth.user'))

    cursor.execute("SELECT * FROM rules_data WHERE id = %s", (data_id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    if not data:
        flash("Không tìm thấy dữ liệu nội quy để cập nhật.", 'error')
        return redirect(url_for('auth.user'))

    return render_template('update_rules.html', data=data)

@data_bp.route('/user_tong_ket', methods=['POST'])
@login_required
def user_tong_ket():
    if session.get('role') != 'user':
        flash("Bạn không có quyền thực hiện thao tác này.", 'error')
        return redirect(url_for('auth.home'))

    user_username = session.get('username')
    user_tuan = session.get('tuan')

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT trangthai FROM accounts WHERE username = %s AND tuan = %s", (user_username, user_tuan))
        current_status = cursor.fetchone()

        if current_status and current_status[0] == 'Đã tổng kết':
            flash(f"Bạn đã tổng kết cho Tuần {user_tuan} rồi. Không thể tổng kết lại.", 'warning')
        else:
            cursor.execute("UPDATE accounts SET trangthai = 'Đã tổng kết' WHERE username = %s AND tuan = %s", (user_username, user_tuan))
            conn.commit()
            flash(f"Bạn đã tổng kết thành công cho Tuần {user_tuan}!", 'success')

    except mysql.connector.Error as err:
        flash(f"Lỗi khi tổng kết: {err}", 'error')
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('auth.home'))