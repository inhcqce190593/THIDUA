import yt_dlp
import os

# Danh sách các URL video YouTube cần tải
video_urls = [
    'https://youtu.be/x5rMkhnjGeQ?si=P8AKstyE3FuBMMqa',
    'https://youtu.be/e57N5PPm7EI?si=fQB5dEv5f0zQ0u6d',
    'https://youtu.be/V-KS-xYumv8?si=uQipXrWvu48VNK8S',
    'https://youtu.be/4F5NvzXA-WQ?si=g32Hh5l0UNgfNKxp',
    'https://youtu.be/Aee2abH7VEI?si=l9DQ7CPfNsPBgto8',
    'https://youtu.be/0UWGeUvxGLs?si=lT8wNVU8yyIluSUo',
    'https://youtu.be/SX7yvAeaMuI?si=OlFtZPelWZq_cgad',
    'https://youtu.be/eaiPc222wL0?si=wjs4ILKbRSWAIVjF',
    'https://youtu.be/6cOiNoptIWc?si=i-E0Kj5Kq2VTEP18',
    'https://youtu.be/qIPON5BvlEM?si=TX0OscP9vCk4ETLD',
    'https://youtu.be/HBuskjjp9qI?si=DYwuM56Orlh5rFKB',
    'https://youtu.be/e57N5PPm7EI?si=ukgnfB99oA9-4ThV',
    'https://youtu.be/iU9YsRVT9HI?si=jTZ2q9Fd-fUZv1IP',
]

# Đường dẫn thư mục lưu video
download_folder = 'downloaded_videos'

# Kiểm tra nếu thư mục chưa tồn tại thì tạo mới
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

# Tùy chọn tải video và âm thanh ghép lại
ydl_opts = {
    'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),  # Đặt tên tệp video
    'format': 'bestvideo+bestaudio/best',  # Lựa chọn video và âm thanh tốt nhất, ghép lại tự động
    'noplaylist': True,  # Không tải danh sách phát
    'merge_output_format': 'mp4',  # Ghép video và âm thanh thành định dạng mp4
}

# Tải video
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for url in video_urls:
        ydl.download([url])

print("Đã tải xong tất cả các video.")
