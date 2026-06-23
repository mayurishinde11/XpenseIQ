import streamlit as st
import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="XpenseIQ",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

css = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
* { font-family: 'Inter', sans-serif !important; }
[data-testid="stAppViewContainer"] { background: #FDF4F7 !important; }
[data-testid="stMain"] { background: #FDF4F7 !important; }
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
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = []
if "scan_index" not in st.session_state:
    st.session_state["scan_index"] = 0    


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
        st.image("logo.png", width=140)
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
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            st.image("logo.png", use_container_width=True)
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

    # Load data
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

    # Empty state
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

    # ── SECTION 1: KPI Cards ─────────────────────────────────────────────
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

    # ── SECTION 2: Spending Snapshot + Activity Feed ──────────────────────
    
    col_main, col_side = st.columns([1.75, 1])

    with col_main:
        st.markdown("""
        <div style="
            background:#FFFFFF;
            border:1px solid #F0DCE4;
            border-radius:18px;
            padding:28px 28px 8px 28px;
            box-shadow:0 2px 10px rgba(45,27,46,.05);
            margin-bottom:10px;
        ">
        <div style="
            font-size:15px;
            font-weight:700;
            color:#2D1B2E;
            margin-bottom:16px;
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
                    import altair as alt
                    chart = alt.Chart(monthly).mark_area(
                        color="#E91E63",
                        opacity=0.15,
                        line={"color": "#E91E63", "strokeWidth": 2}
                    ).encode(
                        x=alt.X("Month:N", axis=alt.Axis(
                            labelAngle=0,
                            title=None,
                            labelFontSize=11,
                            labelColor="#8A6D7C",
                            tickColor="#F0DCE4",
                            domainColor="#F0DCE4"
                        )),
                        y=alt.Y("Amount (Rs):Q", axis=alt.Axis(
                            title=None,
                            labelFontSize=11,
                            labelColor="#8A6D7C",
                            gridColor="#F9EDF3",
                            tickColor="#F0DCE4",
                            domainColor="#F0DCE4"
                        )),
                        tooltip=["Month", "Amount (Rs)"]
                    ).properties(
                        height=200,
                        padding={"left": 16, "right": 16, "top": 12, "bottom": 8}
                    ).configure_view(
                        strokeWidth=0
                    ).configure_axis(
                        grid=True
                    )
                    st.altair_chart(chart, use_container_width=True)
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

    # ── SECTION 3: Items Requiring Attention ─────────────────────────────
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

    # ── SECTION 4: Quick Insights ─────────────────────────────────────────
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
            avg = summary.get("avg_transaction", 0)
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

    # ── SECTION 5: Alerts ────────────────────────────────────────────────
    alerts = []
    for e in pending_expenses:
        risk = e.get("fraud_risk_score", 0) or 0
        flags = e.get("fraud_flags", []) or []
        if risk >= 0.7:
            alerts.append(f"High risk expense from {e.get('vendor_name','Unknown')} — Rs {e.get('total_amount',0):,.0f} (Risk: {risk:.2f})")
        for flag in flags:
            if "duplicate" in flag.lower():
                alerts.append(f"Duplicate receipt detected — {e.get('vendor_name','Unknown')} Rs {e.get('total_amount',0):,.0f}")
                break

    if alerts:
        st.markdown("""
        <div style="font-size:15px;font-weight:700;color:#2D1B2E;margin-bottom:10px;">
          Alerts
        </div>
        """, unsafe_allow_html=True)
        for alert in alerts[:4]:
            st.warning(alert)

    # ── SECTION 6: AI Insights ───────────────────────────────────────────
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

    st.markdown("""
    <style>
    [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border-radius: 14px !important;
            min-height: 340px !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:first-of-type {
        background-color: #FDF4F7 !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background-color: #FFFFFF !important;
        border: 2px dashed #E91E63 !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1.2, 1])

    with col_left:
        st.markdown("#### Upload Receipt")
        with st.container(border=True):
            uploaded_files = st.file_uploader(
                "Click to upload or drag and drop",
                type=["jpg", "jpeg", "png", "webp", "bmp", "tiff", "pdf"],
                accept_multiple_files=True,
            )
            st.caption("Supported: JPG, PNG, WEBP, TIFF, BMP, PDF · Max 10MB per file")

            if uploaded_files:
                st.markdown("---")
                st.markdown(f"**{len(uploaded_files)} file(s) ready**")
                for f in uploaded_files:
                    ftype = "PDF" if "pdf" in f.type else "Image"
                    size = f.size / 1024
                    st.markdown(f"""
                    <div style="padding:8px 10px;margin-bottom:6px;border-radius:8px;
                         border:1px solid #e0e0e0;background:#fafafa;font-size:12px;">
                      <div style="font-weight:600;color:#1C1424;">{f.name}</div>
                      <div style="color:#6D6578;margin-top:2px;">{ftype} · {size:.1f} KB · 🟡 Ready</div>
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

    with col_center:
        st.markdown("#### Document Viewer")
        with st.container(border=True):
            if "scan_results" not in st.session_state or not st.session_state["scan_results"]:
                st.markdown("""
                <div style="padding:60px 20px;text-align:center;">
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
                    <div style="background:#FBF8FC;border:1px solid #EAE2EE;border-radius:12px;
                         padding:14px;margin-top:8px;">
                      <div style="font-size:11px;font-weight:700;color:#6D6578;text-transform:uppercase;
                           letter-spacing:.06em;margin-bottom:10px;">Document Metadata</div>
                      <table style="width:100%;font-size:12px;border-collapse:collapse;">
                        <tr><td style="color:#6D6578;padding:6px 8px;">File Type</td>
                            <td style="font-weight:500;color:#1C1424;text-align:right;padding:6px 8px;">{ocr.get('source','image').upper()}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">Pages</td>
                            <td style="font-weight:500;color:#1C1424;text-align:right;padding:6px 8px;">{ocr.get('pages',1)}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">Words Extracted</td>
                            <td style="font-weight:500;color:#1C1424;text-align:right;padding:6px 8px;">{ocr.get('word_count',0)}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">Expense ID</td>
                            <td style="font-weight:500;color:#1C1424;text-align:right;padding:6px 8px;">#{data.get('expense_id')}</td></tr>
                      </table>
                    </div>
                    """, unsafe_allow_html=True)
                    items = extracted.get("line_items", [])
                    if items:
                        st.markdown("**Line Items**")
                        import pandas as pd
                        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
                else:
                    st.markdown(f"""
                    <div style="background:#FFF5F5;border:1px solid #FED7D7;border-radius:12px;
                         padding:20px;text-align:center;margin-top:20px;">
                      <div style="font-size:28px;margin-bottom:8px;">⚠️</div>
                      <div style="font-size:14px;font-weight:700;color:#C53030;margin-bottom:6px;">
                        Processing Failed
                      </div>
                      <div style="font-size:12px;color:#742A2A;">
                        {result.get('error', 'Unknown error')}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

    with col_right:
        st.markdown("#### AI Analysis")
        with st.container(border=True):
            if "scan_results" not in st.session_state or not st.session_state["scan_results"]:
                st.markdown("""
                <div style="padding:60px 16px;text-align:center;">
                  <div style="font-size:36px;margin-bottom:10px;">🤖</div>
                  <div style="font-size:13px;font-weight:600;color:#4B4458;margin-bottom:4px;">
                    AI Ready
                  </div>
                  <div style="font-size:11px;color:#6D6578;">
                    Upload and scan a receipt to see AI extracted results
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
                        <tr><td style="color:#6D6578;padding:6px 8px;">Subtotal</td>
                            <td style="text-align:right;font-weight:500;padding:6px 8px;">Rs {extracted.get('subtotal','—')}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">{extracted.get('tax_type','Tax')}</td>
                            <td style="text-align:right;font-weight:500;padding:6px 8px;">Rs {extracted.get('tax_amount','—')}</td></tr>
                        <tr style="border-top:1px solid #EAE2EE;">
                          <td style="font-weight:700;color:#1C1424;padding:8px 8px 4px 8px;">Total</td>
                          <td style="text-align:right;font-weight:700;color:#AA225B;font-size:14px;padding:8px 8px 4px 8px;">
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
                        <tr><td style="color:#6D6578;padding:6px 8px;">Date</td>
                            <td style="text-align:right;font-weight:500;padding:6px 8px;">{extracted.get('transaction_date','—')}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">Receipt No</td>
                            <td style="text-align:right;font-weight:500;padding:6px 8px;">{extracted.get('receipt_number','—')}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">Payment</td>
                            <td style="text-align:right;font-weight:500;padding:6px 8px;">{extracted.get('payment_method','—')}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">Currency</td>
                            <td style="text-align:right;font-weight:500;padding:6px 8px;">{extracted.get('currency_code','INR')}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">Category</td>
                            <td style="text-align:right;font-weight:500;padding:6px 8px;">{classification.get('primary_category','—')}</td></tr>
                        <tr><td style="color:#6D6578;padding:6px 8px;">Subcategory</td>
                            <td style="text-align:right;font-weight:500;padding:6px 8px;">{classification.get('subcategory','—')}</td></tr>
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

                else:
                    st.markdown(f"""
                    <div style="background:#FFF5F5;border:1px solid #FED7D7;border-radius:12px;
                         padding:20px;text-align:center;margin-top:20px;">
                      <div style="font-size:28px;margin-bottom:8px;">⚠️</div>
                      <div style="font-size:14px;font-weight:700;color:#C53030;margin-bottom:6px;">
                        Processing Failed
                      </div>
                      <div style="font-size:12px;color:#742A2A;">
                        {result.get('error', 'Unknown error')}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
    
def show_expenses_page():
    import pandas as pd
    st.title("My Expenses")
    st.caption("Showing approved expenses only.")

    st.markdown("""
    <style>
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stDateInput"] input,
    div[data-testid="stNumberInput"] input {
        background-color: #FFFFFF !important;
        border: 1px solid #F0DCE4 !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ── KPI Cards (same style as Dashboard/Reports) ──────────────────
        c1, c2, c3 = st.columns(3, gap="large")

        with c1:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:22px 24px;border-top:4px solid #E91E63;
                 box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
              <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                   letter-spacing:.08em;margin-bottom:12px;">Total Expenses</div>
              <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
                {data.get('count', 0)}
              </div>
              <div style="font-size:12px;color:#E91E63;margin-top:8px;font-weight:600;">
                Matching current filters
              </div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:22px 24px;border-top:4px solid #22C55E;
                 box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
              <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                   letter-spacing:.08em;margin-bottom:12px;">Total Spend</div>
              <div style="font-size:28px;font-weight:800;color:#2D1B2E;line-height:1;">
                Rs {data.get('total_spend', 0):,.0f}
              </div>
              <div style="font-size:12px;color:#22C55E;margin-top:8px;font-weight:600;">
                Approved expenses only
              </div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            flagged_count = data.get('flagged_count', 0)
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:22px 24px;border-top:4px solid #F59E0B;
                 box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
              <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                   letter-spacing:.08em;margin-bottom:12px;">Flagged</div>
              <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
                {flagged_count}
              </div>
              <div style="font-size:12px;color:#F59E0B;margin-top:8px;font-weight:600;">
                {'⚠ Needs review' if flagged_count > 0 else '✓ All clear'}
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # ── Table (same style as Rejected/Reports pages) ─────────────────
        if expenses:
            df_all = pd.DataFrame(expenses)

            st.markdown("""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:24px 24px 8px 24px;box-shadow:0 2px 12px rgba(45,27,46,.07);">
              <div style="font-size:15px;font-weight:700;color:#2D1B2E;margin-bottom:16px;
                   letter-spacing:-0.01em;">All Expenses</div>
            </div>
            """, unsafe_allow_html=True)

            rows_html = ""
            for _, row in df_all.iterrows():
                vendor = row.get("vendor_name", "—") or "—"
                amount = row.get("total_amount", 0) or 0
                category = row.get("primary_category", "—") or "—"
                date = str(row.get("transaction_date", "—") or "—")
                payment = row.get("payment_method", "—") or "—"
                status = row.get("status", "—") or "—"
                status_color = "#15803D" if status.lower() == "approved" else "#E91E63"
                status_bg = "#ECFDF5" if status.lower() == "approved" else "#FCF0F5"
                risk = row.get("fraud_risk_score", 0) or 0
                risk_pct = int(risk * 100)

                if risk >= 0.7:
                    risk_label = "High Risk"
                    bar_color = "#991B1B"
                    risk_text_color = "#991B1B"
                elif risk >= 0.4:
                    risk_label = "Medium Risk"
                    bar_color = "#E91E63"
                    risk_text_color = "#E91E63"
                else:
                    risk_label = "Low Risk"
                    bar_color = "#E91E63"
                    risk_text_color = "#8A6D7C"

                rows_html += f"""
                <tr style="border-bottom:1px solid #F3D6E0;">
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <div style="font-size:13px;font-weight:700;color:#2D1B2E;">{vendor}</div>
                    <div style="font-size:11px;color:#8A6D7C;margin-top:2px;">{category}</div>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <div style="font-size:14px;font-weight:700;color:#E91E63;">
                      Rs {amount:,.0f}
                    </div>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <div style="font-size:13px;color:#2D1B2E;">{date}</div>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;min-width:140px;">
                    <div style="font-size:13px;font-weight:700;color:{risk_text_color};
                         margin-bottom:4px;">{risk_pct}
                      <span style="font-size:11px;font-weight:400;">{risk_label}</span>
                    </div>
                    <div style="background:#F3D6E0;border-radius:4px;height:5px;width:100px;">
                      <div style="width:{risk_pct}%;height:100%;background:{bar_color};
                           border-radius:4px;"></div>
                    </div>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <span style="background:{status_bg};color:{status_color};padding:4px 12px;
                          border-radius:20px;font-size:12px;font-weight:600;">
                      {status.title()}
                    </span>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <div style="font-size:12px;color:#8A6D7C;">{payment}</div>
                  </td>
                </tr>"""

            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-top:none;
                 border-radius:0 0 16px 16px;box-shadow:0 2px 12px rgba(45,27,46,.07);
                 padding:0 0 8px 0;margin-top:-16px;margin-bottom:16px;">
              <div style="overflow-x:auto;">
                <table style="width:100%;border-collapse:collapse;">
                  <thead>
                    <tr style="background:#FCF7F9;border-bottom:2px solid #F0DCE4;">
                      <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                           color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Vendor</th>
                      <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                           color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Amount</th>
                      <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                           color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Date</th>
                      <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                           color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Risk Score</th>
                      <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                           color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Status</th>
                      <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                           color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Payment</th>
                    </tr>
                  </thead>
                  <tbody>{rows_html}</tbody>
                </table>
              </div>
            </div>
            """, unsafe_allow_html=True)

            csv = df_all.to_csv(index=False)
            st.download_button(
                "⬇ Download as CSV", data=csv,
                file_name="expenses.csv", mime="text/csv"
            )
        else:
            st.info("No expenses found.")
    except Exception as e:
        st.error(f"Could not load expenses: {str(e)}")


def show_pending_page():
    st.title("Pending Verification")
    st.caption("Flagged expenses awaiting review. These are NOT counted in totals.")

    with st.spinner("Loading pending expenses..."):
        try:
            response = requests.get(
                f"{BACKEND_URL}/expenses/pending",
                headers=get_headers()
            )
            response.raise_for_status()
            expenses = response.json().get("expenses", [])
        except requests.exceptions.HTTPError as e:
            st.error(f"Server error ({e.response.status_code}): Could not load expenses.")
            return
        except requests.exceptions.RequestException as e:
            st.error(f"Network error: {str(e)}")
            return

    if not expenses:
        st.success("No expenses pending verification. Everything looks clean!")
        return

    risk_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for e in expenses:
        risk = e.get("fraud_risk_score", 0) or 0
        risk_counts["HIGH" if risk >= 0.7 else "MEDIUM" if risk >= 0.5 else "LOW"] += 1

    col_h, col_m, col_l = st.columns(3, gap="large")

    with col_h:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
            padding:22px 24px;border-top:4px solid #EF4444;
            box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
        <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
            letter-spacing:.08em;margin-bottom:12px;">High Risk</div>
        <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
            {risk_counts["HIGH"]}
        </div>
        <div style="font-size:12px;color:#EF4444;margin-top:8px;font-weight:600;">
            🔴 Needs immediate review
        </div>
        </div>
        """, unsafe_allow_html=True)

    with col_m:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
            padding:22px 24px;border-top:4px solid #F59E0B;
            box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
        <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
            letter-spacing:.08em;margin-bottom:12px;">Medium Risk</div>
        <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
            {risk_counts["MEDIUM"]}
        </div>
        <div style="font-size:12px;color:#F59E0B;margin-top:8px;font-weight:600;">
            🟡 Monitor closely
        </div>
        </div>
        """, unsafe_allow_html=True)

    with col_l:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
            padding:22px 24px;border-top:4px solid #22C55E;
            box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
        <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
            letter-spacing:.08em;margin-bottom:12px;">Low Risk</div>
        <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
            {risk_counts["LOW"]}
        </div>
        <div style="font-size:12px;color:#22C55E;margin-top:8px;font-weight:600;">
            🟢 Likely clean
        </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.divider()

    for expense in expenses:
        expense_id = expense.get("id")
        risk = expense.get("fraud_risk_score", 0) or 0
        flags = expense.get("fraud_flags", [])
        risk_label = "HIGH" if risk >= 0.7 else "MEDIUM" if risk >= 0.5 else "LOW"
        risk_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[risk_label]
        confirm_key = f"confirm_{expense_id}"

        with st.expander(
            f"{risk_icon} ID #{expense_id} — {expense.get('vendor_name', 'Unknown')} — "
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
                if risk >= 0.7:
                    st.error(f"🔴 Fraud Risk: {risk:.2f} — {risk_label}")
                elif risk >= 0.5:
                    st.warning(f"🟡 Fraud Risk: {risk:.2f} — {risk_label}")
                else:
                    st.info(f"🟢 Fraud Risk: {risk:.2f} — {risk_label}")
                st.write("**OCR Confidence:**", f"{expense.get('confidence_score', 0):.0%}")
                if flags:
                    st.write("**Fraud Flags:**")
                    for flag in flags:
                        st.write(f"- {flag}")

            with col3:
                state = st.session_state.get(confirm_key)

                if state == "approve":
                    st.warning("Confirm approval?")
                    owner_email = st.text_input(
                        "Owner email",
                        value=st.session_state.get(f"email_{expense_id}", ""),
                        key=f"email_input_app_{expense_id}",
                        placeholder="owner@company.com"
                    )
                    if st.button("✅ Yes, Approve", key=f"yes_app_{expense_id}", use_container_width=True):
                        if not owner_email or "@" not in owner_email:
                            st.error("Valid email required.")
                        else:
                            r = requests.put(
                                f"{BACKEND_URL}/expenses/{expense_id}/approve",
                                headers=get_headers(),
                                params={"owner_email": owner_email}
                            )
                            del st.session_state[confirm_key]
                            if r.status_code == 200:
                                data = r.json()
                                if data.get("email_sent"):
                                    st.success("Approved! Email sent.")
                                else:
                                    st.success("Approved!")
                                st.rerun()
                            else:
                                st.error(f"Failed ({r.status_code})")
                    if st.button("Cancel", key=f"cancel_app_{expense_id}", use_container_width=True):
                        del st.session_state[confirm_key]
                        st.rerun()

                elif state == "reject":
                    st.warning("Confirm rejection?")
                    owner_email = st.text_input(
                        "Owner email",
                        value=st.session_state.get(f"email_{expense_id}", ""),
                        key=f"email_input_rej_{expense_id}",
                        placeholder="owner@company.com"
                    )
                    rejection_reason = st.text_input(
                        "Rejection reason",
                        key=f"reason_{expense_id}",
                        placeholder="e.g. Duplicate submission"
                    )
                    if st.button("❌ Yes, Reject", key=f"yes_rej_{expense_id}", use_container_width=True):
                        if not owner_email or "@" not in owner_email:
                            st.error("Valid email required.")
                        else:
                            r = requests.put(
                                f"{BACKEND_URL}/expenses/{expense_id}/reject",
                                headers=get_headers(),
                                params={
                                    "owner_email": owner_email,
                                    "rejection_reason": rejection_reason
                                }
                            )
                            del st.session_state[confirm_key]
                            if r.status_code == 200:
                                data = r.json()
                                if data.get("email_sent"):
                                    st.success("Rejected! Email sent.")
                                else:
                                    st.success("Rejected!")
                                st.rerun()
                            else:
                                st.error(f"Failed ({r.status_code})")
                    if st.button("Cancel", key=f"cancel_rej_{expense_id}", use_container_width=True):
                        del st.session_state[confirm_key]
                        st.rerun()

                else:
                    if st.button("✅ Approve", key=f"app_{expense_id}", use_container_width=True):
                        st.session_state[confirm_key] = "approve"
                        st.session_state[f"email_{expense_id}"] = expense.get("owner_email", "")
                        st.rerun()
                    if st.button("❌ Reject", key=f"rej_{expense_id}", use_container_width=True):
                        st.session_state[confirm_key] = "reject"
                        st.session_state[f"email_{expense_id}"] = expense.get("owner_email", "")
                        st.rerun()

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

        rows_html = ""
        for expense in expenses:
            vendor = expense.get("vendor_name", "—") or "—"
            amount = expense.get("total_amount", 0) or 0
            category = expense.get("primary_category", "—") or "—"
            date = str(expense.get("transaction_date", "—") or "—")
            payment = expense.get("payment_method", "—") or "—"
            risk = expense.get("fraud_risk_score", 0) or 0
            risk_pct = int(risk * 100)
            location = expense.get("location") or expense.get("vendor_address") or "—"

            if risk >= 0.7:
                risk_label = "High Risk"
                bar_color = "#991B1B"
                risk_text_color = "#991B1B"
            elif risk >= 0.4:
                risk_label = "Medium Risk"
                bar_color = "#E91E63"
                risk_text_color = "#E91E63"
            else:
                risk_label = "Low Risk"
                bar_color = "#E91E63"
                risk_text_color = "#8A6D7C"

            rows_html += f"""
            <tr style="border-bottom:1px solid #F3D6E0;">
              <td style="padding:14px 16px;vertical-align:middle;">
                <div style="font-size:13px;font-weight:700;color:#2D1B2E;">{vendor}</div>
                <div style="font-size:11px;color:#8A6D7C;margin-top:2px;">{category}</div>
              </td>
              <td style="padding:14px 16px;vertical-align:middle;">
                <div style="font-size:14px;font-weight:700;color:#E91E63;">
                  Rs {amount:,.0f}
                </div>
              </td>
              <td style="padding:14px 16px;vertical-align:middle;">
                <div style="font-size:13px;color:#2D1B2E;">{date}</div>
              </td>
              <td style="padding:14px 16px;vertical-align:middle;min-width:140px;">
                <div style="font-size:13px;font-weight:700;color:{risk_text_color};
                     margin-bottom:4px;">{risk_pct}
                  <span style="font-size:11px;font-weight:400;">{risk_label}</span>
                </div>
                <div style="background:#F3D6E0;border-radius:4px;height:5px;width:100px;">
                  <div style="width:{risk_pct}%;height:100%;background:{bar_color};
                       border-radius:4px;"></div>
                </div>
              </td>
              <td style="padding:14px 16px;vertical-align:middle;">
                <div style="font-size:13px;color:#2D1B2E;">{location}</div>
              </td>
              <td style="padding:14px 16px;vertical-align:middle;">
                <div style="font-size:12px;color:#8A6D7C;">{payment}</div>
              </td>
            </tr>"""

        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
             padding:24px 24px 8px 24px;box-shadow:0 2px 12px rgba(45,27,46,.07);">
          <div style="font-size:15px;font-weight:700;color:#2D1B2E;margin-bottom:16px;
               letter-spacing:-0.01em;">All Rejected Expenses</div>
          <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;">
              <thead>
                <tr style="background:#FCF7F9;border-bottom:2px solid #F0DCE4;">
                  <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                       color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Vendor</th>
                  <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                       color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Amount</th>
                  <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                       color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Date</th>
                  <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                       color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Risk Score</th>
                  <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                       color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Location</th>
                  <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                       color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Payment</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>
        <div style="height:16px;"></div>
        """, unsafe_allow_html=True)

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

        c1, c2, c3, c4 = st.columns(4, gap="large")

        with c1:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:22px 24px;border-top:4px solid #E91E63;
                 box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
              <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                   letter-spacing:.08em;margin-bottom:12px;">Total Spend</div>
              <div style="font-size:28px;font-weight:800;color:#2D1B2E;line-height:1;">
                Rs {summary.get('total_spend', 0):,.0f}
              </div>
              <div style="font-size:12px;color:#E91E63;margin-top:8px;font-weight:600;">
                Approved expenses only
              </div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:22px 24px;border-top:4px solid #22C55E;
                 box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
              <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                   letter-spacing:.08em;margin-bottom:12px;">Transactions</div>
              <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
                {summary.get('transaction_count', 0)}
              </div>
              <div style="font-size:12px;color:#22C55E;margin-top:8px;font-weight:600;">
                Total approved count
              </div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:22px 24px;border-top:4px solid #8E40B0;
                 box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
              <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                   letter-spacing:.08em;margin-bottom:12px;">Avg Transaction</div>
              <div style="font-size:28px;font-weight:800;color:#2D1B2E;line-height:1;">
                Rs {summary.get('avg_transaction', 0):,.0f}
              </div>
              <div style="font-size:12px;color:#8E40B0;margin-top:8px;font-weight:600;">
                Per approved expense
              </div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            pending_count = summary.get('pending_count', 0)
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
                 padding:22px 24px;border-top:4px solid #F59E0B;
                 box-shadow:0 2px 12px rgba(45,27,46,.07);min-height:120px;">
              <div style="font-size:10px;font-weight:700;color:#8A6D7C;text-transform:uppercase;
                   letter-spacing:.08em;margin-bottom:12px;">Pending Review</div>
              <div style="font-size:32px;font-weight:800;color:#2D1B2E;line-height:1;">
                {pending_count}
              </div>
              <div style="font-size:12px;color:#F59E0B;margin-top:8px;font-weight:600;">
                {'⚠ Needs attention' if pending_count > 0 else '✓ All clear'}
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2, gap="large")

        with col1:
            cat_data = summary.get("category_breakdown", {})
            if cat_data:
                df_cat = pd.DataFrame(
                    list(cat_data.items()), columns=["Category", "Amount (Rs)"]
                )
                df_cat["Share"] = (
                    df_cat["Amount (Rs)"] / df_cat["Amount (Rs)"].sum() * 100
                ).round(1).astype(str) + "%"

                with st.container(border=True):
                    st.markdown("""
                    <div style="font-size:15px;font-weight:700;color:#2D1B2E;
                         margin-bottom:12px;letter-spacing:-0.01em;">
                      Spend by Category
                    </div>
                    """, unsafe_allow_html=True)
                    st.dataframe(
                        df_cat,
                        use_container_width=True,
                        hide_index=True,
                        height=180,
                        column_config={
                            "Category": st.column_config.TextColumn("Category", width="large"),
                            "Amount (Rs)": st.column_config.NumberColumn("Amount (Rs)", format="%.0f"),
                            "Share": st.column_config.TextColumn("Share", width="small"),
                        }
                    )
                    import altair as alt
                    st.altair_chart(
                        alt.Chart(df_cat).mark_bar(
                            color="#E91E63",
                            cornerRadiusTopLeft=4,
                            cornerRadiusTopRight=4
                        ).encode(
                            x=alt.X("Category:N", axis=alt.Axis(labelAngle=0, title="Category")),
                            y=alt.Y("Amount (Rs):Q", axis=alt.Axis(title="Amount (Rs)")),
                            tooltip=["Category", "Amount (Rs)", "Share"]
                        ).properties(
                            height=280,
                            padding={"left": 10, "right": 20, "top": 20, "bottom": 10}
                        ).configure_view(strokeWidth=0).configure_axis(
                            grid=False, labelFontSize=11, titleFontSize=12
                        ),
                        use_container_width=True
                    )

        with col2:
            df_exp = pd.DataFrame(expenses)
            if "vendor_name" in df_exp.columns:
                top_v = (
                    df_exp.groupby("vendor_name")["total_amount"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                    .reset_index()
                )
                top_v.columns = ["Vendor", "Total Spend (Rs)"]

                with st.container(border=True):
                    st.markdown("""
                    <div style="font-size:15px;font-weight:700;color:#2D1B2E;
                         margin-bottom:12px;letter-spacing:-0.01em;">
                      Top 5 Vendors
                    </div>
                    """, unsafe_allow_html=True)
                    st.dataframe(
                        top_v,
                        use_container_width=True,
                        hide_index=True,
                        height=180,
                        column_config={
                            "Vendor": st.column_config.TextColumn("Vendor", width="large"),
                            "Total Spend (Rs)": st.column_config.NumberColumn(
                                "Total Spend (Rs)", format="%.0f"
                            ),
                        }
                    )
                    import altair as alt
                    st.altair_chart(
                        alt.Chart(top_v).mark_bar(
                            color="#E91E63",
                            cornerRadiusTopLeft=4,
                            cornerRadiusTopRight=4
                        ).encode(
                            x=alt.X("Vendor:N", axis=alt.Axis(labelAngle=0, title="Vendor")),
                            y=alt.Y("Total Spend (Rs):Q", axis=alt.Axis(title="Total Spend (Rs)")),
                            tooltip=["Vendor", "Total Spend (Rs)"]
                        ).properties(
                            height=280,
                            padding={"left": 10, "right": 20, "top": 20, "bottom": 10}
                        ).configure_view(strokeWidth=0).configure_axis(
                            grid=False, labelFontSize=11, titleFontSize=12
                        ),
                        use_container_width=True
                    )

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#FFFFFF;border:1px solid #F0DCE4;border-radius:16px;
             padding:24px 24px 8px 24px;box-shadow:0 2px 12px rgba(45,27,46,.07);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div style="font-size:15px;font-weight:700;color:#2D1B2E;letter-spacing:-0.01em;">
              All Approved Expenses
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        df_all = pd.DataFrame(expenses)
        if not df_all.empty:
            rows_html = ""
            for _, row in df_all.iterrows():
                vendor = row.get("vendor_name", "—") or "—"
                amount = row.get("total_amount", 0) or 0
                category = row.get("primary_category", "—") or "—"
                date = str(row.get("transaction_date", "—") or "—")
                payment = row.get("payment_method", "—") or "—"
                risk = row.get("fraud_risk_score", 0) or 0
                risk_pct = int(risk * 100)

                if risk >= 0.7:
                    risk_label = "High Risk"
                    risk_color = "#991B1B"
                    bar_color = "#991B1B"
                    risk_text_color = "#991B1B"
                elif risk >= 0.4:
                    risk_label = "Medium Risk"
                    risk_color = "#E91E63"
                    bar_color = "#E91E63"
                    risk_text_color = "#E91E63"
                else:
                    risk_label = "Low Risk"
                    risk_color = "#E91E63"
                    bar_color = "#E91E63"
                    risk_text_color = "#8A6D7C"

                rows_html += f"""
                <tr style="border-bottom:1px solid #F3D6E0;">
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <div style="font-size:13px;font-weight:700;color:#2D1B2E;">{vendor}</div>
                    <div style="font-size:11px;color:#8A6D7C;margin-top:2px;">{category}</div>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <div style="font-size:14px;font-weight:700;color:#E91E63;">
                      Rs {amount:,.0f}
                    </div>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <div style="font-size:13px;color:#2D1B2E;">{date}</div>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;min-width:140px;">
                    <div style="font-size:13px;font-weight:700;color:{risk_text_color};
                         margin-bottom:4px;">{risk_pct} 
                      <span style="font-size:11px;font-weight:400;">{risk_label}</span>
                    </div>
                    <div style="background:#F3D6E0;border-radius:4px;height:5px;width:100px;">
                      <div style="width:{risk_pct}%;height:100%;background:{bar_color};
                           border-radius:4px;"></div>
                    </div>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <span style="background:#FCF0F5;color:#E91E63;padding:4px 12px;
                          border-radius:20px;font-size:12px;font-weight:600;">
                      Approved
                    </span>
                  </td>
                  <td style="padding:14px 16px;vertical-align:middle;">
                    <div style="font-size:12px;color:#8A6D7C;">{payment}</div>
                  </td>
                </tr>"""

            csv = df_all.to_csv(index=False)
            import urllib.parse
            csv_href = urllib.parse.quote(csv)

            st.markdown(f"""
            <div style="overflow-x:auto;">
              <table style="width:100%;border-collapse:collapse;">
                <thead>
                  <tr style="background:#FCF7F9;border-bottom:2px solid #F0DCE4;">
                    <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                         color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Vendor</th>
                    <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                         color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Amount</th>
                    <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                         color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Date</th>
                    <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                         color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Risk Score</th>
                    <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                         color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Status</th>
                    <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                         color:#8A6D7C;text-transform:uppercase;letter-spacing:.08em;">Payment</th>
                  </tr>
                </thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>
            <div style="display:flex;justify-content:flex-end;margin-top:16px;">
              <a href="data:text/csv;charset=utf-8,{csv_href}"
                 download="xpenseiq_report.csv"
                 style="background:#8E40B0;color:#FFFFFF;padding:8px 20px;border-radius:8px;
                        font-size:13px;font-weight:600;text-decoration:none;
                        display:inline-flex;align-items:center;gap:6px;">
                ⬇ Download CSV
              </a>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        
    except Exception as e:
        st.error(f"Could not load reports: {str(e)}")


main()
