#!/usr/bin/env powershell

# מדריך מהיר לצפייה בלוגים נקיים

Write-Host "🔍 אפשרויות צפייה בלוגים:" -ForegroundColor Green
Write-Host ""

Write-Host "1. לוגי משתמשים בלבד (נקי):" -ForegroundColor Yellow  
Write-Host "   Get-Content user_activity.log -Wait -Tail 10"
Write-Host ""

Write-Host "2. כל הלוגים (עם טכני):" -ForegroundColor Yellow
Write-Host "   Get-Content bot_activity.log -Wait -Tail 10"  
Write-Host ""

Write-Host "3. חיפוש לוג ספציפי:" -ForegroundColor Yellow
Write-Host "   Select-String '💬|📍|🚀' bot_activity.log"
Write-Host ""

Write-Host "4. ספירת משתמשים ייחודיים:" -ForegroundColor Yellow  
Write-Host "   Select-String 'ID: (\d+)' user_activity.log | ForEach-Object { `$_.Matches.Groups[1].Value } | Sort-Object -Unique | Measure-Object"
Write-Host ""

Write-Host "5. פעילות אחרונה:" -ForegroundColor Yellow
Write-Host "   Get-Content user_activity.log -Tail 5"
Write-Host ""

# הרצה ישירה של הפקודה הכי שימושית
Write-Host "מציג לוגי משתמשים אחרונים..." -ForegroundColor Cyan
if (Test-Path "user_activity.log") {
    Get-Content user_activity.log -Tail 5
} else {
    Write-Host "קובץ user_activity.log עדיין לא קיים - הבוט צריך לקבל הודעות קודם" -ForegroundColor Red
}