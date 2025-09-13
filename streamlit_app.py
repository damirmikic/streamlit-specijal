import streamlit as st
import pandas as pd
from player_props_scraper import get_all_props

# --- Page Configuration ---
st.set_page_config(
    page_title="Player Props Offer Builder",
    page_icon="",
    layout="wide"
)

# --- Session State Initialization ---
# This ensures that our data persists across user interactions.
if 'data_df' not in st.session_state:
    st.session_state.data_df = None
if 'offer_df' not in st.session_state:
    st.session_state.offer_df = pd.DataFrame()

# --- Helper Functions ---
@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV string for downloading."""
    return df.to_csv(index=False).encode('utf-8')

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
                # Store the fetched data as a DataFrame in the session state
                st.session_state.data_df = pd.DataFrame(all_props)
                st.success("Data fetched successfully!")
            else:
                st.error("Failed to fetch data. Check the console for errors.")

if st.session_state.data_df is not None:
    st.markdown("---")
    st.header("1. Select Event and Players")

    df = st.session_state.data_df
    
    # Get a list of unique events that have player props
    events_with_props = df['event_name'].unique()
    
    # Dropdown for selecting an event
    selected_event = st.selectbox(
        "Choose an event:",
        options=events_with_props,
        index=0
    )

    if selected_event:
        # Filter the DataFrame to show only data from the selected event
        event_df = df[df['event_name'] == selected_event].copy()
        
        # --- NEW: Team selection dropdown ---
        teams_in_event = sorted(list(event_df['team'].unique()))
        team_options = ["All Teams"] + teams_in_event

        selected_team = st.selectbox(
            "Choose a team (optional):",
            options=team_options
        )
        
        # Filter by selected team if one is chosen
        if selected_team and selected_team != "All Teams":
            player_df = event_df[event_df['team'] == selected_team]
        else:
            player_df = event_df

        # Get a list of unique players for the multiselect dropdown based on team filter
        available_players = sorted(player_df['player'].unique())

        selected_players = st.multiselect(
            "Select players to add to your offer:",
            options=available_players
        )

        if st.button("➕ Add Players to Offer", use_container_width=True):
            if selected_players:
                # Get all props for the selected players from the original event_df
                props_to_add = event_df[event_df['player'].isin(selected_players)]
                
                # Append to the existing offer DataFrame in the session state
                st.session_state.offer_df = pd.concat(
                    [st.session_state.offer_df, props_to_add]
                ).drop_duplicates().reset_index(drop=True)
                st.success(f"Added props for {', '.join(selected_players)} to the offer.")
            else:
                st.warning("Please select at least one player to add.")

# --- Offer Preview and Download Section ---
if not st.session_state.offer_df.empty:
    st.markdown("---")
    st.header("2. Current Offer (CSV Preview)")

    st.dataframe(st.session_state.offer_df)

    col1, col2 = st.columns(2)
    
    with col1:
        # Prepare the CSV data for download
        csv_data = convert_df_to_csv(st.session_state.offer_df)
        st.download_button(
            label="📥 Download as CSV",
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

