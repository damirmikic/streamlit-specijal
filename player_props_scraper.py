import requests
import json
import time
from datetime import datetime, timezone

def get_all_props(league_id):
    """
    Fetches player props by first getting all event IDs for a league,
    and then fetching props for each event individually, filtering by betOfferType ID 127.
    """
    # KORAK 1: Dobavi sve event ID-jeve za izabranu ligu
    events_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/unibet/listView/{league_id}.json?lang=en_GB&market=GB"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }

    print(f"--- KORAK 1: Preuzimanje Event ID-jeva za ligu {league_id} ---")
    print(f"URL: {events_url}")

    try:
        response = requests.get(events_url, headers=headers, timeout=10)
        response.raise_for_status()
        events_data = response.json()
        
        now = datetime.now(timezone.utc)
        future_event_ids = []
        for event in events_data.get('events', []):
            start_time_str = event.get('event', {}).get('start')
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                if start_time > now:
                    future_event_ids.append(event['event']['id'])

        if not future_event_ids:
            print("[INFO] Nema nadolazećih mečeva za ovu ligu.")
            return []
            
        print(f"Pronađeno {len(future_event_ids)} nadolazećih mečeva.")

    except requests.exceptions.RequestException as e:
        print(f"[GREŠKA] Nije uspelo preuzimanje event ID-jeva: {e}")
        return []
    except json.JSONDecodeError:
        print(f"[GREŠKA] Nije uspelo dekodiranje JSON odgovora za event ID-jeve.")
        return []

    # KORAK 2: Iteriraj kroz svaki Event ID i preuzmi kvote
    all_player_props = []
    
    print(f"\n--- KORAK 2: Preuzimanje kvota za svaki od {len(future_event_ids)} mečeva ---")

    for i, event_id in enumerate(future_event_ids):
        props_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/kambi/betoffer/event/{event_id}.json?lang=en_GB&market=GB&includeParticipants=true"
        
        print(f"({i+1}/{len(future_event_ids)}) Preuzimanje za event ID: {event_id}")

        try:
            event_response = requests.get(props_url, headers=headers, timeout=10)
            if event_response.status_code != 200:
                print(f"[INFO] Preskačem event {event_id}, status kod: {event_response.status_code}")
                continue
                
            event_data = event_response.json()

            team_map = {}
            for participant in event_data.get('participants', []):
                if participant.get('type') == 'TEAM':
                    team_map[participant['id']] = participant['participantName']

            for offer in event_data.get('betOffers', []):
                # KLJUČNA PROMENA: Filtriranje po betOfferType ID
                if offer.get('betOfferType', {}).get('id') == 127:
                    for outcome in offer.get('outcomes', []):
                        player_name = outcome.get('participant')
                        if not player_name: continue

                        # ID tima kojem igrač pripada je 'participantId' u ovom kontekstu
                        team_id = outcome.get('participantId')
                        prop_data = {
                            'event_name': event_data['event'].get('name', 'N/A'),
                            'closed': event_data['event'].get('start', 'N/A'),
                            'player': player_name,
                            'team': team_map.get(team_id, 'N/A'), # Pronalazi ime tima
                            'market': offer['criterion']['label'],
                            'line': outcome.get('line', 0) / 1000.0,
                            'selection': outcome.get('label', 'N/A'),
                            'decimal_odds': outcome.get('odds', 0) / 1000.0
                        }
                        all_player_props.append(prop_data)

            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"[GREŠKA] Problem pri preuzimanju za event {event_id}: {e}")
        except json.JSONDecodeError:
            print(f"[GREŠKA] Nije uspelo dekodiranje JSON-a za event {event_id}")

    print(f"\n--- PREUZIMANJE ZAVRŠENO: Ukupno pronađeno {len(all_player_props)} ponuda za igrače. ---")
    return all_player_props

if __name__ == '__main__':
    premier_league_id = "1000094985" 
    print("--- Testiranje skripte sa Premier League ---")
    props = get_all_props(premier_league_id)

    if props:
        print(f"\nUspešno preuzeto {len(props)} kvota.")
        for prop in props[:5]:
            print(prop)
    else:
        print("\nNisu pronađene kvote ili je došlo do greške.")
