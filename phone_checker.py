"""
Phone Number Checker Module
Integrates with TrueCaller-like services for phone number lookup
"""

import re
import requests
import json
from typing import Dict, Optional, Tuple

# Country codes mapping
COUNTRY_CODES = {
    'israel': {'code': '+972', 'name': 'ישראל', 'flag': '🇮🇱', 'local_prefix': '0'},
    'usa': {'code': '+1', 'name': 'ארה"ב', 'flag': '🇺🇸', 'local_prefix': '1'},
    'uk': {'code': '+44', 'name': 'בריטניה', 'flag': '🇬🇧', 'local_prefix': '0'},
    'germany': {'code': '+49', 'name': 'גרמניה', 'flag': '🇩🇪', 'local_prefix': '0'},
    'france': {'code': '+33', 'name': 'צרפת', 'flag': '🇫🇷', 'local_prefix': '0'},
    'italy': {'code': '+39', 'name': 'איטליה', 'flag': '🇮🇹', 'local_prefix': ''},
    'spain': {'code': '+34', 'name': 'ספרד', 'flag': '🇪🇸', 'local_prefix': ''},
    'netherlands': {'code': '+31', 'name': 'הולנד', 'flag': '🇳🇱', 'local_prefix': '0'},
    'turkey': {'code': '+90', 'name': 'טורקיה', 'flag': '🇹🇷', 'local_prefix': '0'},
    'russia': {'code': '+7', 'name': 'רוסיה', 'flag': '🇷🇺', 'local_prefix': '8'},
    'china': {'code': '+86', 'name': 'סין', 'flag': '🇨🇳', 'local_prefix': ''},
    'india': {'code': '+91', 'name': 'הודו', 'flag': '🇮🇳', 'local_prefix': ''},
    'japan': {'code': '+81', 'name': 'יפן', 'flag': '🇯🇵', 'local_prefix': '0'},
    'australia': {'code': '+61', 'name': 'אוסטרליה', 'flag': '🇦🇺', 'local_prefix': '0'},
    'canada': {'code': '+1', 'name': 'קנדה', 'flag': '🇨🇦', 'local_prefix': '1'},
    'brazil': {'code': '+55', 'name': 'ברזיל', 'flag': '🇧🇷', 'local_prefix': ''},
    'argentina': {'code': '+54', 'name': 'ארגנטינה', 'flag': '🇦🇷', 'local_prefix': ''},
    'egypt': {'code': '+20', 'name': 'מצרים', 'flag': '🇪🇬', 'local_prefix': '0'},
    'uae': {'code': '+971', 'name': 'איחוד האמירויות', 'flag': '🇦🇪', 'local_prefix': '0'},
    'saudi': {'code': '+966', 'name': 'סעודיה', 'flag': '🇸🇦', 'local_prefix': '0'},
}

class PhoneNumberChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def normalize_phone_number(self, phone: str, country_code: str) -> Tuple[str, bool]:
        """
        Normalize phone number to international format
        Returns: (formatted_number, is_valid)
        """
        # Clean the number
        phone = re.sub(r'[^\d+]', '', phone)
        
        if not phone:
            return "", False
            
        country_info = COUNTRY_CODES.get(country_code.lower())
        if not country_info:
            return phone, False
            
        # Remove existing country code if present
        country_num = country_info['code'].replace('+', '')
        if phone.startswith(country_num):
            phone = phone[len(country_num):]
        elif phone.startswith('+' + country_num):
            phone = phone[len(country_num) + 1:]
        
        # Remove local prefix if present
        local_prefix = country_info['local_prefix']
        if local_prefix and phone.startswith(local_prefix):
            phone = phone[len(local_prefix):]
        
        # Format to international
        formatted = f"{country_info['code']}{phone}"
        
        # Basic validation
        is_valid = len(phone) >= 7 and len(phone) <= 15
        
        return formatted, is_valid

    def lookup_truecaller_style(self, phone_number: str) -> Optional[Dict]:
        """
        Simulate TrueCaller-like lookup using free APIs
        """
        try:
            # Try multiple free phone lookup APIs
            results = {}
            
            # Method 1: Use numverify API (free tier)
            results.update(self._try_numverify(phone_number))
            
            # Method 2: Use phone number parsing
            results.update(self._parse_phone_info(phone_number))
            
            return results if results else None
            
        except Exception as e:
            print(f"Error in phone lookup: {e}")
            return None

    def _try_numverify(self, phone_number: str) -> Dict:
        """Try numverify API for phone validation"""
        try:
            # Note: This requires API key for full functionality
            # For demo, we'll simulate the response structure
            
            phone_clean = phone_number.replace('+', '')
            
            # Basic validation and info extraction
            result = {
                'number': phone_number,
                'valid': True,
                'line_type': 'mobile',  # or 'landline'
                'carrier': 'לא ידוע',
                'country_name': 'לא ידוע',
                'location': 'לא ידוע'
            }
            
            # Try to determine country from prefix
            for country, info in COUNTRY_CODES.items():
                country_code = info['code'].replace('+', '')
                if phone_clean.startswith(country_code):
                    result['country_name'] = info['name']
                    result['country_flag'] = info['flag']
                    
                    # Israeli number specific logic
                    if country == 'israel':
                        result.update(self._analyze_israeli_number(phone_clean[3:]))  # Remove 972
                    
                    break
            
            return result
            
        except Exception:
            return {}

    def _analyze_israeli_number(self, local_number: str) -> Dict:
        """Analyze Israeli phone number patterns"""
        carriers = {
            '50': 'פלאפון',
            '52': 'פלאפון', 
            '53': 'פלאפון',
            '54': 'פרטנר',
            '55': 'פרטנר',
            '56': 'פרטנר',
            '57': 'מירס / גולן טלקום',
            '58': 'מירס / גולן טלקום',
            '51': 'הוט מובייל',
            '59': 'הוט מובייל',
        }
        
        line_types = {
            '2': 'קווי',   # Jerusalem area
            '3': 'קווי',   # Central area  
            '4': 'קווי',   # Haifa area
            '8': 'קווי',   # South area
            '9': 'קווי',   # Sharon area
            '72': 'שירותי מידע',
            '73': 'שירותי מידע',
            '74': 'שירותי מידע',
            '75': 'שירותי מידע',
            '76': 'שירותי מידע',
            '77': 'שירותי מידע',
            '78': 'שירותי מידע',
            '79': 'שירותי מידע',
        }
        
        result = {}
        
        if len(local_number) >= 2:
            prefix2 = local_number[:2]
            prefix1 = local_number[:1]
            
            # Check mobile carriers
            if prefix2 in carriers:
                result['carrier'] = carriers[prefix2]
                result['line_type'] = 'נייד'
            elif prefix1 in line_types:
                result['line_type'] = line_types[prefix1]
                result['carrier'] = 'בזק / שירותי קו'
            else:
                result['carrier'] = 'לא ידוע'
                result['line_type'] = 'לא ידוע'
        
        return result

    def _parse_phone_info(self, phone_number: str) -> Dict:
        """Parse basic phone number information"""
        try:
            # Use phonenumbers library if available, otherwise basic parsing
            try:
                import phonenumbers
                from phonenumbers import geocoder, carrier
                
                parsed = phonenumbers.parse(phone_number, None)
                
                result = {
                    'valid': phonenumbers.is_valid_number(parsed),
                    'country_name': geocoder.description_for_number(parsed, 'he'),
                    'carrier': carrier.name_for_number(parsed, 'he') or 'לא ידוע',
                    'line_type': 'נייד' if phonenumbers.number_type(parsed) in [
                        phonenumbers.PhoneNumberType.MOBILE,
                        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE
                    ] else 'קווי'
                }
                
                return result
                
            except ImportError:
                # Fallback to basic analysis
                return self._basic_phone_analysis(phone_number)
                
        except Exception:
            return {}

    def _basic_phone_analysis(self, phone_number: str) -> Dict:
        """Basic phone number analysis without external libraries"""
        phone_clean = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        result = {
            'number': phone_number,
            'valid': len(phone_clean) >= 10 and len(phone_clean) <= 15,
            'carrier': 'לא ידוע',
            'line_type': 'לא ידוע',
            'country_name': 'לא ידוע'
        }
        
        # Determine country and basic info
        for country, info in COUNTRY_CODES.items():
            country_code = info['code'].replace('+', '')
            if phone_clean.startswith(country_code):
                result['country_name'] = info['name']
                result['country_flag'] = info.get('flag', '')
                
                if country == 'israel':
                    local_part = phone_clean[3:]  # Remove 972
                    result.update(self._analyze_israeli_number(local_part))
                
                break
        
        return result

    def format_phone_result(self, phone_data: Dict, original_number: str) -> str:
        """Format phone lookup results for display"""
        if not phone_data:
            return "❌ לא הצלחתי לבדוק את המספר. אנא ודא שהמספר נכון."
        
        # Build result message
        result = f"📱 **בדיקת מספר טלפון**\n\n"
        result += f"🔢 **מספר מקורי:** `{original_number}`\n"
        result += f"🌍 **מספר בינלאומי:** `{phone_data.get('number', 'לא ידוע')}`\n"
        
        if phone_data.get('valid'):
            result += f"✅ **תקינות:** מספר תקין\n"
        else:
            result += f"⚠️ **תקינות:** מספר לא תקין או לא מוכר\n"
        
        if phone_data.get('country_name'):
            flag = phone_data.get('country_flag', '')
            result += f"🏳️ **מדינה:** {flag} {phone_data['country_name']}\n"
        
        if phone_data.get('line_type'):
            result += f"📞 **סוג קו:** {phone_data['line_type']}\n"
        
        if phone_data.get('carrier') and phone_data['carrier'] != 'לא ידוע':
            result += f"📡 **ספק:** {phone_data['carrier']}\n"
        
        if phone_data.get('location') and phone_data['location'] != 'לא ידוע':
            result += f"📍 **מיקום:** {phone_data['location']}\n"
        
        # Add disclaimer
        result += f"\n⚠️ **הערה חשובה:**\n"
        result += f"המידע מבוסס על מסדי נתונים ציבוריים ועשוי להיות לא מדויק או לא עדכני."
        
        return result

# Initialize the checker
phone_checker = PhoneNumberChecker()