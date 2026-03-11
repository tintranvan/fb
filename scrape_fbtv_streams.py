import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime

async def get_stream_link(page, match_url):
    """Lấy tất cả link stream m3u8 và tên trận từ trang chi tiết"""
    try:
        await page.goto(match_url, wait_until='domcontentloaded', timeout=15000)
        await page.wait_for_timeout(800)
        
        html = await page.content()
        
        # Tìm tên trận
        match_name = ""
        title_match = re.search(r'<title>([^|<]+?)\s*(?:\||</title>)', html)
        if title_match:
            match_name = title_match.group(1).strip()
            match_name = re.sub(r'^Xem trực tiếp\s+', '', match_name)
        
        # Tìm m3u8 links
        m3u8_matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
        script_matches = re.findall(r'"(https?://[^"]+m3u8[^"]*)"', html)
        m3u8_matches.extend(script_matches)
        
        # Loại bỏ duplicates
        seen = set()
        unique_matches = []
        for link in m3u8_matches:
            if link not in seen:
                seen.add(link)
                unique_matches.append(link)
        
        return unique_matches, match_name
    
    except Exception as e:
        return [], ""

async def scrape_matches():
    """Cào danh sách trận đấu và link stream"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("📥 Đang tải trang chính...")
        await page.goto("https://bit.ly/bunchatv", wait_until='domcontentloaded', timeout=20000)
        
        print("⏳ Chờ content load...")
        await page.wait_for_timeout(2000)
        
        html = await page.content()
        
        # Tìm tất cả matches
        pattern = r'class="grid-match__body"[^>]*href="([^"]+)"[^>]*title="([^"]+)"'
        matches = re.findall(pattern, html)
        
        print(f"✓ Tìm được {len(matches)} trận đấu")
        
        if len(matches) == 0:
            alt_pattern = r'href="(/truc-tiep/[^"]+)"'
            alt_matches = re.findall(alt_pattern, html)
            if alt_matches:
                matches = [(m, f"Match {i}") for i, m in enumerate(alt_matches)]
        
        # Loại bỏ duplicates
        seen_urls = set()
        unique_matches = []
        for match_path, match_title in matches:
            if match_path not in seen_urls:
                seen_urls.add(match_path)
                unique_matches.append((match_path, match_title))
        
        matches = unique_matches
        print(f"✓ Sau loại bỏ duplicates: {len(matches)} trận đấu\n")
        
        m3u_content = "#EXTM3U\n"
        success_count = 0
        seen_stream_urls = set()
        match_groups = {}
        
        # Xử lý với delay 500ms
        for idx, (match_path, match_title) in enumerate(matches, 1):
            try:
                current_url = page.url
                base_url = re.match(r'https?://[^/]+', current_url).group(0) if current_url.startswith('http') else "https://bit.ly"
                match_url = f"{base_url}{match_path}"
                
                print(f"[{idx}/{len(matches)}] {match_title[:60]}", end=" ", flush=True)
                
                stream_links, match_name = await get_stream_link(page, match_url)
                
                if stream_links:
                    print(f"✓ {len(stream_links)} link(s) - {match_name[:50]}")
                    
                    tvg_id = re.search(r'/(\d+)$', match_path)
                    tvg_id = tvg_id.group(1) if tvg_id else ""
                    
                    if match_name not in match_groups:
                        match_groups[match_name] = {'tvg_id': tvg_id, 'streams': []}
                    
                    for stream_link in stream_links:
                        if stream_link not in seen_stream_urls:
                            seen_stream_urls.add(stream_link)
                            match_groups[match_name]['streams'].append(stream_link)
                            success_count += 1
                else:
                    print("✗")
                
                # Delay 500ms
                await page.wait_for_timeout(500)
            
            except Exception as e:
                print("✗")
                await page.wait_for_timeout(500)
        
        # Tạo M3U
        for match_name, data in match_groups.items():
            tvg_id = data['tvg_id']
            group_title = match_name.replace(' | ', ' - ').strip()
            
            for idx, stream_link in enumerate(data['streams'], 1):
                display_name = f"{group_title} (Link {idx})" if len(data['streams']) > 1 else group_title
                m3u_content += f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="{group_title}", {display_name}\n'
                m3u_content += f"{stream_link}\n"
        
        # Lưu file
        with open("fbtv_streams.m3u", 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        print(f"\n✓ Hoàn thành!")
        print(f"✓ Lấy được {success_count} stream links")
        print(f"✓ File đã lưu: fbtv_streams.m3u")
        
        await browser.close()

if __name__ == '__main__':
    print("🚀 Bắt đầu cào stream links từ FBTV...\n")
    asyncio.run(scrape_matches())
