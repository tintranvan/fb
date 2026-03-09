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
        
        # Chờ React render - chờ grid-matches__item elements
        print("⏳ Chờ content load...")
        try:
            await page.wait_for_selector('.grid-matches__item', timeout=20000)
            print("✓ Content loaded")
        except Exception as e:
            print(f"⚠️  Timeout chờ content: {e}")
            print("   Thử chờ thêm...")
            await page.wait_for_timeout(5000)
        
        # Chờ thêm để đảm bảo render xong
        await page.wait_for_timeout(3000)
        
        # Lấy HTML
        html = await page.content()
        
        # Debug: Lưu HTML để check
        with open('debug_html.txt', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"📄 HTML length: {len(html)}")
        
        # Parse matches từ HTML
        matches = []
        
        # Tìm tất cả grid-match__body links
        pattern = r'class="grid-match__body"[^>]*href="([^"]+)"[^>]*title="([^"]+)"'
        matches = re.findall(pattern, html)
        
        print(f"✓ Tìm được {len(matches)} trận đấu")
        
        if len(matches) == 0:
            print("⚠️  Không tìm được matches")
            # Thử pattern khác - tìm link trong grid-matches__item
            alt_pattern = r'href="(/truc-tiep/[^"]+)"'
            alt_matches = re.findall(alt_pattern, html)
            print(f"   Alt pattern tìm được: {len(alt_matches)}")
            if alt_matches:
                matches = [(m, f"Match {i}") for i, m in enumerate(alt_matches[:10])]
            else:
                # Thử tìm data trong script tags (React state)
                print("   Tìm trong script tags...")
                script_pattern = r'<script[^>]*>(.+?)</script>'
                scripts = re.findall(script_pattern, html, re.DOTALL)
                print(f"   Tìm được {len(scripts)} script tags")
        
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
