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
        status_text = "שוק יציב — אין מניות עם 3 ימים שליליים ברצף"
        status_icon = "✅"
    elif count <= 10:
        status_color = "#f39c12"
        status_text = f"{count} מניות בירידה ברצף — שימו לב"
        status_icon = "⚠️"
    else:
        status_color = "#e74c3c"
        status_text = f"{count} מניות בירידה ברצף — חשיפה גבוהה"
        status_icon = "🚨"

    stock_rows = ""
    for sec_or_ticker, name, d3, d2, d1 in negative_stocks:
        display = sec_or_ticker.replace(".TA", "")
        total = d3 + d2 + d1

        def color_pct(v):
            c = "#e74c3c" if v < 0 else "#27ae60"
            return f'<span style="color:{c};font-weight:bold">{v:+.2f}%</span>'

        stock_rows += f"""
        <tr>
          <td style="padding:10px 15px;font-weight:bold;font-size:15px">{name}</td>
          <td style="padding:10px;color:#7f8c8d;font-size:13px">{display}</td>
          <td style="padding:10px;text-align:center">{color_pct(d3)}</td>
          <td style="padding:10px;text-align:center">{color_pct(d2)}</td>
          <td style="padding:10px;text-align:center">{color_pct(d1)}</td>
          <td style="padding:10px;text-align:center;font-weight:bold;color:#c0392b">{total:+.2f}%</td>
        </tr>
        <tr><td colspan="6" style="height:1px;background:#f0f0f0;padding:0"></td></tr>
        """

    table_html = ""
    if count > 0:
        table_html = f"""
        <h2 style="color:#2c3e50;margin:30px 0 15px;font-size:18px">
          📉 {count} מניות בירידה 3 ימים ברצף:
        </h2>
        <table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;
                      background:white;border-radius:8px;overflow:hidden;
                      box-shadow:0 1px 4px rgba(0,0,0,0.1)">
          <thead>
            <tr style="background:#2c3e50;color:white">
              <th style="padding:12px 15px;text-align:right">מניה</th>
              <th style="padding:12px;text-align:right">סימול</th>
              <th style="padding:12px;text-align:center">לפני 3 ימים</th>
              <th style="padding:12px;text-align:center">לפני 2 ימים</th>
              <th style="padding:12px;text-align:center">אתמול</th>
              <th style="padding:12px;text-align:center">סה"כ</th>
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
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;direction:rtl">
  <div style="max-width:750px;margin:30px auto;background:white;border-radius:12px;
              overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.12)">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                padding:30px;text-align:center;color:white">
      <div style="font-size:40px;margin-bottom:8px">📊</div>
      <h1 style="margin:0;font-size:24px;letter-spacing:1px">סריקת מדד תא-125</h1>
      <p style="margin:8px 0 0;opacity:0.8;font-size:14px">
        3 ימים שליליים ברצף | {date_str} בשעה {time_str}
      </p>
    </div>

    <!-- Status Banner -->
    <div style="background:{status_color};padding:18px 30px;color:white;text-align:center">
      <span style="font-size:20px">{status_icon}</span>
      <span style="font-size:16px;font-weight:bold;margin-right:10px">{status_text}</span>
    </div>

    <!-- Stats -->
    <div style="display:flex;padding:20px 30px;background:#f8f9fa;
                border-bottom:1px solid #e9ecef;gap:20px;justify-content:center">
      <div style="text-align:center;background:white;padding:15px 25px;
                  border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.08)">
        <div style="font-size:28px;font-weight:bold;color:#2c3e50">{total_scanned}</div>
        <div style="font-size:12px;color:#7f8c8d;margin-top:4px">מניות נסרקו</div>
      </div>
      <div style="text-align:center;background:white;padding:15px 25px;
                  border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.08)">
        <div style="font-size:28px;font-weight:bold;color:{status_color}">{count}</div>
        <div style="font-size:12px;color:#7f8c8d;margin-top:4px">3 ימים שליליים</div>
      </div>
      <div style="text-align:center;background:white;padding:15px 25px;
                  border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.08)">
        <div style="font-size:28px;font-weight:bold;color:#7f8c8d">{failed_count}</div>
        <div style="font-size:12px;color:#7f8c8d;margin-top:4px">נכשלו</div>
      </div>
    </div>

    <!-- Table -->
    <div style="padding:20px 30px">
      {table_html if count > 0 else
       '<div style="text-align:center;padding:40px;color:#27ae60;font-size:18px">✅ אין מניות עם 3 ימים שליליים ברצף היום!</div>'}
    </div>

    <!-- Footer -->
    <div style="background:#2c3e50;padding:20px;text-align:center;color:#bdc3c7;font-size:12px">
      <p style="margin:0">📈 נוצר אוטומטית ע"י CrazyBot | מקור: בורסת תל אביב (TASE)</p>
      <p style="margin:6px 0 0;opacity:0.7">{date_str} {time_str} UTC</p>
    </div>
  </div>
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
