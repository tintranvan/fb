import asyncio
from playwright.async_api import async_playwright
import re
import json
from datetime import datetime

async def get_stream_link(page, match_url):
    """Lấy tất cả link stream m3u8 và tên trận từ trang chi tiết"""
    try:
        await page.goto(match_url, wait_until='networkidle', timeout=30000)
        
        # Chờ video player load
        await page.wait_for_timeout(3000)
        
        # Lấy HTML
        html = await page.content()
        
        # Tìm tên trận từ title tag - chỉ lấy phần trước dấu "|" hoặc trước "</title>"
        match_name = ""
        title_match = re.search(r'<title>([^|<]+?)\s*(?:\||</title>)', html)
        if title_match:
            match_name = title_match.group(1).strip()
            # Loại bỏ "Xem trực tiếp " ở đầu
            match_name = re.sub(r'^Xem trực tiếp\s+', '', match_name)
        
        # Tìm tất cả m3u8 links (chỉ m3u8, bỏ mp4)
        m3u8_matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
        
        # Tìm trong script tags
        script_matches = re.findall(r'"(https?://[^"]+m3u8[^"]*)"', html)
        m3u8_matches.extend(script_matches)
        
        # Loại bỏ duplicates nhưng giữ thứ tự
        seen = set()
        unique_matches = []
        for link in m3u8_matches:
            if link not in seen:
                seen.add(link)
                unique_matches.append(link)
        
        if unique_matches:
            return unique_matches, match_name  # Trả về tất cả links và tên trận
        
        return [], match_name
    
    except Exception as e:
        print(f"Lỗi khi lấy stream: {e}")
        return [], ""

async def scrape_matches():
    """Cào danh sách trận đấu và link stream"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Truy cập trang chính
        print("📥 Đang tải trang chính...")
        await page.goto("https://bit.ly/bunchatv", wait_until='networkidle', timeout=30000)
        
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
                matches = [(m, f"Match {i}") for i, m in enumerate(alt_matches)]
            else:
                # Thử tìm data trong script tags (React state)
                print("   Tìm trong script tags...")
                script_pattern = r'<script[^>]*>(.+?)</script>'
                scripts = re.findall(script_pattern, html, re.DOTALL)
                print(f"   Tìm được {len(scripts)} script tags")
        
        # Loại bỏ duplicates dựa trên URL
        seen_urls = set()
        unique_matches = []
        for match_path, match_title in matches:
            if match_path not in seen_urls:
                seen_urls.add(match_path)
                unique_matches.append((match_path, match_title))
        
        matches = unique_matches
        print(f"✓ Sau loại bỏ duplicates: {len(matches)} trận đấu")
        
        m3u_content = "#EXTM3U\n"
        success_count = 0
        seen_stream_urls = set()  # Để loại bỏ duplicates stream links
        match_groups = {}  # Nhóm các trận cùng tên
        
        for idx, (match_path, match_title) in enumerate(matches, 1):  # Lấy tất cả trận
            try:
                # Lấy domain từ current page URL
                current_url = page.url
                if current_url and current_url.startswith('http'):
                    base_url = re.match(r'https?://[^/]+', current_url).group(0)
                else:
                    # Fallback - lấy từ match_path nếu có domain
                    base_url = "https://bit.ly"
                
                match_url = f"{base_url}{match_path}"
                print(f"\n[{idx}] Đang xử lý: {match_title}")
                print(f"    URL: {match_url}")
                
                # Lấy tất cả stream links và tên trận
                stream_links, match_name = await get_stream_link(page, match_url)
                
                if stream_links:
                    print(f"    ✓ Tìm được {len(stream_links)} link(s)")
                    print(f"    ✓ Tên: {match_name}")
                    
                    # Extract tvg_id từ URL
                    tvg_id = re.search(r'/(\d+)$', match_path)
                    tvg_id = tvg_id.group(1) if tvg_id else ""
                    
                    # Nhóm theo tên trận
                    if match_name not in match_groups:
                        match_groups[match_name] = {
                            'tvg_id': tvg_id,
                            'streams': []
                        }
                    
                    # Thêm tất cả links
                    for stream_link in stream_links:
                        if stream_link not in seen_stream_urls:
                            seen_stream_urls.add(stream_link)
                            match_groups[match_name]['streams'].append(stream_link)
                            success_count += 1
                            print(f"      ✓ Link {success_count}: {stream_link[:80]}...")
                else:
                    print(f"    ✗ Không tìm được stream link m3u8")
            
            except Exception as e:
                print(f"    ✗ Lỗi: {e}")
                continue
        
        # Tạo M3U content từ match_groups
        for match_name, data in match_groups.items():
            tvg_id = data['tvg_id']
            # Dùng tên trận làm group-title
            group_title = match_name.replace(' | ', ' - ').strip()
            
            for idx, stream_link in enumerate(data['streams'], 1):
                # Nếu có nhiều link, thêm số thứ tự
                if len(data['streams']) > 1:
                    display_name = f"{group_title} (Link {idx})"
                else:
                    display_name = group_title
                
                extinf_line = f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="{group_title}", {display_name}\n'
                m3u_content += extinf_line
                m3u_content += f"{stream_link}\n"
        
        # Lưu file M3U
        output_file = "fbtv_streams.m3u"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        print(f"\n✓ Hoàn thành!")
        print(f"✓ Lấy được {success_count} stream links")
        print(f"✓ File đã lưu: {output_file}")
        
        # Tạo shortlink bit.ly
        try:
            print(f"\n🔗 Tạo shortlink...")
            # Giả sử file được host tại GitHub raw
            raw_url = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/fbtv_streams.m3u"
            
            # Tạo bit.ly link (cần API token)
            # Nếu không có token, chỉ in URL
            print(f"📥 Raw M3U: {raw_url}")
            print(f"📥 Shortlink: https://bit.ly/bunchatv (cần setup manual)")
        except Exception as e:
            print(f"⚠️  Không thể tạo shortlink: {e}")
        
        await browser.close()

if __name__ == '__main__':
    print("🚀 Bắt đầu cào stream links từ FBTV...\n")
    asyncio.run(scrape_matches())
