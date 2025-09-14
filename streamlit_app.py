import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from player_props_scraper import get_all_props

# --- Konfiguracija i stil ---

st.set_page_config(layout="wide", page_title="Player Props App")

# CSS za moderni izgled, tamnu temu i stakleni efekat
st.markdown("""
<style>
    /* Generalni stilovi */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    body {
        font-family: 'Inter', sans-serif;
    }

    /* Tamna tema */
    .stApp {
        background-color: #1a1a2e;
        color: #e0e0e0;
    }

    /* Stilizacija glavnih elemenata */
    .stButton>button {
        border: 2px solid #4a4e69;
        background-color: transparent;
        color: #e0e0e0;
        padding: 10px 20px;
        border-radius: 10px;
        transition: all 0.2s ease-in-out;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #4a4e69;
        color: #ffffff;
        box-shadow: 0 0 10px #4a4e69;
    }
    
    .stSelectbox, .stTextInput, .stNumberInput {
        border-radius: 10px;
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
</style>
""", unsafe_allow_html=True)

# --- Definicije i konstante ---

LEAGUES = {
    "Premier League": "1000094985",
    "La Liga": "1000095049",
    "Bundesliga": "1000094994",
    "Serie A": "1000095001",
    "Ligue 1": "1000094991",
    "Champions League": "1000093381",
    "Europa League": "2000051195"
}

MARKET_TRANSLATIONS = {
    "Player's shots on target": "ukupno suteva u okvir gola",
    "Player's shots": "ukupno suteva",
    "Player's fouls conceded": "ukupno nacinjenih faulova",
    "To Assist": "asistencija",
    "To Get a Card": "dobija karton",
    "To Get a Red Card": "dobija crveni karton",
    "To Score": "daje gol",
    "To Score Or Assist": "gol ili asistencija",
    "To score from a header": "daje gol glavom",
    "To score from outside the penalty box": "daje gol izvan 16m",
}

def format_line(line_val, market):
    base_market = market.lower()
    if "card" in base_market:
        return "" # Kartoni nemaju "+"
    if line_val in [0.5, 1.0]:
        return "1+"
    if line_val in [1.5, 2.0]:
        return "2+"
    if line_val in [2.5, 3.0]:
        return "3+"
    if line_val in [3.5, 4.0]:
        return "4+"
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
if 'all_props' not in st.session_state:
    st.session_state.all_props = None
if 'selected_players' not in st.session_state:
    st.session_state.selected_players = {}
if 'manual_games' not in st.session_state:
    st.session_state.manual_games = {}
if 'selected_team' not in st.session_state:
    st.session_state.selected_team = None

# --- UI Aplikacije ---
st.title("Player Props CSV Generator")

# 1. KORAK: Izbor lige i preuzimanje podataka
with st.container():
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    st.header("1. Preuzimanje Ponude")
    
    selected_league_name = st.selectbox("Izaberite Ligu:", options=list(LEAGUES.keys()))
    
    if st.button("Prikaži Ponudu"):
        league_id = LEAGUES[selected_league_name]
        with st.spinner(f"Preuzimanje ponude za {selected_league_name}..."):
            st.session_state.all_props = get_all_props(league_id)
            # Resetovanje svega ostalog pri novom preuzimanju
            st.session_state.selected_players = {}
            st.session_state.manual_games = {}
            st.session_state.selected_team = None
            if not st.session_state.all_props:
                st.error("Nije uspelo preuzimanje podataka za izabranu ligu.")
            else:
                st.success(f"Pronađeno {len(st.session_state.all_props)} ponuda!")

    st.markdown('</div>', unsafe_allow_html=True)

# Ostatak UI se prikazuje samo ako su podaci preuzeti
if st.session_state.all_props:
    df = pd.DataFrame(st.session_state.all_props)
    
    # NEW: Filter out props where event_name is 'N/A'
    df = df[df['event_name'] != 'N/A']

    # 2. KORAK: Filtriranje i dodavanje igrača
    with st.container():
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.header("2. Izbor Igrača")

        # Filtriranje po događaju
        events = sorted(df['event_name'].unique())
        if not events:
            st.warning("Nema dostupnih događaja sa ponudom za igrače u izabranoj ligi.")
        else:
            selected_event = st.selectbox("Izaberite Događaj:", options=events, key="event_selector")

            if selected_event:
                event_df = df[df['event_name'] == selected_event]
                teams = sorted(event_df['team'].unique())
                if teams:
                    selected_team = st.selectbox("Izaberite Tim:", options=teams, key="team_selector")
                    
                    if selected_team != st.session_state.selected_team:
                        st.session_state.selected_team = selected_team

                    if selected_team:
                        team_df = event_df[event_df['team'] == selected_team]
                        players = sorted(team_df['player'].unique())
                        
                        if players:
                            selected_player_for_add = st.selectbox("Izaberite Igrača za dodavanje:", options=players)
                            if st.button("➕ Dodaj Igrača", key=f"add_{selected_player_for_add}"):
                                if selected_player_for_add not in st.session_state.selected_players:
                                    player_games = team_df[team_df['player'] == selected_player_for_add].to_dict('records')
                                    st.session_state.selected_players[selected_player_for_add] = player_games
                                    st.success(f"Igrač {selected_player_for_add} dodat u ponudu.")
                        else:
                            st.warning("Nema dostupnih igrača za izabrani tim.")
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. KORAK: Prikaz i modifikacija kreirane ponude
    if st.session_state.selected_players:
        with st.container():
            st.markdown('<div class="glass-container">', unsafe_allow_html=True)
            st.header("3. Kreirana Ponuda")

            for player_name, games in list(st.session_state.selected_players.items()):
                with st.expander(f"Igre za: {player_name}", expanded=True):
                    for i, game in enumerate(games):
                        cols = st.columns([4, 2, 1])
                        market_name_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                        market_name = MARKET_TRANSLATIONS.get(market_name_raw, market_name_raw)
                        line_formatted = format_line(game['line'], market_name_raw)
                        
                        cols[0].write(f"**{market_name} {line_formatted}**")
                        
                        new_odds = cols[1].number_input("Kvota:", value=game['decimal_odds'], min_value=1.01, step=0.01, key=f"odds_{player_name}_{i}", format="%.2f")
                        st.session_state.selected_players[player_name][i]['decimal_odds'] = new_odds

                        if cols[2].button("Ukloni", key=f"del_{player_name}_{i}"):
                            st.session_state.selected_players[player_name].pop(i)
                            if not st.session_state.selected_players[player_name]:
                                del st.session_state.selected_players[player_name]
                            st.rerun()

                    # Forma za ručni unos
                    st.markdown("---")
                    st.subheader("Ručno dodaj igru")
                    manual_cols = st.columns([3,2])
                    manual_game_name = manual_cols[0].text_input("Naziv igre (npr. 'specijal')", key=f"manual_name_{player_name}")
                    manual_odds = manual_cols[1].number_input("Kvota", min_value=1.01, step=0.01, key=f"manual_odds_{player_name}", format="%.2f")
                    if st.button("Dodaj ručnu igru", key=f"manual_add_{player_name}"):
                        if manual_game_name:
                             # Kreiramo 'fake' game objekat
                            manual_game = {
                                'player': player_name,
                                'market': manual_game_name,
                                'line': -1, # Indikator da je ručno
                                'decimal_odds': manual_odds,
                                'closed': games[0]['closed'] if games else datetime.now().isoformat()
                            }
                            st.session_state.selected_players[player_name].append(manual_game)
                            st.rerun()


            # Dugmad za finalne akcije
            final_cols = st.columns(2)
            if final_cols[0].button("Poništi Unos"):
                st.session_state.selected_players = {}
                st.rerun()
            
            if final_cols[1].button("Generiši CSV Pregled"):
                
                # --- Logika za generisanje CSV-a ---
                if st.session_state.selected_team and st.session_state.selected_players:
                    match_name = st.session_state.selected_team
                    
                    output_rows = []
                    
                    # Glavno zaglavlje
                    header = ['Datum', 'Vreme', 'Sifra', 'Domacin', 'Gost', '', '1', 'X', '2', 'GR', 'U', 'O', 'Yes', 'No']
                    output_rows.append(header)
                    
                    # Red sa imenom tima - UPDATED
                    output_rows.append([f'MATCH_NAME:{match_name}', '', '', '', '', '', '', '', '', '', '', '', '', ''])

                    for player_name, games in st.session_state.selected_players.items():
                        if not games: continue
                        
                        # Red sa imenom igrača - UPDATED
                        output_rows.append([f"LEAGUE_NAME:{player_name.replace(' ', '_')}", '', '', '', '', '', '', '', '', '', '', '', '', ''])
                        
                        for game in games:
                            datum, vreme = format_datetime_serbian(game['closed'])
                            odds = game['decimal_odds']
                            
                            if game['line'] == -1: # Ručno dodata igra
                                market_name = game['market']
                                line_formatted = ""
                            else:
                                market_name_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                                market_name = MARKET_TRANSLATIONS.get(market_name_raw, market_name_raw)
                                line_formatted = format_line(game['line'], market_name_raw)
                                
                            row = [datum, vreme, '', '', market_name, f"{line_formatted}", odds]
                            output_rows.append(row)

                    # Kreiranje DataFrame-a za prikaz i download
                    final_df = pd.DataFrame(output_rows)
                    st.dataframe(final_df)
                    
                    # Priprema za download
                    csv_string = final_df.to_csv(index=False, header=False).encode('utf-8')
                    st.download_button(
                        label="Preuzmi CSV Fajl",
                        data=csv_string,
                        file_name=f"{match_name.replace(' ', '_')}_kvote.csv",
                        mime='text/csv',
                    )

        st.markdown('</div>', unsafe_allow_html=True)

