import requests
import json

def get_all_props():
    """
    Fetches all events from a group URL, then iterates through each event's specific
    API endpoint to find and process player prop bets (betOfferType ID 127).
    """
    group_url = "https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/1000093190.json?includeParticipants=true&onlyMain=false&type=2&market=PM&lang=en_GB&suppress_response_codes=true"
    
    try:
        response = requests.get(group_url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching group data: {e}")
        return []

    # Extract unique event IDs from the initial group fetch
    event_ids = list(set([offer['eventId'] for offer in data.get('betOffers', [])]))

    all_player_props = []

    # Iterate over each event ID to fetch detailed event data
    for event_id in event_ids:
        # Construct the specific event URL
        event_url = f"https://eu1.offering-api.kambicdn.com/offering/v2018/kambi/betoffer/event/{event_id}.json?lang=en_GB&market=GB&client_id=2&channel_id=7&ncid=1757795583713&includeParticipants=true"
        
        try:
            event_response = requests.get(event_url)
            # Skip if event not found or other error
            if event_response.status_code != 200:
                continue
            event_data = event_response.json()
        except requests.exceptions.RequestException:
            # Skip this event if there's a connection issue
            continue

        # Filter for bet offers that are player props (ID 127)
        player_prop_offers = [
            offer for offer in event_data.get('betOffers', [])
            if offer.get('betOfferType', {}).get('id') == 127
        ]

        # If no player props are found in this event, move to the next one
        if not player_prop_offers:
            continue

        # --- If we are here, the event has player props, so we process it ---
        
        event_name = event_data.get('event', {}).get('name', 'N/A')
        participants = event_data.get('participants', [])

        # Build maps to link players to teams
        team_map = {p['id']: p['name'] for p in participants if p['type'] == 'TEAM'}
        player_to_team_map = {p['id']: p['teamId'] for p in participants if p['type'] == 'PARTICIPANT'}

        # Process each player prop offer found in the event
        for offer in player_prop_offers:
            for outcome in offer.get('outcomes', []):
                # Ensure the outcome is for a specific participant (player)
                if 'participantId' not in outcome:
                    continue

                player_id = outcome['participantId']
                team_id = player_to_team_map.get(player_id)
                team_name = team_map.get(team_id, 'N/A')

                # Create the dictionary for this specific player prop
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

# Main block for standalone testing
if __name__ == '__main__':
    # This will only run when the script is executed directly
    print("Fetching player props with new logic...")
    props = get_all_props()
    if props:
        print(f"Successfully fetched {len(props)} player props.")
        # Print the first 5 for verification
        for p in props[:5]:
            print(json.dumps(p, indent=2))
    else:
        print("No player props found or an error occurred.")

