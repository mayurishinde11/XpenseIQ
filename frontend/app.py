# app.py
# Main Streamlit application.
# This is the entry point of our frontend dashboard.
# Run with: streamlit run app.py

import streamlit as st
import os
import requests

# Get backend URL from environment variable
# In development: http://127.0.0.1:8000
# In Docker: http://backend:8000
# In production: https://your-railway-url.railway.app
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Page configuration must be the FIRST streamlit command
st.set_page_config(
    page_title="XpenseIQ",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if "token" not in st.session_state:
    st.session_state.token = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "email" not in st.session_state:
    st.session_state.email = None

if "page" not in st.session_state:
    st.session_state.page = "dashboard"


def get_headers():
    """
    Returns authorization headers for all API calls.
    Every protected API call needs this header.
    """
    return {"Authorization": f"Bearer {st.session_state.token}"}


def main():
    """
    Main function that controls which page to show.
    If user is not logged in, show login page.
    If user is logged in, show the main app.
    """
    if not st.session_state.token:
        show_login_page()
    else:
        show_main_app()


def show_login_page():
    """
    Shows the login and registration page.
    """
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title("💰 XpenseIQ")
        st.subheader("AI-powered Smart Expense Scanner")
        st.divider()

        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.subheader("Login to your account")
            email = st.text_input("Email", key="login_email")
            password = st.text_input(
                "Password", type="password", key="login_password"
            )
            if st.button("Login", use_container_width=True):
                if email and password:
                    login(email, password)
                else:
                    st.error("Please enter email and password")

        with tab2:
            st.subheader("Create new account")
            full_name = st.text_input("Full Name", key="reg_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input(
                "Password", type="password", key="reg_password"
            )
            if st.button("Register", use_container_width=True):
                if full_name and reg_email and reg_password:
                    register(full_name, reg_email, reg_password)
                else:
                    st.error("Please fill all fields")


def login(email: str, password: str):
    """
    Calls the login API and stores the token in session state.
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            data={
                "username": email,
                "password": password,
                "grant_type": "password"
            }
        )

        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.user_id = data["user_id"]
            st.session_state.email = data["email"]
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid email or password")

    except Exception as e:
        st.error(f"Cannot connect to server: {str(e)}")


def register(full_name: str, email: str, password: str):
    """
    Calls the register API to create a new account.
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/register",
            params={
                "email": email,
                "password": password,
                "full_name": full_name
            }
        )

        if response.status_code == 200:
            st.success("Account created! Please login.")
        else:
            error = response.json().get("detail", "Registration failed")
            st.error(error)

    except Exception as e:
        st.error(f"Cannot connect to server: {str(e)}")


def show_main_app():
    """
    Shows the main application after login.
    Sidebar for navigation, main area for content.
    """
    with st.sidebar:
        st.title("💰 XpenseIQ")
        st.write(f"Welcome, {st.session_state.email}")
        st.divider()

        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

        if st.button("📷 Scan Receipt", use_container_width=True):
            st.session_state.page = "scan"
            st.rerun()

        if st.button("📋 My Expenses", use_container_width=True):
            st.session_state.page = "expenses"
            st.rerun()

        st.divider()

        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user_id = None
            st.session_state.email = None
            st.session_state.page = "dashboard"
            st.rerun()

    if st.session_state.page == "dashboard":
        show_dashboard()
    elif st.session_state.page == "scan":
        show_scan_page()
    elif st.session_state.page == "expenses":
        show_expenses_page()
    else:
        show_dashboard()


def show_dashboard():
    """
    Shows the main dashboard with metrics and charts.
    """
    st.title("📊 Dashboard")

    try:
        response = requests.get(
            f"{BACKEND_URL}/expenses/summary",
            headers=get_headers()
        )
        summary = response.json()

    except Exception as e:
        st.error(f"Could not load dashboard: {str(e)}")
        return

    # Metric cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Spend",
            value=f"₹{summary.get('total_spend', 0):,.2f}"
        )

    with col2:
        st.metric(
            label="Transactions",
            value=summary.get("transaction_count", 0)
        )

    with col3:
        st.metric(
            label="Flagged",
            value=summary.get("flagged_count", 0),
            delta="needs review" if summary.get(
                "flagged_count", 0) > 0 else "all clear"
        )

    with col4:
        st.metric(
            label="Avg Transaction",
            value=f"₹{summary.get('avg_transaction', 0):,.2f}"
        )

    st.divider()

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spend by Category")
        category_data = summary.get("category_breakdown", {})

        if category_data:
            import pandas as pd
            df = pd.DataFrame(
                list(category_data.items()),
                columns=["Category", "Amount"]
            )
            st.bar_chart(df.set_index("Category"))
        else:
            st.info("No expense data yet. Scan your first receipt!")

    with col2:
        st.subheader("Payment Methods")
        payment_data = summary.get("payment_method_breakdown", {})

        if payment_data:
            import pandas as pd
            df = pd.DataFrame(
                list(payment_data.items()),
                columns=["Method", "Count"]
            )
            st.bar_chart(df.set_index("Method"))
        else:
            st.info("No payment data yet.")

    # Recent expenses table
    st.divider()
    st.subheader("Recent Expenses")

    try:
        response = requests.get(
            f"{BACKEND_URL}/expenses/",
            headers=get_headers()
        )
        data = response.json()
        expenses = data.get("expenses", [])[:5]

        if expenses:
            import pandas as pd
            df = pd.DataFrame(expenses)
            display_cols = [
                "vendor_name", "total_amount",
                "primary_category", "transaction_date",
                "fraud_risk_score"
            ]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True)
        else:
            st.info("No expenses yet.")

    except Exception as e:
        st.error(f"Could not load recent expenses: {str(e)}")


def show_scan_page():
    """
    Shows the receipt upload and scanning page.
    """
    st.title("📷 Scan Receipt")
    st.write("Upload a receipt image or PDF to extract expense data automatically.")

    uploaded_file = st.file_uploader(
        "Choose a receipt image or PDF",
        type=["jpg", "jpeg", "png", "webp", "bmp", "tiff", "pdf"],
        help="Supported formats: JPG, PNG, WEBP, BMP, TIFF, PDF"
    )

    if uploaded_file is not None:
        if uploaded_file.type != "application/pdf":
            st.image(uploaded_file, caption="Uploaded Receipt", width=300)

        st.info(f"File: {uploaded_file.name} ({uploaded_file.type})")

        if st.button("🔍 Scan Receipt", use_container_width=True):
            with st.spinner("Processing receipt... This may take a few seconds."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/expenses/scan-receipt",
                        headers=get_headers(),
                        files={"file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type
                        )}
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.success(
                            f"Receipt scanned successfully! Expense ID: {result['expense_id']}"
                        )

                        # Show extracted data
                        st.subheader("Extracted Data")
                        extracted = result.get("extracted_data", {})

                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Vendor:**", extracted.get(
                                "vendor_name", "Unknown"))
                            st.write("**Date:**", extracted.get(
                                "transaction_date", "Unknown"))
                            st.write("**Total Amount:**",
                                     f"₹{extracted.get('total_amount', 0)}")
                            st.write("**Payment Method:**",
                                     extracted.get("payment_method", "Unknown"))
                            st.write("**Receipt No:**",
                                     extracted.get("receipt_number", "N/A"))
                            if extracted.get("gstin"):
                                st.write("**GSTIN:**",
                                         extracted.get("gstin"))

                        with col2:
                            classification = result.get("classification", {})
                            st.write("**Category:**", classification.get(
                                "primary_category", "Unknown"))
                            st.write("**Subcategory:**",
                                     classification.get("subcategory", "Unknown"))
                            fraud = result.get("fraud_analysis", {})
                            risk = fraud.get("fraud_risk_score", 0)
                            if risk >= 0.5:
                                st.error(f"**Fraud Risk:** {risk:.2f} — HIGH")
                            elif risk >= 0.3:
                                st.warning(f"**Fraud Risk:** {risk:.2f} — MEDIUM")
                            else:
                                st.success(f"**Fraud Risk:** {risk:.2f} — LOW")
                            ocr = result.get("ocr", {})
                            st.write("**OCR Confidence:**",
                                     f"{ocr.get('confidence_score', 0):.2f}")
                            st.write("**File Type:**",
                                     ocr.get("source", "image").upper())
                            if ocr.get("pages"):
                                st.write("**Pages:**", ocr.get("pages"))

                        # Fraud flags
                        fraud_flags = fraud.get("fraud_flags", [])
                        if fraud_flags:
                            st.warning("⚠️ Fraud Flags Detected:")
                            for flag in fraud_flags:
                                st.write(f"• {flag}")

                        # Line items
                        line_items = extracted.get("line_items", [])
                        if line_items:
                            st.subheader("Line Items")
                            import pandas as pd
                            df = pd.DataFrame(line_items)
                            st.dataframe(df, use_container_width=True)

                    else:
                        error = response.json().get("detail", "Scan failed")
                        st.error(f"Error: {error}")

                except Exception as e:
                    st.error(f"Could not connect to server: {str(e)}")


def show_expenses_page():
    """
    Shows all expenses with search and filter options.
    """
    import pandas as pd

    st.title("📋 My Expenses")

    # Filters
    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            vendor_filter = st.text_input("Vendor Name")
            category_filter = st.selectbox(
                "Category",
                ["", "Food & Dining", "Travel & Transport",
                 "Health & Medical", "Office & Supplies",
                 "Utilities", "Entertainment", "Shopping",
                 "Education", "Finance", "Miscellaneous"]
            )

        with col2:
            start_date = st.date_input("Start Date", value=None)
            end_date = st.date_input("End Date", value=None)

        with col3:
            min_amount = st.number_input(
                "Min Amount", min_value=0.0, value=0.0)
            max_amount = st.number_input(
                "Max Amount", min_value=0.0, value=0.0)
            show_flagged = st.checkbox("Show only flagged")

    # Build filter params
    params = {}
    if vendor_filter:
        params["vendor_name"] = vendor_filter
    if category_filter:
        params["category"] = category_filter
    if start_date:
        params["start_date"] = str(start_date)
    if end_date:
        params["end_date"] = str(end_date)
    if min_amount > 0:
        params["min_amount"] = min_amount
    if max_amount > 0:
        params["max_amount"] = max_amount
    if show_flagged:
        params["requires_review"] = True

    # Fetch expenses
    try:
        response = requests.get(
            f"{BACKEND_URL}/expenses/",
            headers=get_headers(),
            params=params
        )
        data = response.json()
        expenses = data.get("expenses", [])

        # Summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Expenses", data.get("count", 0))
        with col2:
            st.metric("Total Spend",
                      f"₹{data.get('total_spend', 0):,.2f}")
        with col3:
            st.metric("Flagged", data.get("flagged_count", 0))

        if expenses:
            df = pd.DataFrame(expenses)
            display_cols = [
                "id", "vendor_name", "total_amount",
                "primary_category", "transaction_date",
                "payment_method", "fraud_risk_score",
                "requires_manual_review"
            ]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True)

            # Download as CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="expenses.csv",
                mime="text/csv"
            )
        else:
            st.info(
                "No expenses found. Try adjusting your filters or scan a receipt.")

    except Exception as e:
        st.error(f"Could not load expenses: {str(e)}")


main()