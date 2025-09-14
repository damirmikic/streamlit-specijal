import requests
from bs4 import BeautifulSoup
import re

# Rečnik za mapiranje različitih naziva timova
TEAM_NAME_MAP = {
    "Man City": "Manchester City",
    "Man Utd": "Manchester United",
    "Spurs": "Tottenham Hotspur",
    "Borussia M'bach": "Borussia Monchengladbach",
    "Athletic Bilbao": "Athletic Club",
    # Dodajte još mapiranja po potrebi
}

def get_all_lineups():
    """
    Scrapes the Sports Mole football preview page to find links to individual
    match previews, then visits each link to extract the predicted starting lineups.
    """
    base_url = "https://www.sportsmole.co.uk"
    preview_url = f"{base_url}/football/preview/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    lineups = {}

    try:
        main_page_response = requests.get(preview_url, headers=headers)
        main_page_response.raise_for_status()
        soup = BeautifulSoup(main_page_response.content, 'lxml')
        
        preview_links = []
        for a_tag in soup.select('a[href*="/preview/"]'):
            href = a_tag.get('href')
            if href and href.endswith('.html'):
                preview_links.append(f"{base_url}{href}")

        preview_links = list(set(preview_links))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching main preview page: {e}")
        return None

    for link in preview_links:
        try:
            article_response = requests.get(link, headers=headers)
            if article_response.status_code != 200:
                continue
            
            article_soup = BeautifulSoup(article_response.content, 'lxml')
            strong_tags = article_soup.select('#article_body strong')
            
            for tag in strong_tags:
                tag_text = tag.get_text(strip=True)
                if tag_text.endswith("possible starting lineup:"):
                    team_name_raw = tag_text.replace(" possible starting lineup:", "").strip()
                    # Primena mapiranja
                    team_name = TEAM_NAME_MAP.get(team_name_raw, team_name_raw)
                    
                    lineup_p = tag.find_next('p', text=re.compile(r'\S'))

                    if lineup_p:
                        lineup_text = lineup_p.get_text(strip=True)
                        players = re.split(r'[;,]\s*', lineup_text)
                        cleaned_players = [p.strip() for p in players if p.strip()]
                        lineups[team_name] = cleaned_players
                        
        except requests.exceptions.RequestException:
            continue
            
    return lineups

if __name__ == '__main__':
    print("Fetching predicted lineups from Sports Mole...")
    all_lineups = get_all_lineups()
    if all_lineups:
        print(f"Successfully scraped lineups for {len(all_lineups)} teams.")
        for i, (team, players) in enumerate(all_lineups.items()):
            if i >= 5: break
            print(f"\n{team}: {', '.join(players)}")
    else:
        print("Failed to scrape lineups.")

