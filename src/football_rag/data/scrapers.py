"""Football data scrapers for WhoScored and other sources.
Migrated from working notebook implementations.
"""

import json
import time
import math
import ast
from typing import Dict, List, Any, Optional, Set

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from pydantic import BaseModel, Field, ValidationError


class MatchEvent(BaseModel):
    """Pydantic model for match event validation."""
    id: int
    event_id: int
    minute: int
    second: Optional[float] = None
    team_id: int
    player_id: int
    x: float
    y: float
    end_x: Optional[float] = None
    end_y: Optional[float] = None
    qualifiers: List[dict]
    is_touch: bool
    blocked_x: Optional[float] = None
    blocked_y: Optional[float] = None
    goal_mouth_z: Optional[float] = None
    goal_mouth_y: Optional[float] = None
    is_shot: bool
    card_type: bool
    is_goal: bool
    type_display_name: str
    outcome_type_display_name: str
    period_display_name: str


class WhoScoredScraper:
    """WhoScored.com data scraper using Selenium."""
    
    def __init__(self, headless: bool = True):
        self.base_url = "https://www.whoscored.com"
        self.rate_limit = 2.0  # seconds between requests
        self.headless = headless
        self.driver = None
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver - simple setup like notebook."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        return webdriver.Chrome(options=chrome_options)
    
    def get_eredivisie_match_urls(self, include_future: bool = False) -> List[str]:
        """Get Eredivisie match URLs from fixtures page."""
        if not self.driver:
            self.driver = self._setup_driver()
        
        # Current season URL
        fixtures_url = "https://www.whoscored.com/Regions/155/Tournaments/13/Seasons/10752/Stages/24542/Fixtures/Netherlands-Eredivisie-2025-2026"
        print(f"Loading fixtures page: {fixtures_url}")
        
        self.driver.get(fixtures_url)
        time.sleep(5)
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find all match links
        match_links = soup.find_all('a', {'class': 'Match-module_score__5Ghhj'})
        
        match_urls: Set[str] = set()
        
        for link in match_links:
            parent_div = link.find_parent('div', class_='Match-module_match__XlKTY')
            if parent_div:
                status_element = parent_div.find('span', class_=['Match-module_FT__2rmH7', 'Match-module_startTime_lineup__H1Krq'])
                
                if status_element:
                    status_text = status_element.get_text().strip()
                    
                    # Include completed matches (FT) and optionally future matches
                    if status_text == 'FT' or (include_future and ':' in status_text):
                        full_url = f"https://www.whoscored.com{link['href']}"
                        match_urls.add(full_url)
        
        result = list(match_urls)
        print(f"Found {len(result)} unique matches")
        return result
    
    def scrape_single_match(self, match_url: str) -> Optional[pd.DataFrame]:
        """Scrape a single match from WhoScored URL."""
        if not self.driver:
            self.driver = self._setup_driver()
        
        print(f"Scraping match: {match_url}")
        
        try:
            self.driver.get(match_url)
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
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
            
            # Add display names
            df['type_display_name'] = df['type'].apply(lambda x: x.get('displayName', '') if x else '')
            df['outcome_type_display_name'] = df['outcomeType'].apply(lambda x: x.get('displayName', '') if x else '')
            df['period_display_name'] = df['period'].apply(lambda x: x.get('displayName', '') if x else '')
            
            # Rename columns to match schema
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
            
            # Drop original columns
            df.drop(columns=["period", "type", "outcome_type"], inplace=True, errors='ignore')
            
            # Handle missing columns
            if 'is_goal' not in df.columns:
                df['is_goal'] = False
            if 'card_type' not in df.columns:
                df['card_type'] = False
            
            # Filter out offside events
            df = df[~(df['type_display_name'] == "OffsideGiven")]
            
            # Select and reorder columns
            columns = [
                'id', 'event_id', 'minute', 'second', 'team_id', 'player_id', 'x', 'y', 'end_x', 'end_y',
                'qualifiers', 'is_touch', 'blocked_x', 'blocked_y', 'goal_mouth_z', 'goal_mouth_y', 'is_shot',
                'card_type', 'is_goal', 'type_display_name', 'outcome_type_display_name', 'period_display_name'
            ]
            
            # Only keep columns that exist
            available_columns = [col for col in columns if col in df.columns]
            df = df[available_columns]
            
            # Convert data types
            int_columns = ['id', 'event_id', 'minute', 'team_id', 'player_id']
            float_columns = ['second', 'x', 'y', 'end_x', 'end_y']
            bool_columns = ['is_shot', 'is_goal', 'card_type']
            
            for col in int_columns:
                if col in df.columns:
                    df[col] = df[col].astype('int64')
            
            for col in float_columns:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].astype(bool)
                    df[col] = df[col].fillna(False)
            
            # Add match URL for reference
            df['match_url'] = match_url
            
            print(f"✅ Successfully scraped {len(df)} events")
            return df
            
        except Exception as e:
            print(f"❌ Error scraping {match_url}: {str(e)}")
            return None
    
    def scrape_all_eredivisie_matches(self, include_future: bool = False) -> Optional[pd.DataFrame]:
        """Scrape all available Eredivisie matches."""
        match_urls = self.get_eredivisie_match_urls(include_future=include_future)
        
        if not match_urls:
            print("❌ No match URLs found")
            return None
        
        all_match_data = []
        
        for i, url in enumerate(match_urls, 1):
            print(f"\nScraping match {i}/{len(match_urls)}")
            
            try:
                match_df = self.scrape_single_match(url)
                
                if match_df is not None:
                    all_match_data.append(match_df)
                
            except KeyboardInterrupt:
                print("\n⚠️ Scraping interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error scraping {url}: {str(e)}")
                continue
            
            # Rate limiting
            time.sleep(self.rate_limit)
        
        if all_match_data:
            combined_df = pd.concat(all_match_data, ignore_index=True)
            print(f"\n✅ Successfully scraped {len(all_match_data)} matches with {len(combined_df)} total events")
            return combined_df
        else:
            print("❌ No match data was scraped")
            return None
    
    def validate_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate events using Pydantic model."""
        validated_events = []
        
        for _, row in df.iterrows():
            try:
                event = MatchEvent(**row.to_dict())
                validated_events.append(event.model_dump())
            except ValidationError as e:
                print(f"Validation error: {e}")
        
        return pd.DataFrame(validated_events)
    
    def parse_qualifiers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse qualifiers from string to JSON-compatible format."""
        def to_jsonable(cell: Any) -> Any:
            if cell is None or (isinstance(cell, float) and (math.isnan(cell) or math.isinf(cell))):
                return None
            if isinstance(cell, str):
                try:
                    cell = ast.literal_eval(cell)
                except Exception:
                    return None
            
            def walk(x: Any) -> Any:
                if isinstance(x, dict):
                    return {k: (float(v) if k == "value" and isinstance(v, (int, float, str)) and str(v).replace('.','',1).isdigit() else walk(v))
                            for k, v in x.items()}
                if isinstance(x, list):
                    return [walk(v) for v in x]
                if isinstance(x, (np.floating,)):
                    return None if (np.isnan(x) or np.isinf(x)) else float(x)
                if isinstance(x, float):
                    return None if (math.isnan(x) or math.isinf(x)) else x
                return x
            return walk(cell)
        
        df = df.copy()
        df['qualifiers'] = df['qualifiers'].apply(to_jsonable)
        return df
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class FotmobScraper:
    """Fotmob.com data scraper with automated token generation."""
    
    def __init__(self):
        self.base_url = "https://www.fotmob.com"
        self.rate_limit = 1.0
        self.secret_key = """[Spoken Intro: Alan Hansen & Trevor Brooking]
I think it's bad news for the English game
We're not creative enough, and we're not positive enough

[Refrain: Ian Broudie & Jimmy Hill]
It's coming home, it's coming home, it's coming
Football's coming home (We'll go on getting bad results)
It's coming home, it's coming home, it's coming
Football's coming home
It's coming home, it's coming home, it's coming
Football's coming home
It's coming home, it's coming home, it's coming
Football's coming home

[Verse 1: Frank Skinner]
Everyone seems to know the score, they've seen it all before
They just know, they're so sure
That England's gonna throw it away, gonna blow it away
But I know they can play, 'cause I remember

[Chorus: All]
Three lions on a shirt
Jules Rimet still gleaming
Thirty years of hurt
Never stopped me dreaming

[Verse 2: David Baddiel]
So many jokes, so many sneers
But all those "Oh, so near"s wear you down through the years
But I still see that tackle by Moore and when Lineker scored
Bobby belting the ball, and Nobby dancing

[Chorus: All]
Three lions on a shirt
Jules Rimet still gleaming
Thirty years of hurt
Never stopped me dreaming

[Bridge]
England have done it, in the last minute of extra time!
What a save, Gordon Banks!
Good old England, England that couldn't play football!
England have got it in the bag!
I know that was then, but it could be again

[Refrain: Ian Broudie]
It's coming home, it's coming
Football's coming home
It's coming home, it's coming home, it's coming
Football's coming home
(England have done it!)
It's coming home, it's coming home, it's coming
Football's coming home
It's coming home, it's coming home, it's coming
Football's coming home
[Chorus: All]
(It's coming home) Three lions on a shirt
(It's coming home, it's coming) Jules Rimet still gleaming
(Football's coming home
It's coming home) Thirty years of hurt
(It's coming home, it's coming) Never stopped me dreaming
(Football's coming home
It's coming home) Three lions on a shirt
(It's coming home, it's coming) Jules Rimet still gleaming
(Football's coming home
It's coming home) Thirty years of hurt
(It's coming home, it's coming) Never stopped me dreaming
(Football's coming home
It's coming home) Three lions on a shirt
(It's coming home, it's coming) Jules Rimet still gleaming
(Football's coming home
It's coming home) Thirty years of hurt
(It's coming home, it's coming) Never stopped me dreaming
(Football's coming home)"""
    
    def _hash_string(self, text: str) -> str:
        """Hash function equivalent to JavaScript l(e) => o()(e).toUpperCase()"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest().upper()
    
    def _generate_signature(self, body_obj: Dict[str, Any], secret: str) -> str:
        """Generate signature: g(e,t) => l(`${JSON.stringify(e)}${t}`)"""
        body_str = json.dumps(body_obj, separators=(',', ':'))
        combined = body_str + secret
        return self._hash_string(combined)
    
    def _generate_fotmob_token(self, url: str, timestamp=None) -> str:
        """Generate complete x-mas token"""
        from datetime import datetime
        import base64
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create body object
        body = {
            "url": url,
            "code": int(timestamp.timestamp() * 1000),  # JavaScript getTime()
            "foo": "production:e590188e5cefd1927f5971700c5e8175db729285-undefined"
        }
        
        # Generate signature
        signature = self._generate_signature(body, self.secret_key)
        
        # Create final token
        token_obj = {"body": body, "signature": signature}
        token = base64.b64encode(
            json.dumps(token_obj, separators=(',', ':')).encode()
        ).decode()
        
        return token
    
    def scrape_shots(self, match_id: int) -> Optional[pd.DataFrame]:
        """Scrape shot data from Fotmob with automated token generation."""
        import requests
        
        # Generate the token automatically
        url = f"/api/data/matchDetails?matchId={match_id}"
        token = self._generate_fotmob_token(url)
        
        headers = {
            'referer': f'https://www.fotmob.com/matches/match/{match_id}',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'x-mas': token
        }

        params = {
            'matchId': match_id,
            'showNewUefaBracket': 'true'
        }

        try:
            response = requests.get('https://www.fotmob.com/api/matchDetails', params=params, headers=headers)
            
            print(f"Fotmob API Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
            data = response.json()
            shotmap = data['content']['shotmap']['shots']
            shots_df = pd.DataFrame(shotmap)
            shots_df['matchId'] = match_id
            
            print(f"✅ Successfully scraped {len(shots_df)} shots from Fotmob")
            return shots_df
            
        except Exception as e:
            print(f"❌ Error scraping Fotmob shots: {e}")
            return None
    
    def scrape_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Scrape full match details from Fotmob."""
        import requests
        
        url = f"/api/data/matchDetails?matchId={match_id}"
        token = self._generate_fotmob_token(url)
        
        headers = {
            'referer': f'https://www.fotmob.com/matches/match/{match_id}',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'x-mas': token
        }

        params = {
            'matchId': match_id,
            'showNewUefaBracket': 'true'
        }

        try:
            response = requests.get('https://www.fotmob.com/api/matchDetails', params=params, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Successfully scraped match details for {match_id}")
                return response.json()
            else:
                print(f"❌ Failed to scrape match details: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error scraping match details: {e}")
            return None