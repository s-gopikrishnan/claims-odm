import streamlit as st
import requests
import json
from datetime import datetime, date, timedelta
import pandas as pd
import os
from typing import Dict, Any
from requests.auth import HTTPBasicAuth
import logging
import sys
import time
from dotenv import load_dotenv
load_dotenv()  # take environment variables from .env.

# Configure logger

logger = logging.getLogger()
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
    )
    logger.info("App started")

# Configuration - Get credentials from environment variables
API_USERNAME = os.getenv("API_USERNAME", "your_username")
API_PASSWORD = os.getenv("API_PASSWORD", "your_password")
API_ENDPOINT = os.getenv("API_ENDPOINT", "https://medicaid.westus.cloudapp.azure.com/DecisionService/rest/v1/ClaimsAdj/1.0/dateCheck/1.14")

# Configure page
st.set_page_config(
    page_title="Claims Pre-check System",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
    }
    
    .success-box {
        border-left: 5px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    
    .error-box {
        border-left: 5px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for history
if 'claim_history' not in st.session_state:
    st.session_state.claim_history = []

def format_datetime_for_api(dt: date) -> str:
    """Convert date to API-expected format with 00:00 time"""
    # Always use 00:00 time
    dt_with_time = datetime.combine(dt, datetime.min.time())
    return dt_with_time.strftime("%Y-%m-%dT00:00:00.000+0000")

def calculate_days_difference(service_date: date, submission_date: date) -> int:
    """Calculate days between service and submission dates"""
    return (submission_date - service_date).days

def submit_claim(claim_data: Dict[str, Any]) -> Dict[str, Any]:
    """Submit claim to ODM REST endpoint with basic authentication"""

    start_time = time.time()

    try:
        logger.info(f"Submitting claim ID {claim_data.get('claim', {}).get('claimId')} to {API_ENDPOINT}")

        response = requests.post(
            API_ENDPOINT,
            json=claim_data,
            headers={'Content-Type': 'application/json'},
            auth=HTTPBasicAuth(API_USERNAME, API_PASSWORD),
            timeout=30
        )

        elapsed = time.time() - start_time
        
        logger.info(f"Response from ODM: status={response.status_code} time={elapsed:.2f}s")
        if response.status_code != 200:
            logger.warning(f"Non-200 response: {response.text[:300]}")  # truncate
      
        response.raise_for_status()
        return {
            "success": True,
            "response": response.json(),
            "request": claim_data,
            "response_time_sec": elapsed
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed after {elapsed:.2f}s: {e}")

        return {
            "success": False,
            "error": True,
            "message": f"API Error: {str(e)}",
            "response": {
                "result": {
                    "claimStatus": "Error",
                    "messages": [f"Failed to connect to ODM service: {str(e)}"]
                }
            },
            "request": claim_data,
            "response_time_sec": elapsed
        }

def add_to_history(claim_id: int, status: str, days_diff: int, messages: list):
    """Add claim attempt to history"""
    history_entry = {
        "Claim ID": claim_id,
        "Status": status,
        "Days Difference": days_diff,
        "Messages": "; ".join(messages),
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    st.session_state.claim_history.insert(0, history_entry)
    # Keep only last 10 entries
    if len(st.session_state.claim_history) > 10:
        st.session_state.claim_history = st.session_state.claim_history[:10]

# Main UI

# Main header
st.markdown("""
<div class="main-header">
    <h1>🏥 Claims Pre-check System</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
# Create two columns for better layout
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📋 Claim Submission")

    # Example data loader
    example_type = st.selectbox(
        "Load Example Data:",
        ["Custom", "Approved Example", "Rejected Example", "Edge Case Example"]
    )

    # Default values based on selection
    if example_type == "Approved Example":
        default_service_date = datetime(2024, 5, 5, 0, 0, 0)
        default_submission_date = datetime(2024, 6, 23, 0, 0, 0)
        default_claim_id = 1001
        default_billed_amt = 1000.0
    elif example_type == "Rejected Example":
        default_service_date = datetime(2024, 5, 5, 0, 0, 0)
        default_submission_date = datetime(2024, 12, 23, 0, 0, 0)
        default_claim_id = 2001
        default_billed_amt = 1000.0
    elif example_type == "Edge Case Example":
        default_service_date = datetime(2024, 1, 1, 0, 0, 0)
        default_submission_date = datetime(2024, 6, 30, 0, 0, 0)
        default_claim_id = 3001
        default_billed_amt = 1500.0
    else:
        default_service_date = datetime.now() - timedelta(days=30)
        default_submission_date = datetime.now()
        default_claim_id = 4001
        default_billed_amt = 500.0

    # Claim input form
    with st.form("claim_form"):

        claim_id = st.number_input(
            "Claim ID",
            min_value=1,
            step=1,
            value=default_claim_id,
            help="Enter a unique claim identifier"
        )
        
        billed_amount = st.number_input(
            "Billed Amount ($)",
            min_value=0.01,
            step=0.01,
            value=default_billed_amt,
            format="%.2f",
            help="Enter the total billed amount"
        )
        
        service_date = st.date_input(
            "Service Date",
            value=default_service_date,
            help="Date when the service was provided"
        )
        
        submission_date = st.date_input(
            "Submission Date",
            value=default_submission_date,
            help="Date when the claim was submitted"
        )
        
        submit_button = st.form_submit_button("🚀 Submit Claim", use_container_width=True)
    
    # Validation and submission
    if submit_button:
        logger.info(f"User submitted claim: ID={claim_id}, Amount={billed_amount}, Service={service_date}, Submission={submission_date}")
        if submission_date < service_date:
            st.error("❌ Submission date cannot be before service date!")
        else:
            days_diff = calculate_days_difference(service_date, submission_date)
            
            # Prepare API payload
            claim_payload = {
                "claim": {
                    "claimId": claim_id,
                    "billedAmt": billed_amount,
                    "serviceDate": format_datetime_for_api(service_date),
                    "submissionDate": format_datetime_for_api(submission_date)
                }
            }
            
            # Show loading spinner
            with st.spinner("Processing claim..."):
                api_result = submit_claim(claim_payload)
            
            # Only add to history here, once per submission:
            if api_result.get("success"):
                claim_result = api_result.get("response", {}).get("result", {})
                status = claim_result.get("claimStatus", "Unknown")
                messages = claim_result.get("messages", [])
                add_to_history(claim_id, status, days_diff, messages)

            # Store result in session state for display
            st.session_state.last_result = api_result
            st.session_state.last_days_diff = days_diff
            st.session_state.last_claim_id = claim_id

with col2:
    st.header("📊 Results")
    
    # Display results if available
    if hasattr(st.session_state, 'last_result'):
        api_result = st.session_state.last_result
        
        if api_result.get("error"):
            st.error(f"❌ {api_result.get('message', 'Unknown error')}")
        else:
            result = api_result.get("response", {})
            claim_result = result.get("result", {})
            status = claim_result.get("claimStatus", "Unknown")
            messages = claim_result.get("messages", [])
            decision_id = result.get('__DecisionID__', 'N/A')
            
            # Display status with appropriate styling
            if status == "Approved":
                st.markdown(f"""
                    <div class="success-box">
                        <h4>✅ Claim {status}</h4>
                        <p><strong>Decision ID:</strong> {decision_id}</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="error-box">
                        <h4>❌ Claim {status}</h4>
                        <p><strong>Decision ID:</strong> {decision_id}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            # Display messages
            st.subheader("📝 Processing Messages:")
            for i, message in enumerate(messages, 1):
                st.write(f"{i}. {message}")
            
            # Show additional info
            st.info(f"📅 **Days between service and submission:** {st.session_state.last_days_diff} days")
            
            # Show decision ID if available
            if "__DecisionID__" in result:
                st.text(f"🔍 Decision ID: {result['__DecisionID__']}")

            # Display response time if available
            response_time = api_result.get("response_time_sec")
            if response_time is not None:
                st.markdown(f"⏱️ **Response time:** {response_time:.2f} seconds")
            
            # Collapsible section for request/response JSONs
            with st.expander("🔍 View Request/Response JSON", expanded=False):
                col_req, col_res = st.columns(2)
                
                with col_req:
                    st.subheader("📤 Request JSON")
                    st.json(api_result.get("request", {}))
                
                with col_res:
                    st.subheader("📥 Response JSON")
                    st.json(api_result.get("response", {}))
    else:
        st.info("Submit a claim to see results here")

# History section
st.markdown("---")
st.header("📚 Claim History")

if st.session_state.claim_history:
    # Create DataFrame for better display
    df = pd.DataFrame(st.session_state.claim_history)
    
    # Style the dataframe
    def style_status(val):
        if val == "Approved":
            return "color: green; font-weight: bold"
        elif val == "Error":
            return "color: red; font-weight: bold"
        else:
            return "color: orange; font-weight: bold"
    
    styled_df = df.style.map(style_status, subset=['Status'])
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Clear history button
    if st.button("🗑️ Clear History"):
        st.session_state.claim_history = []
        st.rerun()
else:
    st.info("No claims submitted yet. Submit your first claim to see history here.")
