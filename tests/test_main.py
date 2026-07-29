# tests/test_main.py
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

# Initialize the synchronous TestClient for our FastAPI app
client = TestClient(app)

def test_health_check():
    """Test that the API health check endpoint is responsive."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "OSINT Engine Active"}

@patch("app.main.osint_app.ainvoke", new_callable=AsyncMock)
def test_analyze_company_success(mock_ainvoke):
    """Test the /analyze endpoint with a successful mock graph execution."""
    
    # Mock the return dictionary that the LangGraph pipeline would normally produce
    mock_ainvoke.return_value = {
        "final_report": {
            "company_name": "Mocked Corp",
            "financial_risks": [],
            "regulatory_risks": ["Routine mocked lawsuit"],
            "operational_risks": [],
            "risk_score": 2
        },
        "news_data": [{"headline": "Mocked Corp sued", "published": "2026-07-29"}],
        "sec_filings": []
    }

    # Send a POST request to the endpoint
    payload = {"query": "Mocked Corp", "ticker_symbol": "MCK"}
    response = client.post("/analyze", json=payload)

    # Assertions to verify the API behaves correctly
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["company_name"] == "Mocked Corp"
    assert data["data"]["risk_score"] == 2
    
    # Verify the mock was called exactly once with the expected inputs
    mock_ainvoke.assert_called_once_with({
        "query": "Mocked Corp",
        "ticker_symbol": "MCK"
    })

def test_analyze_company_missing_query():
    """Test that Pydantic properly blocks requests missing the required 'query' field."""
    
    # Payload missing the required 'query' field
    payload = {"ticker_symbol": "AAPL"}
    response = client.post("/analyze", json=payload)

    # FastAPI should automatically return a 422 Unprocessable Entity error
    assert response.status_code == 422
    assert "detail" in response.json()
    assert response.json()["detail"][0]["loc"] == ["body", "query"]
    assert response.json()["detail"][0]["msg"] == "Field required"

@patch("app.main.osint_app.ainvoke", new_callable=AsyncMock)
def test_analyze_company_graph_failure(mock_ainvoke):
    """Test that the API gracefully handles an internal LangGraph failure."""
    
    # Mock the graph throwing an unexpected exception (e.g., Groq API outage)
    mock_ainvoke.side_effect = Exception("Groq API Timeout")

    payload = {"query": "Error Corp"}
    response = client.post("/analyze", json=payload)

    # The API should catch this and return a 500 Internal Server Error
    assert response.status_code == 500
    # Change this line to expect just the raw exception string
    assert "Groq API Timeout" in response.json()["detail"]