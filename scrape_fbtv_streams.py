import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime, timedelta


async def parse_match_data(page, match_url):
    """Vào trang chi tiết trận, parse JSON data để lấy stream + metadata"""
    try:
        await page.goto(match_url, wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(2000)
        
        html = await page.content()
        
        # Lấy streamUrl chính (dừng trước \ hoặc ")
        stream_url_match = re.search(r'"streamUrl"\s*:\s*"(https?://[^"\\]+\.m3u8)', html)
        stream_url = stream_url_match.group(1) if stream_url_match else None
        
        # Lấy tên đội nhà
        home_match = re.search(r'"homeTeam"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', html)
        home_team = home_match.group(1).strip() if home_match else ""
        
        # Lấy tên đội khách
        away_match = re.search(r'"awayTeam"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', html)
        away_team = away_match.group(1).strip() if away_match else ""
        
        # Lấy tên giải đấu
        league_match = re.search(r'"league"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', html)
        league = league_match.group(1).strip() if league_match else "Thể thao"
        
        # Lấy BLV chính (commentator đầu tiên)
        blv_match = re.search(r'"commentators"\s*:\s*\[\s*\{[^}]*"name"\s*:\s*"([^"]+)"', html)
        blv_name = blv_match.group(1).strip() if blv_match else ""
        
        # Lấy thời gian
        time_match = re.search(r'"startTime"\s*:\s*"[^"]*(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})', html)
        start_time = ""
        if time_match:
            date_str = time_match.group(1)
            time_str = time_match.group(2)
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                dt_vn = dt + timedelta(hours=7)
                start_time = dt_vn.strftime("%H:%M %d/%m")
            except:
                start_time = f"{time_str} {date_str}"
        
        # Fallback: tìm m3u8 trong HTML nếu không có streamUrl
        if not stream_url:
            m3u8s = re.findall(r'(https?://[^\s"\'<>\\]+\.m3u8)', html)
            if m3u8s:
                stream_url = m3u8s[0]
        
        # Clean URL
        if stream_url:
            stream_url = stream_url.rstrip('\\').rstrip('/').strip()
        
        match_name = f"{home_team} vs {away_team}" if home_team and away_team else ""
        
        return {
            'stream_url': stream_url,
            'home_team': home_team,
            'away_team': away_team,
            'match_name': match_name,
            'league': league,
            'blv': blv_name,
            'start_time': start_time,
        }
    
    except Exception as e:
        print(f"    Error: {e}")
        return None


async def resolve_target_url(page):
    """Resolve URL đích từ quechoatv2.net/redirect"""
    print("📥 Đang vào quechoatv2.net/redirect...")
    await page.goto("https://quechoatv2.net/redirect", wait_until='domcontentloaded', timeout=20000)
    
    print("⏳ Chờ redirect...")
    redirected = False
    for i in range(10):
        await page.wait_for_timeout(1000)
        if "quechoatv2.net" not in page.url:
            print(f"  ✓ Redirect sau {i+1}s")
            redirected = True
            break
    
    if not redirected:
        try:
            btn = page.locator('a:has-text("TRUY CẬP"), a:has-text("Truy cập")')
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_timeout(3000)
                if "quechoatv2.net" not in page.url:
                    redirected = True
        except:
            pass
    
    if not redirected:
        html = await page.content()
        target = re.search(r'https?://(quechoa\d+\.live)', html)
        if target:
            return f"https://{target.group(1)}"
        return None
    
    base = re.match(r'(https?://[^/]+)', page.url)
    base_url = base.group(1) if base else page.url.rstrip('/')
    print(f"  ✓ Trang đích: {base_url}")
    return base_url


async def scrape_matches():
    """Cào danh sách trận đấu và link stream từ QuechoaTV"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Bước 1: Resolve URL đích
        base_url = await resolve_target_url(page)
        if not base_url:
            print("❌ Không thể resolve URL đích.")
            await browser.close()
            return
        
        # Bước 2: Lấy danh sách link trận từ trang chính
        print(f"\n📥 Đang tải trang chính: {base_url}")
        await page.goto(base_url, wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        match_links = re.findall(r'href="(/truc-tiep/[^"]+)"', html)
        
        # Dedup
        seen = set()
        unique_paths = []
        for p_path in match_links:
            if p_path not in seen:
                seen.add(p_path)
                unique_paths.append(p_path)
        
        print(f"✓ Tìm được {len(unique_paths)} trận đấu\n")
        
        if not unique_paths:
            print("⚠️ Không tìm được trận nào!")
            await browser.close()
            return
        
        # Bước 3: Vào từng trận, parse JSON data
        m3u_content = "#EXTM3U\n"
        success_count = 0
        
        for idx, match_path in enumerate(unique_paths, 1):
            match_url = f"{base_url}{match_path}"
            slug = match_path.replace('/truc-tiep/', '')
            print(f"[{idx}/{len(unique_paths)}] {slug[:55]}", end=" ", flush=True)
            
            data = await parse_match_data(page, match_url)
            
            if data and data['stream_url']:
                match_name = data['match_name']
                if not match_name:
                    # Fallback: parse từ slug, loại bỏ code+date
                    name_match = re.match(r'(.+?)-[a-z]{2,4}-\d{2}-\d{2}-\d{4}$', slug)
                    if name_match:
                        match_name = name_match.group(1).replace('-', ' ').title()
                    else:
                        match_name = slug.replace('-', ' ').title()
                
                league = data['league']
                blv = data['blv']
                start_time = data['start_time']
                stream_url = data['stream_url']
                
                # Lấy tvg-id từ URL
                code_match = re.search(r'-([a-z]{2,4})-\d{2}-\d{2}-\d{4}$', match_path)
                tvg_id = code_match.group(1) if code_match else str(idx)
                
                # Format display name
                display_name = match_name
                if start_time:
                    display_name = f"{match_name} ({start_time})"
                if blv:
                    display_name += f" [{blv}]"
                
                m3u_content += f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="{league}", {display_name}\n'
                m3u_content += f"{stream_url}\n"
                success_count += 1
                
                print(f"✓ {league} | {blv or '-'} | {stream_url.split('/')[-1]}")
            else:
                print("✗")
            
            await page.wait_for_timeout(500)
        
        # Lưu file
        with open("fbtv_streams.m3u", 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        print(f"\n✅ Hoàn thành!")
        print(f"✅ {success_count}/{len(unique_paths)} trận có stream")
        print(f"✅ File đã lưu: fbtv_streams.m3u")
        
        await browser.close()


if __name__ == '__main__':
    print("🚀 Bắt đầu cào stream links từ QuechoaTV...\n")
    asyncio.run(scrape_matches())
