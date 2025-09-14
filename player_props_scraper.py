import requests
import json
from datetime import datetime, timezone

def get_all_props(league_id):
    """
    Fetches player props for a specific league, ensuring that for each player,
    only props for their single, next upcoming match are included.
    """
    team_url = "https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/1000093190.json?includeParticipants=true&onlyMain=false&type=2&market=PM&lang=en_GB&suppress_response_codes=true"
    props_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/{league_id}.json?includeParticipants=true&onlyMain=false&type=127&market=LV&lang=en_GB&suppress_response_codes=true"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        team_response = requests.get(team_url, headers=headers)
        team_response.raise_for_status()
        team_data = team_response.json()
        
        team_map = {}
        for offer in team_data.get('betOffers', []):
            for outcome in offer.get('outcomes', []):
                if 'participantId' in outcome and 'participant' in outcome:
                    team_map[outcome['participantId']] = outcome['participant']

    except requests.exceptions.RequestException as e:
        print(f"Error fetching team data: {e}")
        return []

    try:
        props_response = requests.get(props_url, headers=headers)
        props_response.raise_for_status()
        props_data = props_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching props for league {league_id}: {e}")
        return []

    # --- NOVA LOGIKA ---
    
    # 1. Kreiraj mapu svih događaja sa vremenom početka
    event_map = {}
    for p in props_data.get('participants', []):
        if 'event' in p and 'id' in p['event'] and 'start' in p['event']:
            event_map[p['event']['id']] = {
                'name': p['event']['name'],
                'start': p['event']['start']
            }

    # 2. Pronađi prvi sledeći meč za svakog igrača
    player_next_event = {}
    now = datetime.now(timezone.utc)

    for offer in props_data.get('betOffers', []):
        event_id = offer.get('eventId')
        event_info = event_map.get(event_id)
        
        if not event_info:
            continue
            
        try:
            start_time = datetime.fromisoformat(event_info['start'].replace('Z', '+00:00'))
            if start_time < now:
                continue # Preskoči mečeve koji su već počeli
        except (ValueError, TypeError):
            continue

        for outcome in offer.get('outcomes', []):
            player_name = outcome.get('participant')
            if not player_name:
                continue

            # Ako igrač nije u listi ili ako je ovaj meč pre onog koji je već sačuvan
            if player_name not in player_next_event or start_time < player_next_event[player_name]['start_time']:
                player_next_event[player_name] = {
                    'eventId': event_id,
                    'start_time': start_time
                }

    # 3. Filtriraj ponudu i sastavi finalnu listu
    all_player_props = []
    for offer in props_data.get('betOffers', []):
        event_id = offer.get('eventId')
        for outcome in offer.get('outcomes', []):
            player_name = outcome.get('participant')
            
            # Proveri da li ovaj offer pripada prvom sledećem meču igrača
            if player_name in player_next_event and player_next_event[player_name]['eventId'] == event_id:
                team_id = outcome.get('eventParticipantId')
                team_name = team_map.get(team_id, 'N/A')
                event_name = event_map.get(event_id, {}).get('name', 'N/A')

                prop_data = {
                    'event_name': event_name,
                    'closed': offer.get('closed', 'N/A'),
                    'player': player_name,
                    'team': team_name,
                    'market': offer['criterion']['label'],
                    'line': outcome.get('line', 0) / 1000.0,
                    'selection': outcome.get('label', 'N/A'),
                    'decimal_odds': outcome.get('odds', 0) / 1000.0
                }
                all_player_props.append(prop_data)
            
    return all_player_props

if __name__ == '__main__':
    premier_league_id = "1000094985"
    print(f"Fetching props for league ID: {premier_league_id}")
    props = get_all_props(premier_league_id)
    if props:
        print(f"Successfully fetched {len(props)} player props.")
        
        # Provera da li jedan igrač ima samo jedan event_name
        player_events = {}
        for p in props:
            if p['player'] not in player_events:
                player_events[p['player']] = set()
            player_events[p['player']].add(p['event_name'])
        
        print("\nVerification: Number of unique events per player:")
        for player, events in list(player_events.items())[:5]:
            print(f"- {player}: {len(events)} event(s)")

    else:
        print("No player props found or an error occurred.")

