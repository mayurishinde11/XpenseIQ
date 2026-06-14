# app.py
# Main Streamlit application.
# This is the entry point of our frontend dashboard.
# Run with: streamlit run app.py

import streamlit as st
import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

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
if "full_name" not in st.session_state:
    st.session_state.full_name = None
if "page" not in st.session_state:
    st.session_state.page = "dashboard"


def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def get_display_name():
    """Returns full name if available, otherwise email username"""
    if st.session_state.full_name:
        return st.session_state.full_name
    elif st.session_state.email:
        return st.session_state.email.split("@")[0].title()
    return "User"


def main():
    if not st.session_state.token:
        show_login_page()
    else:
        show_main_app()


def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title("💰 XpenseIQ")
        st.subheader("AI-powered Smart Expense Scanner")
        st.divider()

        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.subheader("Login to your account")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", use_container_width=True):
                if email and password:
                    login(email, password)
                else:
                    st.error("Please enter email and password")

        with tab2:
            st.subheader("Create new account")
            full_name = st.text_input("Full Name", key="reg_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            if st.button("Register", use_container_width=True):
                if full_name and reg_email and reg_password:
                    register(full_name, reg_email, reg_password)
                else:
                    st.error("Please fill all fields")


def login(email: str, password: str):
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            data={"username": email, "password": password, "grant_type": "password"}
        )

        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.user_id = data["user_id"]
            st.session_state.email = data["email"]
            # Save full_name from response — fallback to email username
            st.session_state.full_name = data.get("full_name") or email.split("@")[0].title()
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid email or password")

    except Exception as e:
        st.error(f"Cannot connect to server: {str(e)}")


def register(full_name: str, email: str, password: str):
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/register",
            params={"email": email, "password": password, "full_name": full_name}
        )

        if response.status_code == 200:
            st.success("Account created! Please login.")
        else:
            error = response.json().get("detail", "Registration failed")
            st.error(error)

    except Exception as e:
        st.error(f"Cannot connect to server: {str(e)}")


def show_main_app():
    with st.sidebar:
        st.title("💰 XpenseIQ")
        # ← FIXED: Show Full Name instead of email
        st.write(f"Welcome, **{get_display_name()}**")
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
            st.session_state.full_name = None
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
    st.title("📊 Dashboard")
    st.markdown(f"Welcome back, **{get_display_name()}**! 👋")

    try:
        response = requests.get(f"{BACKEND_URL}/expenses/summary", headers=get_headers())
        summary = response.json()
    except Exception as e:
        st.error(f"Could not load dashboard: {str(e)}")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="Total Spend", value=f"₹{summary.get('total_spend', 0):,.2f}")
    with col2:
        st.metric(label="Transactions", value=summary.get("transaction_count", 0))
    with col3:
        st.metric(
            label="Flagged",
            value=summary.get("flagged_count", 0),
            delta="needs review" if summary.get("flagged_count", 0) > 0 else "all clear"
        )
    with col4:
        st.metric(label="Avg Transaction", value=f"₹{summary.get('avg_transaction', 0):,.2f}")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spend by Category")
        category_data = summary.get("category_breakdown", {})
        if category_data:
            import pandas as pd
            df = pd.DataFrame(list(category_data.items()), columns=["Category", "Amount"])
            st.bar_chart(df.set_index("Category"))
        else:
            st.info("No expense data yet. Scan your first receipt!")

    with col2:
        st.subheader("Payment Methods")
        payment_data = summary.get("payment_method_breakdown", {})
        if payment_data:
            import pandas as pd
            df = pd.DataFrame(list(payment_data.items()), columns=["Method", "Count"])
            st.bar_chart(df.set_index("Method"))
        else:
            st.info("No payment data yet.")

    st.divider()
    st.subheader("Recent Expenses")

    try:
        response = requests.get(f"{BACKEND_URL}/expenses/", headers=get_headers())
        data = response.json()
        expenses = data.get("expenses", [])[:5]

        if expenses:
            import pandas as pd
            df = pd.DataFrame(expenses)
            display_cols = ["vendor_name", "total_amount", "primary_category", "transaction_date", "fraud_risk_score"]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True)
        else:
            st.info("No expenses yet.")

    except Exception as e:
        st.error(f"Could not load recent expenses: {str(e)}")


def show_scan_page():
    st.title("📷 Scan Receipt")
    st.write("Upload **multiple receipts** at once — mix JPG, PNG and PDF files together!")
    st.info("💡 **Tip:** Hold **Ctrl** (Windows) or **Cmd** (Mac) to select multiple files at once.")

    # ← FIXED: Multiple file upload
    uploaded_files = st.file_uploader(
        "Choose receipt images or PDFs",
        type=["jpg", "jpeg", "png", "webp", "bmp", "tiff", "pdf"],
        accept_multiple_files=True,  # ← allows multiple files
        help="Hold Ctrl/Cmd to select multiple files. Mix JPG, PNG and PDF freely."
    )

    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected**")

        # Preview files
        for f in uploaded_files:
            size_kb = f.size / 1024
            if "pdf" in f.type:
                icon = "📄"
            elif "png" in f.type:
                icon = "🖼️"
            else:
                icon = "📸"
            st.write(f"{icon} **{f.name}** — {size_kb:.1f} KB")

        st.write("")

        if st.button(f"🔍 Scan All {len(uploaded_files)} Receipt(s)", use_container_width=True):
            import time
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, file in enumerate(uploaded_files):
                status_text.write(f"⏳ Processing **{file.name}** ({i+1}/{len(uploaded_files)})...")

                try:
                    response = requests.post(
                        f"{BACKEND_URL}/expenses/scan-receipt",
                        headers=get_headers(),
                        files={"file": (file.name, file.getvalue(), file.type)},
                        timeout=60
                    )

                    if response.status_code == 200:
                        result = response.json()
                        results.append({
                            "status": "success",
                            "filename": file.name,
                            "filetype": file.type,
                            "data": result
                        })
                    else:
                        try:
                            error = response.json().get("detail", "Scan failed")
                        except:
                            error = f"Server error {response.status_code}"
                        results.append({
                            "status": "error",
                            "filename": file.name,
                            "filetype": file.type,
                            "error": error
                        })

                except requests.exceptions.Timeout:
                    results.append({
                        "status": "error",
                        "filename": file.name,
                        "filetype": file.type,
                        "error": "Request timed out. Please try again."
                    })
                except Exception as e:
                    results.append({
                        "status": "error",
                        "filename": file.name,
                        "filetype": file.type,
                        "error": str(e)
                    })

                progress_bar.progress((i + 1) / len(uploaded_files))
                time.sleep(0.2)

            progress_bar.empty()
            status_text.empty()

            # Summary counts
            success_count = sum(1 for r in results if r["status"] == "success")
            error_count = len(results) - success_count

            col_s, col_e = st.columns(2)
            with col_s:
                if success_count > 0:
                    st.success(f"✅ {success_count} receipt(s) scanned successfully!")
            with col_e:
                if error_count > 0:
                    st.error(f"❌ {error_count} file(s) failed!")

            st.divider()
            st.subheader("📊 Results")

            # Show per-file results
            for result in results:
                filename = result["filename"]
                filetype = result["filetype"]

                if "pdf" in filetype:
                    icon = "📄"
                elif "png" in filetype:
                    icon = "🖼️"
                else:
                    icon = "📸"

                if result["status"] == "success":
                    data = result["data"]
                    extracted = data.get("extracted_data", {})
                    classification = data.get("classification", {})
                    fraud = data.get("fraud_analysis", {})
                    risk = fraud.get("fraud_risk_score", 0) or 0
                    amount = extracted.get("total_amount") or 0
                    vendor = extracted.get("vendor_name") or "Unknown"
                    expense_id = data.get("expense_id", "N/A")

                    # Green success card
                    st.success(f"{icon} **{filename}** — ✅ Scanned! | Expense #{expense_id} | Vendor: {vendor} | ₹{amount:,.0f}")

                    with st.expander(f"View details — {filename}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Vendor:**", extracted.get("vendor_name", "Unknown"))
                            st.write("**Date:**", extracted.get("transaction_date", "Unknown"))
                            st.write("**Total Amount:**", f"₹{extracted.get('total_amount', 0)}")
                            st.write("**Payment Method:**", extracted.get("payment_method", "Unknown"))
                            st.write("**Receipt No:**", extracted.get("receipt_number", "N/A"))
                            if extracted.get("gstin"):
                                st.write("**GSTIN:**", extracted.get("gstin"))

                        with col2:
                            st.write("**Category:**", classification.get("primary_category", "Unknown"))
                            st.write("**Subcategory:**", classification.get("subcategory", "Unknown"))
                            if risk >= 0.5:
                                st.error(f"**Fraud Risk:** {risk:.2f} — HIGH ⚠️")
                            elif risk >= 0.3:
                                st.warning(f"**Fraud Risk:** {risk:.2f} — MEDIUM ⚡")
                            else:
                                st.success(f"**Fraud Risk:** {risk:.2f} — LOW ✅")
                            ocr = data.get("ocr", {})
                            st.write("**OCR Confidence:**", f"{ocr.get('confidence_score', 0):.2f}")

                        fraud_flags = fraud.get("fraud_flags", [])
                        if fraud_flags:
                            st.warning("⚠️ Fraud Flags: " + " | ".join(fraud_flags))

                        line_items = extracted.get("line_items", [])
                        if line_items:
                            import pandas as pd
                            st.subheader("Line Items")
                            st.dataframe(pd.DataFrame(line_items), use_container_width=True)

                else:
                    # Red error card — shows exactly what went wrong per file
                    st.error(f"{icon} **{filename}** — ❌ Failed: {result.get('error', 'Unknown error')}")


def show_expenses_page():
    import pandas as pd

    st.title("📋 My Expenses")

    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            vendor_filter = st.text_input("Vendor Name")
            category_filter = st.selectbox(
                "Category",
                ["", "Food & Dining", "Travel & Transport", "Health & Medical",
                 "Office & Supplies", "Utilities", "Entertainment",
                 "Shopping", "Education", "Finance", "Miscellaneous"]
            )
        with col2:
            start_date = st.date_input("Start Date", value=None)
            end_date = st.date_input("End Date", value=None)
        with col3:
            min_amount = st.number_input("Min Amount", min_value=0.0, value=0.0)
            max_amount = st.number_input("Max Amount", min_value=0.0, value=0.0)
            show_flagged = st.checkbox("Show only flagged")

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

    try:
        response = requests.get(f"{BACKEND_URL}/expenses/", headers=get_headers(), params=params)
        data = response.json()
        expenses = data.get("expenses", [])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Expenses", data.get("count", 0))
        with col2:
            st.metric("Total Spend", f"₹{data.get('total_spend', 0):,.2f}")
        with col3:
            st.metric("Flagged", data.get("flagged_count", 0))

        if expenses:
            df = pd.DataFrame(expenses)
            display_cols = ["id", "vendor_name", "total_amount", "primary_category",
                            "transaction_date", "payment_method", "fraud_risk_score", "requires_manual_review"]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True)

            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="expenses.csv",
                mime="text/csv"
            )
        else:
            st.info("No expenses found. Try adjusting filters or scan a receipt.")

    except Exception as e:
        st.error(f"Could not load expenses: {str(e)}")


main()