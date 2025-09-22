import json
import time
import math
import ast
from typing import Dict, List, Any, Optional

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


if __name__ == "__main__":
    """
    Direct execution of scrapers for testing.
    Run with: uv run python -m football_rag.data.fotmob
    """
    print("🚀 Fotmbob Scraper - Direct Test Run")
    print("=" * 50)
    
    # Test Fotmob scraper
    print("\n\n2️⃣ Testing Fotmob scraper...")
    
    fotmob = FotmobScraper()
    test_match_id = 4825080  # Test match
    
    print(f"🔍 Testing shot data scraping for match {test_match_id}...")
    shots_df = fotmob.scrape_shots(test_match_id)
    
    if shots_df is not None:
        print(f"✅ Successfully scraped {len(shots_df)} shots")
        if len(shots_df) > 0:
            print(f"🎯 Teams involved: {shots_df['teamId'].unique()}")
    else:
        print("❌ Failed to scrape shot data")
    
    print("\n" + "=" * 50)
    print("🎉 Scraper testing complete!")
    print("\nNext steps:")
    print("• Run 'make test-scrapers' for full validation")
    print("• Analyze Eredivisie HTML structure for multi-match scraping") 
    print("• Set up MinIO storage integration")