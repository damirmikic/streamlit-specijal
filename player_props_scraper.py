import requests
import json

def get_all_props():
    """
    Fetches all events from a general football group URL, then iterates through
    each event's specific API to find and process player prop bets.
    """
    # REVERTED: Going back to the group ID that is proven to work.
    group_url = "https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/1000093190.json?includeParticipants=true&onlyMain=false&type=2&market=PM&lang=en_GB&suppress_response_codes=true"
    
    try:
        response = requests.get(group_url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching group data: {e}")
        return []

    event_ids = list(set([offer['eventId'] for offer in data.get('betOffers', [])]))
    all_player_props = []

    for event_id in event_ids:
        event_url = f"https://eu1.offering-api.kambicdn.com/offering/v2018/kambi/betoffer/event/{event_id}.json?lang=en_GB&market=GB&client_id=2&channel_id=7&ncid=1757795583713&includeParticipants=true"
        
        try:
            event_response = requests.get(event_url)
            if event_response.status_code != 200:
                continue
            event_data = event_response.json()
        except requests.exceptions.RequestException:
            continue

        player_prop_offers = [
            offer for offer in event_data.get('betOffers', [])
            if offer.get('betOfferType', {}).get('id') == 127
        ]

        if not player_prop_offers:
            continue

        event_name = event_data.get('event', {}).get('name', 'N/A')
        participants = event_data.get('participants', [])

        team_map = {p['id']: p['name'] for p in participants if p['type'] == 'TEAM'}
        player_to_team_map = {p['id']: p['teamId'] for p in participants if p['type'] == 'PARTICIPANT'}

        for offer in player_prop_offers:
            for outcome in offer.get('outcomes', []):
                if 'participantId' not in outcome:
                    continue

                player_id = outcome['participantId']
                team_id = player_to_team_map.get(player_id)
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
    print("Fetching player props with new logic...")
    props = get_all_props()
    if props:
        print(f"Successfully fetched {len(props)} player props.")
        for p in props[:5]:
            print(json.dumps(p, indent=2))
    else:
        print("No player props found or an error occurred.")

