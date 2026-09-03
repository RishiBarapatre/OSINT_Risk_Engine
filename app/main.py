import os
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.graph import osint_app

app = FastAPI(
    title="OSINT Risk Intelligence Engine",
    description="Autonomous Corporate Risk Analysis Pipeline powered by LangGraph, SEC EDGAR, yfinance, and Groq.",
    version="1.0.0"
)

# --- Rate limiting (protects Groq API credits from abuse on a public demo) ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS: only allow the deployed Streamlit frontend to call this API directly ---
# Set FRONTEND_ORIGIN as an env var on Render, e.g. https://your-app.streamlit.app
# Comma-separate multiple origins if needed (e.g. local dev + prod).
_frontend_origins = os.getenv("FRONTEND_ORIGIN", "http://localhost:8501")
allowed_origins = [origin.strip() for origin in _frontend_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    query: str = Field(
        ..., 
        examples=["Alphabet Inc"], 
        description="Target company or corporate entity name."
    )
    ticker_symbol: Optional[str] = Field(
        None, 
        examples=["GOOGL"], 
        description="Public stock ticker symbol for financial and SEC retrieval."
    )


class AnalyzeResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    data: Optional[Dict[str, Any]] = Field(
        None, 
        description="The synthesized risk report containing scores and categorized red flags."
    )


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint for container orchestrators and monitoring tools."""
    return {"status": "ok", "service": "OSINT Engine Active"}


@app.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def analyze_company(request: Request, payload: AnalyzeRequest):
    try:
        inputs = {"query": payload.query, "ticker_symbol": payload.ticker_symbol}
        result = await osint_app.ainvoke(inputs)
        
        final_report = result.get("final_report", {})
        
        # Attach raw evidence for UI transparency
        final_report["raw_sources"] = {
            "news": result.get("news_data", []),
            "sec_filings": result.get("sec_filings", [])
        }
        
        return AnalyzeResponse(status="success", data=final_report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))