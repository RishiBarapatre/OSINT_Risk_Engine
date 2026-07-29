import os
import asyncio
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq
from app.state import OSINTState

# Import previous nodes for local testing
from app.nodes.harvester import harvester_node
from app.nodes.assessor import assessor_node

load_dotenv()

# ==========================================
# Define the Strict JSON Schema
# ==========================================
class RiskReport(BaseModel):
    company_name: str = Field(description="Name of the company analyzed")
    financial_risks: List[str] = Field(description="List of financial red flags. Empty list if none.")
    regulatory_risks: List[str] = Field(description="List of legal or regulatory red flags. Empty list if none.")
    operational_risks: List[str] = Field(description="List of operational or governance red flags. Empty list if none.")
    risk_score: int = Field(
        description=(
            "A holistic corporate risk score from 1 to 10 based on vulnerability, regulatory friction, and financial volatility. "
            "Use this exact calibration:\n"
            "1-3: Routine Operations / Low Friction. Normal business operations, routine legal friction, and standard executive turnover.\n"
            "4-6: Moderate Headwinds / Elevated Volatility. Major structural regulatory changes, significant revenue decline, concerning debt growth, or abnormal leadership churn.\n"
            "7-9: High Regulatory or Financial Friction. Massive combined regulatory fines, active securities fraud investigations, auditor resignations, or severe liquidity crunches.\n"
            "10: Structural Failure / Imminent Collapse. Bankruptcy proceedings, delisting, or complete operational halt."
        )
    )

# ==========================================
# Node 3: The Synthesizer
# ==========================================
def synthesizer_node(state: OSINTState) -> OSINTState:
    """Forces the raw risk assessment into a strict JSON schema."""
    print(f"\n[*] Synthesizing final JSON report for: {state.query}...")
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is missing! Check your .env file.")
    
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=groq_api_key
    )
    
    # Bind the LLM directly to the Pydantic schema
    structured_llm = llm.with_structured_output(RiskReport)
    
    raw_assessment = "\n".join(state.extracted_risks) if state.extracted_risks else "No significant risks identified."
    
    prompt = (
        f"Target Company: {state.query}\n\n"
        "Convert the following corporate risk assessment into the required JSON format. "
        "If the assessment states that no significant risks were identified, return empty lists "
        "for the risk categories and assign a risk_score of 1.\n\n"
        f"Assessment:\n{raw_assessment}"
    )
    
    # Invoke the structured LLM
    response = structured_llm.invoke(prompt)
    
    # Save output as a standard dictionary for JSON compatibility
    state.final_report = response.model_dump()
    print("[*] Synthesis complete.")
    
    return state


# ==========================================
# Local Testing Block
# ==========================================
async def main():
    initial_state = OSINTState(
        query="Boeing", 
        ticker_symbol="BA"
    )
    
    # Run the pipeline sequentially
    state1 = await harvester_node(initial_state)
    state2 = assessor_node(state1)
    final_state = synthesizer_node(state2)
    
    print("\n--- Final JSON Output ---")
    print(json.dumps(final_state.final_report, indent=4))

if __name__ == "__main__":
    asyncio.run(main())