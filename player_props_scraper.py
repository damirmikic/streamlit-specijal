import requests
import json
import time
from datetime import datetime, timezone

# Rečnik koji mapira ID lige na Kambi URL putanju
LEAGUE_URL_MAP = {
    "1000094985": "football/england/premier_league", # Premier League
    "1000095049": "football/spain/la_liga",          # La Liga
    "1000094994": "football/germany/bundesliga",     # Bundesliga
    "1000095001": "football/italy/serie_a",          # Serie A
    "1000094991": "football/france/ligue_1",         # Ligue 1
    "1000093381": "football/europe/champions_league",# Champions League
    "2000051195": "football/europe/europa_league",   # Europa League
}

def get_all_props(league_id):
    """
    Finalna verzija koja objedinjuje oba koraka:
    1. Preuzima sve ID-jeve mečeva za datu ligu.
    2. Za svaki ID meča, preuzima kvote i filtrira samo one za igrače (tip 127).
    """
    league_path = LEAGUE_URL_MAP.get(str(league_id))
    if not league_path:
        print(f"[GREŠKA] Nije pronađen URL za ligu sa ID-jem: {league_id}")
        return []

    # --- KORAK 1: Preuzimanje ID-jeva svih budućih mečeva ---
    events_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/{league_path}/all/matches.json?lang=en_GB&market=GB&useCombined=true"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }

    print(f"--- KORAK 1: Preuzimanje liste mečeva za {league_path} ---")
    print(f"URL: {events_url}")

    try:
        response = requests.get(events_url, headers=headers, timeout=15)
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
            print(f"[INFO] Nema nadolazećih mečeva za ligu: {league_path}")
            return []
            
        print(f"Pronađeno {len(future_event_ids)} nadolazećih mečeva.")

    except requests.exceptions.RequestException as e:
        print(f"[GREŠKA] Nije uspelo preuzimanje liste mečeva: {e}")
        return []

    # --- KORAK 2: Preuzimanje i filtriranje kvota za svaki meč ---
    all_player_props = []
    print(f"\n--- KORAK 2: Preuzimanje kvota za {len(future_event_ids)} mečeva ---")

    for i, event_id in enumerate(future_event_ids):
        props_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/kambi/betoffer/event/{event_id}.json?lang=en_GB&market=GB&includeParticipants=true"
        
        print(f"({i+1}/{len(future_event_ids)}) Preuzimanje za event ID: {event_id}")

        try:
            event_response = requests.get(props_url, headers=headers, timeout=10)
            if event_response.status_code != 200:
                print(f"[INFO] Preskačem event {event_id}, status kod: {event_response.status_code}")
                continue
                
            event_data = event_response.json()
            
            # ISPRAVKA: Bezbedan pristup detaljima meča
            event_list = event_data.get('events', [])
            if not event_list:
                print(f"  [UPOZORENJE] Nedostaju detalji o meču ('events' lista) za ID {event_id}. Preskačem.")
                continue
            event_details = event_list[0]

            team_map = {p['id']: p['participantName'] for p in event_data.get('participants', []) if p.get('type') == 'TEAM'}

            for offer in event_data.get('betOffers', []):
                if offer.get('betOfferType', {}).get('id') == 127:
                    for outcome in offer.get('outcomes', []):
                        player_name = outcome.get('participant')
                        if not player_name: continue
                        
                        team_id = outcome.get('participantId')
                        prop_data = {
                            'event_name': event_details.get('name', 'N/A'),
                            'closed': event_details.get('start', 'N/A'),
                            'player': player_name,
                            'team': team_map.get(team_id, 'N/A'),
                            'market': offer['criterion']['label'],
                            'line': outcome.get('line', 0) / 1000.0,
                            'selection': outcome.get('label', 'N/A'),
                            'decimal_odds': outcome.get('odds', 0) / 1000.0
                        }
                        all_player_props.append(prop_data)
            
            time.sleep(0.5) # Pauza da ne opteretimo server

        except requests.exceptions.RequestException as e:
            print(f"[GREŠKA] Problem pri preuzimanju za event {event_id}: {e}")
        except json.JSONDecodeError:
            print(f"[GREŠKA] Nije uspelo dekodiranje JSON-a za event {event_id}")

    print(f"\n--- PREUZIMANJE ZAVRŠENO: Ukupno pronađeno {len(all_player_props)} ponuda za igrače. ---")
    return all_player_props

if __name__ == '__main__':
    # Test sa Premier League ID-jem
    premier_league_id = "1000094985"
    print("--- Testiranje kompletne skripte sa Premier League ---")
    props = get_all_props(premier_league_id)

    if props:
        print(f"\nUspešno preuzeto {len(props)} kvota.")
        print("Primer prvih 5 preuzetih kvota:")
        for prop in props[:5]:
            print(prop)
    else:
        print("\nNisu pronađene kvote ili je došlo do greške.")
