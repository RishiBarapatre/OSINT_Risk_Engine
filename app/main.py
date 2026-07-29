from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.graph import osint_app

app = FastAPI(
    title="OSINT Risk Intelligence Engine",
    description="Autonomous Corporate Risk Analysis Pipeline powered by LangGraph, SEC EDGAR, yfinance, and Groq.",
    version="1.0.0"
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
async def analyze_company(request: AnalyzeRequest):
    try:
        inputs = {"query": request.query, "ticker_symbol": request.ticker_symbol}
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