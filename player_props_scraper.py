import requests
import json
import time
from datetime import datetime, timezone

# Hardkodovani URL-ovi za svaku ligu
LEAGUE_URL_MAP = {
    "1000094985": "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/england/premier_league/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "1000095049": "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/spain/la_liga/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "1000095001": "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/italy/serie_a/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "1000094994": "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/germany/bundesliga/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "1000094991": "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/france/ligue_1/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "1000093381": "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/europe/champions_league/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "2000051195": "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/europe/europa_league/all/matches.json?lang=en_GB&market=GB&useCombined=true",
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}

def get_events_for_league(league_id):
    """
    Korak 1: Preuzima listu mečeva sa detaljnim ispisom procesa.
    """
    events_url = LEAGUE_URL_MAP.get(str(league_id))
    if not events_url:
        print(f"[GREŠKA] Nije pronađen URL za ligu: {league_id}")
        return []

    print(f"1. Preuzimanje liste mečeva sa: {events_url}")
    try:
        response = requests.get(events_url, headers=HEADERS, timeout=15)
        print(f"2. Statusni kod odgovora: {response.status_code}")
        print(f"3. Početak odgovora (prvih 200 karaktera): {response.text[:200]}")
        
        response.raise_for_status()
        data = response.json()
        print("4. JSON uspešno dekodiran.")
        
        now = datetime.now(timezone.utc)
        events_to_process = []
        
        events_list_from_json = data.get('events', [])
        print(f"5. Pronađeno {len(events_list_from_json)} događaja u JSON-u.")

        for event_wrapper in events_list_from_json:
            event = event_wrapper.get('event', {})
            if not event: continue
            
            start_time_str = event.get('start')
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                if start_time > now:
                    team_map = {}
                    bet_offers = event_wrapper.get('betOffers', [])
                    if bet_offers and bet_offers[0].get('outcomes'):
                        for outcome in bet_offers[0]['outcomes']:
                            if 'participantId' in outcome and 'participant' in outcome:
                                team_map[str(outcome['participantId'])] = outcome['participant']
                    
                    if team_map:
                        event_details = {
                            "event_id": event.get('id'),
                            "event_name": event.get('name'),
                            "kickoff_time": event.get('start'),
                            "team_map": team_map
                        }
                        events_to_process.append(event_details)

        print(f"6. Pronađeno {len(events_to_process)} nadolazećih mečeva za obradu.")
        return events_to_process

    except requests.exceptions.HTTPError as e:
        print(f"[GREŠKA - HTTP] Server je vratio grešku: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[GREŠKA - Konekcija] Nije uspelo preuzimanje liste mečeva: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"[GREŠKA - JSON] Nije moguće dekodirati odgovor sa servera: {e}")
        return []

def get_props_for_event(event_id, team_map):
    """
    Korak 2: Preuzima sve kvote za jedan specifičan meč i filtrira one za igrače.
    """
    if not event_id or not team_map:
        return []

    props_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/kambi/betoffer/event/{event_id}.json?lang=en_GB&market=GB&includeParticipants=true"
    print(f"Preuzimanje kvota za meč ID: {event_id}")
    
    player_props = []
    try:
        response = requests.get(props_url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return []
        
        event_data = response.json()
        
        for offer in event_data.get('betOffers', []):
            if offer.get('betOfferType', {}).get('id') == 127:
                for outcome in offer.get('outcomes', []):
                    player_name = outcome.get('participant')
                    if not player_name: continue
                    
                    event_participant_id = str(outcome.get('eventParticipantId'))
                    team_name = team_map.get(event_participant_id, 'Tim N/A')

                    prop_data = {
                        'player': player_name,
                        'team': team_name,
                        'market': offer['criterion']['label'],
                        'line': outcome.get('line', 0) / 1000.0,
                        'selection': outcome.get('label'),
                        'decimal_odds': outcome.get('odds', 0) / 1000.0
                    }
                    player_props.append(prop_data)
    
    except requests.exceptions.RequestException as e:
        print(f"    [GREŠKA] Problem sa konekcijom za meč {event_id}: {e}")

    print(f"Pronađeno {len(player_props)} kvota za igrače za meč {event_id}.")
    return player_props

