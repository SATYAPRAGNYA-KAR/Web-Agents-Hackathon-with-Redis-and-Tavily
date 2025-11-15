# agent/tools/news_tools.py
import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from tavily import TavilyClient
from langchain.tools import tool
from .geo_utils import distance_km, geo_decay_weight
from dotenv import load_dotenv
import redis

# Load environment variables FIRST
load_dotenv()

# Initialize Tavily client
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
if not TAVILY_API_KEY:
    print('Warning: TAVILY_API_KEY not set')
else:
    print(f'✓ Tavily API Key loaded successfully')

tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

# Initialize Redis client
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
    redis_client.ping()
    print(f'✓ Redis connected successfully at {REDIS_HOST}:{REDIS_PORT}')
except Exception as e:
    print(f'Warning: Redis connection failed: {e}')
    redis_client = None

# Stock exchanges with their locations and major indices
STOCK_EXCHANGES = {
    "NYSE": {
        "name": "New York Stock Exchange",
        "location": (40.7128, -74.0060),
        "city": "New York",
        "country": "USA",
        "indices": ["S&P 500", "Dow Jones", "NYSE Composite"],
        "major_sectors": ["Technology", "Finance", "Healthcare", "Energy"]
    },
    "NASDAQ": {
        "name": "NASDAQ",
        "location": (40.7128, -74.0060),
        "city": "New York",
        "country": "USA",
        "indices": ["NASDAQ Composite", "NASDAQ-100"],
        "major_sectors": ["Technology", "Biotech", "Internet"]
    },
    "LSE": {
        "name": "London Stock Exchange",
        "location": (51.5074, -0.1278),
        "city": "London",
        "country": "UK",
        "indices": ["FTSE 100", "FTSE 250"],
        "major_sectors": ["Finance", "Oil & Gas", "Mining", "Pharmaceuticals"]
    },
    "TSE": {
        "name": "Tokyo Stock Exchange",
        "location": (35.6762, 139.6503),
        "city": "Tokyo",
        "country": "Japan",
        "indices": ["Nikkei 225", "TOPIX"],
        "major_sectors": ["Automotive", "Electronics", "Finance"]
    },
    "SSE": {
        "name": "Shanghai Stock Exchange",
        "location": (31.2304, 121.4737),
        "city": "Shanghai",
        "country": "China",
        "indices": ["SSE Composite", "SSE 50"],
        "major_sectors": ["Finance", "Real Estate", "Manufacturing"]
    },
    "BSE": {
        "name": "Bombay Stock Exchange",
        "location": (18.9294, 72.8310),
        "city": "Mumbai",
        "country": "India",
        "indices": ["BSE Sensex", "BSE 500"],
        "major_sectors": ["IT Services", "Banking", "Pharmaceuticals"]
    },
    "HKEX": {
        "name": "Hong Kong Stock Exchange",
        "location": (22.3193, 114.1694),
        "city": "Hong Kong",
        "country": "Hong Kong",
        "indices": ["Hang Seng", "Hang Seng Tech"],
        "major_sectors": ["Finance", "Real Estate", "Technology"]
    },
    "FSE": {
        "name": "Frankfurt Stock Exchange",
        "location": (50.1109, 8.6821),
        "city": "Frankfurt",
        "country": "Germany",
        "indices": ["DAX", "MDAX"],
        "major_sectors": ["Automotive", "Finance", "Chemicals"]
    }
}

# Broader search queries for correlation-based analysis
# MARKET_IMPACT_QUERIES = [
#     "economic crisis global markets",
#     "central bank interest rate decision",
#     "geopolitical tensions trade impact",
#     "inflation data consumer spending",
#     "corporate earnings technology sector",
#     "supply chain disruption manufacturing",
#     "energy prices oil gas",
#     "regulatory changes financial sector",
#     "merger acquisition major companies",
#     "unemployment data labor market"
# ]
MARKET_IMPACT_QUERIES = [
    # Natural disasters / weather shocks
    "natural disaster economic disruption",
    "hurricane impact supply chains",
    "extreme weather affecting agriculture production",
    "drought effects on commodity prices",

    # Geopolitical shifts (non-financial phrasing)
    "geopolitical tensions international relations",
    "military conflict escalation analysis",
    "trade negotiations government policy update",
    "sanctions global impact industries",

    # Tech & regulation (indirect)
    "technology regulation government policy",
    "data privacy law impact on tech companies",
    "AI regulation industry response",

    # Energy & commodities (indirect)
    "energy grid outage industrial impact",
    "oil supply disruption shipping delays",
    "rare earth mineral shortage manufacturing",

    # Labor markets (indirect)
    "worker strike manufacturing delays",
    "labor shortage industry analysis",

    # Macro society events
    "public health policy update economic activity",
    "major infrastructure failure impact transportation",

    # Corporate signals (indirect)
    "large layoffs impact consumer spending",
    "major cyber attack on corporations security breach",
]

# Global exchange & financial-news keywords that indicate "obvious" market bulletins
MARKET_BULLETIN_KEYWORDS = [
    # US
    "dow jones", "nasdaq", "s&p", "s&p500", "sp500", "nyse",
    
    # Europe
    "ftse", "cac 40", "cac40", "dax", "euro stoxx", "stoxx 600",

    # Asia
    "nikkei", "topix", "hang seng", "hsi", "kospi", "shanghai composite",
    "sensex", "nifty 50", "nifty50", "taipei exchange",

    # Middle East
    "tadawul", "adx", "dfm",

    # Americas
    "bovespa", "tsx", "s&p tsx", "mexbol",

    # Global "market movement" keywords
    "market close",
    "index rises",
    "index falls",
    "stocks rally",
    "stocks surge",
    "stocks tumble",
    "share price",
    "market opens",
    "pre-market trading",
    "after-hours trading",
    "closing bell",
]

def _generate_cache_key(query_type: str, params: Dict) -> str:
    """Generate a unique cache key for the query."""
    param_str = json.dumps(params, sort_keys=True)
    hash_obj = hashlib.md5(param_str.encode())
    return f"news_query:{query_type}:{hash_obj.hexdigest()}"

def _get_cached_result(cache_key: str) -> Optional[Dict]:
    """Retrieve cached result from Redis."""
    if not redis_client:
        return None
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            print(f"✓ Cache hit for {cache_key}")
            return json.loads(cached)
    except Exception as e:
        print(f"Redis get error: {e}")
    
    return None

def _set_cached_result(cache_key: str, data: Dict, ttl: int = 3600):
    """Store result in Redis with TTL (default 1 hour)."""
    if not redis_client:
        return
    
    try:
        redis_client.setex(
            cache_key,
            ttl,
            json.dumps(data)
        )
        print(f"✓ Cached result for {cache_key}")
    except Exception as e:
        print(f"Redis set error: {e}")

def _save_query_to_history(query_id: str, query_data: Dict):
    """Save query to user's history in Redis."""
    if not redis_client:
        return
    
    try:
        # Store individual query
        redis_client.setex(
            f"query_history:{query_id}",
            86400 * 7,  # 7 days TTL
            json.dumps(query_data)
        )
        
        # Add to sorted set for ordering (score = timestamp)
        redis_client.zadd(
            "query_history_index",
            {query_id: datetime.now().timestamp()}
        )
        
        # Keep only last 50 queries
        redis_client.zremrangebyrank("query_history_index", 0, -51)
        
        print(f"✓ Saved query {query_id} to history")
    except Exception as e:
        print(f"Redis history save error: {e}")

def _analyze_market_impact(news_item: Dict, exchange_info: Dict) -> Dict:
    """
    Analyze how a news item might impact the market.
    Returns reasoning and predicted impact direction.
    """
    title = news_item.get("title", "").lower()
    snippet = news_item.get("snippet", "").lower()
    text = f"{title} {snippet}"
    
    # Impact indicators
    positive_indicators = [
        "growth", "profit", "increase", "rise", "gain", "success", "breakthrough",
        "recovery", "expansion", "boost", "strong earnings", "beat expectations",
        "innovation", "deal", "merger", "acquisition", "investment"
    ]
    
    negative_indicators = [
        "crisis", "recession", "decline", "fall", "loss", "layoff", "bankruptcy",
        "investigation", "lawsuit", "scandal", "miss expectations", "downgrade",
        "conflict", "tension", "disruption", "shortage", "inflation"
    ]
    
    # Economic indicators that affect markets
    macro_indicators = {
        "interest rate hike": {
            "impact": "negative",
            "reason": "Higher interest rates increase borrowing costs and can slow economic growth"
        },
        "interest rate cut": {
            "impact": "positive",
            "reason": "Lower interest rates stimulate economic activity and make stocks more attractive"
        },
        "inflation rise": {
            "impact": "negative",
            "reason": "Rising inflation erodes purchasing power and may lead to tighter monetary policy"
        },
        "unemployment fall": {
            "impact": "positive",
            "reason": "Lower unemployment indicates economic strength and consumer spending power"
        },
        "trade war": {
            "impact": "negative",
            "reason": "Trade tensions disrupt supply chains and reduce international commerce"
        },
        "economic stimulus": {
            "impact": "positive",
            "reason": "Government stimulus packages inject liquidity and boost economic activity"
        },
        "supply chain": {
            "impact": "negative",
            "reason": "Supply chain disruptions increase costs and reduce profit margins"
        },
        "geopolitical tension": {
            "impact": "negative",
            "reason": "Geopolitical uncertainty increases market volatility and risk aversion"
        },
        "natural disaster": {
            "impact": "negative",
            "reason": "Disasters disrupt logistics, agriculture, and insurance sectors, which can ripple into broader markets."
        },
        "supply chain delay": {
            "impact": "negative",
            "reason": "Delays in global shipping increase costs and reduce corporate margins."
        },
        "government regulation": {
            "impact": "negative",
            "reason": "Regulatory tightening increases compliance costs and constrains business flexibility."
        },
        "cyber attack": {
            "impact": "negative",
            "reason": "Cyber breaches increase operational risk and can destabilize investor confidence."
        },
        "large layoffs": {
            "impact": "negative",
            "reason": "Mass layoffs signal corporate distress and reduce consumer spending."
        },
        "labor strike": {
            "impact": "negative",
            "reason": "Strikes halt production and disrupt supply chains."
        },
        "heatwave": {
            "impact": "negative",
            "reason": "Extreme heat affects agriculture, energy demand, and worker productivity."
        },

    }
    
    # Analyze text for indicators
    positive_count = sum(1 for indicator in positive_indicators if indicator in text)
    negative_count = sum(1 for indicator in negative_indicators if indicator in text)
    
    # Check for macro indicators
    macro_impact = None
    macro_reason = None
    for indicator, details in macro_indicators.items():
        if indicator in text:
            macro_impact = details["impact"]
            macro_reason = details["reason"]
            break
    
    # Determine overall impact
    if macro_impact:
        predicted_impact = macro_impact
        reasoning = macro_reason
        confidence = "high"
    elif positive_count > negative_count:
        predicted_impact = "positive"
        reasoning = f"News contains positive market indicators suggesting growth and stability for {exchange_info['name']}"
        confidence = "medium"
    elif negative_count > positive_count:
        predicted_impact = "negative"
        reasoning = f"News contains negative market indicators that may cause uncertainty and selling pressure in {exchange_info['name']}"
        confidence = "medium"
    else:
        predicted_impact = "neutral"
        reasoning = "News appears to have mixed or neutral impact on market sentiment"
        confidence = "low"
    
    # Sector-specific analysis
    affected_sectors = []
    for sector in exchange_info.get("major_sectors", []):
        if sector.lower() in text:
            affected_sectors.append(sector)
    
    return {
        "predicted_impact": predicted_impact,
        "reasoning": reasoning,
        "confidence": confidence,
        "affected_sectors": affected_sectors,
        "positive_signals": positive_count,
        "negative_signals": negative_count
    }

def _fetch_news_from_tavily(queries: List[str], max_results: int, days: int) -> List[Dict]:
    """Fetch news from Tavily for multiple queries."""
    if not tavily:
        return [{"error": "Tavily client not initialized"}]
    
    all_results = []
    seen_urls = set()
    
    print(f"📰 Fetching news from last {days} day(s)...")
    
    for query in queries:
        try:
            print(f"  → Searching: {query}")
            response = tavily.search(
                query=query,
                max_results=max_results // len(queries),
                days=days,  # This ensures only recent news
            )
            
            results = response.get('results', []) if isinstance(response, dict) else response
            print(f"    ✓ Found {len(results)} results for '{query}'")
            
            for r in results:
                url = r.get("url", "")
                # Deduplicate by URL
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
                    
        except Exception as e:
            print(f"Tavily search error for '{query}': {e}")
            continue
    
    print(f"📊 Total unique news items: {len(all_results)}")
    return all_results

def _get_market_news_impl(
    lat: float,
    lon: float,
    radius_km: Optional[int] = 1500,
    index: Optional[str] = "SP500",
    days: int = 1,
    max_results: int = 20,
    query_mode: str = "location_based"
) -> List[Dict[str, Any]]:
    """
    Core implementation of market news fetching with Redis caching.
    """
    # Generate cache key
    cache_params = {
        "lat": round(lat, 2),
        "lon": round(lon, 2),
        "radius_km": radius_km,
        "index": index,
        "days": days,
        "mode": query_mode
    }
    cache_key = _generate_cache_key("market_news", cache_params)
    
    # Check cache
    cached_result = _get_cached_result(cache_key)
    if cached_result:
        return cached_result.get("data", [])
    
    if tavily is None:
        return [{"error": "TAVILY_API_KEY not set on server"}]
    
    # Find nearest stock exchanges
    user_location = (lat, lon)
    exchange_distances = []
    
    for exchange_id, exchange_data in STOCK_EXCHANGES.items():
        dist = distance_km(user_location, exchange_data["location"])
        exchange_distances.append({
            "id": exchange_id,
            "distance_km": dist,
            "data": exchange_data
        })
    
    # Sort by distance
    exchange_distances.sort(key=lambda x: x["distance_km"])
    nearest_exchanges = exchange_distances[:3]  # Top 3 nearest
    
    # Build queries based on mode - THIS WAS MISSING!
    queries = []
    if query_mode == "market_signals":
        # non-obvious news affecting markets indirectly
        queries = MARKET_IMPACT_QUERIES
    elif query_mode == "exchange_specific":
        # For exchange-specific mode, focus on that exchange's region
        relevant_exchange = nearest_exchanges[0]
        queries = [
            f"{relevant_exchange['data']['city']} financial news",
            f"{relevant_exchange['data']['country']} stock market",
            f"{' '.join(relevant_exchange['data']['indices'])} news"
        ]
    else:
        # For location-based mode, use broader market impact queries
        queries = MARKET_IMPACT_QUERIES[:5]  # Use first 5 impact queries
    
    print(f"🔍 Query mode: {query_mode}")
    print(f"📍 Location: ({lat}, {lon})")
    print(f"🎯 Using queries: {queries}")
    
    # Fetch news
    results = _fetch_news_from_tavily(queries, max_results, days)
    
    # Calculate the cutoff time (24 hours ago for freshness check)
    from datetime import datetime, timedelta
    cutoff_time = datetime.now() - timedelta(days=days)
    
    # Process results
    output = []
    for r in results:
        title = r.get("title") or ""
        snippet = r.get("content") or r.get("snippet") or ""
        url = r.get("url") or ""
        published_at = r.get("published_date") or r.get("published_at") or r.get("date") or None
        source = r.get("source") or r.get("domain") or ""
        
        # Validate news freshness
        is_fresh = True
        if published_at:
            try:
                # Try to parse the date
                if isinstance(published_at, str):
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    if pub_date < cutoff_time:
                        print(f"⏰ Skipping old news: {title[:50]}... (published: {published_at})")
                        is_fresh = False
            except Exception as e:
                # If we can't parse, include it anyway (benefit of doubt)
                pass
        
        if not is_fresh:
            continue  # Skip old news

        # ----- DOWNRANK obvious market headlines -----
        if any(x in title.lower() for x in MARKET_BULLETIN_KEYWORDS):
            print(f"📉 Downranking obvious market bulletin: {title[:80]}")
            forced_geo_weight_multiplier = 0.1
        else:
            forced_geo_weight_multiplier = 1.0
        
        # Calculate relevance to each nearby exchange
        exchange_impacts = []
        for exchange_info in nearest_exchanges:
            exchange_data = exchange_info["data"]
            distance = exchange_info["distance_km"]
            geo_weight = geo_decay_weight(distance) * forced_geo_weight_multiplier
            
            # Analyze impact
            impact_analysis = _analyze_market_impact(
                {"title": title, "snippet": snippet},
                exchange_data
            )
            
            exchange_impacts.append({
                "exchange_id": exchange_info["id"],
                "exchange_name": exchange_data["name"],
                "distance_km": round(distance, 2),
                "geo_weight": round(geo_weight, 3),
                "indices": exchange_data["indices"],
                **impact_analysis
            })
        
        # Sort by geo_weight to find most relevant exchange
        exchange_impacts.sort(key=lambda x: x["geo_weight"], reverse=True)
        primary_exchange = exchange_impacts[0]
        
        output.append({
            "title": title,
            "snippet": snippet[:400] if snippet else "",
            "url": url,
            "published_at": published_at,
            "source": source,
            "primary_exchange": primary_exchange,
            "all_exchange_impacts": exchange_impacts,
            "query_mode": query_mode,
            "raw": r,
        })
    
    print(f"✅ Processed {len(output)} fresh news items")
    
    # Sort by primary exchange geo_weight
    output_sorted = sorted(
        output,
        key=lambda x: x["primary_exchange"]["geo_weight"],
        reverse=True
    )
    
    # Cache the result
    cache_data = {"data": output_sorted, "timestamp": datetime.now().isoformat()}
    _set_cached_result(cache_key, cache_data, ttl=1800)  # 30 min cache
    
    return output_sorted

# def _get_market_news_impl(
#     lat: float,
#     lon: float,
#     radius_km: Optional[int] = 1500,
#     index: Optional[str] = "SP500",
#     days: int = 1,
#     max_results: int = 20,
#     query_mode: str = "location_based"  # "location_based" or "exchange_specific"
# ) -> List[Dict[str, Any]]:
#     """
#     Core implementation of market news fetching with Redis caching.
#     """
#     # Generate cache key
#     cache_params = {
#         "lat": round(lat, 2),
#         "lon": round(lon, 2),
#         "radius_km": radius_km,
#         "index": index,
#         "days": days,
#         "mode": query_mode
#     }
#     cache_key = _generate_cache_key("market_news", cache_params)
    
#     # Check cache
#     cached_result = _get_cached_result(cache_key)
#     if cached_result:
#         return cached_result.get("data", [])
    
#     if tavily is None:
#         return [{"error": "TAVILY_API_KEY not set on server"}]
    
#     # Find nearest stock exchanges
#     user_location = (lat, lon)
#     exchange_distances = []
    
#     for exchange_id, exchange_data in STOCK_EXCHANGES.items():
#         dist = distance_km(user_location, exchange_data["location"])
#         exchange_distances.append({
#             "id": exchange_id,
#             "distance_km": dist,
#             "data": exchange_data
#         })
    
#     # Sort by distance
#     exchange_distances.sort(key=lambda x: x["distance_km"])
#     nearest_exchanges = exchange_distances[:3]  # Top 3 nearest
    
#     # Build queries based on mode
#     if query_mode == "exchange_specific":
#         # For exchange-specific mode, focus on that exchange's region
#         relevant_exchange = nearest_exchanges[0]
#         queries = [
#             f"{relevant_exchange['data']['city']} financial news",
#             f"{relevant_exchange['data']['country']} stock market",
#             f"{' '.join(relevant_exchange['data']['indices'])} news"
#         ]
#     else:
#         # For location-based mode, use broader market impact queries
#         queries = MARKET_IMPACT_QUERIES[:5]  # Use first 5 impact queries
    
#     # Fetch news
#     results = _fetch_news_from_tavily(queries, max_results, days)
    
#     # Process results
#     output = []
#     for r in results:
#         title = r.get("title") or ""
#         snippet = r.get("content") or r.get("snippet") or ""
#         url = r.get("url") or ""
#         published_at = r.get("published_date") or r.get("published_at") or None
#         source = r.get("source") or r.get("domain") or ""
        
#         # Calculate relevance to each nearby exchange
#         exchange_impacts = []
#         for exchange_info in nearest_exchanges:
#             exchange_data = exchange_info["data"]
#             distance = exchange_info["distance_km"]
#             geo_weight = geo_decay_weight(distance)
            
#             # Analyze impact
#             impact_analysis = _analyze_market_impact(
#                 {"title": title, "snippet": snippet},
#                 exchange_data
#             )
            
#             exchange_impacts.append({
#                 "exchange_id": exchange_info["id"],
#                 "exchange_name": exchange_data["name"],
#                 "distance_km": round(distance, 2),
#                 "geo_weight": round(geo_weight, 3),
#                 "indices": exchange_data["indices"],
#                 **impact_analysis
#             })
        
#         # Sort by geo_weight to find most relevant exchange
#         exchange_impacts.sort(key=lambda x: x["geo_weight"], reverse=True)
#         primary_exchange = exchange_impacts[0]
        
#         output.append({
#             "title": title,
#             "snippet": snippet[:400] if snippet else "",
#             "url": url,
#             "published_at": published_at,
#             "source": source,
#             "primary_exchange": primary_exchange,
#             "all_exchange_impacts": exchange_impacts,
#             "query_mode": query_mode,
#             "raw": r,
#         })
    
#     # Sort by primary exchange geo_weight
#     output_sorted = sorted(
#         output,
#         key=lambda x: x["primary_exchange"]["geo_weight"],
#         reverse=True
#     )
    
#     # Cache the result
#     cache_data = {"data": output_sorted, "timestamp": datetime.now().isoformat()}
#     _set_cached_result(cache_key, cache_data, ttl=1800)  # 30 min cache
    
#     return output_sorted

@tool
def get_market_news(
    lat: float,
    lon: float,
    radius_km: Optional[int] = 1500,
    index: Optional[str] = "SP500",
    days: int = 1,
    max_results: int = 20,
    query_mode: str = "location_based"
) -> List[Dict[str, Any]]:
    """
    Fetch geographically-weighted market news with impact analysis.
    """
    return _get_market_news_impl(lat, lon, radius_km, index, days, max_results, query_mode)

def get_query_history(limit: int = 50) -> List[Dict]:
    """Retrieve recent query history from Redis."""
    if not redis_client:
        return []
    
    try:
        # Get query IDs sorted by timestamp (newest first)
        query_ids = redis_client.zrevrange("query_history_index", 0, limit - 1)
        
        history = []
        for query_id in query_ids:
            query_data = redis_client.get(f"query_history:{query_id}")
            if query_data:
                history.append(json.loads(query_data))
        
        return history
    except Exception as e:
        print(f"Redis history retrieval error: {e}")
        return []

def get_available_exchanges() -> List[Dict]:
    """Return list of all available stock exchanges."""
    return [
        {
            "id": exchange_id,
            "name": data["name"],
            "city": data["city"],
            "country": data["country"],
            "location": data["location"],
            "indices": data["indices"]
        }
        for exchange_id, data in STOCK_EXCHANGES.items()
    ]