import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.state import OSINTState
from app.nodes.harvester import harvester_node

# Load environment variables from .env file
load_dotenv()


def assessor_node(state: OSINTState) -> OSINTState:
    """Analyzes harvested financial, news, and SEC data to extract critical risk factors using Groq."""
    print(f"\n[*] Assessing risks for: {state.query}...")

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is missing! Check your .env file.")

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=groq_api_key
    )

    # Fetch the current system date dynamically
    current_date = datetime.now().strftime("%B %d, %Y")

    system_prompt = (
        "You are an expert corporate financial risk analyst and OSINT intelligence specialist.\n"
        "Review the provided financial metrics, news headlines, and official SEC 8-K disclosures for the target company.\n\n"

        "FINANCIAL BENCHMARK RULES (Do NOT flag as a risk if healthy):\n"
        "- Debt-to-Equity: Below 100% (1.0) is LOW and HEALTHY. Only flag as a financial risk if Debt-to-Equity is ABOVE 150% (1.5).\n"
        "- Liquidity: Current Ratio above 1.0 and Quick Ratio above 0.8 are healthy. Only flag if below these thresholds.\n"
        "- Valuation: High P/E or Price-to-Book alone is NOT a risk for growth companies unless accompanied by falling revenue or negative margins.\n\n"

        "MATERIALITY & SCALE RULES (CRITICAL):\n"
        f"- TEMPORAL AWARENESS: Today's date is {current_date}. Evaluate the publication dates of the news. Completely IGNORE historic events (e.g., settlements, fines, or lawsuits from years ago) that have resurfaced in retrospective articles. Only flag active, recent, or ongoing threats.\n"
        "- Gauge risk relative to the company's scale. Large, established corporations face routine litigation and regulatory friction daily. Do NOT flag standard consumer class actions, minor patent disputes, or routine fines as regulatory risks unless they fundamentally threaten the core business model or represent a significant percentage of enterprise value.\n"
        "- Defensive litigation (e.g., the target company suing a competitor) is a business defense tactic, NOT a risk to the target.\n"
        "- Routine executive transitions (SEC Item 5.02) are normal corporate governance. Do not flag them as Operational Risk unless the news context explicitly indicates fraud, scandal, or a sudden mass exodus of leadership.\n\n"

        "SEC 8-K FILING RULES:\n"
        "- Treat Item 4.01 (Auditor Resignation/Dismissal), Item 4.02 (Accounting Error/Restatement), "
        "Item 1.03 (Bankruptcy), Item 3.01 (Delisting Notice), and Item 1.05 (Material Cybersecurity Incident) "
        "as CRITICAL, HIGH-PRIORITY OPERATIONAL OR REGULATORY RISKS.\n"
        "- Routine 8-Ks like Item 2.02 (Earnings Releases) or standard Item 5.02 (Board changes) should NOT be flagged as risks unless accompanied by adverse news.\n\n"

        "CATEGORIES TO EXTRACT:\n"
        "1. Financial Risk (ONLY genuine material red flags based on benchmark rules)\n"
        "2. Legal/Regulatory Risk (e.g., SEC/DOJ investigations, major antitrust lawsuits, government enforcement)\n"
        "3. Operational/Governance Risk (e.g., auditor departures, accounting restatements, leadership turmoil, cyber breaches)\n\n"

        "If no genuine, material risks meet these threshold criteria, state 'No significant risks identified.'\n"
        "Output ONLY a bulleted list of identified risks grouped by category. Do not include introductory filler."
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", 
         "Target Company: {company} (Ticker: {ticker})\n\n"
         "--- FINANCIAL DATA ---\n{financials}\n\n"
         "--- RECENT NEWS ---\n{news}\n\n"
         "--- OFFICIAL SEC 8-K FILINGS ---\n{sec_filings}"
        )
    ])

    # Format structured data inputs into clean string context blocks for the LLM
    financials_str = str(state.financial_data) if state.financial_data else "No financial data available."
    
    # Inject the publication date directly into the formatted string for the LLM to read
    news_str = "\n".join([f"- [{item.get('published', 'Unknown Date')}] {item.get('headline', item)}" for item in state.news_data]) if state.news_data else "No recent news available."
    
    sec_str = "\n".join([f"- [{item.get('date')}] {item.get('event_details')}" for item in state.sec_filings]) if state.sec_filings else "No recent SEC 8-K filings available."

    chain = prompt_template | llm

    response = chain.invoke({
        "company": state.query,
        "ticker": state.ticker_symbol or "N/A",
        "financials": financials_str,
        "news": news_str,
        "sec_filings": sec_str
    })

    # Store response in extracted_risks
    state.extracted_risks = [response.content]
    print("[*] Risk assessment complete.")

    return state


async def main():
    initial_state = OSINTState(
        query="Pfizer", 
        ticker_symbol="PFE"
    )
    
    state_after_harvest = await harvester_node(initial_state)
    final_state = assessor_node(state_after_harvest)
    
    print("\n--- Extracted Risks ---")
    for risk in final_state.extracted_risks:
        print(risk)

if __name__ == "__main__":
    asyncio.run(main())