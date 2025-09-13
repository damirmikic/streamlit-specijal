import streamlit as st
import pandas as pd
from player_props_scraper import get_all_props
import io
import csv
from datetime import datetime
import math

# --- Page Configuration ---
st.set_page_config(
    page_title="Player Props Offer Builder",
    page_icon="🏀",
    layout="wide"
)

# --- Session State Initialization ---
if 'data_df' not in st.session_state:
    st.session_state.data_df = None
if 'offer_df' not in st.session_state:
    st.session_state.offer_df = pd.DataFrame()

# --- Serbian Translation Mapping ---
MARKET_TRANSLATIONS = {
    "Player's shots on target": "ukupno suteva u okvir gola",
    "Player shots": "ukupno suteva",
    "Player's fouls conceded": "ukupno nacinjenih faulova",
    # Add other market translations here as you discover them
}

# --- Helper Functions ---
def generate_custom_csv(df):
    """
    Transforms a DataFrame into a custom CSV format with Serbian translations,
    MATCH_NAME, and LEAGUE_NAME headers, matching the user's specific format.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow(['Datum', 'Vreme', 'Sifra', 'Domacin', 'Gost', 'Kvota'])

    # Group the offer by the selected team, then by player
    grouped_by_team = df.groupby('team')
    
    for team_name, team_df in grouped_by_team:
        writer.writerow([f'MATCH_NAME:{team_name}', '', '', '', '', ''])
        
        grouped_by_player = team_df.groupby('player')
        for player_name, player_df in grouped_by_player:
            # Sort props by market and then by line for consistent ordering
            player_df = player_df.sort_values(['market', 'line'])
            writer.writerow([f'LEAGUE_NAME:{player_name}', '', '', '', '', ''])

            for _, row in player_df.iterrows():
                # 1. Parse and format date and time
                datum, vreme = ('', '')
                if row['closed'] and isinstance(row['closed'], str):
                    try:
                        dt = datetime.fromisoformat(row['closed'].replace('Z', '+00:00'))
                        datum = dt.strftime('%d.%m.%Y')
                        vreme = dt.strftime('%H:%M')
                    except ValueError:
                        pass # Keep them empty if parsing fails

                # 2. Clean and translate the market name for the 'Domacin' column
                market_cleaned = row['market'].replace('(Settled using Opta data)', '').strip()
                domacin = MARKET_TRANSLATIONS.get(market_cleaned, market_cleaned)

                # 3. Format the line value for the 'Gost' column (e.g., 1.5 -> 2+)
                gost = ''
                if row['line'] > 0:
                    gost = f"{math.ceil(row['line'])}+"
                
                # 4. Sifra (empty as per example)
                sifra = ''

                # 5. Get the odds for 'Kvota'
                kvota = row['decimal_odds']

                writer.writerow([datum, vreme, sifra, domacin, gost, kvota])
                
    return output.getvalue().encode('utf-8')

# --- UI Layout ---
st.title("📊 Player Props Offer Builder")
st.markdown("Fetch the latest player props, build an offer, and export it as a CSV file.")

# --- Main Application Logic ---
fetch_col, clear_col = st.columns([1, 5])

with fetch_col:
    if st.button("🚀 Fetch Latest Props"):
        with st.spinner("Fetching data from API... please wait."):
            all_props = get_all_props()
            if all_props:
                st.session_state.data_df = pd.DataFrame(all_props)
                st.success("Data fetched successfully!")
            else:
                st.error("Failed to fetch data. Check the console for errors.")

if st.session_state.data_df is not None:
    st.markdown("---")
    st.header("1. Select Event and Players")

    df = st.session_state.data_df
    events_with_props = df['event_name'].unique()
    
    selected_event = st.selectbox(
        "Choose an event:",
        options=events_with_props,
        index=0
    )

    if selected_event:
        event_df = df[df['event_name'] == selected_event].copy()
        teams_in_event = sorted(list(event_df['team'].unique()))
        team_options = ["All Teams"] + teams_in_event
        selected_team = st.selectbox("Choose a team (optional):", options=team_options)
        
        player_df = event_df[event_df['team'] == selected_team] if selected_team != "All Teams" else event_df
        available_players = sorted(player_df['player'].unique())

        selected_players = st.multiselect("Select players to add to your offer:", options=available_players)

        if st.button("➕ Add Players to Offer", use_container_width=True):
            if selected_players:
                props_to_add = event_df[event_df['player'].isin(selected_players)]
                st.session_state.offer_df = pd.concat(
                    [st.session_state.offer_df, props_to_add]
                ).drop_duplicates().reset_index(drop=True)
                st.success(f"Added props for {', '.join(selected_players)} to the offer.")
            else:
                st.warning("Please select at least one player to add.")

# --- Offer Preview and Download Section ---
if not st.session_state.offer_df.empty:
    st.markdown("---")
    st.header("2. Current Offer (Raw Data Preview)")

    st.dataframe(st.session_state.offer_df)

    col1, col2 = st.columns(2)
    
    with col1:
        # Use the new function to generate the CSV for download
        csv_data = generate_custom_csv(st.session_state.offer_df)
        st.download_button(
            label="📥 Download as Custom CSV",
            data=csv_data,
            file_name="player_props_offer.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    with col2:
        if st.button("❌ Clear Offer", use_container_width=True):
            st.session_state.offer_df = pd.DataFrame()
            st.rerun()

st.sidebar.info("This app fetches live betting odds. Please use responsibly.")

