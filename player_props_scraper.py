import requests
import json
import time
from datetime import datetime, timezone

# Hardkodovani URL-ovi za svaku ligu da bi se osigurala stabilnost
# Ključ je ID lige koji se koristi u streamlit_app.py
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

def get_all_props(league_id):
    """
    Glavna funkcija koja objedinjuje dva koraka:
    1. Preuzima detalje svih nadolazećih mečeva za datu ligu.
    2. Za svaki meč, preuzima i filtrira kvote za igrače (betOfferType ID 127).
    """
    print(f"--- Započeto preuzimanje ponude za ligu ID: {league_id} ---")

    # --- KORAK 1: Preuzimanje detalja o mečevima ---
    
    events_url = LEAGUE_URL_MAP.get(str(league_id))
    if not events_url:
        print(f"[GREŠKA] Nije pronađen URL za ligu sa ID-jem: {league_id}")
        return []

    print(f"Korak 1: Preuzimanje liste mečeva sa {events_url}")
    
    try:
        response = requests.get(events_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        now = datetime.now(timezone.utc)
        events_to_process = []
        
        for event_wrapper in data.get('events', []):
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

        if not events_to_process:
            print("[INFO] Nema nadolazećih mečeva za izabranu ligu.")
            return []
        
        print(f"Pronađeno {len(events_to_process)} nadolazećih mečeva za obradu.")

    except requests.exceptions.RequestException as e:
        print(f"[GREŠKA] Nije moguće preuzeti listu mečeva: {e}")
        return []

    # --- KORAK 2: Preuzimanje kvota za svaki meč ---
    
    all_player_props = []
    print(f"\nKorak 2: Preuzimanje kvota za igrače za svaki meč...")

    for i, event_info in enumerate(events_to_process):
        event_id = event_info.get("event_id")
        team_map = event_info.get("team_map", {})
        
        if not event_id or not team_map:
            print(f"  Preskačem meč {event_info.get('event_name')} jer nema mapu timova.")
            continue

        props_url = f"https://eu-offering-api.kambicdn.com/offering/v2018/kambi/betoffer/event/{event_id}.json?lang=en_GB&market=GB&includeParticipants=true"
        print(f"  ({i+1}/{len(events_to_process)}) Obrada meča: {event_info.get('event_name')}")
        
        try:
            response = requests.get(props_url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"    [UPOZORENJE] Dobijen status kod {response.status_code}. Preskačem.")
                continue
            
            event_data = response.json()
            
            for offer in event_data.get('betOffers', []):
                if offer.get('betOfferType', {}).get('id') == 127:
                    for outcome in offer.get('outcomes', []):
                        player_name = outcome.get('participant')
                        if not player_name: continue
                        
                        event_participant_id = str(outcome.get('eventParticipantId'))
                        team_name = team_map.get(event_participant_id, 'Tim N/A')

                        prop_data = {
                            'event_name': event_info.get('event_name', 'N/A'),
                            'closed': event_info.get('kickoff_time', 'N/A'),
                            'player': player_name,
                            'team': team_name,
                            'market': offer['criterion']['label'],
                            'line': outcome.get('line', 0) / 1000.0,
                            'selection': outcome.get('label'),
                            'decimal_odds': outcome.get('odds', 0) / 1000.0
                        }
                        all_player_props.append(prop_data)
            
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"    [GREŠKA] Problem sa konekcijom za meč {event_id}: {e}")
            continue
    
    print(f"\n--- PREUZIMANJE ZAVRŠENO ---")
    print(f"Ukupno pronađeno {len(all_player_props)} kvota za igrače.")
    return all_player_props

if __name__ == '__main__':
    test_league_id = "1000094985"
    print(f"--- Pokretanje testa za ligu {test_league_id} ---")
    props = get_all_props(test_league_id)
    if props:
        print("\n--- Primer pronađenih podataka (prvih 5) ---")
        for p in props[:5]:
            print(p)
    else:
        print("\nTest nije pronašao nijednu kvotu.")

