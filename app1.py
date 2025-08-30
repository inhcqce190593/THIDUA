from flask import Flask, render_template, request, jsonify, redirect
import mysql.connector

app = Flask(__name__)

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
        lop_truc = row['from']
        lop_duoc_truc = row['to']
        cursor.execute('''
            INSERT INTO phan_cong (khoi, tuan, lop_truc, lop_duoc_truc)
            VALUES (%s, %s, %s, %s)
        ''', (khoi, tuan, lop_truc, lop_duoc_truc))
    conn.commit()
    cursor.close()
    conn.close()

def update_schedule(data):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE phan_cong
        SET lop_truc = %s, lop_duoc_truc = %s
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

if __name__ == '__main__':
    app.run(debug=True)
