import feedparser
import re
import requests
from datetime import datetime, timezone
from typing import Iterable

CHANNEL_ID_REGEX = re.compile(r'^UC[\w-]{22}$')

def channel_feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def get_channel_id(url_or_id: str) -> dict:
    """
    Resolve a YouTube URL or handle to a canonical Channel ID.
    
    Supports:
    - Direct Channel ID (UC...)
    - youtube.com/channel/UC...
    - youtube.com/@handle
    - youtube.com/watch?v=VIDEO_ID
    - youtube.com/c/custom_name
    - youtube.com/user/username
    
    Returns: {"channel_id": str | None, "name": str | None, "error": str | None}
    """
    url_or_id = url_or_id.strip()
    
    # Already a channel ID
    if CHANNEL_ID_REGEX.match(url_or_id):
        return {"channel_id": url_or_id, "name": None, "error": None}
    
    # Extract from direct channel URL
    direct_match = re.search(r'youtube\.com/channel/(UC[\w-]{22})', url_or_id)
    if direct_match:
        return {"channel_id": direct_match.group(1), "name": None, "error": None}
    
    # For other URLs (@handle, /watch, /c/, /user/), we need to fetch and parse
    target_url = url_or_id
    
    # Normalize URL
    if not target_url.startswith('http'):
        if target_url.startswith('@'):
            target_url = f"https://www.youtube.com/{target_url}"
        else:
            target_url = f"https://www.youtube.com/{target_url}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        resp = requests.get(target_url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        html = resp.text
        
        # Look for channel ID in meta tags or embedded data
        # Pattern 1: <meta itemprop="channelId" content="UC...">
        meta_match = re.search(r'<meta\s+itemprop="channelId"\s+content="(UC[\w-]{22})"', html)
        if meta_match:
            channel_id = meta_match.group(1)
            # Try to get channel name
            name_match = re.search(r'"author":"([^"]+)"', html)
            name = name_match.group(1) if name_match else None
            return {"channel_id": channel_id, "name": name, "error": None}
        
        # Pattern 2: "channelId":"UC..." in JSON data
        json_match = re.search(r'"channelId":"(UC[\w-]{22})"', html)
        if json_match:
            channel_id = json_match.group(1)
            name_match = re.search(r'"author":"([^"]+)"', html)
            name = name_match.group(1) if name_match else None
            return {"channel_id": channel_id, "name": name, "error": None}
        
        # Pattern 3: /channel/UC... in canonical URL
        canonical_match = re.search(r'/channel/(UC[\w-]{22})', html)
        if canonical_match:
            channel_id = canonical_match.group(1)
            return {"channel_id": channel_id, "name": None, "error": None}
        
        return {"channel_id": None, "name": None, "error": "Could not find channel ID in page"}
        
    except requests.RequestException as e:
        return {"channel_id": None, "name": None, "error": f"Failed to fetch URL: {str(e)}"}

def parse_feed(feed_url: str) -> Iterable[dict]:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        yield {
            "youtube_video_id": getattr(entry, "yt_videoid", None),
            "title": getattr(entry, "title", "Untitled"),
            "published_at": _parse_datetime(getattr(entry, "published", None)),
        }

def _parse_datetime(s: str | None) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)
