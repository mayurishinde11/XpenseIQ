import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_NAME = "XpenseIQ"


def send_verification_email(
    to_email: str,
    expense_id: int,
    vendor_name: str,
    total_amount: float,
    status: str,
    verifier_name: str,
    rejection_reason: str = None,
    transaction_date: str = None,
) -> dict:
    try:
        verified_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
        status_color = "#22C55E" if status == "approved" else "#EF4444"
        status_label = "Approved" if status == "approved" else "Rejected"
        status_icon = "✅" if status == "approved" else "❌"

        rejection_row = ""
        if status == "rejected" and rejection_reason:
            rejection_row = f"""
            <tr>
              <td style="padding:10px 16px;color:#8A6D7C;font-size:13px;border-bottom:1px solid #F0DCE4;">
                Rejection Reason
              </td>
              <td style="padding:10px 16px;font-weight:600;color:#EF4444;font-size:13px;border-bottom:1px solid #F0DCE4;">
                {rejection_reason}
              </td>
            </tr>"""

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="margin:0;padding:0;background:#FDF4F7;font-family:Inter,Arial,sans-serif;">
          <div style="max-width:560px;margin:40px auto;background:#ffffff;
               border-radius:16px;border:1px solid #F0DCE4;
               box-shadow:0 4px 24px rgba(45,27,46,0.08);overflow:hidden;">

            <!-- Header -->
            <div style="background:linear-gradient(135deg,#E91E63,#AA225B);
                 padding:28px 32px;text-align:center;">
              <div style="font-size:24px;font-weight:800;color:#ffffff;
                   letter-spacing:-0.5px;">XpenseIQ</div>
              <div style="font-size:13px;color:rgba(255,255,255,0.85);margin-top:4px;">
                AI-Powered Smart Expense Scanner
              </div>
            </div>

            <!-- Status Banner -->
            <div style="background:{status_color}15;border-bottom:3px solid {status_color};
                 padding:20px 32px;text-align:center;">
              <div style="font-size:28px;margin-bottom:6px;">{status_icon}</div>
              <div style="font-size:20px;font-weight:700;color:{status_color};">
                Expense {status_label}
              </div>
              <div style="font-size:13px;color:#8A6D7C;margin-top:4px;">
                Your expense has been reviewed and {status_label.lower()}.
              </div>
            </div>

            <!-- Details Table -->
            <div style="padding:24px 32px 8px;">
              <div style="font-size:14px;font-weight:700;color:#2D1B2E;margin-bottom:12px;">
                Expense Details
              </div>
              <table style="width:100%;border-collapse:collapse;border-radius:10px;
                     overflow:hidden;border:1px solid #F0DCE4;">
                <tr>
                  <td style="padding:10px 16px;color:#8A6D7C;font-size:13px;
                       background:#FCF7F9;border-bottom:1px solid #F0DCE4;width:40%;">
                    Expense ID
                  </td>
                  <td style="padding:10px 16px;font-weight:600;color:#2D1B2E;font-size:13px;
                       background:#FCF7F9;border-bottom:1px solid #F0DCE4;">
                    #{expense_id}
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;color:#8A6D7C;font-size:13px;border-bottom:1px solid #F0DCE4;">
                    Vendor / Description
                  </td>
                  <td style="padding:10px 16px;font-weight:600;color:#2D1B2E;font-size:13px;border-bottom:1px solid #F0DCE4;">
                    {vendor_name or 'N/A'}
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;color:#8A6D7C;font-size:13px;
                       background:#FCF7F9;border-bottom:1px solid #F0DCE4;">
                    Amount
                  </td>
                  <td style="padding:10px 16px;font-weight:700;color:#E91E63;font-size:14px;
                       background:#FCF7F9;border-bottom:1px solid #F0DCE4;">
                    Rs {total_amount:,.2f}
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;color:#8A6D7C;font-size:13px;border-bottom:1px solid #F0DCE4;">
                    Transaction Date
                  </td>
                  <td style="padding:10px 16px;font-weight:600;color:#2D1B2E;font-size:13px;border-bottom:1px solid #F0DCE4;">
                    {transaction_date or 'N/A'}
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;color:#8A6D7C;font-size:13px;
                       background:#FCF7F9;border-bottom:1px solid #F0DCE4;">
                    Status
                  </td>
                  <td style="padding:10px 16px;background:#FCF7F9;border-bottom:1px solid #F0DCE4;">
                    <span style="background:{status_color}20;color:{status_color};
                          padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700;">
                      {status_label}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;color:#8A6D7C;font-size:13px;border-bottom:1px solid #F0DCE4;">
                    Verified By
                  </td>
                  <td style="padding:10px 16px;font-weight:600;color:#2D1B2E;font-size:13px;border-bottom:1px solid #F0DCE4;">
                    {verifier_name}
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;color:#8A6D7C;font-size:13px;
                       background:#FCF7F9;border-bottom:1px solid #F0DCE4;">
                    Verification Date
                  </td>
                  <td style="padding:10px 16px;font-weight:600;color:#2D1B2E;font-size:13px;
                       background:#FCF7F9;border-bottom:1px solid #F0DCE4;">
                    {verified_at}
                  </td>
                </tr>
                {rejection_row}
              </table>
            </div>

            <!-- Footer -->
            <div style="padding:24px 32px;text-align:center;border-top:1px solid #F0DCE4;margin-top:16px;">
              <div style="font-size:12px;color:#8A6D7C;">
                This is an automated notification from
                <strong style="color:#E91E63;">XpenseIQ</strong>.
                Please do not reply to this email.
              </div>
            </div>
          </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"XpenseIQ — Expense #{expense_id} {status_label}"
        msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}