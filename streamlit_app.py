import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import math 
from player_props_scraper import get_all_props
from lineup_scraper import get_all_lineups

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
    "To score at least 2 goals": "daje golova",
    "To score at least 3 goals": "daje golova",
}

def format_line(line_val, market):
    base_market = market.lower()
    if "card" in base_market or "poluvremenu" in base_market or line_val is None:
        return "" 
    
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
if 'manual_games' not in st.session_state: st.session_state.manual_games = {}
if 'selected_team' not in st.session_state: st.session_state.selected_team = None
if 'lineups' not in st.session_state: st.session_state.lineups = None

# --- UI Aplikacije ---
st.title("Player Props CSV Generator")

# --- Automatsko preuzimanje postava pri pokretanju ---
if st.session_state.lineups is None:
    with st.spinner("Preuzimanje očekivanih postava sa Sports Mole..."):
        st.session_state.lineups = get_all_lineups()
        if st.session_state.lineups:
            st.toast(f"Pronađene postave za {len(st.session_state.lineups)} timova.", icon="✅")
        else:
            # Postavljamo prazan rečnik da se ne bi ponovo pokretalo
            st.session_state.lineups = {}
            st.toast("Nije uspelo preuzimanje postava.", icon="❌")


# 1. KORAK: Izbor lige i preuzimanje podataka
with st.container():
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    st.header("1. Preuzimanje Ponude")
    
    selected_league_name = st.selectbox("Izaberite Ligu:", options=list(LEAGUES.keys()))
    
    if st.button("Prikaži Ponudu Kvote"):
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
    
    # 2. KORAK: Filtriranje i dodavanje igrača
    with st.container():
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.header("2. Izbor Igrača")

        teams = sorted(df['team'].unique())
        if not teams:
            st.warning("Nema dostupnih timova sa ponudom za igrače u izabranoj ligi.")
        else:
            selected_team = st.selectbox("Izaberite Tim:", options=teams, key="team_selector")
            
            if selected_team != st.session_state.selected_team:
                st.session_state.selected_team = selected_team
            
            # Prikaz očekivane postave ako postoji
            if st.session_state.lineups and selected_team:
                lineup = st.session_state.lineups.get(selected_team)
                if lineup:
                    with st.expander(f"Očekivana postava za {selected_team}"):
                        st.info(", ".join(lineup))
                else:
                    st.warning(f"Nije pronađena očekivana postava za {selected_team}.")

            if selected_team:
                team_df = df[df['team'] == selected_team]
                players = sorted(team_df['player'].unique())
                
                if players:
                    selected_player_for_add = st.selectbox("Izaberite Igrača za dodavanje:", options=players)
                    if st.button("➕ Dodaj Igrača", key=f"add_{selected_player_for_add}"):
                        if selected_player_for_add not in st.session_state.selected_players:
                            player_games = team_df[team_df['player'] == selected_player_for_add].to_dict('records')
                            
                            to_score_game = next((g for g in player_games if g['market'].replace("(Settled using Opta data)", "").strip() == "To Score"), None)
                            
                            if to_score_game:
                                try:
                                    p_at_least_one = 1 / to_score_game['decimal_odds']
                                    lambda_total = -math.log(1 - p_at_least_one)
                                    odds_1st_half = round(1 / (1 - math.exp(-(lambda_total * 0.44))), 2)
                                    odds_2nd_half = round(1 / (1 - math.exp(-(lambda_total * 0.56))), 2)

                                    game_1st_half = {**to_score_game, 'market': 'daje gol u 1. poluvremenu', 'decimal_odds': odds_1st_half, 'line': None}
                                    game_2nd_half = {**to_score_game, 'market': 'daje gol u 2. poluvremenu', 'decimal_odds': odds_2nd_half, 'line': None}
                                    player_games.extend([game_1st_half, game_2nd_half])

                                except (ValueError, ZeroDivisionError) as e:
                                    st.warning(f"Greška pri računanju kvota za poluvremena za {selected_player_for_add}: {e}")
                            
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
                    
                    col1, col2 = st.columns(2)
                    midpoint = math.ceil(len(games) / 2)
                    
                    def display_game(game, index, player):
                        market_name_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                        market_name = MARKET_TRANSLATIONS.get(market_name_raw, market_name_raw)
                        line_formatted = format_line(game.get('line'), market_name_raw)
                        
                        st.write(f"**{market_name} {line_formatted}**")

                        sub_cols = st.columns([3, 1])
                        new_odds = sub_cols[0].number_input(
                            "Kvota:", value=game['decimal_odds'], min_value=1.01, step=0.01, 
                            key=f"odds_{player}_{index}", format="%.2f", label_visibility="collapsed"
                        )
                        st.session_state.selected_players[player][index]['decimal_odds'] = new_odds

                        if sub_cols[1].button("Ukloni", key=f"del_{player}_{index}"):
                            st.session_state.selected_players[player].pop(index)
                            if not st.session_state.selected_players[player]:
                                del st.session_state.selected_players[player]
                            st.rerun()

                    with col1:
                        for i in range(midpoint):
                            display_game(games[i], i, player_name)
                            if i < midpoint -1 : st.markdown("<hr style='margin-top:10px; margin-bottom:10px; border-color: #4a4e69;'>", unsafe_allow_html=True)
                    with col2:
                        for i in range(midpoint, len(games)):
                            display_game(games[i], i, player_name)
                            if i < len(games) -1: st.markdown("<hr style='margin-top:10px; margin-bottom:10px; border-color: #4a4e69;'>", unsafe_allow_html=True)

                    st.markdown("---")
                    st.subheader("Ručno dodaj igru")
                    manual_cols = st.columns([3,2])
                    manual_game_name = manual_cols[0].text_input("Naziv igre (npr. 'specijal')", key=f"manual_name_{player_name}")
                    manual_odds = manual_cols[1].number_input("Kvota", min_value=1.01, step=0.01, key=f"manual_odds_{player_name}", format="%.2f")
                    if st.button("Dodaj ručnu igru", key=f"manual_add_{player_name}"):
                        if manual_game_name:
                            manual_game = {
                                'player': player_name, 'market': manual_game_name, 'line': -1, 
                                'decimal_odds': manual_odds, 'closed': games[0]['closed'] if games else datetime.now().isoformat()
                            }
                            st.session_state.selected_players[player_name].append(manual_game)
                            st.rerun()

            final_cols = st.columns(2)
            if final_cols[0].button("Poništi Unos"):
                st.session_state.selected_players = {}
                st.rerun()
            
            if final_cols[1].button("Generiši CSV Pregled"):
                if st.session_state.selected_team and st.session_state.selected_players:
                    match_name = st.session_state.selected_team
                    
                    output_rows = []
                    header = ['Datum', 'Vreme', 'Sifra', 'Domacin', 'Gost', '', '1', 'X', '2', 'GR', 'U', 'O', 'Yes', 'No']
                    output_rows.append(header)
                    output_rows.append([f'MATCH_NAME:{match_name}', '', '', '', '', '', '', '', '', '', '', '', '', ''])

                    for player_name, games in st.session_state.selected_players.items():
                        if not games: continue
                        output_rows.append([f"LEAGUE_NAME:{player_name}", '', '', '', '', '', '', '', '', '', '', '', '', ''])
                        
                        for game in games:
                            datum, vreme = format_datetime_serbian(game['closed'])
                            odds = game['decimal_odds']
                            
                            if game.get('line') == -1:
                                market_name, line_formatted = game['market'], ""
                            else:
                                market_name_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                                market_name = MARKET_TRANSLATIONS.get(market_name_raw, market_name_raw)
                                line_formatted = format_line(game.get('line'), market_name_raw)
                                
                            row = [datum, vreme, '', '', market_name, f"{line_formatted}", odds]
                            output_rows.append(row)

                    final_df = pd.DataFrame(output_rows)
                    st.dataframe(final_df)
                    
                    csv_string = final_df.to_csv(index=False, header=False).encode('utf-8')
                    st.download_button(
                        label="Preuzmi CSV Fajl", data=csv_string,
                        file_name=f"{match_name.replace(' ', '_')}_kvote.csv", mime='text/csv'
                    )

        st.markdown('</div>', unsafe_allow_html=True)

