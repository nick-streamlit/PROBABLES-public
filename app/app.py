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
    df1 = pd.read_json(processed_folder / "probable_pitchers.json")
except FileNotFoundError:
    st.error("File not found.")
    df1 = pd.DataFrame()

df1['date_time'] = pd.to_datetime(df1['date'])
df1['date'] = df1['date_time'].dt.date
df1['day'] = df1['date_time'].dt.day_name()



try:
    df2 = pd.read_csv(processed_folder / "FantasyPros_Fantasy_Baseball_Park_Factors.csv")
except FileNotFoundError:
    st.error("File not found.")
    df2 = pd.DataFrame()

df = pd.merge(df1, df2, left_on='home_team', right_on='Team',how='left') 

# Define a dictionary for renaming specific columns
rename_mapping = {'Runs': 'Park_Factor'}

df = df.rename(columns=rename_mapping)


# Set page config for better layout
st.set_page_config(layout="wide")

st.header("Bovine Probable SPs")
st.dataframe(df, use_container_width=True, 
column_order=["date", "day", "time", "home_team", "home_pitcher", "away_team", "away_pitcher", "Park_Factor"])