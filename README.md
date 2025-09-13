Player Props Scraper & Offer BuilderThis project is a web application built with Python and Streamlit that fetches player prop betting odds from the betting API, allows users to interactively build a custom offer, and exports the final selection as a CSV file.FeaturesLive Data Fetching: Pulls the latest player prop and match data directly from the API.Interactive UI: Users can select a specific match from a dropdown menu.Dynamic Filtering: After selecting a match, users can choose from a list of available players.Offer Building: Add props from multiple players to a consolidated offer list.CSV Preview & Export: View the created offer in a table and download it as a player_props_offer.csv file.Tech StackBackend/Scraping: Python, requestsWeb Framework: StreamlitData Manipulation: pandasProject Structure.
├── player_props_scraper.py   # Module for all API fetching and data transformation logic.
├── streamlit_app.py          # The main Streamlit application file.
├── requirements.txt          # A list of Python dependencies for the project.
└── README.md                 # This file.
Setup and InstallationTo run this application locally, please follow these steps:1. Clone the repository:git clone <your-repository-url>
cd <your-repository-directory>
2. (Recommended) Create and activate a virtual environment:Windows:python -m venv venv
.\venv\Scripts\activate
macOS / Linux:python3 -m venv venv
source venv/bin/activate
3. Install the required dependencies:pip install -r requirements.txt
How to Run the ApplicationOnce the setup is complete, run the following command in your terminal from the project's root directory:streamlit run streamlit_app.py
Your web browser should automatically open a new tab with the running application.
