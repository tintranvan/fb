from flask import Flask, Response
import os
import threading
import time
import subprocess
import sys
from datetime import datetime

app = Flask(__name__)

M3U_FILE = 'bunchatv_streams.m3u'
SCRAPER_SCRIPT = 'scrape_bunchatv_streams.py'
UPDATE_INTERVAL = 300  # 5 phút = 300 giây

def run_scraper():
    """Chạy scraper để update file M3U"""
    try:
        print(f"\n[{datetime.now()}] 🔄 Bắt đầu update M3U...")
        sys.stdout.flush()
        # Chạy scraper và stream output real-time
        result = subprocess.run([sys.executable, SCRAPER_SCRIPT], 
                              timeout=180)
        if result.returncode == 0:
            print(f"[{datetime.now()}] ✓ Update thành công\n")
        else:
            print(f"[{datetime.now()}] ✗ Update thất bại\n")
        sys.stdout.flush()
    except Exception as e:
        print(f"[{datetime.now()}] ✗ Lỗi: {e}\n")
        sys.stdout.flush()

def scheduler():
    """Thread để schedule update mỗi 5 phút"""
    while True:
        time.sleep(UPDATE_INTERVAL)
        run_scraper()

@app.route('/')
def index():
    """Hiển thị file M3U dạng text"""
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return f'<pre style="font-family: monospace; white-space: pre-wrap; word-wrap: break-word;">{content}</pre>'
    return 'File not found', 404

@app.route('/raw')
def raw_m3u():
    """Serve file M3U dạng raw text"""
    if os.path.exists(M3U_FILE):
        with open(M3U_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='application/vnd.apple.mpegurl')
    return 'File not found', 404

@app.route('/download')
def download():
    """Download file M3U"""
    if os.path.exists(M3U_FILE):
        return Response(
            open(M3U_FILE, 'rb').read(),
            mimetype='application/vnd.apple.mpegurl',
            headers={'Content-Disposition': 'attachment; filename=bunchatv_streams.m3u'}
        )
    return 'File not found', 404

@app.route('/health')
def health():
    """Health check"""
    exists = os.path.exists(M3U_FILE)
    size = os.path.getsize(M3U_FILE) if exists else 0
    return {
        'status': 'ok',
        'file': M3U_FILE,
        'exists': exists,
        'size': size,
        'updated': datetime.fromtimestamp(os.path.getmtime(M3U_FILE)).isoformat() if exists else None
    }

if __name__ == '__main__':
    # Chạy scraper lần đầu trong thread riêng (không block Flask)
    def initial_scrape():
        print("🔄 Cào dữ liệu lần đầu...")
        run_scraper()
        print("✓ Cào xong, bắt đầu schedule update mỗi 5 phút\n")
        # Sau khi cào xong, bắt đầu scheduler
        scheduler()
    
    scrape_thread = threading.Thread(target=initial_scrape, daemon=True)
    scrape_thread.start()
    
    import socket
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
    except:
        ip = "0.0.0.0"
    
    port = 8080
    print(f"\n🚀 Server chạy tại http://localhost:{port}")
    print(f"📱 Truy cập từ mạng nội bộ: http://{ip}:{port}")
    print(f"📥 Web: http://{ip}:{port}/")
    print(f"📥 Raw M3U: http://{ip}:{port}/raw")
    print(f"📥 Download M3U: http://{ip}:{port}/download")
    print(f"📊 Health check: http://{ip}:{port}/health")
    print(f"🔄 Update mỗi {UPDATE_INTERVAL} giây\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
