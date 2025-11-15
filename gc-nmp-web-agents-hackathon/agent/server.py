# agent/server.py
import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from tools.news_tools import (
    _get_market_news_impl,
    _save_query_to_history,
    get_query_history,
    get_available_exchanges
)
from dotenv import load_dotenv

# Load .env from the agent directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Verify the API key is loaded
tavily_key = os.getenv("TAVILY_API_KEY")
if not tavily_key:
    print("ERROR: TAVILY_API_KEY not found in environment!")
else:
    print(f"✓ TAVILY_API_KEY loaded: {tavily_key[:10]}...")

app = FastAPI(title="LangGraph Tools Proxy")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MarketNewsRequest(BaseModel):
    lat: float
    lon: float
    radius_km: Optional[int] = 1500
    index: Optional[str] = "SP500"
    days: Optional[int] = 1
    max_results: Optional[int] = 20
    query_mode: Optional[str] = "location_based"  # or "exchange_specific"
    save_to_history: Optional[bool] = True

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/exchanges")
def list_exchanges():
    """Get list of all available stock exchanges."""
    try:
        exchanges = get_available_exchanges()
        return {"ok": True, "exchanges": exchanges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def query_history(limit: int = 50):
    """Get query history."""
    try:
        history = get_query_history(limit)
        return {"ok": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/get_market_news")
def tools_get_market_news(req: MarketNewsRequest):
    try:
        print(f"Received request: lat={req.lat}, lon={req.lon}, index={req.index}, mode={req.query_mode}")
        
        res = _get_market_news_impl(
            lat=req.lat,
            lon=req.lon,
            radius_km=req.radius_km,
            index=req.index,
            days=req.days,
            max_results=req.max_results,
            query_mode=req.query_mode,
        )
        
        print(f"Returning {len(res)} results")
        
        # Save to history if requested
        if req.save_to_history and res:
            query_id = str(uuid.uuid4())
            
            # Determine which exchange(s) this query is for
            exchange_info = "User location" if req.query_mode == "location_based" else req.index
            
            query_data = {
                "query_id": query_id,
                "timestamp": datetime.now().isoformat(),
                "params": {
                    "lat": req.lat,
                    "lon": req.lon,
                    "index": req.index,
                    "query_mode": req.query_mode,
                    "days": req.days
                },
                "result_count": len(res),
                "exchange_info": exchange_info,
                "preview": {
                    "title": res[0].get("title", "") if res else "",
                    "primary_exchange": res[0].get("primary_exchange", {}).get("exchange_name", "") if res else ""
                }
            }
            
            _save_query_to_history(query_id, query_data)
        
        return {"ok": True, "data": res}
    except Exception as e:
        print(f"Error in tools_get_market_news: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))