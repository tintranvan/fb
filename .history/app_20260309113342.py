from flask import Flask, render_template, send_file, jsonify
import os
from datetime import datetime

app = Flask(__name__)

M3U_FILE = 'bunchatv_channels.m3u'

def read_m3u():
    """Đọc file M3U và parse dữ liệu"""
    channels = []
    if not os.path.exists(M3U_FILE):
        return channels
    
    with open(M3U_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # Lấy tên channel
            name = line.split(',', 1)[1].strip() if ',' in line else 'Unknown'
            # Lấy URL (dòng tiếp theo)
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                channels.append({'name': name, 'url': url})
                i += 2
            else:
                i += 1
        else:
            i += 1
    
    return channels

@app.route('/')
def index():
    """Trang chính - hiển thị danh sách channel"""
    channels = read_m3u()
    return render_template('index.html', channels=channels, total=len(channels))

@app.route('/api/channels')
def api_channels():
    """API trả về danh sách channel dạng JSON"""
    channels = read_m3u()
    return jsonify({
        'total': len(channels),
        'channels': channels,
        'updated': datetime.now().isoformat()
    })

@app.route('/download')
def download():
    """Download file M3U"""
    if os.path.exists(M3U_FILE):
        return send_file(M3U_FILE, as_attachment=True, download_name='bunchatv_channels.m3u')
    return 'File not found', 404

@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'file': M3U_FILE, 'exists': os.path.exists(M3U_FILE)})

if __name__ == '__main__':
    print(f"🚀 Server chạy tại http://localhost:5000")
    print(f"📱 Truy cập từ mạng nội bộ: http://<your-ip>:5000")
    print(f"📥 Download M3U: http://localhost:5000/download")
    print(f"📊 API JSON: http://localhost:5000/api/channels")
    app.run(host='0.0.0.0', port=5000, debug=True)
