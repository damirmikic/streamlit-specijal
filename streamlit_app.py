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

# --- Session State Initialization ---
if 'data_df' not in st.session_state:
    st.session_state.data_df = None
if 'offer_list' not in st.session_state:
    # We use a list of dicts to handle duplicates and allow removal
    st.session_state.offer_list = []
if 'preview_df' not in st.session_state:
    st.session_state.preview_df = None


# --- Serbian Translation Mapping ---
MARKET_TRANSLATIONS = {
    "Player's shots on target": "ukupno suteva u okvir gola",
    "Player shots": "ukupno suteva",
    "Player's fouls conceded": "ukupno nacinjenih faulova",
    "to Assist": "asistencija",
    "to get a card": "dobija karton",
    "to get a red card": "dobija crveni karton",
    "to score": "daje gol",
    "to score or assist": "gol ili asistencija",
    "to score from a header": "daje gol glavom",
    "To score from outside the penalty box": "daje gol izvan 16m",
    # Add other market translations here as you discover them
}

# --- Helper Functions ---
def generate_formatted_df(offer_list):
    """
    Transforms the offer list into a formatted DataFrame ready for display or CSV export.
    """
    if not offer_list:
        return pd.DataFrame()

    df = pd.DataFrame(offer_list)
    output_rows = []
    
    # CSV Header as specified in the image
    header = ['Datum', 'Vreme', 'Sifra', 'Domacin', 'Gost', '1', 'X', '2', 'GR', 'U', 'O', 'Yes', 'No']
    
    # Group by team, then by player
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

                market_cleaned = row['market'].replace('(Settled using Opta data)', '').strip()
                domacin = MARKET_TRANSLATIONS.get(market_cleaned, market_cleaned)

                gost = f"{math.ceil(row['line'])}+" if row['line'] > 0 else ''
                
                # Create a blank row, then place the odds in the correct column
                output_row = {h: '' for h in header}
                output_row.update({'Datum': datum, 'Vreme': vreme, 'Domacin': domacin, 'Gost': gost})
                
                # Place odds in 'O' (Over) column as it's the most common prop type
                # This can be expanded if 'Under' or other types are needed
                output_row['O'] = row['decimal_odds']

                output_rows.append(output_row)
                
    return pd.DataFrame(output_rows)

# --- UI Layout ---
st.title("📊 Player Props Offer Builder")

# --- 1. Fetching Data ---
if st.button("🚀 Učitaj najnovije kvote"):
    with st.spinner("Preuzimanje podataka sa API-ja... molimo sačekajte."):
        all_props = get_all_props()
        if all_props:
            st.session_state.data_df = pd.DataFrame(all_props)
            st.success("Podaci su uspešno učitani!")
        else:
            st.error("Neuspešno preuzimanje podataka. Proverite konzolu za greške.")

# --- 2. Main Application UI ---
if st.session_state.data_df is not None:
    st.markdown("---")
    st.header("1. Izbor Igrača i Igara")

    df = st.session_state.data_df
    events_with_props = df['event_name'].unique()
    
    col1, col2 = st.columns(2)
    with col1:
        selected_event = st.selectbox("Izaberite događaj:", options=events_with_props)
    
    if selected_event:
        event_df = df[df['event_name'] == selected_event].copy()
        teams_in_event = sorted([team for team in event_df['team'].unique() if team != 'N/A'])
        
        with col2:
            selected_team = st.selectbox("Izaberite tim:", options=teams_in_event)
        
        if selected_team:
            player_df = event_df[event_df['team'] == selected_team]
            available_players = sorted(player_df['player'].unique())
            
            player_col, add_btn_col = st.columns([4, 1])
            with player_col:
                player_to_add = st.selectbox("Izaberite igrača za dodavanje:", options=available_players, label_visibility="collapsed")
            with add_btn_col:
                if st.button("➕ Dodaj Igrača", use_container_width=True):
                    props_to_add = player_df[player_df['player'] == player_to_add].to_dict('records')
                    for prop in props_to_add:
                        # Add a unique ID to each prop to manage removal
                        prop['id'] = str(uuid.uuid4())
                        st.session_state.offer_list.append(prop)
                    # Clear preview when new players are added
                    st.session_state.preview_df = None


    # --- 3. Current Offer Display ---
    if st.session_state.offer_list:
        st.markdown("---")
        st.header("2. Kreirana Ponuda")

        offer_df = pd.DataFrame(st.session_state.offer_list)
        for player_name, props in offer_df.groupby('player'):
            with st.expander(f"Igre za: {player_name}", expanded=True):
                for index, prop in props.iterrows():
                    prop_col1, prop_col2, prop_col3, btn_col = st.columns([3,1,1,1])
                    market_clean = prop['market'].replace('(Settled using Opta data)', '').strip()
                    prop_col1.write(f"**Tržište:** {MARKET_TRANSLATIONS.get(market_clean, market_clean)}")
                    prop_col2.write(f"**Linija:** {math.ceil(prop['line'])}+")
                    prop_col3.write(f"**Kvota:** {prop['decimal_odds']}")
                    if btn_col.button("Ukloni", key=prop['id'], use_container_width=True):
                        st.session_state.offer_list = [p for p in st.session_state.offer_list if p['id'] != prop['id']]
                        st.session_state.preview_df = None # Clear preview on change
                        st.rerun()
    
    # --- 4. Manual Entry ---
    with st.expander("Ručni Unos Igre"):
        with st.form("manual_entry_form"):
            st.write("Dodajte igru koja nije na listi.")
            m_col1, m_col2 = st.columns(2)
            manual_player = m_col1.text_input("Ime Igrača")
            manual_team = m_col2.text_input("Ime Tima", value=selected_team if selected_team else "")
            
            m_col3, m_col4, m_col5 = st.columns(3)
            manual_market = m_col3.text_input("Tržište (npr. ukupno suteva)")
            manual_line = m_col4.number_input("Linija (npr. 1.5)", step=1.0, value=0.5)
            manual_odds = m_col5.number_input("Kvota (npr. 1.85)", step=0.01)

            submitted = st.form_submit_button("Dodaj Ručno")
            if submitted:
                if manual_player and manual_team and manual_market:
                    manual_prop = {
                        'id': str(uuid.uuid4()),
                        'event_name': selected_event,
                        'closed': st.session_state.data_df[st.session_state.data_df['event_name']==selected_event]['closed'].iloc[0],
                        'player': manual_player,
                        'team': manual_team,
                        'market': manual_market,
                        'line': manual_line,
                        'selection': 'Over',
                        'decimal_odds': manual_odds
                    }
                    st.session_state.offer_list.append(manual_prop)
                    st.session_state.preview_df = None # Clear preview
                    st.success(f"Ručno dodata igra za {manual_player}.")
                    st.rerun()
                else:
                    st.warning("Molimo popunite sva polja.")


    # --- 5. Generate Preview and Download ---
    if st.session_state.offer_list:
        st.markdown("---")
        st.header("3. Pregled i Preuzimanje")
        
        preview_col, clear_col = st.columns(2)
        
        with preview_col:
            if st.button("📊 Generiši Pregled Tabele", use_container_width=True):
                st.session_state.preview_df = generate_formatted_df(st.session_state.offer_list)

        with clear_col:
            if st.button("❌ Poništi Unos", use_container_width=True):
                st.session_state.offer_list = []
                st.session_state.preview_df = None
                st.rerun()

        if st.session_state.preview_df is not None:
            st.info("Ovo je pregled kako će tabela izgledati u CSV fajlu.")
            st.dataframe(st.session_state.preview_df.fillna(''))

            team_name = pd.DataFrame(st.session_state.offer_list)['team'].unique()[0] if len(pd.DataFrame(st.session_state.offer_list)['team'].unique()) == 1 else "ponuda"
            file_name = f"{team_name}_kvote.csv"
            
            csv_data = st.session_state.preview_df.to_csv(index=False, header=True).encode('utf-8')

            st.download_button(
                label="📥 Preuzmi CSV",
                data=csv_data,
                file_name=file_name,
                mime="text/csv",
                use_container_width=True
            )

