"""
Simple WhoScored scraper based on working notebook code.
"""

import json
import time
import pandas as pd
from pathlib import Path
from typing import Optional, List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

from .schemas import WhoScoredMatchEvent


def scrape_single_match(url: str, driver) -> Optional[pd.DataFrame]:
    """Scrape match events from a single WhoScored URL"""
    print(f"Scraping: {url}")
    
    driver.get(url)
    time.sleep(3)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    element = soup.select_one('script:-soup-contains("matchCentreData")')
    
    if not element:
        print("❌ matchCentreData not found")
        return None
    
    # Extract and parse match data
    match_data_raw = element.text.split("matchCentreData: ")[1].split(',\n')[0]
    matchdict = json.loads(match_data_raw)
    
    # Process events
    match_events = matchdict['events']
    df = pd.DataFrame(match_events)
    
    if df.empty:
        print("⚠️ No events found")
        return None
    
    # Clean and transform data
    df.dropna(subset='playerId', inplace=True)
    df = df.where(pd.notnull(df), None)
    
    # Rename columns
    df = df.rename({
        'eventId': 'event_id',
        'outcomeType': 'outcome_type',
        'isTouch': 'is_touch',
        'playerId': 'player_id',
        'teamId': 'team_id',
        'endX': 'end_x',
        'endY': 'end_y',
        'blockedX': 'blocked_x',
        'blockedY': 'blocked_y',
        'goalMouthZ': 'goal_mouth_z',
        'goalMouthY': 'goal_mouth_y',
        'isShot': 'is_shot',
        'cardType': 'card_type',
        'isGoal': 'is_goal'
    }, axis=1)
    
    # Add display names
    df['period_display_name'] = df['period'].apply(lambda x: x['displayName'])
    df['type_display_name'] = df['type'].apply(lambda x: x['displayName'])
    df['outcome_type_display_name'] = df['outcome_type'].apply(lambda x: x['displayName'])
    
    # Drop original columns
    df.drop(columns=["period", "type", "outcome_type"], inplace=True)
    
    # Handle missing columns
    if 'is_goal' not in df.columns:
        df['is_goal'] = False
    if 'card_type' not in df.columns:
        df['card_type'] = False
    
    # Filter and select columns
    df = df[~(df['type_display_name'] == "OffsideGiven")]
    
    df = df[[
        'id', 'event_id', 'minute', 'second', 'team_id', 'player_id', 'x', 'y', 'end_x', 'end_y',
        'qualifiers', 'is_touch', 'blocked_x', 'blocked_y', 'goal_mouth_z', 'goal_mouth_y', 'is_shot',
        'card_type', 'is_goal', 'type_display_name', 'outcome_type_display_name', 'period_display_name'
    ]]
    
    # Convert data types
    df[['id', 'event_id', 'minute', 'team_id', 'player_id']] = df[['id', 'event_id', 'minute', 'team_id', 'player_id']].astype('int64')
    df[['second', 'x', 'y', 'end_x', 'end_y']] = df[['second', 'x', 'y', 'end_x', 'end_y']].astype(float)
    df[['is_shot', 'is_goal', 'card_type']] = df[['is_shot', 'is_goal', 'card_type']].astype(bool)
    
    # Handle NaN values
    df['is_goal'] = df['is_goal'].fillna(False)
    df['is_shot'] = df['is_shot'].fillna(False)
    
    # Add match URL
    df['match_url'] = url
    
    # Validate with Pydantic
    validated_events = []
    for _, row in df.iterrows():
        try:
            event = WhoScoredMatchEvent(**row.to_dict())
            validated_events.append(event.model_dump())
        except Exception as e:
            print(f"Validation error: {e}")
    
    if validated_events:
        validated_df = pd.DataFrame(validated_events)
        print(f'✅ Successfully scraped {len(validated_df)} events')
        return validated_df
    else:
        print("❌ No valid events after validation")
        return None


def collect_all_season_matches(driver) -> List[str]:
    """Navigate through calendar to collect all season match URLs"""
    fixtures_url = "https://www.whoscored.com/Regions/155/Tournaments/13/Seasons/10752/Stages/24542/Fixtures/Netherlands-Eredivisie-2025-2026"
    driver.get(fixtures_url)
    time.sleep(5)
    
    all_match_urls = set()
    
    # Go back to August
    for i in range(15):
        try:
            prev_button = driver.find_element(By.ID, "dayChangeBtn-prev")
            prev_button.click()
            time.sleep(2)
        except:
            break
    
    # Go forward collecting all finished matches
    for period in range(30):
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        containers = soup.find_all('div', class_='Match-module_match__XlKTY')
        for container in containers:
            if container.find('span', class_='Match-module_FT__2rmH7'):
                score_link = container.find('a', class_='Match-module_score__5Ghhj')
                if score_link and score_link.get('href'):
                    match_url = f"https://www.whoscored.com{score_link['href']}"
                    all_match_urls.add(match_url)
        
        try:
            next_button = driver.find_element(By.ID, "dayChangeBtn-next")
            next_button.click()
            time.sleep(2)
        except:
            break
    
    return list(all_match_urls)


def scrape_complete_season():
    """Main function to scrape complete season"""
    driver = webdriver.Chrome()
    
    try:
        print("Collecting all match URLs...")
        all_match_urls = collect_all_season_matches(driver)
        print(f"Found {len(all_match_urls)} finished matches")
        
        if not all_match_urls:
            print("No matches found")
            return None
        
        print("Scraping match data...")
        all_match_data = []
        
        for i, url in enumerate(all_match_urls, 1):
            print(f"Scraping match {i}/{len(all_match_urls)}")
            
            try:
                match_df = scrape_single_match(url, driver)
                if match_df is not None:
                    all_match_data.append(match_df)
            except Exception as e:
                print(f"Error scraping {url}: {str(e)}")
                continue
            
            time.sleep(2)
        
        if all_match_data:
            combined_df = pd.concat(all_match_data, ignore_index=True)
            print(f"✅ Successfully scraped {len(all_match_data)} matches with {len(combined_df)} total events")
            return combined_df
        else:
            print("No match data was scraped")
            return None
    
    finally:
        driver.quit()


def save_to_minio(df: pd.DataFrame, filename: str):
    """Save dataframe to MinIO bucket"""
    try:
        import boto3
        from botocore.client import Config
        
        # MinIO client configuration
        minio_client = boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin',
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        
        # Create bucket if it doesn't exist
        bucket_name = 'football-data'
        try:
            minio_client.head_bucket(Bucket=bucket_name)
        except:
            minio_client.create_bucket(Bucket=bucket_name)
            print(f"Created bucket: {bucket_name}")
        
        # Save CSV to MinIO
        csv_buffer = df.to_csv(index=False)
        minio_client.put_object(
            Bucket=bucket_name,
            Key=f"raw/{filename}",
            Body=csv_buffer.encode('utf-8'),
            ContentType='text/csv'
        )
        
        print(f"✅ Saved to MinIO: s3://{bucket_name}/raw/{filename}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to save to MinIO: {e}")
        return False


if __name__ == "__main__":
    season_data = scrape_complete_season()
    
    if season_data is not None:
        # Ensure data directory exists
        Path("data/raw").mkdir(parents=True, exist_ok=True)
        
        # Save to local CSV
        local_file = 'data/raw/eredivisie_2025_2026_whoscored.csv'
        season_data.to_csv(local_file, index=False)
        print(f"✅ Saved locally: {local_file}")
        
        # Save to MinIO
        save_to_minio(season_data, 'eredivisie_2025_2026_whoscored.csv')