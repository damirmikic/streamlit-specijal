import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import math 
import time
from player_props_scraper import get_all_props
from lineup_scraper import get_all_lineups
from injury_scraper import get_all_injuries
from calculations import recalculate_related_odds

# --- Konfiguracija i stil ---
st.set_page_config(layout="wide", page_title="Merkur Specijali")

# CSS (identičan kao pre)
st.markdown("""
<style>
    /* Generalni stilovi i preporučena tipografija */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html { font-size: 100%; }
    body { font-family: 'Inter', sans-serif; font-size: 1rem; line-height: 1.5; }
    .stApp { background-color: #1a1a2e; color: #e0e0e0; }
    .stButton>button { border: 2px solid #8d99ae; background-color: transparent; color: #e0e0e0; padding: 10px 20px; border-radius: 10px; transition: all 0.2s ease-in-out; font-weight: 600; width: 100%; }
    .stButton>button:hover { background-color: #8d99ae; color: #1a1a2e; box-shadow: 0 0 10px #8d99ae; }
    .stSelectbox, .stTextInput, .stNumberInput { border-radius: 10px; }
    :is(button, a, input, select):focus-visible { outline: 3px solid #fca311; outline-offset: 2px; border-radius: 5px; }
    .glass-container { background: rgba(43, 45, 66, 0.6); border-radius: 16px; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1); backdrop-filter: blur(7.5px); -webkit-backdrop-filter: blur(7.5px); border: 1px solid rgba(255, 255, 255, 0.2); padding: 25px; margin-bottom: 20px; }
    h1, h2, h3 { font-weight: 700; color: #ffffff; }
    .stExpander { border-radius: 10px; border: none; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
    .stSelectbox label, .stTextInput label, .stNumberInput label { color: #ffffff !important; font-weight: 600 !important; }
    div[data-testid="stInfo"] { background-color: rgba(255, 235, 238, 0.9); border: 1px solid #ef9a9a; border-radius: 10px; }
    div[data-testid="stInfo"] div[data-testid="stMarkdownContainer"] { color: #c62828 !important; }
    div[data-testid="stWarning"] { background-color: rgba(255, 243, 224, 0.9); border: 1px solid #ffb74d; border-radius: 10px; }
    div[data-testid="stWarning"] div[data-testid="stMarkdownContainer"] { color: #e65100 !important; }
    div[data-testid="stError"] { background-color: rgba(255, 235, 238, 0.9); border: 1px solid #ef9a9a; border-radius: 10px; }
    div[data-testid="stError"] div[data-testid="stMarkdownContainer"] { color: #c62828 !important; }
</style>
""", unsafe_allow_html=True)

# --- Definicije i konstante (iste kao pre) ---
LEAGUES = { "Premier League": "1000094985", "La Liga": "1000095049", "Bundesliga": "1000094994", "Serie A": "1000095001", "Ligue 1": "1000094991", "Champions League": "1000093381", "Europa League": "2000051195" }
LEAGUE_TO_INJURY_KEY = { "Premier League": "england-premier-league", "La Liga": "spain-la-liga", "Serie A": "italy-serie-a", "Bundesliga": "germany-bundesliga", "Ligue 1": "france-ligue-1" }
MARKET_TRANSLATIONS = { "Player's shots on target": "ukupno suteva u okvir gola", "Player's shots": "ukupno suteva", "Player's fouls conceded": "ukupno nacinjenih faulova", "To Assist": "asistencija", "To Get a Card": "dobija karton", "To Get a Red Card": "dobija crveni karton", "To Score": "daje gol", "To Score Or Assist": "gol ili asistencija", "To score from a header": "daje gol glavom", "To score from outside the penalty box": "daje gol izvan 16m", "To score at least 2 goals": "daje golova", "To score at least 3 goals": "daje golova" }
MARKET_ORDER = { "To Score": 1, "daje gol u 1. poluvremenu": 2, "daje gol u 2. poluvremenu": 3, "To score at least 2 goals": 4, "To score at least 3 goals": 5, "To score from a header": 6, "To score from outside the penalty box": 7, "Player's shots on target": 8, "Player's shots": 9, "To Assist": 10, "To Score Or Assist": 11, "Player's fouls conceded": 12, "To Get a Card": 13, "To Get a Red Card": 14 }

# --- Helper funkcije (iste kao pre) ---
def get_sort_key(game):
    market_key = game['market'].replace("(Settled using Opta data)", "").strip()
    return MARKET_ORDER.get(market_key, 99)

def format_line(line_val, market):
    base_market = market.lower().replace("(settled using opta data)", "").strip()
    no_line_markets = {"to assist", "to score or assist", "to score from a header", "to get a card", "to get a red card", "to score"}
    if base_market in no_line_markets or "poluvremenu" in base_market or line_val is None or line_val == 0.0: return ""
    if "score at least" in base_market:
        if line_val == 1.5: return "2+"
        if line_val == 2.5: return "3+"
    if line_val in [0.5, 1.0]: return "1+"
    if line_val in [1.5, 2.0]: return "2+"
    if line_val in [2.5, 3.0]: return "3+"
    return f"{line_val}"

def format_datetime_serbian(utc_str):
    try:
        utc_dt = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
        cet = pytz.timezone('Europe/Belgrade')
        local_dt = utc_dt.astimezone(cet)
        return local_dt.strftime('%d.%m.%Y'), local_dt.strftime('%H:%M')
    except (ValueError, TypeError):
        return 'N/A', 'N/A'

# --- Inicijalizacija Session State ---
if 'all_props' not in st.session_state: st.session_state.all_props = None
if 'selected_players' not in st.session_state: st.session_state.selected_players = {}
if 'selected_event' not in st.session_state: st.session_state.selected_event = None
if 'selected_team' not in st.session_state: st.session_state.selected_team = None

# --- Keširanje podataka o povredama i postavama ---
@st.cache_data(ttl=14400)
def load_external_data():
    lineups = get_all_lineups()
    injuries = get_all_injuries()
    return lineups, injuries

lineups, injuries = load_external_data()

# --- SIDEBAR ---
st.sidebar.image("merkur.png", use_container_width=True)
st.sidebar.title("Merkur Specijali")
st.sidebar.header("1. Preuzimanje Ponude")

selected_league_name = st.sidebar.selectbox("Izaberite Ligu:", options=list(LEAGUES.keys()))

if st.sidebar.button("Prikaži Mečeve"):
    league_id = LEAGUES[selected_league_name]
    
    # Koristimo st.status da prikažemo ceo proces preuzimanja
    with st.status(f"Preuzimanje za {selected_league_name}...", expanded=True) as status:
        # Svi print() pozivi iz get_all_props će biti prikazani unutar ovog bloka
        st.session_state.all_props = get_all_props(league_id)
        
        # Resetovanje izbora
        st.session_state.selected_event = None
        st.session_state.selected_team = None
        st.session_state.selected_players = {}
        
        if not st.session_state.all_props:
            status.update(label="Greška prilikom preuzimanja!", state="error", expanded=True)
        else:
            status.update(label=f"Pronađeno {len(st.session_state.all_props)} ponuda! Preuzimanje uspešno!", state="complete", expanded=False)
            time.sleep(2) # Pauza da korisnik vidi poruku
            st.rerun() # Rerun da bi se popunili padajući meniji

# --- NOVI MENI ZA IZBOR ---
if st.session_state.all_props:
    st.sidebar.header("2. Izbor Igrača")
    df = pd.DataFrame(st.session_state.all_props)

    # 1. Izbor meča
    event_names = sorted(df['event_name'].unique())
    selected_event = st.sidebar.selectbox("Izaberite Meč:", options=event_names, index=None, placeholder="Izaberite meč...")
    st.session_state.selected_event = selected_event

    # 2. Izbor tima
    if selected_event:
        event_df = df[df['event_name'] == selected_event]
        teams_in_event = sorted([team for team in event_df['team'].unique() if team and team != 'Tim N/A'])
        selected_team = st.sidebar.selectbox("Izaberite Tim:", options=teams_in_event, index=None, placeholder="Izaberite tim...")
        st.session_state.selected_team = selected_team

        # 3. Izbor igrača
        if selected_team:
            team_df = event_df[event_df['team'] == selected_team]
            players = sorted(team_df['player'].unique())
            
            if players:
                selected_player_for_add = st.sidebar.selectbox("Izaberite Igrača za dodavanje:", options=players)
                if st.sidebar.button("➕ Dodaj Igrača"):
                    if selected_player_for_add not in st.session_state.selected_players:
                        player_games = team_df[team_df['player'] == selected_player_for_add].to_dict('records')
                        for game in player_games: game['original_odds'] = game['decimal_odds']
                        
                        to_score_game = next((g for g in player_games if g['market'].strip() == "To Score"), None)
                        if to_score_game:
                            try:
                                p_at_least_one = 1 / to_score_game['decimal_odds']
                                lambda_total = -math.log(1 - p_at_least_one)
                                odds_1h = round(1 / (1 - math.exp(-(lambda_total * 0.44))), 2)
                                odds_2h = round(1 / (1 - math.exp(-(lambda_total * 0.56))), 2)
                                game_1h = {**to_score_game, 'market': 'daje gol u 1. poluvremenu', 'decimal_odds': odds_1h, 'line': 0.0, 'original_odds': odds_1h}
                                game_2h = {**to_score_game, 'market': 'daje gol u 2. poluvremenu', 'decimal_odds': odds_2h, 'line': 0.0, 'original_odds': odds_2h}
                                player_games.extend([game_1h, game_2h])
                            except (ValueError, ZeroDivisionError): pass 
                        
                        player_games.sort(key=get_sort_key)
                        st.session_state.selected_players[selected_player_for_add] = player_games
                        st.success(f"Igrač {selected_player_for_add} dodat u ponudu.")
                    else:
                        st.warning(f"Igrač {selected_player_for_add} je već u ponudi.")

# --- GLAVNI DEO APLIKACIJE ---
st.header("Merkur Specijal App")
tab1, tab2 = st.tabs(["Kreiranje Ponude", "Svi Podaci (Raw Data)"])

with tab1:
    if st.session_state.selected_team:
        st.subheader(f"Podaci za: {st.session_state.selected_team}")
        info_cols = st.columns(2)
        with info_cols[0]:
            lineup = lineups.get(st.session_state.selected_team)
            if lineup: st.info(f"**Očekivana postava:** {', '.join(lineup)}")
            else: st.warning("Nije pronađena očekivana postava.")
        with info_cols[1]:
            injury_league_key = LEAGUE_TO_INJURY_KEY.get(selected_league_name)
            if injury_league_key and injury_league_key in injuries:
                team_injuries = [p for p in injuries[injury_league_key] if p['team'] == st.session_state.selected_team]
                if team_injuries:
                    st.error(f"**Povređeni igrači ({len(team_injuries)}):**")
                    for p in team_injuries: st.error(f"- {p['player_name']}: {p['info']}")
                else: st.success("Nema prijavljenih povreda.")
        st.markdown("---")

    if st.session_state.selected_players:
        with st.container(border=False):
            st.markdown('<div class="glass-container">', unsafe_allow_html=True)
            st.header("Kreirana Ponuda")
            for player_name, games in list(st.session_state.selected_players.items()):
                 with st.expander(f"Igre za: {player_name}", expanded=True):
                    for i, game in enumerate(games):
                        market_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                        market_name = MARKET_TRANSLATIONS.get(market_raw, market_raw)
                        line_formatted = format_line(game.get('line'), market_raw)
                        
                        cols = st.columns([4, 2, 1, 1])
                        cols[0].write(f"**{market_name} {line_formatted}**")
                        
                        new_odds = cols[1].number_input(
                            label="Kvota", value=game['decimal_odds'], min_value=1.01, step=0.01,
                            key=f"odds_{player_name}_{i}", label_visibility="collapsed",
                            on_change=recalculate_related_odds, args=(player_name, i)
                        )
                        st.session_state.selected_players[player_name][i]['decimal_odds'] = new_odds

                        if cols[2].button("🔄", key=f"revert_{player_name}_{i}", help="Vrati originalnu kvotu"):
                            st.session_state[f"odds_{player_name}_{i}"] = game.get('original_odds', 1.01)
                            st.rerun()
                        if cols[3].button("🗑️", key=f"del_{player_name}_{i}", help="Ukloni igru"):
                            st.session_state.selected_players[player_name].pop(i)
                            if not st.session_state.selected_players[player_name]: del st.session_state.selected_players[player_name]
                            st.rerun()
            st.markdown("---")
            final_cols = st.columns(2)
            if final_cols[0].button("🗑️ Poništi Ceo Unos"):
                st.session_state.selected_players = {}
                st.rerun()
            if final_cols[1].button("📄 Generiši CSV Pregled"):
                output_rows = [['Datum', 'Vreme', 'Sifra', 'Domacin', 'Gost', '', '1', 'X', '2', 'GR', 'U', 'O', 'Yes', 'No']]
                for player, games in st.session_state.selected_players.items():
                    if not games: continue
                    event_name_for_csv = games[0]['event_name']
                    output_rows.append([f"LEAGUE_NAME:{event_name_for_csv}"])
                    output_rows.append([f"MATCH_NAME:{player}"])
                    for game in games:
                        datum, vreme = format_datetime_serbian(game['closed'])
                        market_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                        market_name = MARKET_TRANSLATIONS.get(market_raw, market_raw)
                        line_formatted = format_line(game.get('line'), market_raw)
                        row = [datum, vreme, '', '', market_name, f"{line_formatted}", game['decimal_odds']]
                        output_rows.append(row)
                final_df = pd.DataFrame(output_rows)
                st.session_state.final_df_for_download = final_df
            if 'final_df_for_download' in st.session_state:
                st.dataframe(st.session_state.final_df_for_download)
                csv_string = st.session_state.final_df_for_download.to_csv(index=False, header=False).encode('utf-8')
                st.download_button(label="📥 Preuzmi CSV Fajl", data=csv_string, file_name="merkur_specijal_ponuda.csv", mime='text/csv')
            st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state.all_props is not None:
        st.info("Izaberite meč, tim i igrača iz menija sa leve strane da biste počeli sa kreiranjem ponude.")
    else:
        st.info("Kliknite na 'Prikaži Mečeve' da biste učitali ponudu.")

with tab2:
    st.header("Pregled Svih Preuzetih Kvota (Raw Data)")
    if st.session_state.all_props:
        st.info(f"Prikazano je {len(st.session_state.all_props)} preuzetih ponuda.")
        raw_df = pd.DataFrame(st.session_state.all_props)
        st.dataframe(raw_df, use_container_width=True)
    else:
        st.warning("Nema preuzetih podataka. Molimo Vas da prvo izaberete ligu i kliknete na 'Prikaži Mečeve' u meniju sa leve strane.")

