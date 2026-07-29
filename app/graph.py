import asyncio
import json
from langgraph.graph import StateGraph, START, END
from app.state import OSINTState
from app.nodes.harvester import harvester_node
from app.nodes.assessor import assessor_node
from app.nodes.synthesizer import synthesizer_node

# ==========================================
# Conditional Routing Logic
# ==========================================
def route_after_harvest(state: OSINTState) -> str:
    """Decides where the graph should go after data ingestion."""
    # Check if all data sources came back completely empty
    has_financials = bool(state.financial_data and "error" not in state.financial_data)
    has_news = bool(state.news_data and not (len(state.news_data) == 1 and "error" in state.news_data[0]))
    has_sec = bool(state.sec_filings and not (len(state.sec_filings) == 1 and "error" in state.sec_filings[0]))

    if not (has_financials or has_news or has_sec):
        print("\n[!] No valid OSINT data found across any source. Aborting LLM analysis.")
        return "skip_to_end"
    
    return "continue_to_assessor"

# ==========================================
# Graph Compilation
# ==========================================
# 1. Initialize the StateGraph with our Pydantic state
workflow = StateGraph(OSINTState)

# 2. Add nodes to the graph
workflow.add_node("harvester", harvester_node)
workflow.add_node("assessor", assessor_node)
workflow.add_node("synthesizer", synthesizer_node)

# 3. Define the Flow (Edges)
workflow.add_edge(START, "harvester")

# Add conditional routing after the harvester
workflow.add_conditional_edges(
    "harvester",
    route_after_harvest,
    {
        "continue_to_assessor": "assessor",
        "skip_to_end": END
    }
)

# Linear execution path
workflow.add_edge("assessor", "synthesizer")
workflow.add_edge("synthesizer", END)

# 4. Compile the autonomous application
osint_app = workflow.compile()


# ==========================================
# Local Testing Block
# ==========================================
async def main():
    print("--- Testing Standard Flow (Boeing) ---")
    inputs = {"query": "Boeing", "ticker_symbol": "BA"}
    
    # Invoke the compiled graph
    result = await osint_app.ainvoke(inputs)
    
    print("\n--- Final Graph Output ---")
    print(json.dumps(result.get("final_report"), indent=4))
    
    print("\n\n--- Testing Conditional Edge (Non-Existent Target) ---")
    bad_inputs = {"query": "SomeFakeCompanyThatDoesNotExist12345", "ticker_symbol": "NONEXISTENT123"}
    bad_result = await osint_app.ainvoke(bad_inputs)
    
    print("\n--- Fallback Output ---")
    print("Final Report:", bad_result.get("final_report"))

if __name__ == "__main__":
    asyncio.run(main())