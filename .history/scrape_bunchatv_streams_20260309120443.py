import asyncio
from playwright.async_api import async_playwright
import re
import json
from datetime import datetime

async def get_stream_link(page, match_url):
    """Lấy link stream từ trang chi tiết trận đấu"""
    try:
        await page.goto(match_url, wait_until='networkidle', timeout=30000)
        
        # Chờ video player load
        await page.wait_for_timeout(3000)
        
        # Lấy tất cả network requests tìm m3u8
        stream_links = []
        
        # Cách 1: Tìm trong HTML
        html = await page.content()
        
        # Tìm m3u8 links
        m3u8_matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
        stream_links.extend(m3u8_matches)
        
        # Tìm mp4 links
        mp4_matches = re.findall(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html)
        stream_links.extend(mp4_matches)
        
        # Tìm trong script tags
        script_matches = re.findall(r'"(https?://[^"]+(?:m3u8|mp4)[^"]*)"', html)
        stream_links.extend(script_matches)
        
        # Loại bỏ duplicates
        stream_links = list(set(stream_links))
        
        if stream_links:
            return stream_links[0]  # Trả về link đầu tiên
        
        return None
    
    except Exception as e:
        print(f"Lỗi khi lấy stream: {e}")
        return None

async def scrape_matches():
    """Cào danh sách trận đấu và link stream"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Truy cập trang chính
        print("📥 Đang tải trang chính...")
        await page.goto("http://bunchatv1.net/", wait_until='networkidle', timeout=30000)
        
        # Chờ page load
        await page.wait_for_timeout(3000)
        
        # Lấy HTML
        html = await page.content()
        
        # Debug: Lưu HTML để check
        with open('debug_html.txt', 'w', encoding='utf-8') as f:
            f.write(html[:5000])
        
        # Parse matches từ HTML - thử nhiều pattern
        matches = []
        
        # Pattern 1: Tìm link trực tiếp
        pattern1 = re.findall(r'href="(/truc-tiep/[^"]+)"[^>]*title="([^"]+)"', html)
        matches.extend(pattern1)
        
        # Pattern 2: Tìm trong grid-match__body
        pattern2 = re.findall(r'class="grid-match__body"[^>]*href="([^"]+)"[^>]*title="([^"]+)"', html)
        matches.extend(pattern2)
        
        # Pattern 3: Tìm team names
        team_pattern = re.findall(r'grid-match__team--name[^>]*>([^<]+)<', html)
        
        print(f"✓ Tìm được {len(matches)} trận đấu (pattern 1+2)")
        print(f"✓ Tìm được {len(team_pattern)} team names")
        
        if len(matches) == 0:
            print("⚠️  Không tìm được matches, check debug_html.txt")
            print(f"HTML length: {len(html)}")
        
        m3u_content = "#EXTM3U\n"
        success_count = 0
        
        for idx, (match_path, match_title) in enumerate(matches[:10], 1):  # Giới hạn 10 trận
            try:
                match_url = f"http://bunchatv1.net{match_path}"
                print(f"\n[{idx}] Đang xử lý: {match_title}")
                print(f"    URL: {match_url}")
                
                # Lấy stream link
                stream_link = await get_stream_link(page, match_url)
                
                if stream_link:
                    print(f"    ✓ Stream: {stream_link[:80]}...")
                    
                    # Extract thông tin từ title
                    tvg_id = re.search(r'/(\d+)$', match_path)
                    tvg_id = tvg_id.group(1) if tvg_id else ""
                    
                    # Tạo EXTINF line
                    extinf_line = f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="BunchaTV", {match_title}\n'
                    m3u_content += extinf_line
                    m3u_content += f"{stream_link}\n"
                    success_count += 1
                else:
                    print(f"    ✗ Không tìm được stream link")
            
            except Exception as e:
                print(f"    ✗ Lỗi: {e}")
                continue
        
        # Lưu file M3U
        output_file = "bunchatv_streams.m3u"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        print(f"\n✓ Hoàn thành!")
        print(f"✓ Lấy được {success_count} stream links")
        print(f"✓ File đã lưu: {output_file}")
        
        await browser.close()

if __name__ == '__main__':
    print("🚀 Bắt đầu cào stream links từ BunchaTV...\n")
    asyncio.run(scrape_matches())
