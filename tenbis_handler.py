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
                message = f"✅ נמצאו {len(all_vouchers)} שוברים פעילים!\n💰 סה\"כ: {total_amount} ₪"
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
