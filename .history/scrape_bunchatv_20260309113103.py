import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# URL trang chính
url = "http://bunchatv1.net/"

# Headers để tránh bị chặn
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

try:
    # Fetch trang web
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = 'utf-8'
    
    if response.status_code != 200:
        print(f"Lỗi: Không thể truy cập trang web (Status: {response.status_code})")
        exit(1)
    
    # Parse HTML
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Tìm tất cả các trận đấu
    matches = soup.find_all('div', class_='grid-matches__item')
    
    if not matches:
        print("Không tìm thấy trận đấu nào")
        exit(1)
    
    # Tạo danh sách M3U
    m3u_content = "#EXTM3U\n"
    
    match_count = 0
    
    for match in matches:
        try:
            # Lấy tên trận đấu (team names)
            team_home = match.find('span', class_='grid-match__team--home-name')
            team_away = match.find('span', class_='grid-match__team--away-name')
            
            if not team_home or not team_away:
                continue
            
            home_name = team_home.get_text(strip=True)
            away_name = team_away.get_text(strip=True)
            
            # Lấy giờ thi đấu
            time_elem = match.find('div', class_='grid-match__datef')
            match_time = time_elem.get_text(strip=True) if time_elem else "TBD"
            
            # Lấy giải đấu
            league_elem = match.find('span', class_='text-ellipsis-max')
            league_name = league_elem.get_text(strip=True) if league_elem else "Unknown"
            
            # Tạo tên channel
            channel_name = f"{home_name} vs {away_name} - {league_name} ({match_time})"
            
            # Lấy link trận đấu
            link_elem = match.find('a', class_='grid-match__body')
            if link_elem and link_elem.get('href'):
                match_link = link_elem['href']
                if not match_link.startswith('http'):
                    match_link = "http://bunchatv1.net" + match_link
                
                # Thêm vào M3U
                m3u_content += f"#EXTINF:-1, {channel_name}\n"
                m3u_content += f"{match_link}\n"
                match_count += 1
                print(f"✓ {channel_name}")
        
        except Exception as e:
            print(f"Lỗi khi xử lý trận đấu: {e}")
            continue
    
    # Lưu file M3U
    output_file = "bunchatv_channels.m3u"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    
    print(f"\n✓ Hoàn thành! Tìm được {match_count} trận đấu")
    print(f"✓ File đã lưu: {output_file}")

except requests.exceptions.RequestException as e:
    print(f"Lỗi kết nối: {e}")
except Exception as e:
    print(f"Lỗi: {e}")
