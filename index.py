from flask import Flask, request, render_template
import google.generativeai as genai

# Cấu hình API key Gemini (giữ nguyên hoặc thay đổi nếu cần)
genai.configure(api_key="AIzaSyCsFUauXy4vJffw511g48jeJwH17WlCctU")

app = Flask(__name__)

# Lưu lịch sử hội thoại
messages = []
chat_history = []

# Kiểm tra danh sách các model có sẵn
def get_available_models():
    try:
        models = genai.list_models()  # Lấy danh sách model
        return models
    except Exception as e:
        return f"❌ Lỗi khi lấy danh sách models: {str(e)}"

# Chọn model hợp lệ (ví dụ: "text-bison")
model = genai.GenerativeModel('text-bison')  # Sử dụng model 'text-bison' nếu 'gemini-pro' không hợp lệ

def get_gemini_response(message):
    try:
        # Kiểm tra nếu lịch sử chưa có
        if not chat_history:
            chat = model.start_chat(history=[])
        else:
            chat = model.start_chat(history=chat_history)

        # Gửi tin nhắn và nhận phản hồi
        response = chat.send_message(message)
        answer = response.text

        # Lưu vào lịch sử
        chat_history.append({"role": "user", "parts": [message]})
        chat_history.append({"role": "model", "parts": [answer]})
        return answer
    except Exception as e:
        return f"❌ Lỗi kết nối Gemini: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def chat():
    global messages
    error = None
    if request.method == 'POST':
        message = request.form.get('message', '')
        if message:
            answer = get_gemini_response(message)
            if answer.startswith("❌"):
                error = answer
            else:
                messages.append({"is_user": True, "q": message})
                messages.append({"is_user": False, "a": answer})
    return render_template('index.html', messages=messages, error=error)

@app.route('/reset', methods=['POST'])
def reset():
    global messages, chat_history
    messages = []
    chat_history = []
    return render_template('index.html', messages=messages, error=None)

if __name__ == '__main__':
    app.run(debug=True)
