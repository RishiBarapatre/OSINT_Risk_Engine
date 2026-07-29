# Autonomous OSINT Risk Engine

An asynchronous, agentic pipeline built with **LangGraph** and **FastAPI** that autonomously harvests real-time open-source intelligence (OSINT), financial metrics, and SEC filings to generate enterprise-grade corporate risk assessments.

## Interface Preview

Here is a look at the Streamlit dashboard rendering live OSINT intelligence into our Friction & Volatility Scale:

### High Regulatory Friction (Score: 7/10)
![Alphabet Dashboard](assets/dashboard_alphabet.png)

### Moderate Headwinds (Score: 4/10)
![Apple Dashboard](assets/dashboard_apple.png)

---

## System Architecture

The engine is built on a directed acyclic graph (DAG) architecture using LangGraph, consisting of three primary nodes:

1. **Harvester Node (`harvester.py`)**: Concurrently scrapes live data using `asyncio.gather`:
   - **Financials:** Pulls live balance sheet metrics (Debt-to-Equity, Liquidity) via `yfinance`.
   - **News:** Aggregates and deduplicates live headlines via Google News RSS.
   - **Regulatory:** Queries the US SEC EDGAR database for recent 8-K material disclosures.
2. **Assessor Node (`assessor.py`)**: Uses a Large Language Model (Groq / LLaMA-3) equipped with a strict temporal and materiality ruleset to filter out historic noise and evaluate genuine corporate friction.
3. **Synthesizer Node (`synthesizer.py`)**: Structures the LLM output into a rigid Pydantic JSON schema, calibrating a final 1-10 Friction & Volatility score.

## Tech Stack

* **Orchestration:** LangGraph, LangChain
* **Backend REST API:** FastAPI, Uvicorn, Pydantic
* **Frontend:** Streamlit
* **LLM Inference:** Groq (LLaMA-3 70B)
* **Data Sources:** `yfinance`, SEC EDGAR API, RSS
* **Infrastructure:** Docker, Docker Compose
* **Testing:** Pytest

## Quickstart (Docker)

The easiest way to run the OSINT Risk Engine is via Docker Compose.

**1. Clone the repository and navigate to the root directory:**
```bash
git clone https://github.com/RishiBarapatre/osint-engine.git
cd osint-engine
```

**2. Configure your Environment Variables:**
Create a `.env` file in the root directory and add your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
```

**3. Build and launch the microservices:**
```bash
docker-compose up --build
```

**4. Access the Applications:**
* **Intelligence Dashboard (Streamlit):** `http://localhost:8501`
* **Backend API Docs (Swagger UI):** `http://localhost:8000/docs`

## Testing

To run the unit test suite (which mocks the LangGraph execution to save API credits and ensure CI/CD safety):
```bash
python -m pytest tests/
```

## Friction & Volatility Scale
The engine avoids binary "buy/sell" advice, instead utilizing a standard OSINT friction scale:
* **1-3:** Routine Operations / Low Friction
* **4-6:** Moderate Headwinds / Elevated Volatility
* **7-9:** High Regulatory or Financial Friction (e.g., active fraud probes, multi-billion dollar fines)
* **10:** Structural Failure / Imminent Collapse