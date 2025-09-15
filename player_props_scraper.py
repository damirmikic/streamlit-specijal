import requests
import json
import time
from datetime import datetime, timezone

def get_all_props(league_id):
    """
    Fetches player props by first getting all event IDs for a specific league group,
    then fetching props for each event, and finally filtering for betOfferType ID 127.
    """
    # KORAK 1: Dobavi sve event ID-jeve koristeći 'paf11lv' i specifični URL
    
    # URL za dobijanje liste svih mečeva (događaja) u ligi
    events_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/paf11lv/betoffer/group/{league_id}.json?includeParticipants=false&onlyMain=true&type=2&market=LV&lang=en_GB"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }

    print(f"--- KORAK 1: Preuzimanje Event ID-jeva za ligu {league_id} ---")
    print(f"URL: {events_url}")

    try:
        response = requests.get(events_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Ekstrakcija event ID-jeva iz 'events' liste unutar JSON-a
        # Filtriramo samo mečeve koji još nisu počeli
        now = datetime.now(timezone.utc)
        event_ids = []
        for event in data.get('events', []):
            start_time_str = event.get('start')
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                if start_time > now:
                    event_ids.append(event['id'])

        if not event_ids:
            print(f"[INFO] Nema nadolazećih mečeva za ligu sa ID-jem {league_id}.")
            return []
            
        print(f"Pronađeno {len(event_ids)} nadolazećih mečeva.")

    except requests.exceptions.RequestException as e:
        print(f"[GREŠKA] Nije uspelo preuzimanje event ID-jeva: {e}")
        return []
    except json.JSONDecodeError:
        print(f"[GREŠKA] Nije uspelo dekodiranje JSON odgovora za listu mečeva.")
        return []

    # KORAK 2: Za svaki event ID, preuzmi kvote i filtriraj po betOfferType ID 127
    all_player_props = []
    
    print(f"\n--- KORAK 2: Preuzimanje kvota za svaki od {len(event_ids)} mečeva ---")

    for i, event_id in enumerate(event_ids):
        # URL za pojedinačni meč sa svim kvotama
        props_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/kambi/betoffer/event/{event_id}.json?lang=en_GB&market=GB&includeParticipants=true"
        
        print(f"({i+1}/{len(event_ids)}) Preuzimanje za event ID: {event_id}")

        try:
            event_response = requests.get(props_url, headers=headers, timeout=10)
            if event_response.status_code != 200:
                print(f"[INFO] Preskačem event {event_id}, status kod: {event_response.status_code}")
                continue
                
            event_data = event_response.json()

            # Kreiranje mape timova za trenutni meč radi lakšeg pronalaženja imena
            team_map = {p['id']: p['participantName'] for p in event_data.get('participants', []) if p.get('type') == 'TEAM'}

            # Iteracija kroz sve ponude i filtriranje
            for offer in event_data.get('betOffers', []):
                # KLJUČNI FILTER: Provera da li je ID tipa ponude tačno 127
                if offer.get('betOfferType', {}).get('id') == 127:
                    for outcome in offer.get('outcomes', []):
                        player_name = outcome.get('participant')
                        if not player_name: continue

                        team_id = outcome.get('participantId')
                        prop_data = {
                            'event_name': event_data['event'].get('name', 'N/A'),
                            'closed': event_data['event'].get('start', 'N/A'),
                            'player': player_name,
                            'team': team_map.get(team_id, 'N/A'),
                            'market': offer['criterion']['label'],
                            'line': outcome.get('line', 0) / 1000.0,
                            'selection': outcome.get('label', 'N/A'),
                            'decimal_odds': outcome.get('odds', 0) / 1000.0
                        }
                        all_player_props.append(prop_data)

            # Pauza od pola sekunde da ne preopteretimo server
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"[GREŠKA] Problem pri preuzimanju za event {event_id}: {e}")
        except json.JSONDecodeError:
            print(f"[GREŠKA] Nije uspelo dekodiranje JSON-a za event {event_id}")

    print(f"\n--- PREUZIMANJE ZAVRŠENO: Ukupno pronađeno {len(all_player_props)} ponuda za igrače (tip 127). ---")
    return all_player_props

if __name__ == '__main__':
    # Test sa La Liga ID-jem
    la_liga_id = "1000095049" 
    print("--- Testiranje skripte sa La Liga ---")
    props = get_all_props(la_liga_id)

    if props:
        print(f"\nUspešno preuzeto {len(props)} kvota.")
        # Ispis nekoliko primera radi provere
        for prop in props[:5]:
            print(prop)
    else:
        print("\nNisu pronađene kvote ili je došlo do greške.")
