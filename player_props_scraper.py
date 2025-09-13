import requests
import json
from collections import defaultdict

def fetch_match_data_maps():
    """
    Fetches match odds data (type=2) to build two reliable maps:
    1. team_map: Maps team IDs to team names.
    2. event_map: Maps event IDs to a formatted event name string (e.g., "Team A vs. Team B").
    """
    team_map = {}
    event_map = {}
    events_by_id = defaultdict(list)
    url = "https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/1000093190.json?includeParticipants=true&onlyMain=false&type=2&market=PM&lang=en_GB&suppress_response_codes=true"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if 'betOffers' in data and isinstance(data['betOffers'], list):
            for offer in data['betOffers']:
                event_id = offer.get('eventId')
                for outcome in offer.get('outcomes', []):
                    team_id = outcome.get('participantId')
                    team_name = outcome.get('participant')
                    if team_id and team_name:
                        team_map[team_id] = team_name
                        if event_id and team_name not in events_by_id[event_id]:
                             events_by_id[event_id].append(team_name)
    
        # Create formatted event name strings
        for event_id, teams in events_by_id.items():
            if len(teams) >= 2:
                event_map[event_id] = f"{teams[0]} vs {teams[1]}"
            else:
                event_map[event_id] = teams[0] if teams else "Unknown Event"

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while building the data maps: {e}")
    except json.JSONDecodeError:
        print("Failed to parse JSON when building the data maps.")
        
    return team_map, event_map

def fetch_and_transform_player_props(team_map, event_map):
    """
    Fetches player prop data, uses pre-built maps for enrichment,
    transforms odds/line values, and returns a structured list.
    """
    url = "https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/1000093190.json?includeParticipants=true&onlyMain=false&type=127&market=PM&lang=en_GB&suppress_response_codes=true"
    transformed_data = []
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'betOffers' in data and isinstance(data['betOffers'], list):
            for offer in data['betOffers']:
                market_label = offer.get('criterion', {}).get('label', 'N/A')
                event_id = offer.get('eventId')
                event_name = event_map.get(event_id, "Unknown Event")

                for outcome in offer.get('outcomes', []):
                    player_name = outcome.get('participant', 'N/A')
                    team_id_key = outcome.get('eventParticipantId')
                    team_name = team_map.get(team_id_key, 'N/A')
                    decimal_odds = outcome.get('odds', 0) / 1000.0
                    transformed_line = outcome.get('line', 0) / 1000.0

                    clean_offer = {
                        "event_name": event_name,
                        "player": player_name,
                        "team": team_name,
                        "market": market_label,
                        "line": transformed_line,
                        "selection": outcome.get('label', 'N/A'),
                        "decimal_odds": round(decimal_odds, 2)
                    }
                    transformed_data.append(clean_offer)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching player data: {e}")
        return None
    except json.JSONDecodeError:
        print("Failed to parse JSON from the player data response.")
        return None
        
    return transformed_data

def get_all_props():
    """Main function to orchestrate the fetching and transformation."""
    team_map, event_map = fetch_match_data_maps()
    if not team_map or not event_map:
        print("Could not build team/event maps. Aborting.")
        return None
    
    player_props = fetch_and_transform_player_props(team_map, event_map)
    return player_props

if __name__ == "__main__":
    all_player_props = get_all_props()
    if all_player_props:
        print("\nSuccessfully fetched and transformed all player props:")
        print(json.dumps(all_player_props, indent=2, ensure_ascii=False))

