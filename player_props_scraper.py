import requests
import json

def get_all_props(league_id):
    """
    Fetches player props for a specific league ID and maps players to teams.
    This new logic is more direct and reliable.
    """
    team_url = "https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/1000093190.json?includeParticipants=true&onlyMain=false&type=2&market=PM&lang=en_GB&suppress_response_codes=true"
    props_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/{league_id}.json?includeParticipants=true&onlyMain=false&type=127&market=LV&lang=en_GB&suppress_response_codes=true"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 1. Fetch all teams to create a master team map
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

    # 2. Fetch player props for the selected league
    try:
        props_response = requests.get(props_url, headers=headers)
        props_response.raise_for_status()
        props_data = props_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching props for league {league_id}: {e}")
        return []

    # 3. Process and combine the data
    all_player_props = []
    
    # Get event names from the participants list in the props response
    event_name_map = {p['eventId']: p['event']['name'] for p in props_data.get('participants', []) if 'event' in p}

    for offer in props_data.get('betOffers', []):
        event_id = offer.get('eventId')
        event_name = event_name_map.get(event_id, 'N/A')

        for outcome in offer.get('outcomes', []):
            if 'participantId' not in outcome:
                continue

            # The eventParticipantId directly maps to the team's participantId
            team_id = outcome.get('eventParticipantId')
            team_name = team_map.get(team_id, 'N/A')

            prop_data = {
                'event_name': event_name,
                'closed': offer.get('closed', 'N/A'),
                'player': outcome.get('participant', 'N/A'),
                'team': team_name,
                'market': offer['criterion']['label'],
                'line': outcome.get('line', 0) / 1000.0,
                'selection': outcome.get('label', 'N/A'),
                'decimal_odds': outcome.get('odds', 0) / 1000.0
            }
            all_player_props.append(prop_data)
            
    return all_player_props

if __name__ == '__main__':
    # Example: Fetching Premier League props
    premier_league_id = "1000094985"
    print(f"Fetching props for league ID: {premier_league_id}")
    props = get_all_props(premier_league_id)
    if props:
        print(f"Successfully fetched {len(props)} player props.")
        for p in props[:5]:
            print(json.dumps(p, indent=2))
    else:
        print("No player props found or an error occurred.")

