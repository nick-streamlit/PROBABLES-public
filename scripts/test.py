import pandas as pd
from pathlib import Path


# Define the base directory (project_root) relative to the current script location
# Go up one level from 'src' to 'project_root'
project_root = Path(__file__).parent.parent

# Define the path to the 'input' data folder
input_folder = project_root / 'data' / 'input'
processed_folder = project_root / 'data' / 'processed'

pitchers_df = pd.read_csv(f"{input_folder}/roster.csv")

try:
    proj_pts = pd.read_csv(f"{processed_folder}/2026 Fantasy Baseball Draft - Starting Pitchers.csv")
except FileNotFoundError:
    st.error("File not found.")
    runs_df = pd.DataFrame()

roster_proj = pitchers_df.merge(proj_pts, left_on='pitcher_name', right_on='Player',how='left')

roster_proj.to_csv(f"{processed_folder}/roster_proj.csv", index=False)
#code that could be used to merge projections to roster though is easier and more info to merge directly with probables.