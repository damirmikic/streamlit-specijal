import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import math 
from player_props_scraper import get_all_props
from lineup_scraper import get_all_lineups
from injury_scraper import get_all_injuries
from calculations import recalculate_related_odds

# --- Konfiguracija i stil ---

st.set_page_config(layout="wide", page_title="Merkur Specijali")

# CSS sa primenjenim izmenama za pristupačnost i vidljivost
st.markdown("""
<style>
    /* Generalni stilovi i preporučena tipografija */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html {
        font-size: 100%;
    }
    body {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        line-height: 1.5;
    }

    /* Tamna tema */
    .stApp {
        background-color: #1a1a2e;
        color: #e0e0e0;
    }

    /* Stilizacija glavnih elemenata sa poboljšanim kontrastom */
    .stButton>button {
        border: 2px solid #8d99ae; /* Poboljšan kontrast */
        background-color: transparent;
        color: #e0e0e0;
        padding: 10px 20px;
        border-radius: 10px;
        transition: all 0.2s ease-in-out;
        font-weight: 600;
        width: 100%; /* Dugmad u sidebar-u da zauzmu punu širinu */
    }
    .stButton>button:hover {
        background-color: #8d99ae; /* Poboljšan kontrast */
        color: #1a1a2e; /* Poboljšan kontrast teksta na hover */
        box-shadow: 0 0 10px #8d99ae;
    }
    
    .stSelectbox, .stTextInput, .stNumberInput {
        border-radius: 10px;
    }
    
    /* Poboljšana navigacija tastaturom */
    :is(button, a, input, select):focus-visible {
        outline: 3px solid #fca311; /* Jasan indikator fokusa */
        outline-offset: 2px;
        border-radius: 5px;
    }

    /* Glassmorphism efekat za kontejnere */
    .glass-container {
        background: rgba(43, 45, 66, 0.6);
        border-radius: 16px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(7.5px);
        -webkit-backdrop-filter: blur(7.5px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 25px;
        margin-bottom: 20px;
    }

    /* Naslovi */
    h1, h2, h3 {
        font-weight: 700;
        color: #ffffff;
    }

    /* Mikro-interakcije */
    .stExpander {
        border-radius: 10px;
        border: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    
    /* --- POBOLJŠANJE VIDLJIVOSTI ELEMENATA --- */
    .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* ISPRAVLJENO: Poboljšanje vidljivosti za st.info (očekivana postava) */
    div[data-testid="stInfo"] {
        background-color: rgba(255, 235, 238, 0.9);
        border: 1px solid #ef9a9a;
        border-radius: 10px;
    }
    div[data-testid="stInfo"] div[data-testid="stMarkdownContainer"] {
         color: #c62828 !important; /* Ciljamo unutrašnji kontejner za tekst */
    }

    div[data-testid="stWarning"] {
        background-color: rgba(255, 243, 224, 0.9);
        border: 1px solid #ffb74d;
        border-radius: 10px;
    }
    div[data-testid="stWarning"] div[data-testid="stMarkdownContainer"] {
         color: #e65100 !important;
    }

    div[data-testid="stError"] {
        background-color: rgba(255, 235, 238, 0.9);
        border: 1px solid #ef9a9a;
        border-radius: 10px;
    }
     div[data-testid="stError"] div[data-testid="stMarkdownContainer"] {
         color: #c62828 !important;
    }

</style>
""", unsafe_allow_html=True)

# --- Funkcije za keširanje ---
@st.cache_data(ttl=14400)
def cached_get_all_lineups():
    return get_all_lineups()

@st.cache_data(ttl=14400)
def cached_get_all_injuries():
    return get_all_injuries()

# --- Definicije i konstante ---
LEAGUES = {
    "Premier League": "1000094985", "La Liga": "1000095049", "Bundesliga": "1000094994",
    "Serie A": "1000095001", "Ligue 1": "1000094991", "Champions League": "1000093381", "Europa League": "2000051195"
}
LEAGUE_TO_INJURY_KEY = {
    "Premier League": "england-premier-league", "La Liga": "spain-la-liga", "Serie A": "italy-serie-a",
    "Bundesliga": "germany-bundesliga", "Ligue 1": "france-ligue-1",
}
MARKET_TRANSLATIONS = {
    "Player's shots on target": "ukupno suteva u okvir gola", "Player's shots": "ukupno suteva",
    "Player's fouls conceded": "ukupno nacinjenih faulova", "To Assist": "asistencija",
    "To Get a Card": "dobija karton", "To Get a Red Card": "dobija crveni karton", "To Score": "daje gol",
    "To Score Or Assist": "gol ili asistencija", "To score from a header": "daje gol glavom",
    "To score from outside the penalty box": "daje gol izvan 16m", "To score at least 2 goals": "daje golova",
    "To score at least 3 goals": "daje golova",
}
MARKET_ORDER = {
    "To Score": 1, "daje gol u 1. poluvremenu": 2, "daje gol u 2. poluvremenu": 3,
    "To score at least 2 goals": 4, "To score at least 3 goals": 5, "To score from a header": 6,
    "To score from outside the penalty box": 7, "Player's shots on target": 8, "Player's shots": 9,
    "To Assist": 10, "To Score Or Assist": 11, "Player's fouls conceded": 12, "To Get a Card": 13,
    "To Get a Red Card": 14,
}

# --- Helper funkcije ---
def get_sort_key(game):
    market_key = game['market'].replace("(Settled using Opta data)", "").strip()
    return MARKET_ORDER.get(market_key, 99) 

def format_line(line_val, market):
    base_market = market.lower().replace("(settled using opta data)", "").strip()
    no_line_markets = {"to assist", "to score or assist", "to score from a header", "to get a card", "to get a red card", "to score"}
    if base_market in no_line_markets or "poluvremenu" in base_market or line_val is None: return ""
    if "score at least" in base_market:
        if line_val == 1.5: return "2+"
        if line_val == 2.5: return "3+"
    if line_val in [0.5, 1.0]: return "1+"
    if line_val in [1.5, 2.0]: return "2+"
    if line_val in [2.5, 3.0]: return "3+"
    if line_val in [3.5, 4.0]: return "4+"
    if line_val == 4.5: return "5+"
    if line_val == 5.5: return "6+"
    if line_val == 6.5: return "7+"
    if line_val == 7.5: return "8+"
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
if 'selected_team' not in st.session_state: st.session_state.selected_team = None
if 'lineups' not in st.session_state: st.session_state.lineups = None
if 'injuries' not in st.session_state: st.session_state.injuries = None

# --- Automatsko preuzimanje i keširanje dodatnih podataka ---
if st.session_state.lineups is None and st.session_state.injuries is None:
    with st.spinner("Preuzimanje i keširanje dodatnih podataka (postave i povrede)..."):
        st.session_state.lineups = cached_get_all_lineups()
        st.session_state.injuries = cached_get_all_injuries()
        st.toast("Podaci o postavama i povredama su keširani.", icon="💾")

# --- SIDEBAR ---
try:
    st.sidebar.image("merkur.png", use_container_width=True)
except FileNotFoundError:
    st.sidebar.warning("Logo fajl 'merkur.png' nije pronađen.")

st.sidebar.title("Merkur Specijali")
st.sidebar.header("1. Preuzimanje Ponude")

selected_league_name = st.sidebar.selectbox("Izaberite Ligu:", options=list(LEAGUES.keys()))
if st.sidebar.button("Prikaži Ponudu Kvote"):
    league_id = LEAGUES[selected_league_name]
    with st.spinner(f"Preuzimanje ponude za {selected_league_name}..."):
        st.session_state.all_props = get_all_props(league_id)
        st.session_state.selected_players = {}
        st.session_state.selected_team = None
        if not st.session_state.all_props:
            st.error("Nije uspelo preuzimanje kvota.")
        else:
            st.success(f"Pronađeno {len(st.session_state.all_props)} ponuda!")

# Ostatak SIDEBAR-a se prikazuje samo ako su podaci preuzeti
if st.session_state.all_props:
    st.sidebar.header("2. Izbor Igrača")
    df = pd.DataFrame(st.session_state.all_props)
    teams = sorted(df['team'].unique())
    
    if not teams:
        st.sidebar.warning("Nema dostupnih timova sa ponudom za igrače u izabranoj ligi.")
    else:
        selected_team = st.sidebar.selectbox("Izaberite Tim:", options=teams, key="team_selector")
        
        if selected_team != st.session_state.selected_team:
            st.session_state.selected_team = selected_team
        
        if selected_team:
            team_df = df[df['team'] == selected_team]
            players = sorted(team_df['player'].unique())
            
            if players:
                selected_player_for_add = st.sidebar.selectbox("Izaberite Igrača za dodavanje:", options=players)
                if st.sidebar.button("➕ Dodaj Igrača", key=f"add_{selected_player_for_add}"):
                    if selected_player_for_add not in st.session_state.selected_players:
                        player_games = team_df[team_df['player'] == selected_player_for_add].to_dict('records')
                        for game in player_games: game['original_odds'] = game['decimal_odds']
                        
                        to_score_game = next((g for g in player_games if g['market'].replace("(Settled using Opta data)", "").strip() == "To Score"), None)
                        if to_score_game:
                            try:
                                p_at_least_one = 1 / to_score_game['decimal_odds']
                                lambda_total = -math.log(1 - p_at_least_one)
                                odds_1st_half = round(1 / (1 - math.exp(-(lambda_total * 0.44))), 2)
                                odds_2nd_half = round(1 / (1 - math.exp(-(lambda_total * 0.56))), 2)
                                game_1st_half = {**to_score_game, 'market': 'daje gol u 1. poluvremenu', 'decimal_odds': odds_1st_half, 'line': None, 'original_odds': odds_1st_half}
                                game_2nd_half = {**to_score_game, 'market': 'daje gol u 2. poluvremenu', 'decimal_odds': odds_2nd_half, 'line': None, 'original_odds': odds_2nd_half}
                                player_games.extend([game_1st_half, game_2nd_half])
                            except (ValueError, ZeroDivisionError): pass 
                        
                        player_games.sort(key=get_sort_key)
                        st.session_state.selected_players[selected_player_for_add] = player_games
                        st.success(f"Igrač {selected_player_for_add} dodat u ponudu.")
            else:
                st.sidebar.warning("Nema dostupnih igrača za izabrani tim.")

# --- GLAVNI DEO APLIKACIJE ---
st.header("Pregled i Kreiranje Ponude")

# Prikaz postava i povreda u glavnom delu
if st.session_state.get('selected_team'):
    selected_team_main = st.session_state.selected_team
    st.subheader(f"Podaci za: {selected_team_main}")
    
    info_cols = st.columns(2)
    with info_cols[0]:
        if st.session_state.lineups:
            lineup = st.session_state.lineups.get(selected_team_main)
            if lineup:
                with st.expander(f"Očekivana postava", expanded=True):
                    st.info(", ".join(lineup))
            else:
                st.warning(f"Nije pronađena očekivana postava.")
    
    with info_cols[1]:
        if st.session_state.injuries and selected_league_name in LEAGUE_TO_INJURY_KEY:
            league_key = LEAGUE_TO_INJURY_KEY.get(selected_league_name)
            if league_key and league_key in st.session_state.injuries:
                team_injuries = [p for p in st.session_state.injuries[league_key] if p['team'] == selected_team_main]
                if team_injuries:
                    with st.expander(f"Povređeni igrači ({len(team_injuries)})", expanded=True):
                        for player in team_injuries:
                            st.error(f"**{player['player_name']}**: {player['info']} (Povratak: {player['expected_return']})")
                else:
                    st.success(f"Nema prijavljenih povreda.")
    st.markdown("---")


# Prikaz i modifikacija kreirane ponude
if st.session_state.selected_players:
    with st.container():
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.header("Kreirana Ponuda")

        for player_name, games in list(st.session_state.selected_players.items()):
            with st.expander(f"Igre za: {player_name}", expanded=True):
                col1, col2 = st.columns(2)
                midpoint = math.ceil(len(games) / 2)
                
                def display_game(game, index, player):
                    market_name_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                    market_name = MARKET_TRANSLATIONS.get(market_name_raw, market_name_raw)
                    line_formatted = format_line(game.get('line'), market_name_raw)
                    game_label = f"Kvota za {market_name} {line_formatted} ({player})"
                    st.write(f"**{market_name} {line_formatted}**")
                    sub_cols = st.columns([5, 2, 2])
                    new_odds = sub_cols[0].number_input(
                        label=game_label, value=game['decimal_odds'], min_value=1.01, step=0.01, 
                        key=f"odds_{player}_{index}", format="%.2f",
                        on_change=recalculate_related_odds, args=(player, index)
                    )
                    st.session_state.selected_players[player][index]['decimal_odds'] = new_odds
                    if sub_cols[1].button("🔄", key=f"revert_{player}_{index}", help="Vrati originalnu kvotu"):
                        original_odds = st.session_state.selected_players[player][index].get('original_odds')
                        if original_odds:
                            st.session_state[f"odds_{player}_{index}"] = original_odds
                            recalculate_related_odds(player, index)
                            st.rerun()
                    if sub_cols[2].button("🗑️", key=f"del_{player}_{index}", help="Ukloni igru"):
                        st.session_state.selected_players[player].pop(index)
                        if not st.session_state.selected_players[player]: del st.session_state.selected_players[player]
                        st.rerun()

                with col1:
                    for i in range(midpoint):
                        display_game(games[i], i, player_name)
                        if i < midpoint - 1: st.markdown("<hr style='margin-top:10px; margin-bottom:10px; border-color: #4a4e69;'>", unsafe_allow_html=True)
                with col2:
                    for i in range(midpoint, len(games)):
                        display_game(games[i], i, player_name)
                        if i < len(games) - 1: st.markdown("<hr style='margin-top:10px; margin-bottom:10px; border-color: #4a4e69;'>", unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("Ručno dodaj igru")
                manual_cols = st.columns([3,2])
                manual_game_name = manual_cols[0].text_input("Naziv igre (npr. 'specijal')", key=f"manual_name_{player_name}")
                manual_odds = manual_cols[1].number_input("Kvota", min_value=1.01, step=0.01, key=f"manual_odds_{player_name}", format="%.2f")
                if st.button("Dodaj ručnu igru", key=f"manual_add_{player_name}"):
                    if manual_game_name:
                        manual_game = {'player': player_name, 'market': manual_game_name, 'line': -1, 'decimal_odds': manual_odds, 'closed': games[0]['closed'] if games else datetime.now().isoformat()}
                        st.session_state.selected_players[player_name].append(manual_game)
                        st.rerun()

        final_cols = st.columns(2)
        if final_cols[0].button("Poništi Unos"):
            st.session_state.selected_players = {}
            st.rerun()
        
        if final_cols[1].button("Generiši CSV Pregled"):
            if st.session_state.selected_team and st.session_state.selected_players:
                match_name = st.session_state.selected_team
                output_rows, header = [], ['Datum', 'Vreme', 'Sifra', 'Domacin', 'Gost', '', '1', 'X', '2', 'GR', 'U', 'O', 'Yes', 'No']
                output_rows.append(header)
                output_rows.append([f'MATCH_NAME:{match_name}', '', '', '', '', '', '', '', '', '', '', '', '', ''])
                for player_name, games in st.session_state.selected_players.items():
                    if not games: continue
                    output_rows.append([f"LEAGUE_NAME:{player_name}", '', '', '', '', '', '', '', '', '', '', '', '', ''])
                    for game in games:
                        datum, vreme = format_datetime_serbian(game['closed'])
                        odds = game['decimal_odds']
                        if game.get('line') == -1: market_name, line_formatted = game['market'], ""
                        else:
                            market_name_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                            market_name = MARKET_TRANSLATIONS.get(market_name_raw, market_name_raw)
                            line_formatted = format_line(game.get('line'), market_name_raw)
                        row = [datum, vreme, '', '', market_name, f"{line_formatted}", odds]
                        output_rows.append(row)
                final_df = pd.DataFrame(output_rows)
                st.dataframe(final_df)
                csv_string = final_df.to_csv(index=False, header=False).encode('utf-8')
                st.download_button(label="Preuzmi CSV Fajl", data=csv_string, file_name=f"{match_name.replace(' ', '_')}_kvote.csv", mime='text/csv')

        st.markdown('</div>', unsafe_allow_html=True)

