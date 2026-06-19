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

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
* { font-family: 'Inter', sans-serif !important; }
[data-testid="stAppViewContainer"] { background: #FDF4F7 !important; }
[data-testid="stMain"] { background: #FDF4F7 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
[data-testid="stFileUploaderDropzone"] button { display: none !important; }
details summary p { display: none !important; }
details summary::after { display: none !important; }

button[kind="primary"] {
    background-color: #FFFFFF !important;
    color: #22C55E !important;
    border: 1px solid #22C55E !important;
}
button[kind="primary"]:hover {
    background-color: #F0FDF4 !important;
    color: #16A34A !important;
    border-color: #16A34A !important;
}

button[kind="secondary"] {
    background-color: #FFFFFF !important;
    color: #EC105C !important;
    border: 1px solid #EC105C !important;
}
button[kind="secondary"]:hover {
    background-color: #FDF2F6 !important;
    color: #AA225B !important;
    border-color: #AA225B !important;
}
</style>
"""
st.html(CSS)


DEFAULT_STATE = {
    "token": None,
    "user_id": None,
    "email": None,
    "full_name": None,
    "page": "dashboard",
    "scan_results": [],
    "scan_index": 0,
}
for key, default_value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def get_greeting():
    import datetime
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    return "Good evening"


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
    import pandas as pd

    st.markdown(
        f"<p class='dash-greeting'>{get_greeting()}, "
        f"<strong>{get_display_name()}</strong> — "
        f"here's what needs your attention right now.</p>",
        unsafe_allow_html=True
    )

    try:
        summary = requests.get(
            f"{BACKEND_URL}/expenses/summary", headers=get_headers()
        ).json()
        all_expenses = requests.get(
            f"{BACKEND_URL}/expenses/", headers=get_headers()
        ).json().get("expenses", [])
        pending_expenses = requests.get(
            f"{BACKEND_URL}/expenses/pending", headers=get_headers()
        ).json().get("expenses", [])
        rejected_expenses = requests.get(
            f"{BACKEND_URL}/expenses/",
            headers=get_headers(),
            params={"status": "rejected"}
        ).json().get("expenses", [])
    except Exception as e:
        st.error(f"Could not load dashboard: {str(e)}")
        return

    if not all_expenses and not pending_expenses:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;">
          <div style="font-size:64px;margin-bottom:16px;">📊</div>
          <div style="font-size:22px;font-weight:700;color:#2D1B2E;margin-bottom:8px;">
            Welcome to XpenseIQ
          </div>
          <div style="font-size:14px;color:#8A6D7C;margin-bottom:24px;">
            Start by uploading your first expense receipt to see insights here.
          </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Upload Your First Receipt", type="primary"):
            st.session_state.page = "scan"
            st.rerun()
        return

    total = summary.get("total_spend", 0)
    approved_count = summary.get("transaction_count", 0)
    pending_count = summary.get("pending_count", 0)
    rejected_count = summary.get("rejected_count", 0)
    rejected_total = sum(e.get("total_amount", 0) or 0 for e in rejected_expenses)
    total_volume = approved_count + pending_count + rejected_count

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4, gap="large")

    with c1:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
             padding:22px 24px;border-top:4px solid #F59E0B;
             box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
          <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
               letter-spacing:.08em;margin-bottom:12px;">Pending Approvals</div>
          <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
            {pending_count}
          </div>
          <div style="font-size:12px;color:#F59E0B;margin-top:8px;font-weight:600;">
            {'⚠ Needs review' if pending_count > 0 else '✓ All clear'}
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
             padding:22px 24px;border-top:4px solid #22C55E;
             box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
          <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
               letter-spacing:.08em;margin-bottom:12px;">Approved This Month</div>
          <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
            {approved_count}
          </div>
          <div style="font-size:12px;color:#22C55E;margin-top:8px;font-weight:600;">
            Rs {total:,.0f} total value
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
             padding:22px 24px;border-top:4px solid #EF4444;
             box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
          <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
               letter-spacing:.08em;margin-bottom:12px;">Rejected This Month</div>
          <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
            {rejected_count}
          </div>
          <div style="font-size:12px;color:#EF4444;margin-top:8px;font-weight:600;">
            Rs {rejected_total:,.0f} blocked
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
             padding:22px 24px;border-top:4px solid #E91E63;
             box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
          <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
               letter-spacing:.08em;margin-bottom:12px;">Total Expense Volume</div>
          <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
            {total_volume}
          </div>
          <div style="font-size:12px;color:#E91E63;margin-top:8px;font-weight:600;">
            Rs {total:,.0f} approved spend
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    col_main, col_side = st.columns([1.75, 1])

    with col_main:
        st.markdown("""
        <div style="
            background:#FFFFFF;
            border:1px solid #F0DCE4;
            border-radius:18px;
            padding:18px;
            box-shadow:0 2px 10px rgba(45,27,46,.05);
            margin-bottom:10px;
        ">
        <div style="
            font-size:15px;
            font-weight:700;
            color:#2D1B2E;
            margin-bottom:10px;
        ">
            Monthly Spending Snapshot
        </div>
        """, unsafe_allow_html=True)

        if all_expenses:
            df = pd.DataFrame(all_expenses)
            if "transaction_date" in df.columns and "total_amount" in df.columns:
                df["transaction_date"] = pd.to_datetime(
                    df["transaction_date"], errors="coerce"
                )
                df = df.dropna(subset=["transaction_date"])
                if not df.empty:
                    df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
                    monthly = (
                        df.groupby("month")["total_amount"]
                        .sum()
                        .reset_index()
                        .sort_values("month")
                        .tail(6)
                    )
                    monthly.columns = ["Month", "Amount (Rs)"]
                    st.area_chart(
                        monthly.set_index("Month"),
                        color="#E91E63",
                        height=220
                    )
                else:
                    st.info("Not enough date data for trend chart.")
            else:
                st.info("No spending trend data available.")
        else:
            st.info("No approved expenses yet.")

    st.markdown("</div>", unsafe_allow_html=True)

    with col_side:
        activities = []
        for e in (all_expenses or [])[:3]:
            activities.append({
                "action": "Expense approved",
                "vendor": e.get("vendor_name", "Unknown"),
                "amount": e.get("total_amount", 0),
                "status": "approved",
                "color": "#22C55E"
            })
        for e in (pending_expenses or [])[:2]:
            activities.append({
                "action": "Pending review",
                "vendor": e.get("vendor_name", "Unknown"),
                "amount": e.get("total_amount", 0),
                "status": "pending",
                "color": "#F59E0B"
            })
        for e in (rejected_expenses or [])[:2]:
            activities.append({
                "action": "Expense rejected",
                "vendor": e.get("vendor_name", "Unknown"),
                "amount": e.get("total_amount", 0),
                "status": "rejected",
                "color": "#EF4444"
            })

        if activities:
            rows_html = ""
            for act in activities[:6]:
                rows_html += (
                    f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;'
                    f'border-bottom:1px solid #F3D6E0;">'
                    f'<div style="width:8px;height:8px;border-radius:50%;'
                    f'background:{act["color"]};flex-shrink:0;"></div>'
                    f'<div style="flex:1;min-width:0;">'
                    f'<div style="font-size:12px;font-weight:600;color:#2D1B2E;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                    f'{act["vendor"]}</div>'
                    f'<div style="font-size:11px;color:#8A6D7C;">{act["action"]}</div>'
                    f'</div>'
                    f'<div style="font-size:12px;font-weight:600;color:#2D1B2E;flex-shrink:0;">'
                    f'Rs {act["amount"]:,.0f}</div>'
                    f'</div>'
                )
        else:
            rows_html = '<div style="font-size:12px;color:#8A6D7C;">No recent activity.</div>'

        card_html = (
            '<div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:18px;'
            'padding:18px;box-shadow:0 2px 10px rgba(45,27,46,.05);">'
            '<div style="font-size:15px;font-weight:700;color:#2D1B2E;margin-bottom:12px;">'
            'Recent Activity</div>'
            f'{rows_html}'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    if pending_expenses:
        st.markdown("""
        <div style="font-size:15px;font-weight:700;color:#2D1B2E;margin-bottom:10px;">
          Items Requiring Attention
        </div>
        """, unsafe_allow_html=True)

        high_risk = sorted(
            pending_expenses,
            key=lambda x: x.get("fraud_risk_score", 0) or 0,
            reverse=True
        )[:5]

        rows = ""
        for e in high_risk:
            risk = e.get("fraud_risk_score", 0) or 0
            risk_color = "#EF4444" if risk >= 0.7 else "#F59E0B" if risk >= 0.5 else "#8A6D7C"
            rows += f"""
            <tr style="border-bottom:1px solid #F3D6E0;">
              <td style="padding:10px 12px;font-weight:500;color:#2D1B2E;font-size:12px;">
                {e.get('vendor_name','Unknown')}
              </td>
              <td style="padding:10px 12px;font-weight:600;color:#E91E63;font-size:12px;">
                Rs {e.get('total_amount',0):,.0f}
              </td>
              <td style="padding:10px 12px;font-size:12px;">
                <span style="font-weight:700;color:{risk_color};">{risk:.2f}</span>
              </td>
              <td style="padding:10px 12px;font-size:12px;color:#8A6D7C;">
                {e.get('transaction_date','—')}
              </td>
            </tr>"""

        st.markdown(f"""
        <div style="background:#fff;border:1px solid #F3D6E0;border-radius:14px;
             overflow:hidden;box-shadow:0 1px 4px rgba(45,27,46,.06);">
          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="background:#FCF7F9;">
                <th style="padding:10px 12px;text-align:left;font-size:10px;font-weight:700;
                     color:#8A6D7C;text-transform:uppercase;letter-spacing:.06em;">Vendor</th>
                <th style="padding:10px 12px;text-align:left;font-size:10px;font-weight:700;
                     color:#8A6D7C;text-transform:uppercase;letter-spacing:.06em;">Amount</th>
                <th style="padding:10px 12px;text-align:left;font-size:10px;font-weight:700;
                     color:#8A6D7C;text-transform:uppercase;letter-spacing:.06em;">Risk Score</th>
                <th style="padding:10px 12px;text-align:left;font-size:10px;font-weight:700;
                     color:#8A6D7C;text-transform:uppercase;letter-spacing:.06em;">Date</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("View All Pending", type="primary"):
            st.session_state.page = "pending"
            st.rerun()

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:15px;font-weight:700;color:#2D1B2E;margin-bottom:10px;">
      Quick Insights
    </div>
    """, unsafe_allow_html=True)

    i1, i2, i3 = st.columns(3)

    if all_expenses:
        df = pd.DataFrame(all_expenses)

        with i1:
            if "primary_category" in df.columns and "total_amount" in df.columns:
                top_cat = (
                    df.groupby("primary_category")["total_amount"]
                    .sum()
                    .idxmax()
                )
                top_cat_amt = df.groupby("primary_category")["total_amount"].sum().max()
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #F3D6E0;border-radius:14px;
                     padding:16px 18px;box-shadow:0 1px 4px rgba(45,27,46,.06);">
                  <div style="font-size:11px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                       letter-spacing:.06em;margin-bottom:6px;">Top Spending Category</div>
                  <div style="font-size:16px;font-weight:700;color:#2D1B2E;">{top_cat}</div>
                  <div style="font-size:12px;color:#E91E63;margin-top:4px;">Rs {top_cat_amt:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

        with i2:
            if "vendor_name" in df.columns and "total_amount" in df.columns:
                top_vendor = (
                    df.groupby("vendor_name")["total_amount"]
                    .sum()
                    .idxmax()
                )
                top_vendor_amt = df.groupby("vendor_name")["total_amount"].sum().max()
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #F3D6E0;border-radius:14px;
                     padding:16px 18px;box-shadow:0 1px 4px rgba(45,27,46,.06);">
                  <div style="font-size:11px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                       letter-spacing:.06em;margin-bottom:6px;">Top Vendor This Month</div>
                  <div style="font-size:16px;font-weight:700;color:#2D1B2E;">{top_vendor}</div>
                  <div style="font-size:12px;color:#E91E63;margin-top:4px;">Rs {top_vendor_amt:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

        with i3:
            potential = total * 0.08
            st.markdown(f"""
            <div style="background:#fff;border:1px solid #F3D6E0;border-radius:14px;
                 padding:16px 18px;box-shadow:0 1px 4px rgba(45,27,46,.06);">
              <div style="font-size:11px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                   letter-spacing:.06em;margin-bottom:6px;">Potential Savings</div>
              <div style="font-size:16px;font-weight:700;color:#2D1B2E;">Rs {potential:,.0f}</div>
              <div style="font-size:12px;color:#22C55E;margin-top:4px;">~8% of total spend</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    alerts = []
    for e in pending_expenses:
        risk = e.get("fraud_risk_score", 0) or 0
        flags = e.get("fraud_flags", []) or []
        if risk >= 0.7:
            alerts.append(
                f"High risk expense from {e.get('vendor_name','Unknown')} — "
                f"Rs {e.get('total_amount',0):,.0f} (Risk: {risk:.2f})"
            )
        for flag in flags:
            if "duplicate" in flag.lower():
                alerts.append(
                    f"Duplicate receipt detected — "
                    f"{e.get('vendor_name','Unknown')} Rs {e.get('total_amount',0):,.0f}"
                )
                break

    if alerts:
        st.markdown("""
        <div style="font-size:15px;font-weight:700;color:#2D1B2E;margin-bottom:10px;">
          Alerts
        </div>
        """, unsafe_allow_html=True)
        for alert in alerts[:4]:
            st.warning(alert)

    try:
        insights = requests.get(
            f"{BACKEND_URL}/expenses/insights", headers=get_headers()
        ).json().get("insights", [])
        if insights:
            st.markdown("""
            <div style="font-size:15px;font-weight:700;color:#2D1B2E;
                 margin-bottom:10px;margin-top:20px;">
              AI Spending Insights
            </div>
            """, unsafe_allow_html=True)
            for insight in insights:
                st.info(insight)
    except Exception:
        pass


def show_scan_page():
    st.title("Scan Receipt")
    st.caption("Upload invoices and let AI extract, validate and analyse all details automatically.")

    col_left, col_center, col_right = st.columns([1, 1.2, 1])

    with col_left:
        st.markdown("#### Upload Document")

        uploaded_files = st.file_uploader(
            "Drop files here",
            type=["jpg", "jpeg", "png", "webp", "bmp", "tiff", "pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        st.caption("Supported: JPG, PNG, WEBP, TIFF, BMP, PDF · Max 10MB per file")

        if uploaded_files:
            st.markdown("---")
            st.markdown(f"**{len(uploaded_files)} file(s) ready**")
            for f in uploaded_files:
                ftype = "PDF" if "pdf" in f.type else "Image"
                size = f.size / 1024
                status = "🟡 Ready"
                st.markdown(f"""
                <div style="padding:8px 10px;margin-bottom:6px;border-radius:8px;
                     border:1px solid #e0e0e0;background:#fafafa;font-size:12px;">
                  <div style="font-weight:600;color:#1C1424;">{f.name}</div>
                  <div style="color:#6D6578;margin-top:2px;">{ftype} · {size:.1f} KB · {status}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            if st.button("Scan All Receipts", use_container_width=True, type="primary"):
                import time
                results = []
                bar = st.progress(0)
                status_txt = st.empty()

                for i, file in enumerate(uploaded_files):
                    status_txt.write(f"Processing {file.name} ({i+1}/{len(uploaded_files)})...")
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
                    time.sleep(0.1)

                bar.empty()
                status_txt.empty()
                st.session_state["scan_results"] = results
                st.session_state["scan_index"] = 0
                st.rerun()

        if "scan_results" in st.session_state and st.session_state["scan_results"]:
            results = st.session_state["scan_results"]
            ok = sum(1 for r in results if r["status"] == "success")
            fail = len(results) - ok
            pending = sum(
                1 for r in results
                if r["status"] == "success" and
                r["data"].get("expense_status") == "pending_verification"
            )
            approved = ok - pending

            st.markdown("---")
            st.markdown("#### Processing Summary")
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Approved", approved)
                st.metric("Failed", fail)
            with m2:
                st.metric("Pending Review", pending)
                st.metric("Total", len(results))

            st.markdown("#### Recent Uploads")
            for i, r in enumerate(results):
                if r["status"] == "success":
                    exp_status = r["data"].get("expense_status", "approved")
                    icon = "✅" if exp_status == "approved" else "⚠️"
                else:
                    icon = "❌"

                if st.button(
                    f"{icon} {r['filename']}",
                    key=f"file_select_{i}",
                    use_container_width=True
                ):
                    st.session_state["scan_index"] = i
                    st.rerun()

    with col_center:
        st.markdown("#### Document Viewer")

        if "scan_results" not in st.session_state or not st.session_state["scan_results"]:
            st.markdown("""
            <div style="border:2px dashed #D9CCE0;border-radius:16px;padding:60px 20px;
                 text-align:center;background:#FBF8FC;margin-top:8px;">
              <div style="font-size:48px;margin-bottom:12px;">📄</div>
              <div style="font-size:14px;font-weight:600;color:#4B4458;margin-bottom:6px;">
                No document selected
              </div>
              <div style="font-size:12px;color:#6D6578;">
                Upload a receipt on the left to preview it here
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            results = st.session_state["scan_results"]
            idx = st.session_state.get("scan_index", 0)
            result = results[idx]

            if len(results) > 1:
                nav1, nav2, nav3 = st.columns([1, 2, 1])
                with nav1:
                    if st.button("Prev", disabled=idx == 0):
                        st.session_state["scan_index"] = idx - 1
                        st.rerun()
                with nav2:
                    st.markdown(
                        f"<div style='text-align:center;font-size:12px;color:#6D6578;padding-top:8px;'>"
                        f"Document {idx+1} of {len(results)}</div>",
                        unsafe_allow_html=True
                    )
                with nav3:
                    if st.button("Next", disabled=idx == len(results)-1):
                        st.session_state["scan_index"] = idx + 1
                        st.rerun()

            st.markdown(f"**{result['filename']}**")

            if result["status"] == "success":
                data = result["data"]
                extracted = data.get("extracted_data", {})
                ocr = data.get("ocr", {})
                expense_status = data.get("expense_status", "approved")

                conf = ocr.get("confidence_score", 0)
                conf_color = "#AA225B" if conf < 0.6 else "#8E40B0" if conf < 0.8 else "#2d6a4f"
                st.markdown(f"""
                <div style="margin-bottom:12px;">
                  <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                    <span style="font-size:11px;font-weight:600;color:#6D6578;">OCR CONFIDENCE</span>
                    <span style="font-size:11px;font-weight:700;color:{conf_color};">{conf:.0%}</span>
                  </div>
                  <div style="background:#EAE2EE;border-radius:4px;height:6px;">
                    <div style="width:{int(conf*100)}%;height:100%;background:{conf_color};border-radius:4px;"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if expense_status == "approved":
                    st.success("Approved — added to expenses")
                else:
                    st.warning("Pending Verification — awaiting review")

                st.markdown(f"""
                <div style="background:#FBF8FC;border:1px solid #EAE2EE;border-radius:12px;padding:14px;margin-top:8px;">
                  <div style="font-size:11px;font-weight:700;color:#6D6578;text-transform:uppercase;
                       letter-spacing:.06em;margin-bottom:10px;">Document Metadata</div>
                  <table style="width:100%;font-size:12px;border-collapse:collapse;">
                    <tr><td style="color:#6D6578;padding:3px 0;">File Type</td>
                        <td style="font-weight:500;color:#1C1424;text-align:right;">{ocr.get('source','image').upper()}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">Pages</td>
                        <td style="font-weight:500;color:#1C1424;text-align:right;">{ocr.get('pages',1)}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">Words Extracted</td>
                        <td style="font-weight:500;color:#1C1424;text-align:right;">{ocr.get('word_count',0)}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">Expense ID</td>
                        <td style="font-weight:500;color:#1C1424;text-align:right;">#{data.get('expense_id')}</td></tr>
                  </table>
                </div>
                """, unsafe_allow_html=True)

                items = extracted.get("line_items", [])
                if items:
                    st.markdown("**Line Items**")
                    import pandas as pd
                    st.dataframe(
                        pd.DataFrame(items),
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.error(f"Failed: {result.get('error', 'Unknown error')}")

    with col_right:
        st.markdown("#### AI Analysis")

        if "scan_results" not in st.session_state or not st.session_state["scan_results"]:
            st.markdown("""
            <div style="border:1px solid #EAE2EE;border-radius:12px;padding:40px 16px;
                 text-align:center;background:#FBF8FC;margin-top:8px;">
              <div style="font-size:36px;margin-bottom:10px;">🤖</div>
              <div style="font-size:13px;font-weight:600;color:#4B4458;margin-bottom:4px;">
                AI Ready
              </div>
              <div style="font-size:11px;color:#6D6578;">
                Upload and scan a receipt to see AI extraction results
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            results = st.session_state["scan_results"]
            idx = st.session_state.get("scan_index", 0)
            result = results[idx]

            if result["status"] == "success":
                data = result["data"]
                extracted = data.get("extracted_data", {})
                classification = data.get("classification", {})
                fraud = data.get("fraud_analysis", {})
                risk = fraud.get("fraud_risk_score", 0) or 0

                st.markdown(f"""
                <div style="background:#FBF8FC;border:1px solid #EAE2EE;border-radius:12px;
                     padding:14px;margin-bottom:10px;">
                  <div style="font-size:11px;font-weight:700;color:#6D6578;text-transform:uppercase;
                       letter-spacing:.06em;margin-bottom:8px;">Vendor Information</div>
                  <div style="font-size:15px;font-weight:700;color:#1C1424;margin-bottom:2px;">
                    {extracted.get('vendor_name','Unknown')}
                  </div>
                  <div style="font-size:11px;color:#6D6578;">{extracted.get('vendor_category_hint','—')}</div>
                  {f'<div style="font-size:11px;color:#8E40B0;margin-top:4px;">GSTIN: {extracted.get("gstin")}</div>' if extracted.get('gstin') else ''}
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:#FBF8FC;border:1px solid #EAE2EE;border-radius:12px;
                     padding:14px;margin-bottom:10px;">
                  <div style="font-size:11px;font-weight:700;color:#6D6578;text-transform:uppercase;
                       letter-spacing:.06em;margin-bottom:8px;">Amount Breakdown</div>
                  <table style="width:100%;font-size:12px;border-collapse:collapse;">
                    <tr><td style="color:#6D6578;padding:3px 0;">Subtotal</td>
                        <td style="text-align:right;font-weight:500;">Rs {extracted.get('subtotal','—')}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">{extracted.get('tax_type','Tax')}</td>
                        <td style="text-align:right;font-weight:500;">Rs {extracted.get('tax_amount','—')}</td></tr>
                    <tr style="border-top:1px solid #EAE2EE;">
                      <td style="font-weight:700;color:#1C1424;padding-top:6px;">Total</td>
                      <td style="text-align:right;font-weight:700;color:#AA225B;font-size:14px;padding-top:6px;">
                        Rs {extracted.get('total_amount',0):,.2f}
                      </td>
                    </tr>
                  </table>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:#FBF8FC;border:1px solid #EAE2EE;border-radius:12px;
                     padding:14px;margin-bottom:10px;">
                  <div style="font-size:11px;font-weight:700;color:#6D6578;text-transform:uppercase;
                       letter-spacing:.06em;margin-bottom:8px;">Invoice Details</div>
                  <table style="width:100%;font-size:12px;border-collapse:collapse;">
                    <tr><td style="color:#6D6578;padding:3px 0;">Date</td>
                        <td style="text-align:right;font-weight:500;">{extracted.get('transaction_date','—')}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">Receipt No</td>
                        <td style="text-align:right;font-weight:500;">{extracted.get('receipt_number','—')}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">Payment</td>
                        <td style="text-align:right;font-weight:500;">{extracted.get('payment_method','—')}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">Currency</td>
                        <td style="text-align:right;font-weight:500;">{extracted.get('currency_code','INR')}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">Category</td>
                        <td style="text-align:right;font-weight:500;">{classification.get('primary_category','—')}</td></tr>
                    <tr><td style="color:#6D6578;padding:3px 0;">Subcategory</td>
                        <td style="text-align:right;font-weight:500;">{classification.get('subcategory','—')}</td></tr>
                  </table>
                </div>
                """, unsafe_allow_html=True)

                risk_color = "#EC105C" if risk >= 0.5 else "#c2410c" if risk >= 0.3 else "#8E40B0"
                risk_label = "HIGH RISK" if risk >= 0.5 else "MEDIUM" if risk >= 0.3 else "LOW RISK"
                risk_bg = "#fff5f5" if risk >= 0.5 else "#fffbf0" if risk >= 0.3 else "#f5edfb"

                flags = fraud.get("fraud_flags", [])
                flags_html = "".join(
                    f'<div style="font-size:11px;color:#AA225B;padding:2px 0;">• {f}</div>'
                    for f in flags
                ) if flags else '<div style="font-size:11px;color:#6D6578;">No flags detected</div>'

                dup = fraud.get("is_duplicate", False)
                near_dup = fraud.get("is_near_duplicate", False)
                if dup:
                    dup_html = (
                        f'<div style="font-size:11px;color:#EC105C;font-weight:600;margin-top:4px;">'
                        f'DUPLICATE — matches Expense #{fraud.get("duplicate_match_id")}</div>'
                    )
                elif near_dup:
                    dup_html = (
                        '<div style="font-size:11px;color:#c2410c;font-weight:600;margin-top:4px;">'
                        'POSSIBLE DUPLICATE — similar bill found</div>'
                    )
                else:
                    dup_html = '<div style="font-size:11px;color:#8E40B0;margin-top:4px;">No duplicate found</div>'

                st.markdown(f"""
                <div style="background:{risk_bg};border:1px solid #EAE2EE;border-radius:12px;
                     padding:14px;margin-bottom:10px;">
                  <div style="font-size:11px;font-weight:700;color:#6D6578;text-transform:uppercase;
                       letter-spacing:.06em;margin-bottom:8px;">Fraud & Risk Assessment</div>
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-size:12px;font-weight:600;color:{risk_color};">Risk Score</span>
                    <span style="font-size:14px;font-weight:700;color:{risk_color};">{risk:.2f} — {risk_label}</span>
                  </div>
                  <div style="background:#EAE2EE;border-radius:4px;height:6px;margin-bottom:10px;">
                    <div style="width:{int(risk*100)}%;height:100%;background:{risk_color};border-radius:4px;"></div>
                  </div>
                  <div style="font-size:11px;font-weight:600;color:#6D6578;margin-bottom:4px;">Fraud Flags</div>
                  {flags_html}
                  <div style="font-size:11px;font-weight:600;color:#6D6578;margin-top:8px;margin-bottom:2px;">Duplicate Check</div>
                  {dup_html}
                </div>
                """, unsafe_allow_html=True)

                expense_status = data.get("expense_status", "approved")
                if expense_status == "pending_verification":
                    expense_id = data.get("expense_id")
                    st.markdown("**Review Action Required**")
                    ba, br = st.columns(2)
                    with ba:
                        if st.button("Approve", key=f"scan_app_{expense_id}",
                                     use_container_width=True, type="primary"):
                            r = requests.put(
                                f"{BACKEND_URL}/expenses/{expense_id}/approve",
                                headers=get_headers()
                            )
                            if r.status_code == 200:
                                st.success("Approved!")
                                st.rerun()
                    with br:
                        if st.button("Reject", key=f"scan_rej_{expense_id}",
                                     use_container_width=True):
                            r = requests.put(
                                f"{BACKEND_URL}/expenses/{expense_id}/reject",
                                headers=get_headers()
                            )
                            if r.status_code == 200:
                                st.success("Rejected")
                                st.rerun()
            else:
                st.error(f"Processing failed: {result.get('error','Unknown error')}")


def show_expenses_page():
    import pandas as pd

    st.markdown(
        "<h1 style='display:flex;align-items:center;gap:8px;margin-bottom:0;'>"
        "My Expenses</h1>",
        unsafe_allow_html=True
    )
    st.caption("Showing approved expenses only.")

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1.2])
        with col1:
            vendor_filter = st.text_input("Search by vendor", placeholder="Search vendor name")
        with col2:
            category_filter = st.selectbox("Category", [
                "", "Food & Dining", "Travel & Transport", "Health & Medical",
                "Office & Supplies", "Utilities", "Entertainment",
                "Shopping", "Education", "Finance", "Miscellaneous"
            ])
        with col3:
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
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
        data = requests.get(
            f"{BACKEND_URL}/expenses/", headers=get_headers(), params=params
        ).json()
        expenses = data.get("expenses", [])

        st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

        kpi1, kpi2, kpi3 = st.columns(3)

        with kpi1:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:18px 20px;box-shadow:0 2px 10px rgba(45,27,46,.05);
                 display:flex;align-items:center;gap:16px;">
              <div style="width:48px;height:48px;border-radius:50%;background:#FCE0E8;
                   display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;">
                👛
              </div>
              <div>
                <div style="font-size:13px;color:#6D6578;margin-bottom:2px;">Total Expenses</div>
                <div style="font-size:26px;font-weight:800;color:#1C1424;">{data.get('count', 0)}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        with kpi2:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:18px 20px;box-shadow:0 2px 10px rgba(45,27,46,.05);
                 display:flex;align-items:center;gap:16px;">
              <div style="width:48px;height:48px;border-radius:50%;background:#F3E8FB;
                   display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;">
                💲
              </div>
              <div>
                <div style="font-size:13px;color:#6D6578;margin-bottom:2px;">Total Spend</div>
                <div style="font-size:26px;font-weight:800;color:#1C1424;">Rs {data.get('total_spend', 0):,.2f}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        with kpi3:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:18px 20px;box-shadow:0 2px 10px rgba(45,27,46,.05);
                 display:flex;align-items:center;gap:16px;">
              <div style="width:48px;height:48px;border-radius:50%;background:#FEF3E2;
                   display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;">
                🚩
              </div>
              <div>
                <div style="font-size:13px;color:#6D6578;margin-bottom:2px;">Flagged</div>
                <div style="font-size:26px;font-weight:800;color:#1C1424;">{data.get('flagged_count', 0)}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            header_left, header_right = st.columns([3, 1])
            with header_left:
                st.markdown(
                    "<div style='font-size:16px;font-weight:700;color:#1C1424;padding-top:6px;'>"
                    "Approved Expenses</div>",
                    unsafe_allow_html=True
                )
            with header_right:
                if expenses:
                    df_for_csv = pd.DataFrame(expenses)
                    csv = df_for_csv.to_csv(index=False)
                    st.download_button(
                        "⬇ Download as CSV", data=csv,
                        file_name="expenses.csv", mime="text/csv",
                        use_container_width=True
                    )

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
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.caption(f"Showing {len(expenses)} approved expense(s)")
            else:
                st.info("No expenses found.")
    except Exception as e:
        st.error(f"Could not load expenses: {str(e)}")

def show_pending_page():
    st.title("Pending Verification")
    st.caption("Flagged expenses awaiting review. These are NOT counted in totals.")

    st.markdown("""
    <style>
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

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
            flags = expense.get("fraud_flags", []) or []

            if risk >= 0.7:
                risk_label = "HIGH"
            elif risk >= 0.5:
                risk_label = "MEDIUM"
            else:
                risk_label = "LOW"

            risk_color = "#EC105C" if risk >= 0.5 else "#c2410c" if risk >= 0.3 else "#8E40B0"
            risk_bg = "#FCE4EC" if risk >= 0.5 else "#FFF3E0" if risk >= 0.3 else "#F3E8FB"

            if flags:
                flag_html = (
                    "<div style='font-size:13px;font-weight:700;color:#1C1424;"
                    "margin-bottom:4px;'>Fraud Flags:</div>"
                )
                for f in flags:
                    flag_html += (
                        "<div style='font-size:13px;color:#1C1424;margin-bottom:4px;'>"
                        "<span style='color:#EC105C;'>●</span> <strong>" + str(f) + "</strong></div>"
                    )
            else:
                flag_html = "<div style='font-size:13px;color:#6D6578;'>No flags detected</div>"

            with st.container(border=True):
                st.markdown(
                    "<div style='font-size:11px;font-weight:700;color:#8E40B0;"
                    "text-transform:uppercase;letter-spacing:.08em;"
                    "border-bottom:1px solid #F0DCE4;padding-bottom:10px;margin-bottom:14px;'>"
                    "Review Details</div>",
                    unsafe_allow_html=True
                )

                col_details, col_risk, col_buttons = st.columns([1.1, 2, 1.1])

                with col_details:
                    st.markdown(
                        "<div style='background:#FFFFFF;padding:4px;'>"
                        "<div style='font-size:12px;color:#6D6578;'>Vendor:</div>"
                        "<div style='font-size:15px;font-weight:700;color:#1C1424;margin-bottom:12px;'>"
                        + str(expense.get('vendor_name', '—')) + "</div>"
                        "<div style='font-size:12px;color:#6D6578;'>Amount:</div>"
                        "<div style='font-size:15px;font-weight:700;color:#E91E63;margin-bottom:12px;'>Rs "
                        + f"{expense.get('total_amount', 0):,.2f}" + "</div>"
                        "<div style='font-size:12px;color:#6D6578;'>Category:</div>"
                        "<div style='font-size:15px;font-weight:700;color:#1C1424;margin-bottom:12px;'>"
                        + str(expense.get('primary_category', '—')) + "</div>"
                        "<div style='font-size:12px;color:#6D6578;'>Date:</div>"
                        "<div style='font-size:15px;font-weight:700;color:#1C1424;'>"
                        + str(expense.get('transaction_date', '—')) + "</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )

                with col_risk:
                    st.markdown(
                        "<div style='background:#FFFFFF;padding:4px;'>"
                        "<div style='background:" + risk_bg + ";border-radius:10px;"
                        "padding:14px 16px;margin-bottom:14px;'>"
                        "<span style='font-size:14px;font-weight:600;color:" + risk_color + ";'>"
                        "🛡️ Fraud Risk: <strong>" + f"{risk:.2f} — {risk_label}" + "</strong></span>"
                        "</div>"
                        "<div style='font-size:13px;color:#1C1424;margin-bottom:14px;'>"
                        "OCR Confidence: <strong style='color:#EC105C;'>"
                        + f"{expense.get('confidence_score', 0):.0%}" + "</strong></div>"
                        + flag_html +
                        "</div>",
                        unsafe_allow_html=True
                    )

                with col_buttons:
                    st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
                    if st.button("✅ Approve", key=f"app_{expense['id']}",
                                 use_container_width=True, type="primary"):
                        r = requests.put(
                            f"{BACKEND_URL}/expenses/{expense['id']}/approve",
                            headers=get_headers()
                        )
                        if r.status_code == 200:
                            st.success("Approved!")
                            st.rerun()
                        else:
                            st.error("Failed")
                    if st.button("❌ Reject", key=f"rej_{expense['id']}",
                                 use_container_width=True, type="secondary"):
                        r = requests.put(
                            f"{BACKEND_URL}/expenses/{expense['id']}/reject",
                            headers=get_headers()
                        )
                        if r.status_code == 200:
                            st.success("Rejected")
                            st.rerun()
                        else:
                            st.error("Failed")

            st.markdown("<div style='margin-bottom:18px;'></div>", unsafe_allow_html=True)

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

        header_html = (
            "<div style='background:#FFFFFF;border:1px solid #F0DCE4;border-radius:14px;"
            "overflow:hidden;box-shadow:0 2px 10px rgba(45,27,46,.05);'>"
            "<table style='width:100%;border-collapse:collapse;'>"
            "<thead><tr style='background:#FAF5F7;'>"
            "<th style='padding:14px 18px;text-align:left;font-size:13px;font-weight:700;color:#1C1424;'>ID</th>"
            "<th style='padding:14px 18px;text-align:left;font-size:13px;font-weight:700;color:#1C1424;'>Vendor Name</th>"
            "<th style='padding:14px 18px;text-align:left;font-size:13px;font-weight:700;color:#1C1424;'>Total Amount</th>"
            "<th style='padding:14px 18px;text-align:left;font-size:13px;font-weight:700;color:#1C1424;'>Primary Category</th>"
            "<th style='padding:14px 18px;text-align:left;font-size:13px;font-weight:700;color:#1C1424;'>Transaction Date</th>"
            "<th style='padding:14px 18px;text-align:left;font-size:13px;font-weight:700;color:#1C1424;'>Fraud Risk Score</th>"
            "</tr></thead><tbody>"
        )

        rows_html = ""
        for i, e in enumerate(expenses):
            risk = e.get("fraud_risk_score", 0) or 0
            rows_html += (
                "<tr style='border-top:1px solid #F0DCE4;'>"
                f"<td style='padding:14px 18px;font-size:14px;color:#6D6578;'>{i}</td>"
                f"<td style='padding:14px 18px;font-size:14px;font-weight:700;color:#1C1424;'>{e.get('vendor_name', '—')}</td>"
                f"<td style='padding:14px 18px;font-size:14px;color:#1C1424;'>{e.get('total_amount', 0):,.0f}</td>"
                f"<td style='padding:14px 18px;font-size:14px;color:#1C1424;'>{e.get('primary_category', '—')}</td>"
                f"<td style='padding:14px 18px;font-size:14px;color:#1C1424;'>{e.get('transaction_date', '—')}</td>"
                "<td style='padding:14px 18px;'>"
                "<span style='background:#FCE0E8;color:#EC105C;font-weight:700;font-size:13px;"
                f"padding:4px 12px;border-radius:20px;display:inline-block;'>{risk:.1f}</span>"
                "</td>"
                "</tr>"
            )

        footer_html = "</tbody></table></div>"

        st.markdown(header_html + rows_html + footer_html, unsafe_allow_html=True)

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

        # ── KPI Cards ────────────────────────────────────────────────
        kpi_data = [
            ("👛", "#FCE0E8", "Total Spend", f"Rs {summary.get('total_spend', 0):,.2f}"),
            ("⇄", "#F3E8FB", "Transactions", str(summary.get("transaction_count", 0))),
            ("📈", "#FEF0E6", "Avg Transaction", f"Rs {summary.get('avg_transaction', 0):,.2f}"),
            ("🕐", "#E3F8EC", "Pending Review", str(summary.get("pending_count", 0))),
        ]
        kcols = st.columns(4)
        for col, (icon, bg, label, value) in zip(kcols, kpi_data):
            with col:
                st.markdown(f"""
                <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                     padding:18px 20px;box-shadow:0 2px 10px rgba(45,27,46,.05);
                     display:flex;align-items:center;gap:14px;">
                  <div style="width:44px;height:44px;border-radius:50%;background:{bg};
                       display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">
                    {icon}
                  </div>
                  <div>
                    <div style="font-size:13px;color:#6D6578;margin-bottom:2px;">{label}</div>
                    <div style="font-size:22px;font-weight:800;color:#1C1424;">{value}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        # ── Spend by Category ───────────────────────────────────────
        with col1:
            st.markdown(
                "<div style='font-size:17px;font-weight:700;color:#1C1424;margin-bottom:10px;'>"
                "Spend by Category</div>",
                unsafe_allow_html=True
            )
            cat_data = summary.get("category_breakdown", {})
            if cat_data:
                df_cat = pd.DataFrame(
                    list(cat_data.items()), columns=["Category", "Amount"]
                )
                df_cat["Share"] = (
                    df_cat["Amount"] / df_cat["Amount"].sum() * 100
                ).round(1).astype(str) + "%"

                table_html = (
                    "<div style='background:#FFFFFF;border:1px solid #F0DCE4;border-radius:12px;"
                    "overflow:hidden;margin-bottom:14px;'>"
                    "<table style='width:100%;border-collapse:collapse;'>"
                    "<thead><tr style='background:#FCE0E8;'>"
                    "<th style='padding:10px 14px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Category</th>"
                    "<th style='padding:10px 14px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Amount (Rs)</th>"
                    "<th style='padding:10px 14px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Share</th>"
                    "</tr></thead><tbody>"
                )
                for _, row in df_cat.iterrows():
                    table_html += (
                        "<tr style='border-top:1px solid #F3E1E8;'>"
                        f"<td style='padding:10px 14px;font-size:13px;color:#1C1424;'>{row['Category']}</td>"
                        f"<td style='padding:10px 14px;font-size:13px;color:#1C1424;'>{row['Amount']:,.0f}</td>"
                        f"<td style='padding:10px 14px;font-size:13px;color:#1C1424;'>{row['Share']}</td>"
                        "</tr>"
                    )
                table_html += "</tbody></table></div>"
                st.markdown(table_html, unsafe_allow_html=True)

                chart_df = df_cat.set_index("Category")[["Amount"]]
                chart_df.columns = ["Amount (Rs)"]
                st.bar_chart(chart_df, color="#EC105C")

        # ── Top 5 Vendors ────────────────────────────────────────────
        with col2:
            st.markdown(
                "<div style='font-size:17px;font-weight:700;color:#1C1424;margin-bottom:10px;'>"
                "Top 5 Vendors</div>",
                unsafe_allow_html=True
            )
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

                table_html = (
                    "<div style='background:#FFFFFF;border:1px solid #F0DCE4;border-radius:12px;"
                    "overflow:hidden;margin-bottom:14px;'>"
                    "<table style='width:100%;border-collapse:collapse;'>"
                    "<thead><tr style='background:#FCE0E8;'>"
                    "<th style='padding:10px 14px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Vendor</th>"
                    "<th style='padding:10px 14px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Total Spend (Rs)</th>"
                    "</tr></thead><tbody>"
                )
                for _, row in top_v.iterrows():
                    table_html += (
                        "<tr style='border-top:1px solid #F3E1E8;'>"
                        f"<td style='padding:10px 14px;font-size:13px;color:#1C1424;'>{row['Vendor']}</td>"
                        f"<td style='padding:10px 14px;font-size:13px;color:#1C1424;'>{row['Total Spend']:,.0f}</td>"
                        "</tr>"
                    )
                table_html += "</tbody></table></div>"
                st.markdown(table_html, unsafe_allow_html=True)

                chart_df = top_v.set_index("Vendor")[["Total Spend"]]
                chart_df.columns = ["Amount (Rs)"]
                st.bar_chart(chart_df, color="#EC105C")

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        # ── All Approved Expenses ───────────────────────────────────
        header_left, header_right = st.columns([3, 1])
        with header_left:
            st.markdown(
                "<div style='font-size:17px;font-weight:700;color:#1C1424;padding-top:6px;'>"
                "All Approved Expenses</div>",
                unsafe_allow_html=True
            )

        df_all = pd.DataFrame(expenses)
        with header_right:
            if not df_all.empty:
                csv = df_all.to_csv(index=False)
                st.download_button(
                    "⬇ Download as CSV", data=csv,
                    file_name="xpenseiq_report.csv", mime="text/csv",
                    use_container_width=True
                )

        if not df_all.empty:
            table_html = (
                "<div style='background:#FFFFFF;border:1px solid #F0DCE4;border-radius:12px;"
                "overflow:hidden;margin-top:10px;box-shadow:0 2px 10px rgba(45,27,46,.05);'>"
                "<table style='width:100%;border-collapse:collapse;'>"
                "<thead><tr style='background:#FCE0E8;'>"
                "<th style='padding:12px 16px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Vendor Name</th>"
                "<th style='padding:12px 16px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Total Amount (Rs)</th>"
                "<th style='padding:12px 16px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Primary Category</th>"
                "<th style='padding:12px 16px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Transaction Date</th>"
                "<th style='padding:12px 16px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Payment Method</th>"
                "<th style='padding:12px 16px;text-align:left;font-size:12px;font-weight:700;color:#1C1424;'>Fraud Risk Score</th>"
                "</tr></thead><tbody>"
            )
            for _, row in df_all.iterrows():
                risk = row.get("fraud_risk_score", 0) or 0
                vendor = row.get("vendor_name") or "—"
                amount = row.get("total_amount")
                amount_str = f"{amount:,.2f}" if amount is not None else "—"
                category = row.get("primary_category") or "—"
                date = row.get("transaction_date") or "—"
                payment = row.get("payment_method") or "—"

                badge_color = "#16A34A" if risk < 0.3 else "#c2410c" if risk < 0.5 else "#EC105C"
                badge_bg = "#E3F8EC" if risk < 0.3 else "#FEF3E2" if risk < 0.5 else "#FCE0E8"

                table_html += (
                    "<tr style='border-top:1px solid #F3E1E8;'>"
                    f"<td style='padding:12px 16px;font-size:13px;font-weight:700;color:#1C1424;'>{vendor}</td>"
                    f"<td style='padding:12px 16px;font-size:13px;color:#1C1424;'>{amount_str}</td>"
                    f"<td style='padding:12px 16px;font-size:13px;color:#1C1424;'>{category}</td>"
                    f"<td style='padding:12px 16px;font-size:13px;color:#1C1424;'>{date}</td>"
                    f"<td style='padding:12px 16px;font-size:13px;color:#1C1424;'>{payment}</td>"
                    "<td style='padding:12px 16px;'>"
                    f"<span style='background:{badge_bg};color:{badge_color};font-weight:700;font-size:12px;"
                    f"padding:3px 10px;border-radius:20px;display:inline-block;'>{risk:.1f}</span>"
                    "</td>"
                    "</tr>"
                )
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Could not load reports: {str(e)}")

main()