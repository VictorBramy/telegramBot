"""
10Bis Voucher Handler for Telegram Bot
Extracts and displays active 10bis vouchers
"""

import requests
import pickle
import urllib3
import json
from datetime import date
import os
import tempfile
from typing import Optional, List, Dict, Tuple

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TENBIS_FQDN = "https://www.10bis.co.il"

class TenbisHandler:
    """Handler for 10bis voucher operations"""
    
    def __init__(self, user_id: int):
        """Initialize handler for specific user"""
        self.user_id = user_id
        self.temp_dir = tempfile.gettempdir()
        self.session_path = os.path.join(self.temp_dir, f"tenbis_session_{user_id}.pickle")
        self.token_path = os.path.join(self.temp_dir, f"tenbis_token_{user_id}.pickle")
        self.session = None
        self.user_token = None
    
    def load_session(self) -> bool:
        """Load existing session if available"""
        if os.path.exists(self.session_path) and os.path.exists(self.token_path):
            try:
                with open(self.session_path, 'rb') as f:
                    self.session = pickle.load(f)
                with open(self.token_path, 'rb') as f:
                    self.user_token = pickle.load(f)
                self.session.user_token = self.user_token
                return True
            except Exception:
                return False
        return False
    
    def save_session(self):
        """Save session for future use"""
        try:
            with open(self.session_path, 'wb') as f:
                pickle.dump(self.session, f)
            with open(self.token_path, 'wb') as f:
                pickle.dump(self.user_token, f)
        except Exception:
            pass
    
    def clear_session(self):
        """Clear saved session"""
        try:
            if os.path.exists(self.session_path):
                os.remove(self.session_path)
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
        except Exception:
            pass
    
    async def authenticate(self, email: str, otp: str = None) -> Tuple[bool, str]:
        """
        Authenticate with 10bis
        Returns: (success, message)
        """
        # Phase 1: Send OTP to email
        if not otp:
            endpoint = TENBIS_FQDN + "/NextApi/GetUserAuthenticationDataAndSendAuthenticationCodeToUser"
            payload = {"culture": "he-IL", "uiCulture": "he", "email": email}
            headers = {
                "content-type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
                "Referer": "https://www.10bis.co.il/"
            }
            
            self.session = requests.session()
            
            try:
                response = self.session.post(endpoint, data=json.dumps(payload), 
                                           headers=headers, verify=False)
                resp_json = json.loads(response.text)
                
                error_msg = resp_json.get('Errors', [])
                if 200 <= response.status_code <= 210 and len(error_msg) == 0:
                    self.auth_token = resp_json.get('Data', {}).get('codeAuthenticationData', {}).get('authenticationToken', '')
                    self.shop_cart_guid = resp_json.get('ShoppingCartGuid', '')
                    self.email = email
                    return True, "קוד אימות נשלח לאימייל שלך 📧\n\nשלח לי את הקוד כדי להמשיך."
                else:
                    error_text = error_msg[0].get('ErrorDesc', 'שגיאה לא ידועה') if error_msg else 'שגיאה לא ידועה'
                    return False, f"❌ שגיאה: {error_text}"
            except Exception as e:
                return False, f"❌ שגיאה בחיבור: {str(e)}"
        
        # Phase 2: Verify OTP
        else:
            endpoint = TENBIS_FQDN + "/NextApi/GetUserV2"
            payload = {
                "shoppingCartGuid": self.shop_cart_guid,
                "culture": "he-IL",
                "uiCulture": "he",
                "email": self.email,
                "authenticationToken": self.auth_token,
                "authenticationCode": otp
            }
            headers = {
                "content-type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
                "Referer": "https://www.10bis.co.il/"
            }
            
            try:
                response = self.session.post(endpoint, data=json.dumps(payload), 
                                           headers=headers, verify=False)
                resp_json = json.loads(response.text)
                
                error_msg = resp_json.get('Errors', [])
                user_token = resp_json.get('Data', {}).get('userToken')
                session_token = resp_json.get('Data', {}).get('sessionToken')
                
                if not user_token and session_token:
                    user_token = session_token
                
                if 200 <= response.status_code <= 210 and len(error_msg) == 0 and user_token:
                    self.user_token = user_token
                    self.session.user_token = user_token
                    self.save_session()
                    return True, "✅ אימות הצליח! עכשיו תוכל לראות את השוברים שלך."
                else:
                    error_text = error_msg[0].get('ErrorDesc', 'קוד שגוי') if error_msg else 'קוד שגוי'
                    return False, f"❌ {error_text}"
            except Exception as e:
                return False, f"❌ שגיאה באימות: {str(e)}"
    
    def get_vouchers(self, months_back: int = 12) -> Tuple[bool, str, List[Dict]]:
        """
        Get active vouchers
        Returns: (success, message, vouchers_list)
        """
        if not self.load_session():
            return False, "❌ אין אימות פעיל. השתמש ב-/tenbis_login כדי להתחבר.", []
        
        all_vouchers = []
        
        try:
            for num in range(0, -months_back, -1):
                month_orders = self._get_report_for_month(str(num))
                if not month_orders:
                    # Check if token expired
                    if not os.path.exists(self.session_path):
                        return False, "⏰ הסשן פג תוקף. התחבר שוב עם /tenbis_login", []
                    continue
                
                for order in month_orders:
                    # Skip already used vouchers
                    if order.get('isUsed', False):
                        continue
                    
                    used, barcode_number, barcode_img_url, amount, valid_date = self._get_barcode_info(
                        order['orderId'], order['restaurantId']
                    )
                    
                    if not used and barcode_number:
                        # Parse date for sorting
                        date_parts = order['orderDateStr'].split('.')
                        if len(date_parts) == 3:
                            day, month, year = date_parts
                            if len(year) == 2:
                                year = '20' + year
                            sort_key = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        else:
                            sort_key = order['orderDateStr']
                        
                        all_vouchers.append({
                            'store': order['restaurantName'],
                            'order_date': order['orderDateStr'],
                            'barcode_number': barcode_number,
                            'barcode_img_url': barcode_img_url,
                            'amount': amount,
                            'valid_date': valid_date,
                            'sort_key': sort_key
                        })
            
            # Sort by date (oldest first)
            all_vouchers.sort(key=lambda x: x['sort_key'])
            
            if all_vouchers:
                total_amount = sum(float(v['amount']) for v in all_vouchers)
                newline = '\n'
                quote = '"'
                message = f"✅ נמצאו {len(all_vouchers)} שוברים פעילים!{newline}💰 סה{quote}כ: {total_amount} ₪"
                return True, message, all_vouchers
            else:
                return True, "אין שוברים פעילים כרגע 🤷‍♂️", []
                
        except Exception as e:
            return False, f"❌ שגיאה בקבלת שוברים: {str(e)}", []
    
    def _get_report_for_month(self, month: str) -> Optional[List]:
        """Get barcode orders for specific month"""
        endpoint = TENBIS_FQDN + "/NextApi/UserTransactionsReport"
        payload = {"culture": "he-IL", "uiCulture": "he", "dateBias": month}
        headers = {
            "content-type": "application/json",
            "user-token": self.user_token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
            "Referer": "https://www.10bis.co.il/"
        }
        
        try:
            response = self.session.post(endpoint, data=json.dumps(payload), 
                                        headers=headers, verify=False)
            
            # Check for 401 Unauthorized
            if response.status_code == 401:
                self.clear_session()
                return None
            
            resp_json = json.loads(response.text)
            
            if not resp_json.get('Success', False):
                return None
            
            all_orders = resp_json.get('Data', {}).get('orderList', [])
            barcode_orders = [x for x in all_orders if x.get('isBarCodeOrder') == True]
            
            return barcode_orders
        except Exception:
            return None
    
    def _get_barcode_info(self, order_id: int, res_id: int) -> Tuple:
        """Get barcode information for specific order"""
        endpoint = f"https://api.10bis.co.il/api/v2/Orders/{order_id}"
        headers = {
            "content-type": "application/json",
            "user-token": self.user_token,
            "session-token": self.user_token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
            "Referer": "https://www.10bis.co.il/"
        }
        
        try:
            response = self.session.get(endpoint, headers=headers, verify=False)
            resp_json = json.loads(response.text)
            
            barcode_data = resp_json.get('barcode')
            if not barcode_data:
                return True, '', '', '', ''
            
            used = barcode_data.get('used', True)
            barcode_number = barcode_data.get('barCodeNumber', '')
            barcode_number_formatted = '-'.join(barcode_number[i:i+4] for i in range(0, len(barcode_number), 4))
            
            if not used:
                barcode_img_url = barcode_data.get('barCodeImgUrl', '')
                amount = barcode_data.get('amount', 0)
                valid_date = barcode_data.get('validDate', '')
                return used, barcode_number_formatted, barcode_img_url, amount, valid_date
            else:
                return used, '', '', '', ''
        except Exception:
            return True, '', '', '', ''


def format_voucher_message(voucher: Dict, index: int) -> str:
    """Format single voucher as message"""
    return f"""
🎫 **שובר #{index}**
💰 {voucher['amount']} ₪
🏪 {voucher['store']}
📅 תאריך הזמנה: {voucher['order_date']}
⏰ תוקף: {voucher['valid_date']}
🔢 ברקוד: `{voucher['barcode_number']}`
"""


def generate_html_report(vouchers: List[Dict], user_name: str = "User") -> str:
    """Generate HTML report with all vouchers and interactive barcode gallery"""
    
    # HTML templates
    HTML_ROW_TEMPLATE = """
    <div class="voucher-card">
        <div class="voucher-header">
            <span class="voucher-number">#{counter}</span>
            <span class="voucher-amount">{amount} ₪</span>
        </div>
        <div class="barcode-container">
            <img class="barcode-image" src='{barcode_img_url}' alt='Barcode'>
        </div>
        <div class="voucher-details">
            <div class="detail-row"><strong>חנות:</strong> {store}</div>
            <div class="detail-row"><strong>תאריך הזמנה:</strong> {order_date}</div>
            <div class="detail-row"><strong>מספר ברקוד:</strong> {barcode_number}</div>
            <div class="detail-row"><strong>תוקף:</strong> {valid_date}</div>
        </div>
    </div>
    """
    
    # Build voucher cards HTML
    rows_data = ''
    gallery_data = ''
    barcodes_js_array = ''
    count = 0
    total_amount = 0
    
    for voucher in vouchers:
        count += 1
        total_amount += float(voucher['amount'])
        
        # Generate card HTML
        rows_data += HTML_ROW_TEMPLATE.format(
            counter=str(count),
            store=voucher['store'],
            order_date=voucher['order_date'],
            barcode_number=voucher['barcode_number'],
            barcode_img_url=voucher['barcode_img_url'],
            amount=voucher['amount'],
            valid_date=voucher['valid_date']
        )
        
        # Generate gallery item HTML
        img_url = voucher['barcode_img_url']
        count_minus_one = count - 1
        gallery_data += """
            <div class="gallery-item" onclick="openBarcode(""" + str(count_minus_one) + """)">
                <img src=\"""" + img_url + """\" alt="Barcode """ + str(count) + """\">
                <div class="gallery-label">#""" + str(count) + """</div>
            </div>
        """
        
        # Generate JavaScript array item
        barcode_num = voucher['barcode_number']
        barcodes_js_array += """            {img: \"""" + img_url + """\", number: \"""" + barcode_num + """\"},
"""
    
    # Complete HTML page
    today_date = date.today().strftime('%d/%m/%Y')
    html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
<title>שוברים פעילים - 10Bis</title>
<style>
* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 10px;
    min-height: 100vh;
}}

h1 {{
    color: white;
    text-align: center;
    padding: 20px;
    font-size: 28px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}}

.container {{
    max-width: 600px;
    margin: 0 auto;
    padding-bottom: 20px;
}}

.summary {{
    background: white;
    padding: 20px;
    border-radius: 15px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}}

.summary h2 {{
    color: #43b17d;
    font-size: 22px;
    margin-bottom: 10px;
}}

.summary p {{
    font-size: 18px;
    color: #666;
    margin: 5px 0;
}}

.gallery-section {{
    background: white;
    padding: 20px;
    border-radius: 15px;
    margin-bottom: 20px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}}

.gallery-title {{
    color: #667eea;
    font-size: 22px;
    font-weight: bold;
    margin-bottom: 15px;
    text-align: center;
}}

.gallery-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 10px;
    max-height: 400px;
    overflow-y: auto;
}}

.gallery-item {{
    position: relative;
    background: #f9f9f9;
    border-radius: 10px;
    padding: 10px;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    border: 2px solid #e0e0e0;
}}

.gallery-item:hover {{
    transform: scale(1.05);
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
}}

.gallery-item:active {{
    transform: scale(0.98);
}}

.gallery-item img {{
    width: 100%;
    height: auto;
    border-radius: 5px;
}}

.gallery-label {{
    position: absolute;
    top: 5px;
    right: 5px;
    background: #667eea;
    color: white;
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 12px;
    font-weight: bold;
}}

.barcode-modal {{
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.95);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    flex-direction: column;
}}

.barcode-modal.active {{
    display: flex;
}}

.modal-content {{
    max-width: 90%;
    max-height: 80%;
    background: white;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    position: relative;
}}

.modal-content img {{
    width: 100%;
    height: auto;
    margin-bottom: 15px;
}}

.modal-barcode-number {{
    font-size: 18px;
    color: #333;
    margin-bottom: 15px;
}}

.modal-nav {{
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(102, 126, 234, 0.9);
    color: white;
    border: none;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    font-size: 24px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
}}

.modal-nav:hover {{
    background: rgba(102, 126, 234, 1);
    transform: translateY(-50%) scale(1.1);
}}

.modal-nav:active {{
    transform: translateY(-50%) scale(0.9);
}}

.modal-nav-prev {{
    left: 10px;
}}

.modal-nav-next {{
    right: 10px;
}}

.modal-counter {{
    font-size: 16px;
    color: #666;
    margin-bottom: 10px;
}}

.modal-close {{
    background: #667eea;
    color: white;
    border: none;
    padding: 12px 30px;
    border-radius: 25px;
    font-size: 16px;
    cursor: pointer;
    margin-top: 10px;
}}

.modal-close:active {{
    transform: scale(0.95);
}}

.voucher-card {{
    background: white;
    border-radius: 15px;
    margin-bottom: 20px;
    padding: 20px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    transition: transform 0.2s;
}}

.voucher-card:active {{
    transform: scale(0.98);
}}

.voucher-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 2px solid #f0f0f0;
}}

.voucher-number {{
    font-size: 24px;
    font-weight: bold;
    color: #667eea;
}}

.voucher-amount {{
    font-size: 28px;
    font-weight: bold;
    color: #43b17d;
}}

.barcode-container {{
    background: #f9f9f9;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    margin: 15px 0;
}}

.barcode-image {{
    width: 100%;
    max-width: 100%;
    height: auto;
    border-radius: 5px;
}}

.voucher-details {{
    margin-top: 15px;
}}

.detail-row {{
    padding: 8px 0;
    font-size: 16px;
    color: #333;
    border-bottom: 1px solid #f0f0f0;
}}

.detail-row:last-child {{
    border-bottom: none;
}}

.detail-row strong {{
    color: #667eea;
    margin-left: 5px;
}}

@media (max-width: 480px) {{
    h1 {{
        font-size: 24px;
        padding: 15px 10px;
    }}
    
    .gallery-grid {{
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    }}
    
    .voucher-card {{
        padding: 15px;
    }}
    
    .voucher-number {{
        font-size: 20px;
    }}
    
    .voucher-amount {{
        font-size: 24px;
    }}
    
    .detail-row {{
        font-size: 14px;
    }}
}}
</style>
<script>
// Store all barcodes data
const barcodes = [
{barcodes_js_array.rstrip(', ').rstrip()}
];

let currentIndex = 0;
let touchStartX = 0;
let touchEndX = 0;

function openBarcode(index) {{
    currentIndex = index;
    showCurrentBarcode();
    const modal = document.getElementById('barcodeModal');
    modal.classList.add('active');
}}

function showCurrentBarcode() {{
    const barcode = barcodes[currentIndex];
    const modalImg = document.getElementById('modalBarcodeImg');
    const modalNumber = document.getElementById('modalBarcodeNumber');
    const modalCounter = document.getElementById('modalCounter');
    
    modalImg.src = barcode.img;
    modalNumber.textContent = barcode.number;
    modalCounter.textContent = 'שובר ' + (currentIndex + 1) + ' מתוך ' + barcodes.length;
    
    document.getElementById('prevBtn').style.display = currentIndex > 0 ? 'flex' : 'none';
    document.getElementById('nextBtn').style.display = currentIndex < barcodes.length - 1 ? 'flex' : 'none';
}}

function navigatePrev() {{
    if (currentIndex > 0) {{
        currentIndex--;
        showCurrentBarcode();
    }}
}}

function navigateNext() {{
    if (currentIndex < barcodes.length - 1) {{
        currentIndex++;
        showCurrentBarcode();
    }}
}}

function closeBarcode() {{
    const modal = document.getElementById('barcodeModal');
    modal.classList.remove('active');
}}

function handleSwipe() {{
    const swipeThreshold = 50;
    const diff = touchStartX - touchEndX;
    
    if (Math.abs(diff) > swipeThreshold) {{
        if (diff > 0) {{
            navigateNext();
        }} else {{
            navigatePrev();
        }}
    }}
}}

document.addEventListener('DOMContentLoaded', function() {{
    const modal = document.getElementById('barcodeModal');
    const modalContent = document.querySelector('.modal-content');
    
    modal.addEventListener('click', function(e) {{
        if (e.target === modal) {{
            closeBarcode();
        }}
    }});
    
    if (modalContent) {{
        modalContent.addEventListener('touchstart', function(e) {{
            touchStartX = e.changedTouches[0].screenX;
        }}, false);
        
        modalContent.addEventListener('touchend', function(e) {{
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }}, false);
    }}
    
    document.addEventListener('keydown', function(e) {{
        if (!modal.classList.contains('active')) return;
        
        if (e.key === 'ArrowLeft') {{
            navigateNext();
        }} else if (e.key === 'ArrowRight') {{
            navigatePrev();
        }} else if (e.key === 'Escape') {{
            closeBarcode();
        }}
    }});
}});
</script>
</head>
<body>
    <h1>🎫 שוברים פעילים - 10Bis</h1>
    <div class="container">
        <div class="summary">
            <h2>סיכום</h2>
            <p><strong>סה״כ שוברים:</strong> {count}</p>
            <p><strong>סה״כ סכום:</strong> {total_amount} ₪</p>
            <p><strong>נוצר עבור:</strong> {user_name}</p>
            <p><strong>תאריך:</strong> {today_date}</p>
        </div>
        
        <div class="gallery-section">
            <div class="gallery-title">🖼️ גלריית ברקודים - לחץ לסריקה מהירה</div>
            <div class="gallery-grid">
                {gallery_data}
            </div>
        </div>
        
        {rows_data}
    </div>
    
    <!-- Barcode Modal -->
    <div id="barcodeModal" class="barcode-modal">
        <div class="modal-content">
            <button id="prevBtn" class="modal-nav modal-nav-prev" onclick="navigatePrev()">‹</button>
            <button id="nextBtn" class="modal-nav modal-nav-next" onclick="navigateNext()">›</button>
            <div class="modal-counter" id="modalCounter"></div>
            <img id="modalBarcodeImg" src="" alt="Barcode">
            <div class="modal-barcode-number" id="modalBarcodeNumber"></div>
            <button class="modal-close" onclick="closeBarcode()">✕ סגור</button>
        </div>
    </div>
</body>
</html>"""
    
    return html_content

