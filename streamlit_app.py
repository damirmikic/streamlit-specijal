import streamlit as st
import pandas as pd
from player_props_scraper import get_all_props
import io
import csv
from datetime import datetime
import math
import uuid

# --- Page Configuration ---
st.set_page_config(
    page_title="Player Props Offer Builder",
    page_icon="⚽",
    layout="wide"
)

# --- Serbian Translation Mapping (Updated) ---
MARKET_TRANSLATIONS = {
    "Player's Shots On Target": "ukupno suteva u okvir gola",
    "Player's Shots": "ukupno suteva",
    "Player's Fouls Conceded": "ukupno nacinjenih faulova",
    "To Assist": "asistencija",
    "To Get A Card": "dobija karton",
    "To Get A Red Card": "dobija crveni karton",
    "To Score": "daje gol",
    "To Score Or Assist": "gol ili asistencija",
    "To Score From A Header": "daje gol glavom",
    "To Score From Outside The Penalty Box": "daje gol izvan 16m",
    "To score at least 2 goal": "daje golova"
}

# --- Custom CSS for Modern UI/UX ---
def load_css():
    """Injects custom CSS for a modern, accessible, and interactive UI."""
    st.markdown("""
        <style>
            /* --- Global & Typography --- */
            html, body, [class*="st-"] {
                font-family: 'Inter', sans-serif;
                color: #E5E7EB; /* Light gray text for readability */
            }
            h1, h2, h3 {
                font-weight: 600;
            }
            .main {
                background-color: #030712; /* Dark background */
                background-image: radial-gradient(circle at top right, rgba(12,74,110,0.3), transparent 40%);
                background-attachment: fixed;
            }

            /* --- Glassmorphism Containers --- */
            .glass-container {
                background: rgba(31, 41, 55, 0.5);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 2rem;
                margin-bottom: 2rem;
                transition: all 0.2s ease-in-out;
            }
            .glass-container:hover {
                box-shadow: 0 0 20px rgba(0, 191, 255, 0.1); /* Subtle glow on hover */
            }
            
            /* --- Button & Interactive Elements Styling --- */
            div[data-testid="stButton"] > button, .stDownloadButton > button {
                border: 1px solid #38BDF8; /* Light blue border */
                border-radius: 12px;
                background-color: transparent;
                color: #38BDF8;
                padding: 12px 24px; /* Larger tap area */
                transition: all 0.2s ease-in-out;
                font-weight: 600;
            }
            div[data-testid="stButton"] > button:hover, .stDownloadButton > button:hover {
                background-color: #38BDF8;
                color: #030712;
                box-shadow: 0 0 15px rgba(56, 189, 248, 0.5);
                transform: translateY(-2px); /* Subtle lift */
            }
            div[data-testid="stButton"] > button:active, .stDownloadButton > button:active {
                transform: translateY(0);
            }
            
            /* Style for 'Remove' button */
            div[data-testid="stButton"] > button:contains("Ukloni") {
                border-color: #F472B6;
                color: #F472B6;
            }
             div[data-testid="stButton"] > button:contains("Ukloni"):hover {
                background-color: #F472B6;
                color: #FFFFFF;
                box-shadow: 0 0 15px rgba(244, 114, 182, 0.5);
            }

            /* --- Input Fields (Selectbox, Text Input) --- */
            div[data-testid="stSelectbox"], div[data-testid="stTextInput"], div[data-testid="stNumberInput"] {
                 background-color: rgba(17, 24, 39, 0.8);
                 border-radius: 12px;
                 padding: 8px;
                 border: 1px solid rgba(255, 255, 255, 0.1);
            }

            /* --- Expander for player cards --- */
            .stExpander {
                background: rgba(17, 24, 39, 0.8);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .stExpander header {
                font-size: 1.25rem;
                font-weight: 600;
                color: #F9FAFB;
            }
            
            /* --- Dataframe styling --- */
            .stDataFrame {
                border-radius: 16px;
                overflow: hidden;
            }
        </style>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap">
    """, unsafe_allow_html=True)

# --- Session State Initialization ---
if 'data_df' not in st.session_state:
    st.session_state.data_df = None
if 'offer_list' not in st.session_state:
    st.session_state.offer_list = []
if 'preview_df' not in st.session_state:
    st.session_state.preview_df = None
if 'selected_team' not in st.session_state:
    st.session_state.selected_team = ""

# --- Helper Functions ---
def get_translation(market_name):
    """Gets the Serbian translation for a market name, ignoring case."""
    cleaned_name = market_name.replace('(Settled using Opta data)', '').strip()
    # Convert to title case to match the dictionary keys
    title_case_name = cleaned_name.title()
    return MARKET_TRANSLATIONS.get(title_case_name, cleaned_name)

def generate_formatted_df(offer_list):
    """
    Transforms the offer list into a formatted DataFrame ready for display or CSV export.
    """
    if not offer_list:
        return pd.DataFrame()

    df = pd.DataFrame(offer_list)
    output_rows = []
    
    header = ['Datum', 'Vreme', 'Sifra', 'Domacin', 'Gost', '1', 'X', '2', 'GR', 'U', 'O', 'Yes', 'No']
    
    grouped_by_team = df.groupby('team')
    
    for team_name, team_df in grouped_by_team:
        output_rows.append({header[0]: f'MATCH_NAME:{team_name}'})
        
        grouped_by_player = team_df.groupby('player')
        for player_name, player_df in grouped_by_player:
            player_df = player_df.sort_values(['market', 'line'])
            output_rows.append({header[0]: f'LEAGUE_NAME:{player_name}'})

            for _, row in player_df.iterrows():
                datum, vreme = ('', '')
                if row.get('closed') and isinstance(row['closed'], str):
                    try:
                        dt = datetime.fromisoformat(row['closed'].replace('Z', '+00:00'))
                        datum = dt.strftime('%d.%m.%Y')
                        vreme = dt.strftime('%H:%M')
                    except ValueError:
                        pass

                domacin = get_translation(row['market'])
                gost = f"{math.ceil(row['line'])}+" if row['line'] > 0 else ''
                
                output_row = {h: '' for h in header}
                output_row.update({'Datum': datum, 'Vreme': vreme, 'Domacin': domacin, 'Gost': gost, 'O': row['decimal_odds']})
                output_rows.append(output_row)
                
    return pd.DataFrame(output_rows)

# --- UI Layout ---
load_css()

st.title("📊 Player Props Offer Builder")

# --- 1. Fetching Data ---
if st.button("🚀 Učitaj Najnovije Kvote"):
    with st.spinner("Preuzimanje podataka sa API-ja..."):
        all_props = get_all_props()
        if all_props:
            st.session_state.data_df = pd.DataFrame(all_props)
            st.success("Podaci su uspešno učitani!")
        else:
            st.error("Neuspešno preuzimanje podataka.")

# --- 2. Main Application UI ---
if st.session_state.data_df is not None:
    with st.container():
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.header("1. Izbor Događaja i Tima")
        df = st.session_state.data_df
        events_with_props = df['event_name'].unique()
        
        col1, col2 = st.columns(2)
        with col1:
            selected_event = st.selectbox("Izaberite događaj:", options=events_with_props, key="event_selector")
        
        if selected_event:
            event_df = df[df['event_name'] == selected_event].copy()
            teams_in_event = sorted([team for team in event_df['team'].unique() if team != 'N/A'])
            
            with col2:
                # Store selected team in session state to fix the manual entry bug
                st.session_state.selected_team = st.selectbox("Izaberite tim:", options=teams_in_event, key="team_selector")
            
            st.markdown("---")
            st.subheader("Dodaj Igrača u Ponudu")

            if st.session_state.selected_team:
                player_df = event_df[event_df['team'] == st.session_state.selected_team]
                available_players = sorted(player_df['player'].unique())
                
                player_col, add_btn_col = st.columns([3, 1])
                with player_col:
                    player_to_add = st.selectbox("Izaberite igrača:", options=available_players, label_visibility="collapsed")
                with add_btn_col:
                    if st.button("➕ Dodaj Igrača", use_container_width=True):
                        props_to_add = player_df[player_df['player'] == player_to_add].to_dict('records')
                        for prop in props_to_add:
                            prop['id'] = str(uuid.uuid4())
                            st.session_state.offer_list.append(prop)
                        st.session_state.preview_df = None
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. Current Offer Display ---
    if st.session_state.offer_list:
        with st.container():
            st.markdown('<div class="glass-container">', unsafe_allow_html=True)
            st.header("2. Kreirana Ponuda")
            
            offer_df = pd.DataFrame(st.session_state.offer_list)
            for player_name, props in offer_df.groupby('player'):
                with st.expander(f"Igre za: {player_name}", expanded=True):
                    for _, prop in props.iterrows():
                        prop_col1, prop_col2, btn_col = st.columns([5, 2, 1])
                        prop_col1.markdown(f"**{get_translation(prop['market'])}** ({math.ceil(prop['line'])}+)")
                        prop_col2.markdown(f"**Kvota:** `{prop['decimal_odds']}`")
                        if btn_col.button("Ukloni", key=prop['id'], use_container_width=True):
                            st.session_state.offer_list = [p for p in st.session_state.offer_list if p['id'] != prop['id']]
                            st.session_state.preview_df = None
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
    # --- 4. Manual Entry & Actions ---
    with st.container():
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        with st.expander("📝 Ručni Unos Igre"):
            with st.form("manual_entry_form"):
                st.write("Dodajte igru koja nije na listi.")
                m_col1, m_col2 = st.columns(2)
                manual_player = m_col1.text_input("Ime Igrača")
                # Use session state for a stable default value
                manual_team = m_col2.text_input("Ime Tima", value=st.session_state.get("selected_team", ""))
                
                m_col3, m_col4, m_col5 = st.columns(3)
                manual_market = m_col3.text_input("Tržište (npr. ukupno suteva)")
                manual_line = m_col4.number_input("Linija (npr. 1.5)", step=1.0, value=0.5)
                manual_odds = m_col5.number_input("Kvota (npr. 1.85)", step=0.01)

                if st.form_submit_button("Dodaj Ručno", use_container_width=True):
                    if manual_player and manual_team and manual_market:
                        manual_prop = {
                            'id': str(uuid.uuid4()), 'event_name': selected_event,
                            'closed': st.session_state.data_df[st.session_state.data_df['event_name']==selected_event]['closed'].iloc[0],
                            'player': manual_player, 'team': manual_team, 'market': manual_market,
                            'line': manual_line, 'selection': 'Over', 'decimal_odds': manual_odds
                        }
                        st.session_state.offer_list.append(manual_prop)
                        st.session_state.preview_df = None
                        st.success(f"Ručno dodata igra za {manual_player}.")
                        st.rerun()
                    else:
                        st.warning("Molimo popunite sva polja.")
        
        st.markdown("---")
        st.header("3. Generisanje Fajla")
        
        preview_col, clear_col, download_col = st.columns(3)
        
        with preview_col:
            if st.button("📊 Generiši Pregled", use_container_width=True):
                st.session_state.preview_df = generate_formatted_df(st.session_state.offer_list) if st.session_state.offer_list else None

        with clear_col:
            if st.button("❌ Poništi Unos", use_container_width=True):
                st.session_state.offer_list = []
                st.session_state.preview_df = None
                st.rerun()
        
        with download_col:
            if st.session_state.preview_df is not None and not st.session_state.preview_df.empty:
                team_name = pd.DataFrame(st.session_state.offer_list)['team'].unique()[0] if len(pd.DataFrame(st.session_state.offer_list)['team'].unique()) == 1 else "ponuda"
                file_name = f"{team_name}_kvote.csv"
                csv_data = st.session_state.preview_df.to_csv(index=False, header=True).encode('utf-8')
                st.download_button(
                    label="📥 Preuzmi CSV", data=csv_data, file_name=file_name,
                    mime="text/csv", use_container_width=True
                )

        if st.session_state.preview_df is not None:
            st.info("Ovo je pregled kako će tabela izgledati u CSV fajlu.")
            st.dataframe(st.session_state.preview_df.fillna(''))
        st.markdown('</div>', unsafe_allow_html=True)

