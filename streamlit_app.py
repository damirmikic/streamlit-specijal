import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from io import StringIO
import csv
from bs4 import BeautifulSoup
import re

# -----------------------------
# Konstante
# -----------------------------
LEAGUE_URLS = {
    "Premier League": "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/england/premier_league/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "La Liga":        "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/spain/la_liga/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "Serie A":        "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/italy/serie_a/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "Bundesliga":     "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/germany/bundesliga/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "Ligue 1":        "https://eu-offering-api.kambicdn.com/offering/v2018/kambi/listView/football/france/ligue_1/all/matches.json?lang=en_GB&market=GB&useCombined=true",
    "Champions League": "https://eu1.offering-api.kambicdn.com/offering/v2018/kambi/listView/football/champions_league/all/all/matches.json?category=12579&channel_id=7&channel_id=7&client_id=2&client_id=2&competitionId=undefined&lang=en_GB&lang=en_GB&market=GB&market=GB&useCombined=true&useCombinedLive=true",
    "Europa League": "https://eu1.offering-api.kambicdn.com/offering/v2018/kambi/listView/football/europa_league/all/all/matches.json?category=12579&channel_id=7&channel_id=7&client_id=2&client_id=2&competitionId=undefined&lang=en_GB&lang=en_GB&market=GB&market=GB&useCombined=true&useCombinedLive=true"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,sr;q=0.8",
    "Referer": "https://retail.kambicdn.com/bring-your-own-device/latest/"  # Primer, stavite sajt sa kog ste preuzeli link
}

TEAM_NAME_MAP = {
    "Man City": "Manchester City", "Man Utd": "Manchester United", "Spurs": "Tottenham Hotspur",
    "Borussia M'bach": "Borussia Monchengladbach", "Athletic Bilbao": "Athletic Club",
    "Nottingham": "Nottingham Forest", "West Ham": "West Ham United", "Wolves": "Wolverhampton Wanderers",
    "Inter": "Inter Milan", "Real Sociedad": "Real Sociedad", "Atletico Madrid": "Atletico Madrid",
    "Paris Saint Germain": "Paris Saint-Germain",
}

MARKET_SORT_ORDER = [
    "daje gol", "daje 2+ golova", "daje gol glavom", "daje gol izvan 16m",
    "gol ili asistencija", "asistencija", "ukupno šuteva", "ukupno šuteva u okvir gola",
    "ukupno načinjenih faulova", "dobija karton", "dobija crveni karton"
]

# -----------------------------
# Konfiguracija stranice
# -----------------------------
st.set_page_config(
    page_title="Player Props – Kvote, Sastavi i Povrede",
    page_icon="🎯",
    layout="wide",
)
st.title("🎯 Player Props – Kvote, Sastavi i Povrede")

# -----------------------------
# Helper funkcije
# -----------------------------
def get_sort_key(market_srp: str):
    """Pruža primarni ključ za sortiranje za dati naziv igre."""
    if market_srp.startswith("daje") and "golova" in market_srp:
        try:
            return MARKET_SORT_ORDER.index("daje 2+ golova")
        except ValueError:
            return len(MARKET_SORT_ORDER)
    try:
        return MARKET_SORT_ORDER.index(market_srp)
    except ValueError:
        return len(MARKET_SORT_ORDER)

def get_advanced_sort_key(row: dict):
    """Pruža tuple za napredno sortiranje (po tipu igre, pa po vrednosti)."""
    primary_key = get_sort_key(row['market'])
    secondary_key = 0 
    selection = row.get('selection', '')
    if isinstance(selection, str) and selection.endswith('+'):
        try:
            secondary_key = int(selection[:-1])
        except (ValueError, IndexError):
            secondary_key = 0
    return (primary_key, secondary_key)

def translate_market(m: str) -> str:
    if not m: return m
    ml = m.lower()
    if "goal or assist" in ml: return "gol ili asistencija"
    if "assist" in ml and "goal or assist" not in ml: return "asistencija"
    if "header" in ml: return "daje gol glavom"
    if "outside the box" in ml or "outside the penalty box" in ml: return "daje gol izvan 16m"
    if "red card" in ml: return "dobija crveni karton"
    if "card" in ml and "red" not in ml: return "dobija karton"
    if "shots on target" in ml: return "ukupno šuteva u okvir gola"
    if "total shots" in ml or ("shots" in ml and "on target" not in ml): return "ukupno šuteva"
    if "fouls" in ml: return "ukupno načinjenih faulova"
    if "to score at least" in ml or "or more goals" in ml:
        n = re.findall(r"\d+", m)
        return f"daje {n[0]}+ golova" if n else "daje 2+ golova"
    if "anytime goalscorer" in ml or ("to score" in ml): return "daje gol"
    return m

def is_over_line_market(m: str) -> bool:
    if not m: return False
    ml = m.lower()
    return ("shots" in ml or "shots on target" in ml or "fouls" in ml or "total shots" in ml)

def clean_market_label(label: str) -> str:
    return label.replace("(Settled using Opta data)", "").strip() if label else ""

def is_opta_market(offer: dict) -> bool:
    """Proverava da li je igra bazirana na Opta podacima, ali dozvoljava one koje želimo."""
    crit = (offer.get("criterion") or {}).get("label", "") or ""
    crit_lower = crit.lower()
    
    # Dozvoli ove igre čak i ako imaju "Opta" u nazivu
    allowed_opta_markets = ["shots", "fouls", "assist"]
    if any(keyword in crit_lower for keyword in allowed_opta_markets):
        return False
        
    tags = offer.get("tags", []) or []
    tags_l = " ".join([str(t) for t in tags]).lower() if isinstance(tags, list) else str(tags).lower()
    return "opta" in crit_lower or "opta" in tags_l

def odds_decimal(outcome: dict) -> float:
    return (outcome.get("odds", 0) or 0) / 1000.0

def over_line_to_plus(x: float) -> str:
    try:
        return f"{int(float(x) + 0.5)}+"
    except Exception:
        return ""

def selection_label_for_market(outcome: dict, market_eng: str) -> str:
    label = (outcome.get("label") or "").strip()
    if label.lower() == "yes": return "DA"
    line = (outcome.get("line", 0) or 0) / 1000.0
    if is_over_line_market(market_eng):
        return over_line_to_plus(line) if label.lower().startswith("over") or label.lower() == "yes" else ""
    if label: return label
    return over_line_to_plus(line) if line and line > 0 else ""

def format_dt_local(iso_ts: str):
    dt_utc = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    dt_plus_2 = dt_utc + timedelta(hours=2)
    return dt_plus_2.strftime("%d.%m.%Y"), dt_plus_2.strftime("%H:%M")

def normalize_team_name(name: str):
    name = TEAM_NAME_MAP.get(name, name)
    replacements = {"Saint-Etienne": "St Etienne"}
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name

# -----------------------------
# Scraperi (Lineups & Injuries)
# -----------------------------
@st.cache_data(ttl=3600)
def get_all_lineups():
    base_url = "https://www.sportsmole.co.uk"
    preview_url = f"{base_url}/football/preview/"
    lineups = {}
    try:
        main_page_response = requests.get(preview_url, headers=HEADERS, timeout=15)
        main_page_response.raise_for_status()
        soup = BeautifulSoup(main_page_response.content, 'lxml')
        preview_links = list(set(f"{base_url}{a.get('href')}" for a in soup.select('a[href*="/preview/"]') if a.get('href','').endswith('.html')))
    except requests.exceptions.RequestException:
        return {}
    for link in preview_links:
        try:
            article_response = requests.get(link, headers=HEADERS, timeout=10)
            if article_response.status_code != 200: continue
            article_soup = BeautifulSoup(article_response.content, 'lxml')
            for tag in article_soup.select('#article_body strong'):
                tag_text = tag.get_text(strip=True)
                if tag_text.endswith("possible starting lineup:"):
                    team_name = normalize_team_name(tag_text.replace(" possible starting lineup:", "").strip())
                    lineup_p = tag.find_next('p', text=re.compile(r'\S'))
                    if lineup_p:
                        players = re.split(r'[;,]\s*', lineup_p.get_text(strip=True))
                        lineups[team_name] = [p.strip() for p in players if p.strip()]
        except requests.exceptions.RequestException:
            continue
    return lineups

@st.cache_data(ttl=3600)
def get_all_injuries():
    urls = {
        "premier-league": "https://www.sportsgambler.com/injuries/football/england-premier-league/",
        "la-liga": "https://www.sportsgambler.com/injuries/football/spain-la-liga/",
        "serie-a": "https://www.sportsgambler.com/injuries/football/italy-serie-a/",
        "bundesliga": "https://www.sportsgambler.com/injuries/football/germany-bundesliga/",
        "ligue-1": "https://www.sportsgambler.com/injuries/football/france-ligue-1/"
    }
    all_injuries = {}
    for url in urls.values():
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            for h3 in soup.find_all('h3'):
                team_name_raw = h3.get_text(strip=True)
                exclude = ['injuries', 'suspensions', 'premier', 'liga', 'bundesliga', 'serie', 'ligue', 'news', 'updates']
                if any(word in team_name_raw.lower() for word in exclude): continue
                team_name = normalize_team_name(team_name_raw)
                players = []
                for sibling in h3.find_next_siblings():
                    if sibling.name == 'h3': break
                    if sibling.name == 'div' and 'inj-row' in sibling.get('class', []):
                        lines = [line.strip() for line in sibling.get_text(separator='\n', strip=True).split('\n') if line.strip()]
                        if len(lines) >= 4 and lines[0] != "N/A":
                            players.append({'player_name': lines[0], 'info': lines[5] if len(lines) >= 6 else "N/A", 'expected_return': lines[6] if len(lines) >= 7 else "N/A"})
                if players: all_injuries[team_name] = players
        except requests.exceptions.RequestException:
            continue
    return all_injuries

# -----------------------------
# API funkcije
# -----------------------------
@st.cache_data(ttl=300)
def fetch_league_events(league_name: str):
    r = requests.get(LEAGUE_URLS[league_name], headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()
    now = datetime.now(timezone.utc)
    events = []
    for w in data.get("events", []):
        event = w.get("event", {})
        start = event.get("start")
        if not start or datetime.fromisoformat(start.replace("Z", "+00:00")) <= now: continue
        team_map = {str(o["participantId"]): o["participant"] for o in (w.get("betOffers") or [{}])[0].get("outcomes", []) if "participantId" in o and "participant" in o}
        events.append({"event_id": event.get("id"), "event_name": event.get("name"), "kickoff_time": start, "team_map": team_map})
    events.sort(key=lambda e: e["kickoff_time"])
    return events

@st.cache_data(ttl=300)
def fetch_event_betoffers(event_id: int):
    url = f"https://eu-offering-api.kambicdn.com/offering/v2018/kambi/betoffer/event/{event_id}.json?lang=en_GB&market=GB&includeParticipants=true"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def build_players_maps(betoffers: dict, team_map: dict):
    players_by_team = {team: set() for team in team_map.values()}
    inv_team_map = {str(k): v for k, v in team_map.items()}
    player_to_team = {}
    for offer in betoffers.get("betOffers", []):
        for outc in offer.get("outcomes", []):
            p_name, ev_pid = outc.get("participant"), str(outc.get("eventParticipantId"))
            if not p_name or ev_pid not in inv_team_map: continue
            team_name = inv_team_map[ev_pid]
            players_by_team.setdefault(team_name, set()).add(p_name)
            player_to_team.setdefault(p_name, team_name)
    return {t: sorted(list(v)) for t, v in players_by_team.items()}, player_to_team

def filter_rows_for_player(betoffers, team_map, team_name, player_name):
    rows = []
    seen_markets = set()
    team_ep_ids = {pid for pid, tname in team_map.items() if tname == team_name}
    for offer in betoffers.get("betOffers", []):
        if (offer.get("betOfferType", {}) or {}).get("id") != 127 or is_opta_market(offer): continue
        raw_label = (offer.get("criterion") or {}).get("label") or (offer.get("betOfferType") or {}).get("name", "N/A")
        market_eng = clean_market_label(raw_label)
        market_srp = translate_market(market_eng)
        for outc in offer.get("outcomes", []):
            if outc.get("participant") != player_name or str(outc.get("eventParticipantId")) not in team_ep_ids: continue
            
            decimal_odds = odds_decimal(outc)
            if not (1.1 <= decimal_odds <= 50.0):
                continue

            sel = selection_label_for_market(outc, market_eng)
            if is_over_line_market(market_eng) and not sel: continue

            market_key = (market_srp, sel)
            if market_key in seen_markets:
                continue
            seen_markets.add(market_key)

            rows.append({"market": market_srp, "selection": sel, "decimal_odds": decimal_odds})
    
    rows.sort(key=get_advanced_sort_key)
    return rows

def build_combined_csv(kickoff_iso, event_name, player_rows_map):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Datum", "Vreme", "Sifra", "Domacin", "Gost", "", "1", "X", "2", "GR", "U", "O", "Yes", "No"])
    writer.writerow([f"MATCH_NAME:{event_name}"])
    datum, vreme = format_dt_local(kickoff_iso)
    for (team_name, player_name, rows_list) in player_rows_map:
        writer.writerow([f"LEAGUE_NAME:{player_name}"])
        for item in rows_list:
            writer.writerow([datum, vreme, "", item.get("market", ""), item.get("selection", ""), item.get("decimal_odds", ""), "", "", "", "", "", "", "", ""])
    return output.getvalue()

# -----------------------------
# UI (sidebar)
# -----------------------------
with st.sidebar:
    league = st.selectbox("Liga", list(LEAGUE_URLS.keys()))
    events = fetch_league_events(league)
    event_name_to_obj = {e["event_name"]: e for e in events}
    event_name = st.selectbox("Meč", list(event_name_to_obj.keys()) or ["Nema dostupnih mečeva"])
    selected_event = event_name_to_obj.get(event_name)

    if selected_event:
        betoffers = fetch_event_betoffers(selected_event["event_id"])
        players_by_team, player_to_team = build_players_maps(betoffers, selected_event.get("team_map", {}))
        sel_team = st.selectbox("Tim", sorted(players_by_team.keys()))
        team_players = players_by_team.get(sel_team, [])
        
        if "selected_players" not in st.session_state:
            st.session_state.selected_players = []
        
        player_to_add = st.selectbox("Igrač", team_players)
        if st.button("➕ Dodaj igrača na listu"):
            if player_to_add and player_to_add not in st.session_state.selected_players:
                st.session_state.selected_players.append(player_to_add)
                st.rerun()
        
        st.write("---")
        st.write("📋 **Izabrani igrači za CSV:**")
        
        for player in st.session_state.selected_players:
            col1, col2 = st.columns([0.8, 0.2])
            with col1: st.write(f"- {player}")
            with col2:
                if st.button("✖️", key=f"remove_{player}"):
                    st.session_state.selected_players.remove(player)
                    st.rerun()
        
        if st.session_state.selected_players and st.button("🗑️ Očisti sve igrače"):
            st.session_state.selected_players = []
            st.rerun()

if st.sidebar.button("🔄 Očisti Cache i Osveži Podatke"):
    st.cache_data.clear()
    st.rerun()

# -----------------------------
# Glavni prikaz
# -----------------------------
if selected_event:
    st.subheader("📰 Vesti o Timovima")
    all_lineups = get_all_lineups()
    all_injuries = get_all_injuries()
    
    team_names = list(selected_event.get("team_map", {}).values())
    if len(team_names) == 2:
        cols = st.columns(2)
        for i, team_name in enumerate(team_names):
            with cols[i]:
                st.markdown(f"#### {team_name}")
                norm_name = normalize_team_name(team_name)
                with st.expander("⭐ **Verovatan sastav**"):
                    lineup = all_lineups.get(norm_name)
                    if lineup:
                        st.text("\n".join(f"- {p}" for p in lineup))
                    else:
                        st.warning("Nema informacija.")
                with st.expander("⚕️ **Povrede i suspenzije**"):
                    injuries = all_injuries.get(norm_name)
                    if injuries:
                        for p in injuries:
                            st.text(f"- {p['player_name']} ({p.get('info', 'N/A')})")
                            st.caption(f"  Povratak: {p.get('expected_return', 'Nepoznato')}")
                    else:
                        st.info("Nema prijavljenih povreda.")

    if st.session_state.get("selected_players"):
        preview_rows = []
        for p in st.session_state.selected_players:
            team_guess = player_to_team.get(p)
            if not team_guess: continue
            rows = filter_rows_for_player(betoffers, selected_event.get("team_map", {}), team_guess, p)
            for r in rows:
                preview_rows.append({"Tim": team_guess, "Igrač": p, "Market (SR)": r["market"], "Selekcija": r["selection"], "Kvota": r["decimal_odds"]})
        
        st.subheader("📊 Pregled i izmena kvota")
        if not preview_rows:
            st.info("Nema kvota za prikaz za izabrane igrače (proverite filtere).")
        else:
            preview_df = pd.DataFrame(preview_rows)
            edited_df = st.data_editor(
                preview_df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="odds_editor"
            )

            if not edited_df.empty:
                edited_player_rows_map = []
                for (team, player), group in edited_df.groupby(["Tim", "Igrač"]):
                    rows_list = []
                    for _, row in group.iterrows():
                        rows_list.append({
                            "market": row["Market (SR)"],
                            "selection": row["Selekcija"],
                            "decimal_odds": row["Kvota"]
                        })
                    edited_player_rows_map.append((team, player, rows_list))
                
                csv_text = build_combined_csv(selected_event["kickoff_time"], selected_event["event_name"], edited_player_rows_map)
                file_name = f"{selected_event['event_name'].replace(' ', '_').replace('/', '-')}_igraci.csv"
                st.download_button("⬇️ Preuzmi CSV", data=csv_text.encode("utf-8-sig"), file_name=file_name, mime="text/csv")
            else:
                st.warning("Sve igre su uklonjene. Nema podataka za generisanje CSV fajla.")
else:
    st.info("Izaberite ligu i meč iz menija sa leve strane.")
