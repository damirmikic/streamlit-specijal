import requests
from bs4 import BeautifulSoup

def get_all_injuries():
    """
    Preuzima podatke o povredama sa sportsgambler.com za top 5 evropskih liga.
    """
    urls = {
        "england-premier-league": "https://www.sportsgambler.com/injuries/football/england-premier-league/",
        "spain-la-liga": "https://www.sportsgambler.com/injuries/football/spain-la-liga/",
        "italy-serie-a": "https://www.sportsgambler.com/injuries/football/italy-serie-a/",
        "germany-bundesliga": "https://www.sportsgambler.com/injuries/football/germany-bundesliga/",
        "france-ligue-1": "https://www.sportsgambler.com/injuries/football/france-ligue-1/"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    all_injuries = {}

    for league, url in urls.items():
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            league_injuries = []
            
            # Pronalazi sve naslove timova (h3 tagovi)
            team_headings = soup.find_all('h3')
            
            for team_heading in team_headings:
                team_name = team_heading.get_text(strip=True)
                
                # Filtrira naslove koji nisu timovi
                exclude_words = ['injuries', 'suspensions', 'premier', 'liga', 'bundesliga', 'serie', 'ligue', 'news', 'updates']
                if any(word in team_name.lower() for word in exclude_words):
                    continue

                # Iterira kroz sledeće elemente do sledećeg tima
                for sibling in team_heading.find_next_siblings():
                    if sibling.name == 'h3':
                        break 
                    
                    if sibling.name == 'div' and 'inj-row' in sibling.get('class', []):
                        data_div = sibling.find('div')
                        if data_div:
                            text = data_div.get_text(separator='\n', strip=True)
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            
                            if len(lines) >= 4:
                                player = {
                                    'team': team_name,
                                    'player_name': lines[0] or "N/A",
                                    'position': lines[1] or "N/A",
                                    'info': lines[5] if len(lines) >= 6 else "N/A",
                                    'expected_return': lines[6] if len(lines) >= 7 else "N/A"
                                }
                                
                                if player['player_name'] != "N/A":
                                    league_injuries.append(player)
            
            all_injuries[league] = league_injuries
        
        except requests.exceptions.RequestException as e:
            print(f"Greška pri preuzimanju za {league}: {e}")
            all_injuries[league] = []
            
    return all_injuries

if __name__ == '__main__':
    print("Testiranje skripte za povrede...")
    injuries = get_all_injuries()
    if injuries:
        total_injured_count = sum(len(v) for v in injuries.values())
        print(f"Uspešno preuzeti podaci za {total_injured_count} povređenih igrača.")
        # Primer ispisa za jednu ligu
        if "england-premier-league" in injuries and injuries["england-premier-league"]:
            print("\nPrimer (Premier League):")
            print(injuries["england-premier-league"][0])
