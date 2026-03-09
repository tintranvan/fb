from flask import Flask, render_template, send_file, jsonify
import os
from datetime import datetime

app = Flask(__name__)

M3U_FILE = 'bunchatv_channels.m3u'

def read_m3u():
    """Đọc file M3U và parse dữ liệu với đầy đủ thông tin"""
    channels = []
    if not os.path.exists(M3U_FILE):
        return channels
    
    with open(M3U_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # Parse EXTINF line
            extinf_data = {
                'tvg_id': '',
                'group_title': '',
                'tvg_logo': '',
                'name': 'Unknown',
                'url': ''
            }
            
            # Extract tvg-id
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            if tvg_id_match:
                extinf_data['tvg_id'] = tvg_id_match.group(1)
            
            # Extract group-title
            group_match = re.search(r'group-title="([^"]*)"', line)
            if group_match:
                extinf_data['group_title'] = group_match.group(1)
            
            # Extract tvg-logo
            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            if logo_match:
                extinf_data['tvg_logo'] = logo_match.group(1)
            
            # Extract name (sau dấu phẩy cuối cùng)
            name_match = re.search(r',\s*(.+)$', line)
            if name_match:
                extinf_data['name'] = name_match.group(1).strip()
            
            # Lấy URL (dòng tiếp theo)
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    extinf_data['url'] = url
                    channels.append(extinf_data)
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
    print(f"🚀 Server chạy tại http://localhost:8080")
    print(f"📱 Truy cập từ mạng nội bộ: http://<your-ip>:8080")
    print(f"📥 Download M3U: http://localhost:8080/download")
    print(f"📊 API JSON: http://localhost:8080/api/channels")
    app.run(host='0.0.0.0', port=8080, debug=True)
