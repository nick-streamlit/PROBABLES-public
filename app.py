import streamlit as st
import pandas as pd
import numpy as np
import os

try:
    df = pd.read_json("probable_pitchers.json")
except FileNotFoundError:
    st.error("File not found.")
    df = pd.DataFrame()

df['date_time'] = pd.to_datetime(df['date'])
df['date'] = df['date_time'].dt.date
df['day'] = df['date_time'].dt.day_name()

# Set page config for better layout
st.set_page_config(layout="wide")

st.header("Bovine Probable SPs")
st.dataframe(df, use_container_width=True, 
column_order=["date", "day", "time", "home_team", "home_pitcher", "away_team", "away_pitcher"])