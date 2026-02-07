
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from football_rag.data.whoscored_scraper import collect_all_season_matches, extract_match_id

@pytest.mark.asyncio
async def test_collect_all_season_matches_limit():
    """Test that the collector respects the limit argument."""
    
    # Mock page object
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.content = AsyncMock()
    
    # Mock HTML content with 5 matches
    html_content = """
    <html>
        <body>
            <div class="Match-module_match__XlKTY">
                <span class="Match-module_FT__2rmH7">FT</span>
                <a class="Match-module_score__5Ghhj" href="/Matches/1/Match-1">0-0</a>
            </div>
            <div class="Match-module_match__XlKTY">
                <span class="Match-module_FT__2rmH7">FT</span>
                <a class="Match-module_score__5Ghhj" href="/Matches/2/Match-2">1-1</a>
            </div>
             <div class="Match-module_match__XlKTY">
                <span class="Match-module_FT__2rmH7">FT</span>
                <a class="Match-module_score__5Ghhj" href="/Matches/3/Match-3">2-2</a>
            </div>
        </body>
    </html>
    """
    mock_page.content.return_value = html_content
    
    # Mock locator for navigation buttons (make them invisible effectively to stop loop)
    mock_locator = AsyncMock()
    mock_locator.is_visible.return_value = False
    mock_page.locator.return_value = mock_locator

    # Test with limit=2
    # We expect it to find 3 matches on page but slice to 2
    result = await collect_all_season_matches(mock_page, limit=2)
    
    assert len(result) == 2
    assert "https://www.whoscored.com/Matches/1/Match-1" in result
    assert "https://www.whoscored.com/Matches/2/Match-2" in result

@pytest.mark.asyncio
async def test_collect_all_season_matches_no_limit():
    """Test that the collector returns all matches when no limit is set."""
    
    mock_page = AsyncMock()
    mock_page.content.return_value = """
    <html>
        <body>
            <div class="Match-module_match__XlKTY">
                <span class="Match-module_FT__2rmH7">FT</span>
                <a class="Match-module_score__5Ghhj" href="/Matches/1/Match-1">0-0</a>
            </div>
        </body>
    </html>
    """
    mock_locator = AsyncMock()
    mock_locator.is_visible.return_value = False
    mock_page.locator.return_value = mock_locator

    result = await collect_all_season_matches(mock_page, limit=None)
    assert len(result) == 1

def test_extract_match_id():
    url = "https://www.whoscored.com/Matches/123456/Live/Netherlands-Eredivisie-2023-2024-Team-A-vs-Team-B"
    assert extract_match_id(url) == "123456"

    with pytest.raises(ValueError):
        extract_match_id("https://www.whoscored.com/Invalid/Url")
