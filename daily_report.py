"""
Daily TA-125 Stock Report Generator
Runs the TA-125 scanner and generates an HTML report for email delivery.
Called by GitHub Actions every morning.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path so ta125_scanner imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ta125_scanner import scan_ta125_async


def build_html_report(
    negative_stocks: list,
    total_scanned: int,
    failed_count: int,
) -> str:
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M")
    count = len(negative_stocks)

    # Status color
    if count == 0:
        status_color = "#27ae60"
        status_text = "שוק יציב — אין מניות עם 3+ ימים שליליים ברצף"
        status_icon = "✅"
    elif count <= 10:
        status_color = "#f39c12"
        status_text = f"{count} מניות בירידה ברצף — שימו לב"
        status_icon = "⚠️"
    else:
        status_color = "#e74c3c"
        status_text = f"{count} מניות בירידה ברצף — חשיפה גבוהה"
        status_icon = "🚨"

    def fmt_price(v):
        """Format price in ILS, hide if zero."""
        if v <= 0:
            return "—"
        if v >= 1000:
            return f"₪{v:,.0f}"
        return f"₪{v:,.2f}"

    def color_pct(v):
        c = "#e74c3c" if v < 0 else "#27ae60"
        return f'<span style="color:{c};font-weight:bold">{v:+.2f}%</span>'

    stock_rows = ""
    for entry in negative_stocks:
        sec_or_ticker = entry[0]
        name = entry[1]
        d3, d2, d1 = entry[2], entry[3], entry[4]
        consecutive = entry[5] if len(entry) > 5 else 3
        total_all   = entry[6] if len(entry) > 6 else d3 + d2 + d1
        cur_price   = entry[7] if len(entry) > 7 else 0.0
        high_52w    = entry[8] if len(entry) > 8 else 0.0

        # Strip leading zeros from TASE security numbers
        raw = sec_or_ticker.replace(".TA", "")
        display = str(int(raw)) if raw.isdigit() else raw

        # Days badge color
        if consecutive >= 7:
            days_color = "#8e44ad"
        elif consecutive >= 5:
            days_color = "#e74c3c"
        else:
            days_color = "#e67e22"

        price_cell = fmt_price(cur_price)
        high_cell  = fmt_price(high_52w)

        # Mobile sub-line shows 52w high + days
        onclick_copy = f"navigator.clipboard.writeText('{display}');this.style.background='#27ae60';this.style.color='white';setTimeout(()=>{{this.style.background='';this.style.color='#34495e';}},1200)"
        display_span = f'<span onclick="{onclick_copy}" style="cursor:pointer;text-decoration:underline dotted;color:#34495e;padding:1px 3px;border-radius:3px;transition:all .2s" title="לחץ להעתיק">{display}</span>'
        mobile_sub = f'{display_span} · <span style="color:{days_color};font-weight:bold">{consecutive}↓</span>'
        if high_52w > 0:
            mobile_sub += f' · שיא: {high_cell}'

        stock_rows += f"""
        <tr>
          <td style="padding:12px 15px;font-weight:bold;font-size:15px">{name}
            <div class="stock-sub" style="font-size:11px;color:#7f8c8d;font-weight:normal;margin-top:3px">{mobile_sub}</div>
          </td>
          <td class="hide-mobile" style="padding:12px 8px;text-align:center;font-size:13px">{color_pct(d3)}</td>
          <td class="hide-mobile" style="padding:12px 8px;text-align:center;font-size:13px">{color_pct(d2)}</td>
          <td style="padding:12px 8px;text-align:center;font-size:13px">{color_pct(d1)}</td>
          <td style="padding:12px 8px;text-align:center">
            <span style="background:{days_color};color:white;border-radius:12px;padding:3px 9px;font-size:12px;font-weight:bold;white-space:nowrap">{consecutive} ימים</span>
          </td>
          <td style="padding:12px 8px;text-align:center;font-weight:bold;color:#c0392b;font-size:14px">{total_all:+.2f}%</td>
          <td style="padding:12px 8px;text-align:center;font-size:13px;color:#2c3e50">{price_cell}</td>
          <td class="hide-mobile" style="padding:12px 8px;text-align:center;font-size:13px;color:#7f8c8d">{high_cell}</td>
        </tr>
        <tr><td colspan="8" style="height:1px;background:#f0f0f0;padding:0"></td></tr>
        """

    table_html = ""
    if count > 0:
        table_html = f"""
        <h2 style="color:#2c3e50;margin:25px 0 12px;font-size:17px;padding:0 5px">
          📉 {count} מניות בירידה 3+ ימים ברצף:
        </h2>
        <table width="100%" cellspacing="0" cellpadding="0"
               style="border-collapse:collapse;font-family:Arial,sans-serif;
                      background:white;border-radius:8px;overflow:hidden;
                      box-shadow:0 1px 4px rgba(0,0,0,0.1)">
          <thead>
            <tr style="background:#2c3e50;color:white">
              <th style="padding:11px 15px;text-align:right;font-size:13px">מניה</th>
              <th class="hide-mobile" style="padding:11px 8px;text-align:center;font-size:12px">לפני 3</th>
              <th class="hide-mobile" style="padding:11px 8px;text-align:center;font-size:12px">לפני 2</th>
              <th style="padding:11px 8px;text-align:center;font-size:12px">אתמול</th>
              <th style="padding:11px 8px;text-align:center;font-size:12px">ימים ↓</th>
              <th style="padding:11px 8px;text-align:center;font-size:12px">סה"כ</th>
              <th style="padding:11px 8px;text-align:center;font-size:12px">מחיר</th>
              <th class="hide-mobile" style="padding:11px 8px;text-align:center;font-size:12px">שיא 52W</th>
            </tr>
          </thead>
          <tbody>
            {stock_rows}
          </tbody>
        </table>
        """

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>סריקת תא-125 יומית</title>
  <style>
    @media only screen and (max-width: 600px) {{
      .email-wrapper {{ margin: 0 !important; border-radius: 0 !important; }}
      .header-title {{ font-size: 20px !important; }}
      .header-sub {{ font-size: 12px !important; }}
      .stats-cell {{ padding: 10px 8px !important; }}
      .stats-num {{ font-size: 22px !important; }}
      .stats-label {{ font-size: 11px !important; }}
      .hide-mobile {{ display: none !important; }}
      .section-pad {{ padding: 15px !important; }}
      .status-text {{ font-size: 14px !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;direction:rtl">
  <table width="100%" cellspacing="0" cellpadding="0" style="background:#f0f2f5">
    <tr><td align="center" style="padding:20px 0">

  <table class="email-wrapper" width="100%" cellspacing="0" cellpadding="0"
         style="max-width:720px;background:white;border-radius:12px;
                overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.12)">

    <!-- Header -->
    <tr>
      <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                 padding:28px 20px;text-align:center;color:white">
        <div style="font-size:38px;margin-bottom:6px">📊</div>
        <div class="header-title" style="font-size:22px;font-weight:bold;letter-spacing:1px">סריקת מדד תא-125</div>
        <div class="header-sub" style="margin:6px 0 0;opacity:0.8;font-size:13px">
          3+ ימים שליליים ברצף &nbsp;|&nbsp; {date_str} בשעה {time_str}
        </div>
      </td>
    </tr>

    <!-- Status Banner -->
    <tr>
      <td style="background:{status_color};padding:15px 20px;color:white;text-align:center">
        <span style="font-size:18px">{status_icon}</span>
        <span class="status-text" style="font-size:15px;font-weight:bold;margin-right:8px">{status_text}</span>
      </td>
    </tr>

    <!-- Stats (table-based for email client compat) -->
    <tr>
      <td style="background:#f8f9fa;padding:16px 12px;border-bottom:1px solid #e9ecef">
        <table width="100%" cellspacing="0" cellpadding="0">
          <tr>
            <td class="stats-cell" width="33%" style="padding:10px 6px;text-align:center">
              <table width="100%" cellspacing="0" cellpadding="0">
                <tr><td style="background:white;border-radius:8px;padding:14px 8px;text-align:center;
                               box-shadow:0 1px 4px rgba(0,0,0,0.08)">
                  <div class="stats-num" style="font-size:26px;font-weight:bold;color:#2c3e50">{total_scanned}</div>
                  <div class="stats-label" style="font-size:11px;color:#7f8c8d;margin-top:4px">מניות נסרקו</div>
                </td></tr>
              </table>
            </td>
            <td class="stats-cell" width="33%" style="padding:10px 6px;text-align:center">
              <table width="100%" cellspacing="0" cellpadding="0">
                <tr><td style="background:white;border-radius:8px;padding:14px 8px;text-align:center;
                               box-shadow:0 1px 4px rgba(0,0,0,0.08)">
                  <div class="stats-num" style="font-size:26px;font-weight:bold;color:{status_color}">{count}</div>
                  <div class="stats-label" style="font-size:11px;color:#7f8c8d;margin-top:4px">3+ ימים שליליים</div>
                </td></tr>
              </table>
            </td>
            <td class="stats-cell" width="33%" style="padding:10px 6px;text-align:center">
              <table width="100%" cellspacing="0" cellpadding="0">
                <tr><td style="background:white;border-radius:8px;padding:14px 8px;text-align:center;
                               box-shadow:0 1px 4px rgba(0,0,0,0.08)">
                  <div class="stats-num" style="font-size:26px;font-weight:bold;color:#7f8c8d">{failed_count}</div>
                  <div class="stats-label" style="font-size:11px;color:#7f8c8d;margin-top:4px">נכשלו</div>
                </td></tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Table / Empty state -->
    <tr>
      <td class="section-pad" style="padding:20px 25px">
        {'<div style="text-align:center;padding:35px 20px;color:#27ae60;font-size:17px">✅ אין מניות עם 3+ ימים שליליים ברצף היום!</div>' if count == 0 else table_html}
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="background:#2c3e50;padding:18px 20px;text-align:center;color:#bdc3c7;font-size:12px">
        <div>📈 נוצר אוטומטית ע"י CrazyBot | מקור: בורסת תל אביב (TASE)</div>
        <div style="margin:5px 0 0;opacity:0.7">{date_str} {time_str} UTC</div>
      </td>
    </tr>

  </table>

    </td></tr>
  </table>
</body>
</html>"""
    return html
async def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting TA-125 scan...")

    negative_stocks, total_scanned, failed_count = await scan_ta125_async()

    count = len(negative_stocks)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan complete: {count} negative stocks out of {total_scanned}")

    html = build_html_report(negative_stocks, total_scanned, failed_count)

    with open("report.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Report written to report.html")

    # Also write a plain-text subject line for the email
    date_str = datetime.now().strftime("%d/%m/%Y")
    subject = f"📊 סריקת תא-125 | {date_str} | {count} מניות שליליות מתוך {total_scanned}"
    with open("email_subject.txt", "w", encoding="utf-8") as f:
        f.write(subject)

    print(f"Subject: {subject}")


if __name__ == "__main__":
    asyncio.run(main())
