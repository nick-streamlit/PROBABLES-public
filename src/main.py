from turtle import pd, st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import json
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


# Define the base directory (project_root) relative to the current script location
# Go up one level from 'src' to 'project_root'
project_root = Path(__file__).parent.parent

# Define the path to the 'input' data folder
input_folder = project_root / 'data' / 'input'
processed_folder = project_root / 'data' / 'processed'
output_folder = project_root / 'outputs'


def convert_utc_to_et_12hr(utc_time_str: str) -> str:
    """
    Convert UTC time string to 12-hour Eastern Time format.
    
    Args:
        utc_time_str: Time string in format like "2026-03-28T18:15:00Z"
        
    Returns:
        12-hour format time string like "2:15 PM"
    """
    try:
        # Parse the UTC time
        utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        
        # Convert to Eastern Time (UTC-4 EDT or UTC-5 EST)
        # For simplicity, we'll use offset based on month
        # March 28, 2026 is in EDT (UTC-4)
        et_offset = -4  # EDT
        if utc_dt.month in [11, 12, 1, 2]:
            et_offset = -5  # EST
        
        et_tz = timezone(timedelta(hours=et_offset))
        et_dt = utc_dt.astimezone(et_tz)
        
        # Format as 12-hour format with AM/PM
        return et_dt.strftime("%-I:%M %p")
    except Exception:
        return "TBD"


def load_target_pitchers(csv_file: str = f"{input_folder}/roster.csv") -> List[str]:
    """
    Load target pitcher names from a CSV file.
    
    Args:
        csv_file: Path to the CSV file with pitcher names
        
    Returns:
        List of pitcher names
    """
    pitchers = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('pitcher_name'):
                    pitchers.append(row['pitcher_name'].strip())
    except FileNotFoundError:
        print(f"Warning: {csv_file} not found. Using empty pitcher list.")
    
    return pitchers


def get_game_pitchers(game) -> dict:
    """
    Fetch probable pitcher information from individual game live feed endpoint.
    
    Args:
        game: Game object from schedule endpoint
        
    Returns:
        Dictionary with pitcher information or None if not available
    """
    game_pk = game.get("gamePk")
    if not game_pk:
        return None
    
    try:
        live_url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        response = requests.get(live_url, timeout=5)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # Get probable pitchers from gameData
        probable_pitchers = data.get("gameData", {}).get("probablePitchers", {})
        
        away_pitcher_name = probable_pitchers.get("away", {}).get("fullName")
        home_pitcher_name = probable_pitchers.get("home", {}).get("fullName")
        
        return {
            "away_pitcher": away_pitcher_name,
            "home_pitcher": home_pitcher_name
        }
    except Exception as e:
        # Silently fail for individual games
        return None


def get_probable_pitchers(days_ahead: int = 7) -> dict:
    """
    Fetch probable pitchers for the next N days from MLB Stats API.
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
    
    Returns:
        Dictionary with games organized by date
    """
    base_url = "https://statsapi.mlb.com/api/v1"
    
    # Calculate date range
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=days_ahead)
    
    # Format dates for API (YYYY-MM-DD)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # Fetch schedule using the game endpoint which returns dates list
    schedule_url = f"{base_url}/schedule?startDate={start_str}&endDate={end_str}&sportId=1"
    
    try:
        response = requests.get(schedule_url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching MLB schedule: {e}")
        return {}
    
    # Parse probable pitchers by date
    pitchers_by_date = {}
    
    # The API returns a dict with a 'dates' key containing a list of date objects
    if not isinstance(data, dict) or "dates" not in data:
        print("Unexpected API response format")
        return {}
    
    dates = data.get("dates", [])
    
    # Collect all games
    all_games = []
    for date_obj in dates:
        if not isinstance(date_obj, dict):
            continue
            
        date_str = date_obj.get("date", "")
        games = date_obj.get("games", [])
        
        if not date_str or not games:
            continue
        
        for game in games:
            all_games.append((date_str, game))
    
    # Fetch pitcher data for all games in parallel
    print(f"Fetching pitcher data for {len(all_games)} games...")
    pitcher_data = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all game requests
        future_to_game = {executor.submit(get_game_pitchers, game): (date_str, game) 
                         for date_str, game in all_games}
        
        # Process results as they complete
        for future in as_completed(future_to_game):
            date_str, game = future_to_game[future]
            try:
                result = future.result()
                game_pk = game.get("gamePk")
                if result:
                    pitcher_data[game_pk] = result
            except Exception:
                pass
    
    # Build final data structure
    for date_str, game in all_games:
        if date_str not in pitchers_by_date:
            pitchers_by_date[date_str] = []
        
        # Extract team information
        teams = game.get("teams", {})
        away_data = teams.get("away", {})
        home_data = teams.get("home", {})
        
        away_team = away_data.get("team", {})
        home_team = home_data.get("team", {})
        
        away_name = away_team.get("name", "Unknown")
        home_name = home_team.get("name", "Unknown")
        
        # Get pitcher data from our fetched info
        game_pk = game.get("gamePk")
        pitcher_info = pitcher_data.get(game_pk, {})
        away_pitcher_name = pitcher_info.get("away_pitcher", "TBD")
        home_pitcher_name = pitcher_info.get("home_pitcher", "TBD")
        
        # Extract game time and convert to ET 12-hour format
        game_date = game.get("gameDate", "")
        game_time = convert_utc_to_et_12hr(game_date) if game_date else "TBD"
        
        pitchers_by_date[date_str].append({
            "time": game_time,
            "matchup": f"{away_name} @ {home_name}",
            "away_team": away_name,
            "home_team": home_name,
            "away_pitcher": away_pitcher_name,
            "home_pitcher": home_pitcher_name,
            "status": game.get("status", "Scheduled")
        })
    
    return pitchers_by_date


def display_pitchers(pitchers_by_date: dict) -> None:
    """
    Display probable pitchers in a readable format.
    
    Args:
        pitchers_by_date: Dictionary with games organized by date
    """
    if not pitchers_by_date:
        print("No games found for the next 7 days.")
        return
    
    print("\n" + "="*80)
    print("MLB PROBABLE PITCHERS - NEXT 7 DAYS")
    print("="*80 + "\n")
    
    for date in sorted(pitchers_by_date.keys()):
        try:
            # Format date nicely
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            day_name = date_obj.strftime("%A")
            formatted_date = date_obj.strftime("%B %d, %Y")
            
            print(f"\n{day_name.upper()} - {formatted_date}")
            print("-" * 80)
            
            games = pitchers_by_date[date]
            for game in sorted(games, key=lambda x: x.get("time", "00:00")):
                print(f"\n  {game['time']} - {game['matchup']}")
                print(f"    {game['away_team']:15} | {game['away_pitcher']}")
                print(f"    {game['home_team']:15} | {game['home_pitcher']}")
        except (ValueError, KeyError) as e:
            print(f"Error parsing date {date}: {e}")
            continue
    
    print("\n" + "="*80 + "\n")


def export_to_json(export_data: dict, filename: str = None) -> None:
    """
    Export probable pitchers to a JSON file.
    
    Args:
        export_data: Dictionary with data to export
        filename: Output filename
    """
    if filename is None:
        filename = f"{processed_folder}/none.json"
    else:
        filename = f"{processed_folder}/{filename}.json"
    with open(filename, "w") as f:
        json.dump(export_data, f, indent=2)
    print(f"Data exported to {filename}")


def filter_target_pitchers(pitchers_by_date: dict, target_pitchers: List[str]) -> List[dict]:
    """
    Filter games to only show those with target pitchers.
    
    Args:
        pitchers_by_date: Dictionary with games organized by date
        target_pitchers: List of pitcher names to find
        
    Returns:
        List of filtered games with target pitchers
    """
    filtered_games = []
    
    for date in sorted(pitchers_by_date.keys()):
        for game in pitchers_by_date[date]:
            away_pitcher = game.get("away_pitcher", "")
            home_pitcher = game.get("home_pitcher", "")
            
            # Check if either pitcher is in target list (case-insensitive)
            if any(away_pitcher and target.lower() in away_pitcher.lower() for target in target_pitchers) or \
               any(home_pitcher and target.lower() in home_pitcher.lower() for target in target_pitchers):
                filtered_games.append({
                    "date": date,
                    **game
                })
    
    return filtered_games


def display_target_pitchers_table(filtered_games: List[dict]) -> None:
    """
    Display filtered games in a simple table format.
    
    Args:
        filtered_games: List of games containing target pitchers
    """
    if not filtered_games:
        print("\nNo games found with bovine pitchers.\n")
        return
    
    print("\n" + "="*120)
    print("BOVINE PITCHERS - UPCOMING MATCHUPS")
    print("="*120)
    print(f"\n{'Date':<12} {'Day':<9} {'Time':<9} {'Away Team':<25} {'Pitcher':<17} {'Home Team':<25} {'Pitcher':<17}")
    print("-" * 120)
    
    for game in sorted(filtered_games, key=lambda x: x.get("date", "")):
        date = game.get("date", "")
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            day_name = date_obj.strftime("%a")
        except:
            day_name = "TBD"
        time = game.get("time", "TBD")
        away_team = (game.get("away_team", "") or "")[:24]
        home_team = (game.get("home_team", "") or "")[:24]
        away_pitcher = (game.get("away_pitcher") or "TBD")[:16] if game.get("away_pitcher") else "TBD"
        home_pitcher = (game.get("home_pitcher") or "TBD")[:16] if game.get("home_pitcher") else "TBD"
        
        print(f"{date:<12} {day_name:<9} {time:<9} {away_team:<25} {away_pitcher:<17} {home_team:<25} {home_pitcher:<17}")
    
    print("\n" + "="*120 + "\n")


def save_table_as_image(filtered_games: List[dict], filename: str = f"{output_folder}/bovine_pitchers_table.png") -> None:
    """
    Save the target pitchers table as an image.
    
    Args:
        filtered_games: List of games containing target pitchers
        filename: Output image filename
    """
    if not filtered_games:
        print("No games to save to image.")
        return
    
    # Image settings
    img_width = 1400
    padding = 20
    line_height = 30
    header_height = 40
    
    # Calculate image height
    num_rows = len(filtered_games) + 2  # +2 for title and header
    img_height = padding * 2 + header_height + (num_rows * line_height) + 20
    
    # Create image
    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default if not available
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        header_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
        text_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    y = padding
    
    # Draw title
    title = "BOVINE PITCHERS - UPCOMING MATCHUPS"
    draw.text((padding, y), title, fill='black', font=title_font)
    y += header_height
    
    # Draw header row
    header = f"{'Date':<12} {'Day':<8} {'Time':<9} {'Away Team':<25} {'Pitcher':<17} {'Home Team':<25} {'Pitcher':<17}"
    draw.text((padding, y), header, fill='#333333', font=header_font)
    y += line_height
    
    # Draw separator
    draw.line([(padding, y), (img_width - padding, y)], fill='#cccccc', width=1)
    y += 10
    
    # Draw data rows
    for game in sorted(filtered_games, key=lambda x: x.get("date", "")):
        date = game.get("date", "")[:12]
        date_str = game.get("date", "")
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = date_obj.strftime("%a")
        except:
            day_name = "TBD"
        time = game.get("time", "TBD")[:9]
        away_team = (game.get("away_team", "") or "")[:24]
        home_team = (game.get("home_team", "") or "")[:24]
        away_pitcher = (game.get("away_pitcher") or "TBD")[:16] if game.get("away_pitcher") else "TBD"
        home_pitcher = (game.get("home_pitcher") or "TBD")[:16] if game.get("home_pitcher") else "TBD"
        
        row = f"{date:<12} {day_name:<8} {time:<9} {away_team:<25} {away_pitcher:<17} {home_team:<25} {home_pitcher:<17}"
        draw.text((padding, y), row, fill='black', font=text_font)
        y += line_height
    
    # Save image
    img.save(filename)
    print(f"Table saved as image: {filename}")


def main():
    """Main function to fetch and display probable pitchers."""
    print("Fetching MLB probable pitchers for the next 7 days...")
    
    # Load target pitchers from CSV
    target_pitchers = load_target_pitchers()
    
    pitchers_by_date = get_probable_pitchers(days_ahead=7)
    display_pitchers(pitchers_by_date)
    
    # Display filtered table for target pitchers
    filtered_games = filter_target_pitchers(pitchers_by_date, target_pitchers)
    display_target_pitchers_table(filtered_games)
    save_table_as_image(filtered_games)
    
    # Optionally export to JSON
    export_to_json(filtered_games, "probable_pitchers")

if __name__ == "__main__":
    main()
