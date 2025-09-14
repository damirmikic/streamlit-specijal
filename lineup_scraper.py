import requests
from bs4 import BeautifulSoup
import re

def get_all_lineups():
    """
    Scrapes the Sports Mole football preview page to find links to individual
    match previews, then visits each link to extract the predicted starting lineups.

    Returns:
        dict: A dictionary where keys are team names and values are lists of player names.
              e.g., {'Liverpool': ['Alisson', 'Szoboszlai', ...]}
    """
    base_url = "https://www.sportsmole.co.uk"
    preview_url = f"{base_url}/football/preview/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    lineups = {}

    try:
        # 1. Get all preview links from the main page
        main_page_response = requests.get(preview_url, headers=headers)
        main_page_response.raise_for_status()
        soup = BeautifulSoup(main_page_response.content, 'lxml')
        
        preview_links = []
        # Find all <a> tags that link to a preview article
        for a_tag in soup.select('a[href*="/preview/"]'):
            href = a_tag.get('href')
            if href and href.endswith('.html'):
                preview_links.append(f"{base_url}{href}")

        # Remove duplicate links
        preview_links = list(set(preview_links))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching main preview page: {e}")
        return None

    # 2. Visit each link and scrape the lineups
    for link in preview_links:
        try:
            article_response = requests.get(link, headers=headers)
            if article_response.status_code != 200:
                continue
            
            article_soup = BeautifulSoup(article_response.content, 'lxml')
            
            # Find all <strong> tags which usually precede the lineup list
            strong_tags = article_soup.select('#article_body strong')
            
            for tag in strong_tags:
                tag_text = tag.get_text(strip=True)
                # Check if the text matches the pattern for a possible lineup
                if tag_text.endswith("possible starting lineup:"):
                    team_name = tag_text.replace(" possible starting lineup:", "").strip()
                    
                    # UPDATED LOGIC: Find the next <p> tag that contains actual text, skipping any empty ones.
                    lineup_p = tag.find_next('p', text=re.compile(r'\S'))

                    if lineup_p:
                        lineup_text = lineup_p.get_text(strip=True)
                        # Clean up the lineup string and split into a list of players
                        # It can be separated by ";" or ",". We'll handle both.
                        players = re.split(r'[;,]\s*', lineup_text)
                        # Further clean up each player name
                        cleaned_players = [p.strip() for p in players if p.strip()]
                        lineups[team_name] = cleaned_players
                        
        except requests.exceptions.RequestException:
            # Silently continue if a single article fails
            continue
            
    return lineups

if __name__ == '__main__':
    print("Fetching predicted lineups from Sports Mole...")
    all_lineups = get_all_lineups()
    if all_lineups:
        print(f"Successfully scraped lineups for {len(all_lineups)} teams.")
        # Print a few examples
        for i, (team, players) in enumerate(all_lineups.items()):
            if i >= 3: break
            print(f"\n{team}:")
            print(", ".join(players))
    else:
        print("Failed to scrape lineups.")

