from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Add the parent directory to the system path
sys.path.insert(1, parent_dir)

# Now you can import 'main' from 'app'
from src.main import main

main()

project_root = Path(__file__).parent.parent

# Define the path to the 'input' data folder
processed_folder = project_root / 'data' / 'processed'

try:
    pitcher_df = pd.read_json(processed_folder / "probable_pitchers.json")
except FileNotFoundError:
    st.error("File not found.")
    pitcher_df = pd.DataFrame()

pitcher_df['date_time'] = pd.to_datetime(pitcher_df['date'])
pitcher_df['date'] = pitcher_df['date_time'].dt.date
pitcher_df['day'] = pitcher_df['date_time'].dt.day_name()



try:
    park_factor_df = pd.read_csv(processed_folder / "FantasyPros_Fantasy_Baseball_Park_Factors.csv")
except FileNotFoundError:
    st.error("File not found.")
    park_factor_df = pd.DataFrame()

try:
    runs_df = pd.read_csv(processed_folder / "standings.csv")
except FileNotFoundError:
    st.error("File not found.")
    runs_df = pd.DataFrame()

try:
    proj_df = pd.read_csv(processed_folder / "2026 Fantasy Baseball Draft - Starting Pitchers.csv")
except FileNotFoundError:
    st.error("File not found.")
    proj_df = pd.DataFrame()

df = pitcher_df.merge(park_factor_df, left_on='home_team', right_on='Team',how='left').merge(runs_df, left_on='home_team', right_on='Team', how='left').merge(proj_df, left_on='home_pitcher', right_on='Player', how='left').merge(proj_df, left_on='away_pitcher', right_on='Player', how='left', suffixes=('_home', '_away')) 

#intermeditate view to test
#df.to_csv(processed_folder / "probable_pitchers_merged.csv", index=False)

# Define a dictionary for renaming specific columns
rename_mapping = {'Runs': 'Park_Factor','2026 Projected Rest of Season RS/G': 'Home Proj RS/G'}

df = df.rename(columns=rename_mapping)

df = df.merge(runs_df[['Team', '2026 Projected Rest of Season RS/G']], left_on='away_team', right_on='Team', how='left') 

rename_mapping = {'2026 Projected Rest of Season RS/G': 'Away Proj RS/G'}

df = df.rename(columns=rename_mapping)

#calc start score


# Set page config for better layout
st.set_page_config(layout="wide")

st.header("Bovine Probable SPs")
st.dataframe(df, width='stretch', 
column_order=["date", "day", "time", "home_team", "home_pitcher", "away_team", "away_pitcher", "Park_Factor", "Home Proj RS/G", "Away Proj RS/G", "2026 proj Pts_home", "2026 proj Pts_away"])