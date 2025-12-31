# בדיקת מצב הבוט
# הרץ את זה כדי לבדוק אם הכל תקין

import sys
import os

print("🔍 בודק את מצב הבוט...\n")

# בדיקה 1: האם tenbis_handler.py קיים?
if os.path.exists("tenbis_handler.py"):
    print("✅ tenbis_handler.py קיים")
else:
    print("❌ tenbis_handler.py לא נמצא!")
    sys.exit(1)

# בדיקה 2: האם ניתן לייבא?
try:
    from tenbis_handler import TenbisHandler, format_voucher_message, generate_html_report
    print("✅ Import של tenbis_handler עובד")
except Exception as e:
    print(f"❌ Import נכשל: {e}")
    sys.exit(1)

# בדיקה 3: האם יש את כל הפונקציות?
print("\n📦 פונקציות זמינות:")
print(f"  - TenbisHandler: {TenbisHandler is not None}")
print(f"  - format_voucher_message: {format_voucher_message is not None}")
print(f"  - generate_html_report: {generate_html_report is not None}")

print("\n✅ הכל תקין! הבוט אמור לעבוד.")
print("\n💡 אם עדיין לא עובד ב-Railway:")
print("   1. חכה עוד דקה לסיום הפריסה")
print("   2. בדוק את הלוגים ב-Railway Dashboard")
print("   3. נסה Restart ידני של הבוט")
