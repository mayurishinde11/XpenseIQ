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

css = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
* { font-family: 'Inter', sans-serif !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
[data-testid="stFileUploaderDropzone"] button { display: none !important; }
details summary p { display: none !important; }
details summary::after { display: none !important; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

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
        st.title("XpenseIQ")
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


def login(email, password):
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
            st.session_state.full_name = data.get("full_name") or email.split("@")[0].title()
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid email or password")
    except Exception as e:
        st.error(f"Cannot connect to server: {str(e)}")


def register(full_name, email, password):
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/register",
            params={"email": email, "password": password, "full_name": full_name}
        )
        if response.status_code == 200:
            st.success("Account created! Please login.")
        else:
            st.error(response.json().get("detail", "Registration failed"))
    except Exception as e:
        st.error(f"Cannot connect to server: {str(e)}")


def show_main_app():
    with st.sidebar:
        st.title("XpenseIQ")
        st.write(f"Welcome, **{get_display_name()}**")
        st.divider()
        pages = [
            ("Dashboard", "dashboard"),
            ("Scan Receipt", "scan"),
            ("My Expenses", "expenses"),
            ("Pending Verification", "pending"),
            ("Rejected", "rejected"),
            ("Reports", "reports"),
        ]
        for label, page_key in pages:
            if st.button(label, use_container_width=True, key=f"nav_{page_key}"):
                st.session_state.page = page_key
                st.rerun()
        st.divider()
        if st.button("Logout", use_container_width=True, key="nav_logout"):
            for k in ["token", "user_id", "email", "full_name"]:
                st.session_state[k] = None
            st.session_state.page = "dashboard"
            st.rerun()

    page_map = {
        "dashboard": show_dashboard,
        "scan": show_scan_page,
        "expenses": show_expenses_page,
        "pending": show_pending_page,
        "rejected": show_rejected_page,
        "reports": show_reports_page,
    }
    page_map.get(st.session_state.page, show_dashboard)()


def show_dashboard():
    st.title("Dashboard")
    st.write(f"Welcome back, **{get_display_name()}**!")

    try:
        summary = requests.get(
            f"{BACKEND_URL}/expenses/summary", headers=get_headers()
        ).json()
    except Exception as e:
        st.error(f"Could not load dashboard: {str(e)}")
        return

    pending_count = summary.get("pending_count", 0)
    if pending_count > 0:
        st.warning(
            f"{pending_count} expense(s) pending verification. "
            f"Go to Pending Verification to review."
        )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Spend", f"Rs {summary.get('total_spend', 0):,.2f}")
    with col2:
        st.metric("Approved", summary.get("transaction_count", 0))
    with col3:
        st.metric("Pending Review", pending_count)
    with col4:
        st.metric("Avg Transaction", f"Rs {summary.get('avg_transaction', 0):,.2f}")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spend by Category")
        category_data = summary.get("category_breakdown", {})
        if category_data:
            import pandas as pd
            df = pd.DataFrame(
                list(category_data.items()), columns=["Category", "Amount"]
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
                list(payment_data.items()), columns=["Method", "Count"]
            )
            st.bar_chart(df.set_index("Method"))
        else:
            st.info("No payment data yet.")

    st.divider()
    st.subheader("Recent Approved Expenses")
    try:
        import pandas as pd
        expenses = requests.get(
            f"{BACKEND_URL}/expenses/", headers=get_headers()
        ).json().get("expenses", [])[:5]
        if expenses:
            df = pd.DataFrame(expenses)
            cols = ["vendor_name", "total_amount", "primary_category",
                    "transaction_date", "fraud_risk_score", "status"]
            cols = [c for c in cols if c in df.columns]
            st.dataframe(df[cols], use_container_width=True)
        else:
            st.info("No approved expenses yet.")
    except Exception as e:
        st.error(f"Could not load expenses: {str(e)}")

    try:
        insights = requests.get(
            f"{BACKEND_URL}/expenses/insights", headers=get_headers()
        ).json().get("insights", [])
        if insights:
            st.divider()
            st.subheader("AI Spending Insights")
            for insight in insights:
                st.info(insight)
    except Exception:
        pass


def show_scan_page():
    st.title("Scan Receipt")
    st.write("Upload receipts — images or PDFs. AI will extract all details automatically.")
    st.info("Invalid, blank, or dummy files are automatically rejected before processing.")

    st.write("**Upload Receipts**")
    uploaded_files = st.file_uploader(
        "Upload receipts",
        type=["jpg", "jpeg", "png", "webp", "bmp", "tiff", "pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected:**")
        for f in uploaded_files:
            file_type = "PDF" if "pdf" in f.type else "Image"
            st.write(f"- {file_type}: **{f.name}** ({f.size/1024:.1f} KB)")

        if st.button(f"Scan {len(uploaded_files)} Receipt(s)", use_container_width=True):
            import time
            results = []
            bar = st.progress(0)
            status = st.empty()

            for i, file in enumerate(uploaded_files):
                status.write(f"Processing {file.name} ({i+1}/{len(uploaded_files)})...")
                try:
                    r = requests.post(
                        f"{BACKEND_URL}/expenses/scan-receipt",
                        headers=get_headers(),
                        files={"file": (file.name, file.getvalue(), file.type)},
                        timeout=60
                    )
                    if r.status_code == 200:
                        results.append({
                            "status": "success",
                            "filename": file.name,
                            "filetype": file.type,
                            "data": r.json()
                        })
                    else:
                        results.append({
                            "status": "error",
                            "filename": file.name,
                            "filetype": file.type,
                            "error": r.json().get("detail", "Scan failed")
                        })
                except requests.exceptions.Timeout:
                    results.append({
                        "status": "error",
                        "filename": file.name,
                        "filetype": file.type,
                        "error": "Request timed out."
                    })
                except Exception as e:
                    results.append({
                        "status": "error",
                        "filename": file.name,
                        "filetype": file.type,
                        "error": str(e)
                    })
                bar.progress((i + 1) / len(uploaded_files))
                time.sleep(0.2)

            bar.empty()
            status.empty()

            ok = sum(1 for r in results if r["status"] == "success")
            fail = len(results) - ok

            col1, col2 = st.columns(2)
            with col1:
                if ok > 0:
                    st.success(f"{ok} receipt(s) scanned successfully!")
            with col2:
                if fail > 0:
                    st.error(f"{fail} file(s) failed!")

            st.divider()
            st.subheader("Results")

            for result in results:
                if result["status"] == "success":
                    data = result["data"]
                    extracted = data.get("extracted_data", {})
                    classification = data.get("classification", {})
                    fraud = data.get("fraud_analysis", {})
                    risk = fraud.get("fraud_risk_score", 0) or 0
                    expense_status = data.get("expense_status", "approved")
                    amount = extracted.get("total_amount") or 0
                    vendor = extracted.get("vendor_name") or "Unknown"

                    if expense_status == "approved":
                        st.success(
                            f"**{result['filename']}** — Approved | "
                            f"ID #{data.get('expense_id')} | {vendor} | Rs {amount:,.0f}"
                        )
                    else:
                        st.warning(
                            f"**{result['filename']}** — Pending Verification | "
                            f"ID #{data.get('expense_id')} | {vendor} | Rs {amount:,.0f}"
                        )

                    with st.expander(f"Details — {result['filename']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Vendor:**", extracted.get("vendor_name", "Unknown"))
                            st.write("**Date:**", extracted.get("transaction_date", "Unknown"))
                            st.write("**Amount:**", f"Rs {extracted.get('total_amount', 0)}")
                            st.write("**Payment:**", extracted.get("payment_method", "Unknown"))
                            st.write("**Receipt No:**", extracted.get("receipt_number", "N/A"))
                            if extracted.get("gstin"):
                                st.write("**GSTIN:**", extracted.get("gstin"))
                        with col2:
                            st.write("**Category:**", classification.get("primary_category", "Unknown"))
                            st.write("**Subcategory:**", classification.get("subcategory", "Unknown"))
                            st.write("**Status:**", expense_status.replace("_", " ").title())
                            if risk >= 0.5:
                                st.error(f"**Fraud Risk:** {risk:.2f} — HIGH")
                            elif risk >= 0.3:
                                st.warning(f"**Fraud Risk:** {risk:.2f} — MEDIUM")
                            else:
                                st.success(f"**Fraud Risk:** {risk:.2f} — LOW")
                            ocr = data.get("ocr", {})
                            st.write("**OCR Confidence:**", f"{ocr.get('confidence_score', 0):.2f}")

                        flags = fraud.get("fraud_flags", [])
                        if flags:
                            st.warning("Fraud Flags:")
                            for flag in flags:
                                st.write(f"- {flag}")

                        items = extracted.get("line_items", [])
                        if items:
                            import pandas as pd
                            st.subheader("Line Items")
                            st.dataframe(pd.DataFrame(items), use_container_width=True)
                else:
                    st.error(
                        f"**{result['filename']}** — Failed: "
                        f"{result.get('error', 'Unknown error')}"
                    )


def show_expenses_page():
    import pandas as pd
    st.title("My Expenses")
    st.caption("Showing approved expenses only.")

    col1, col2, col3 = st.columns(3)
    with col1:
        vendor_filter = st.text_input("Search by vendor")
    with col2:
        category_filter = st.selectbox("Category", [
            "", "Food & Dining", "Travel & Transport", "Health & Medical",
            "Office & Supplies", "Utilities", "Entertainment",
            "Shopping", "Education", "Finance", "Miscellaneous"
        ])
    with col3:
        show_flagged = st.checkbox("Show only flagged")

    col4, col5, col6, col7 = st.columns(4)
    with col4:
        start_date = st.date_input("From date", value=None)
    with col5:
        end_date = st.date_input("To date", value=None)
    with col6:
        min_amount = st.number_input("Min amount", min_value=0.0, value=0.0)
    with col7:
        max_amount = st.number_input("Max amount", min_value=0.0, value=0.0)

    params = {}
    if vendor_filter: params["vendor_name"] = vendor_filter
    if category_filter: params["category"] = category_filter
    if start_date: params["start_date"] = str(start_date)
    if end_date: params["end_date"] = str(end_date)
    if min_amount > 0: params["min_amount"] = min_amount
    if max_amount > 0: params["max_amount"] = max_amount
    if show_flagged: params["requires_review"] = True

    try:
        data = requests.get(
            f"{BACKEND_URL}/expenses/", headers=get_headers(), params=params
        ).json()
        expenses = data.get("expenses", [])

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Expenses", data.get("count", 0))
        with col2:
            st.metric("Total Spend", f"Rs {data.get('total_spend', 0):,.2f}")
        with col3:
            st.metric("Flagged", data.get("flagged_count", 0))

        if expenses:
            df = pd.DataFrame(expenses)
            display_cols = [
                "id", "vendor_name", "total_amount", "primary_category",
                "transaction_date", "payment_method", "fraud_risk_score", "status"
            ]
            display_cols = [c for c in display_cols if c in df.columns]
            df_display = df[display_cols].copy()
            df_display.columns = [
                {"id": "ID", "vendor_name": "Vendor", "total_amount": "Amount (Rs)",
                 "primary_category": "Category", "transaction_date": "Transaction Date",
                 "payment_method": "Payment Method", "fraud_risk_score": "Fraud Risk",
                 "status": "Status"}.get(c, c)
                for c in display_cols
            ]
            st.dataframe(df_display, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button(
                "Download as CSV", data=csv,
                file_name="expenses.csv", mime="text/csv"
            )
        else:
            st.info("No expenses found.")
    except Exception as e:
        st.error(f"Could not load expenses: {str(e)}")


def show_pending_page():
    st.title("Pending Verification")
    st.caption("Flagged expenses awaiting review. These are NOT counted in totals.")

    try:
        expenses = requests.get(
            f"{BACKEND_URL}/expenses/pending", headers=get_headers()
        ).json().get("expenses", [])

        if not expenses:
            st.success("No expenses pending verification. Everything looks clean!")
            return

        st.warning(f"{len(expenses)} expense(s) require your review.")

        for expense in expenses:
            risk = expense.get("fraud_risk_score", 0) or 0
            flags = expense.get("fraud_flags", [])
            risk_label = "HIGH" if risk >= 0.7 else "MEDIUM" if risk >= 0.5 else "LOW"

            with st.expander(
                f"ID #{expense.get('id')} — {expense.get('vendor_name', 'Unknown')} — "
                f"Rs {expense.get('total_amount', 0):,.0f} — Risk: {risk:.2f} ({risk_label})",
                expanded=True
            ):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write("**Vendor:**", expense.get("vendor_name", "—"))
                    st.write("**Amount:**", f"Rs {expense.get('total_amount', 0):,.2f}")
                    st.write("**Category:**", expense.get("primary_category", "—"))
                    st.write("**Date:**", expense.get("transaction_date", "—"))
                with col2:
                    if risk >= 0.5:
                        st.error(f"Fraud Risk: {risk:.2f} — {risk_label}")
                    else:
                        st.warning(f"Fraud Risk: {risk:.2f} — {risk_label}")
                    st.write("**OCR Confidence:**", f"{expense.get('confidence_score', 0):.0%}")
                    if flags:
                        st.write("**Fraud Flags:**")
                        for flag in flags:
                            st.write(f"- {flag}")
                with col3:
                    if st.button("Approve", key=f"app_{expense['id']}", use_container_width=True):
                        r = requests.put(
                            f"{BACKEND_URL}/expenses/{expense['id']}/approve",
                            headers=get_headers()
                        )
                        if r.status_code == 200:
                            st.success("Approved!")
                            st.rerun()
                        else:
                            st.error("Failed")
                    if st.button("Reject", key=f"rej_{expense['id']}", use_container_width=True):
                        r = requests.put(
                            f"{BACKEND_URL}/expenses/{expense['id']}/reject",
                            headers=get_headers()
                        )
                        if r.status_code == 200:
                            st.success("Rejected")
                            st.rerun()
                        else:
                            st.error("Failed")
    except Exception as e:
        st.error(f"Could not load pending expenses: {str(e)}")


def show_rejected_page():
    import pandas as pd
    st.title("Rejected Expenses")
    st.caption("Archived expenses excluded from all calculations.")

    try:
        expenses = requests.get(
            f"{BACKEND_URL}/expenses/",
            headers=get_headers(),
            params={"status": "rejected"}
        ).json().get("expenses", [])

        if not expenses:
            st.info("No rejected expenses.")
            return

        st.error(f"{len(expenses)} rejected expense(s) archived.")
        df = pd.DataFrame(expenses)
        display_cols = [
            "id", "vendor_name", "total_amount", "primary_category",
            "transaction_date", "fraud_risk_score"
        ]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)
    except Exception as e:
        st.error(f"Could not load rejected expenses: {str(e)}")


def show_reports_page():
    import pandas as pd
    st.title("Reports")
    st.caption("Summary of approved expenses only.")

    try:
        summary = requests.get(
            f"{BACKEND_URL}/expenses/summary", headers=get_headers()
        ).json()
        expenses = requests.get(
            f"{BACKEND_URL}/expenses/", headers=get_headers()
        ).json().get("expenses", [])

        if not expenses:
            st.info("No approved expenses yet.")
            return

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Spend", f"Rs {summary.get('total_spend', 0):,.2f}")
        with col2:
            st.metric("Transactions", summary.get("transaction_count", 0))
        with col3:
            st.metric("Avg Transaction", f"Rs {summary.get('avg_transaction', 0):,.2f}")
        with col4:
            st.metric("Pending Review", summary.get("pending_count", 0))

        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Spend by Category")
            cat_data = summary.get("category_breakdown", {})
            if cat_data:
                df_cat = pd.DataFrame(
                    list(cat_data.items()), columns=["Category", "Amount"]
                )
                df_cat["Share"] = (
                    df_cat["Amount"] / df_cat["Amount"].sum() * 100
                ).round(1).astype(str) + "%"
                st.dataframe(df_cat, use_container_width=True, hide_index=True)
                st.bar_chart(df_cat.set_index("Category")["Amount"])

        with col2:
            st.subheader("Top 5 Vendors")
            df_exp = pd.DataFrame(expenses)
            if "vendor_name" in df_exp.columns:
                top_v = (
                    df_exp.groupby("vendor_name")["total_amount"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                    .reset_index()
                )
                top_v.columns = ["Vendor", "Total Spend"]
                st.dataframe(top_v, use_container_width=True, hide_index=True)
                st.bar_chart(top_v.set_index("Vendor"))

        st.divider()
        st.subheader("All Approved Expenses")
        df_all = pd.DataFrame(expenses)
        if not df_all.empty:
            cols = [
                "vendor_name", "total_amount", "primary_category",
                "transaction_date", "payment_method", "fraud_risk_score"
            ]
            cols = [c for c in cols if c in df_all.columns]
            st.dataframe(df_all[cols], use_container_width=True, hide_index=True)
            csv = df_all.to_csv(index=False)
            st.download_button(
                "Download Report CSV", data=csv,
                file_name="xpenseiq_report.csv", mime="text/csv",
                use_container_width=True
            )
    except Exception as e:
        st.error(f"Could not load reports: {str(e)}")


main()