from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OSINTState(BaseModel):
    query: str = Field(
        description="The name of the target company or corporate entity being analyzed."
    )

    ticker_symbol: Optional[str] = Field(
        default=None,
        description="The stock ticker symbol (e.g., 'MSFT', 'SMCI') used to query financial APIs and SEC databases. None if private.",
    )

    financial_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured financial metrics, ratios (P/E, Debt-to-Equity), and balance sheet health harvested from yfinance.",
    )

    news_data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Qualitative news headlines and media coverage harvested via targeted Google News RSS feeds.",
    )

    sec_filings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Official Form 8-K material event disclosures fetched directly from SEC EDGAR, with decoded Item event categories (e.g., auditor departures, restatements, cyber breaches).",
    )

    extracted_risks: List[str] = Field(
        default_factory=list,
        description="Categorized red flags (financial, regulatory, operational) extracted and synthesized across all data sources by the Assessor node.",
    )

    final_report: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The final synthesized risk report, including category breakdowns, overall score (1-10), and key takeaways, formatted for API response.",
    )

    error_logs: List[str] = Field(
        default_factory=list,
        description="Tracks non-fatal errors, API timeouts, or missing data across harvester nodes for graceful fallback handling.",
    )