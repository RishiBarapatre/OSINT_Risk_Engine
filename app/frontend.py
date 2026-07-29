import streamlit as st
import requests
import time
import os

# Configure the Streamlit page
st.set_page_config(
    page_title="OSINT Risk Engine",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS for styling the Risk Score badge
st.markdown("""
    <style>
    .risk-badge {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 20px;
    }
    .low-risk { background-color: #2e7d32; }
    .mod-risk { background-color: #f57c00; }
    .high-risk { background-color: #c62828; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Autonomous OSINT Risk Engine")
st.markdown("Enter a company name and ticker symbol to harvest live SEC filings, news, and financial data for instant LLM risk assessment.")

# Input Form
with st.form("analyze_form"):
    col1, col2 = st.columns(2)
    with col1:
        company = st.text_input("Target Company Name", placeholder="e.g., Alphabet Inc")
    with col2:
        ticker = st.text_input("Ticker Symbol (Optional)", placeholder="e.g., GOOGL")
    
    submitted = st.form_submit_button("Run Risk Assessment", type="primary")

# Execution Logic
if submitted:
    if not company:
        st.warning("Please enter a company name.")
    else:
        # Show a spinner while the LangGraph pipeline does its work
        with st.spinner(f"Harvesting OSINT data & assessing risks for {company}... (this takes a few seconds)"):
            try:
                # Call our FastAPI backend
                api_url = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/analyze")
                payload = {"query": company, "ticker_symbol": ticker if ticker else None}
                
                response = requests.post(api_url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})
                    
                    # 1. Display the Final Risk Score
                    score = data.get("risk_score", 1)
                    
                    # Determine styling based on the new OSINT friction scale
                    if score <= 3:
                        risk_class, threat_level = "low-risk", "Routine Operations / Low Friction"
                    elif score <= 6:
                        risk_class, threat_level = "mod-risk", "Moderate Headwinds / Elevated Volatility"
                    elif score <= 9:
                        risk_class, threat_level = "high-risk", "High Regulatory or Financial Friction"
                    else:
                        risk_class, threat_level = "high-risk", "Structural Failure / Imminent Collapse"
                        
                    st.markdown(f"""
                        <div class="risk-badge {risk_class}">
                            <h1 style='margin: 0; padding: 0;'>Risk Score: {score} / 10</h1>
                            <p style='margin: 0; padding: 0; font-size: 1.2em;'>{threat_level}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.divider()
                    
                    # 2. Display the Extracted Risks cleanly
                    st.header(f"Intelligence Report: {data.get('company_name', company)}")
                    
                    col_fin, col_reg, col_ops = st.columns(3)
                    
                    with col_fin:
                        st.subheader("💰 Financial Risks")
                        fin_risks = data.get("financial_risks", [])
                        if fin_risks:
                            for risk in fin_risks:
                                st.error(risk)
                        else:
                            st.success("No significant financial risks identified.")
                            
                    with col_reg:
                        st.subheader("⚖️ Regulatory Risks")
                        reg_risks = data.get("regulatory_risks", [])
                        if reg_risks:
                            for risk in reg_risks:
                                st.warning(risk)
                        else:
                            st.success("No significant regulatory risks identified.")
                            
                    with col_ops:
                        st.subheader("🏢 Operational Risks")
                        ops_risks = data.get("operational_risks", [])
                        if ops_risks:
                            for risk in ops_risks:
                                st.info(risk)
                        else:
                            st.success("No significant operational risks identified.")
                            
                    # 3. Add Raw Intelligence Sources Accordion for Auditability
                    st.divider()
                    with st.expander("🔍 View Raw Primary Evidence & Harvested Sources"):
                        raw_sources = data.get("raw_sources", {})
                        
                        col_raw_news, col_raw_sec = st.columns(2)
                        
                        with col_raw_news:
                            st.write("**Harvested News Headlines & Links**")
                            news_list = raw_sources.get("news", [])
                            if news_list:
                                for item in news_list:
                                    if "headline" in item:
                                        st.markdown(f"- [{item['headline']}]({item.get('link', '#')}) *({item.get('published', 'N/A')})*")
                            else:
                                st.write("No news entries captured.")
                                
                        with col_raw_sec:
                            st.write("**Harvested SEC Form 8-K Filings**")
                            sec_list = raw_sources.get("sec_filings", [])
                            if sec_list:
                                for filing in sec_list:
                                    if "event_details" in filing:
                                        st.markdown(f"- **{filing.get('date', 'N/A')}**: {filing.get('event_details')}")
                            else:
                                st.write("No recent SEC 8-K filings captured.")

                else:
                    st.error(f"Backend Error {response.status_code}: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend. Is your FastAPI server running on http://127.0.0.1:8000?")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")