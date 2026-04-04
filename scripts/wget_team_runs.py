import wget
import pandas as pd
from pathlib import Path
import requests
project_root = Path(__file__).parent.parent

# Define the path to the 'input' data folder
input_folder = project_root / 'data' / 'input'
processed_folder = project_root / 'data' / 'processed'
# Scrape all tables from the given URL
# 
# # Define a standard browser User-Agent
# headers = {"User-Agent": "Mozilla/5.0"}
url = 'https://www.fangraphs.com/standings/projected-standings'

# This downloads the file and returns the local filename
filename = wget.download(url, out=f"{input_folder}/projected-standings.html")
print(f"Downloaded: {filename}")
# # Fetch the page content first
response = input_folder / 'projected-standings.html'
# #parse table
tables = pd.read_html(response)
df = tables[6]
print(df.head())
df.to_csv(f"{processed_folder}/projected-standings.csv", index=False)

#need to merge double headed with suffix and integrate into the code that currently uses standings.csv
