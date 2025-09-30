"""
Phone Number Checker Module
Integrates with TrueCaller-like services for phone number lookup
"""

import re
import requests
import json
from datetime import datetime
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

    def lookup_truecaller_bot(self, phone_number: str, bot_token: str = None) -> Optional[Dict]:
        """
        Query actual TrueCaller Bot via Telegram for phone number information
        """
        try:
            # Method 1: Try to query real TrueCaller bot if we have bot token
            if bot_token:
                print(f"Attempting to query TrueCaller bot for number: {phone_number}")
                result = self._query_truecaller_bot_real(phone_number, bot_token)
                if result:
                    print("Successfully got response from TrueCaller bot")
                    return result
                else:
                    print("No response from TrueCaller bot, falling back to alternatives")
            else:
                print("No bot token provided for TrueCaller bot query")
            
            # Method 2: Fallback to alternative lookup services
            print("Using alternative phone lookup methods")
            result = self._try_alternative_lookup(phone_number)
            return result
            
        except Exception as e:
            print(f"Error in TrueCaller lookup: {e}")
            return None

    def _find_truecaller_bot(self, bot_token: str) -> Optional[str]:
        """
        Find TrueCaller bot chat_id or username
        """
        try:
            # List of possible TrueCaller bot usernames to try
            possible_bots = [
                "@TrueCallerBot",
                "@truecaller_bot", 
                "@TrueCaller",
                "@GetContactBot",
                "@caller_id_bot"
            ]
            
            # Try each bot to see which one responds
            for bot_username in possible_bots:
                try:
                    # Try to get bot info
                    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    test_data = {
                        'chat_id': bot_username,
                        'text': '/start'
                    }
                    
                    response = self.session.post(send_url, json=test_data, timeout=5)
                    if response.status_code == 200:
                        return bot_username
                        
                except Exception:
                    continue
                    
            return None
            
        except Exception as e:
            print(f"Error finding TrueCaller bot: {e}")
            return None

    def _query_truecaller_bot_real(self, phone_number: str, bot_token: str) -> Optional[Dict]:
        """
        Actually send message to TrueCaller Bot via Telegram API and get response
        """
        try:
            import time
            
            # First find TrueCaller bot
            truecaller_bot = self._find_truecaller_bot(bot_token)
            if not truecaller_bot:
                print("Could not find TrueCaller bot")
                return None
            
            print(f"Found TrueCaller bot: {truecaller_bot}")
            
            # Get current message offset to avoid old messages
            updates_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            updates_response = self.session.get(updates_url, timeout=10)
            
            current_offset = 0
            if updates_response.status_code == 200:
                updates_data = updates_response.json()
                if updates_data.get('result'):
                    current_offset = updates_data['result'][-1].get('update_id', 0) + 1
            
            # Send message to TrueCaller bot
            send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Send the phone number to TrueCaller bot
            message_data = {
                'chat_id': truecaller_bot,
                'text': phone_number
            }
            
            # Send message
            response = self.session.post(send_url, json=message_data, timeout=10)
            
            if response.status_code != 200:
                print(f"Failed to send message to TrueCaller bot: {response.status_code}")
                response_data = response.json()
                print(f"Error details: {response_data}")
                return None
                
            print(f"Message sent successfully to {truecaller_bot}")
                
            # Wait for TrueCaller bot to respond
            time.sleep(5)
            
            # Get new updates to receive TrueCaller bot's response
            updates_with_offset_url = f"{updates_url}?offset={current_offset}"
            updates_response = self.session.get(updates_with_offset_url, timeout=10)
            
            if updates_response.status_code != 200:
                print("Failed to get updates from Telegram")
                return None
                
            updates_data = updates_response.json()
            print(f"Received {len(updates_data.get('result', []))} new updates")
            
            # Parse TrueCaller bot's response
            return self._parse_truecaller_response(updates_data, phone_number)
            
        except Exception as e:
            print(f"Error querying real TrueCaller bot: {e}")
            return None

    def _parse_truecaller_response(self, updates_data: dict, phone_number: str) -> Optional[Dict]:
        """
        Parse TrueCaller bot's response from Telegram updates
        """
        try:
            if not updates_data.get('ok') or not updates_data.get('result'):
                print("No valid updates received")
                return None
                
            print(f"Processing {len(updates_data['result'])} updates...")
                
            # Look for messages from TrueCaller bot
            for update in reversed(updates_data['result']):
                message = update.get('message', {})
                from_user = message.get('from', {})
                response_text = message.get('text', '')
                
                print(f"Checking message from: {from_user.get('username', 'Unknown')}")
                print(f"Message text: {response_text[:100]}...")
                
                # Check if this looks like a TrueCaller bot response
                if (from_user.get('is_bot') and 
                    ('truecaller' in from_user.get('username', '').lower() or
                     'caller' in from_user.get('first_name', '').lower() or
                     any(keyword in response_text.lower() for keyword in ['name:', 'caller:', 'country:', 'carrier:']))):
                    
                    print(f"Found TrueCaller response: {response_text}")
                    
                    # Parse the TrueCaller response text
                    parsed_info = self._extract_info_from_truecaller_text(response_text, phone_number)
                    if parsed_info:
                        return parsed_info
                        
            print("No TrueCaller bot response found in updates")
            return None
            
        except Exception as e:
            print(f"Error parsing TrueCaller response: {e}")
            return None

    def _extract_info_from_truecaller_text(self, text: str, phone_number: str) -> Optional[Dict]:
        """
        Extract information from TrueCaller bot's response text
        """
        try:
            result = {
                'number': phone_number,
                'valid': True,
                'name': 'לא ידוע',
                'carrier': 'לא ידוע',
                'line_type': 'לא ידוע',
                'country_name': 'לא ידוע',
                'spam_score': 0,
                'source': 'TrueCaller Bot',
                'raw_response': text
            }
            
            # Extract name (looking for patterns like "Name: John Doe")
            import re
            
            name_patterns = [
                r'Name:\s*([^\n\r]+)',
                r'שם:\s*([^\n\r]+)',
                r'Called ID:\s*([^\n\r]+)',
                r'Caller:\s*([^\n\r]+)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result['name'] = match.group(1).strip()
                    break
            
            # Extract carrier info
            carrier_patterns = [
                r'Carrier:\s*([^\n\r]+)',
                r'ספק:\s*([^\n\r]+)',
                r'Operator:\s*([^\n\r]+)'
            ]
            
            for pattern in carrier_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result['carrier'] = match.group(1).strip()
                    break
            
            # Extract country
            if 'Israel' in text or 'ישראל' in text:
                result['country_name'] = 'ישראל'
                result['country_flag'] = '🇮🇱'
            elif 'USA' in text or 'United States' in text:
                result['country_name'] = 'ארצות הברית'
                result['country_flag'] = '🇺🇸'
            
            # Check for spam indicators
            if any(word in text.lower() for word in ['spam', 'scam', 'fraud', 'ספאם']):
                result['spam_score'] = 80
            elif any(word in text.lower() for word in ['unknown', 'private', 'לא ידוע']):
                result['spam_score'] = 20
            
            return result
            
        except Exception as e:
            print(f"Error extracting info from TrueCaller text: {e}")
            return None

    def _try_opencnam_api(self, phone_number: str) -> Optional[Dict]:
        """
        Try OpenCNAM API for caller ID information
        """
        try:
            # OpenCNAM is a free caller ID API
            url = f"https://api.opencnam.com/v3/phone/{phone_number}"
            headers = {'Accept': 'application/json'}
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'number': phone_number,
                    'valid': True,
                    'name': data.get('name', 'לא ידוע'),
                    'carrier': 'לא ידוע',
                    'line_type': 'לא ידוע',
                    'country_name': 'לא ידוע',
                    'source': 'OpenCNAM'
                }
            return None
            
        except Exception:
            return None

    def _try_numverify_simulation(self, phone_number: str) -> Optional[Dict]:
        """
        Simulate NumVerify API call (requires API key for real use)
        """
        try:
            # This is a simulation - in real use you'd need an API key
            # For demo purposes, we'll analyze the number structure
            
            result = {
                'number': f"+{phone_number}",
                'valid': len(phone_number) >= 10,
                'name': 'לא ידוע',
                'carrier': 'לא ידוע',
                'line_type': 'נייד' if phone_number.startswith(('972', '1')) else 'לא ידוע',
                'country_name': 'לא ידוע',
                'source': 'NumVerify Simulation'
            }
            
            # Add country detection based on prefix
            if phone_number.startswith('972'):
                result.update({
                    'country_name': 'ישראל',
                    'country_flag': '🇮🇱'
                })
                # Add Israeli carrier detection
                if len(phone_number) > 3:
                    local_number = phone_number[3:]
                    israeli_info = self._analyze_israeli_number(local_number)
                    result.update(israeli_info)
                    
            elif phone_number.startswith('1'):
                result.update({
                    'country_name': 'ארצות הברית/קנדה',
                    'country_flag': '🇺🇸'
                })
            
            return result if result['valid'] else None
            
        except Exception:
            return None

    def _try_carrier_lookup(self, phone_number: str) -> Optional[Dict]:
        """
        Try carrier lookup using phone number analysis
        """
        try:
            # Use phonenumbers library for carrier detection
            import phonenumbers
            from phonenumbers import geocoder, carrier
            
            # Parse with different possible regions
            for region in ['IL', 'US', 'GB', 'DE', 'FR']:
                try:
                    parsed = phonenumbers.parse(f"+{phone_number}", region)
                    if phonenumbers.is_valid_number(parsed):
                        return {
                            'number': f"+{phone_number}",
                            'valid': True,
                            'name': 'לא ידוע',
                            'carrier': carrier.name_for_number(parsed, 'he') or 'לא ידוע',
                            'line_type': 'נייד' if phonenumbers.number_type(parsed) == phonenumbers.PhoneNumberType.MOBILE else 'קווי',
                            'country_name': geocoder.description_for_number(parsed, 'he') or 'לא ידוע',
                            'source': 'PhoneNumbers Library'
                        }
                except:
                    continue
                    
            return None
            
        except ImportError:
            # Fallback if phonenumbers not available
            return self._basic_phone_analysis(f"+{phone_number}")
        except Exception:
            return None

    def _parse_api_response(self, data: dict, phone_number: str) -> Optional[Dict]:
        """
        Parse API response and extract relevant information
        """
        try:
            result = {
                'number': phone_number,
                'valid': False,
                'name': 'לא ידוע',
                'carrier': 'לא ידוע',
                'line_type': 'לא ידוע',
                'country_name': 'לא ידוע',
                'location': 'לא ידוע',
                'spam_score': 0,
                'source': 'TrueCaller API'
            }
            
            # Handle different API response formats
            if 'data' in data:
                # TrueCaller format
                tc_data = data['data'][0] if data['data'] else {}
                result.update({
                    'valid': True,
                    'name': tc_data.get('name', 'לא ידוע'),
                    'carrier': tc_data.get('carrier', {}).get('name', 'לא ידוע'),
                    'country_name': tc_data.get('countryDetails', {}).get('name', 'לא ידוע'),
                    'spam_score': tc_data.get('spamInfo', {}).get('spamScore', 0)
                })
                
            elif 'valid' in data:
                # NumVerify format
                result.update({
                    'valid': data.get('valid', False),
                    'country_name': data.get('country_name', 'לא ידוע'),
                    'carrier': data.get('carrier', 'לא ידוע'),
                    'line_type': data.get('line_type', 'לא ידוע'),
                    'location': data.get('location', 'לא ידוע')
                })
                
            elif 'phone_valid' in data:
                # VeriPhone format  
                result.update({
                    'valid': data.get('phone_valid', False),
                    'country_name': data.get('country', 'לא ידוע'),
                    'carrier': data.get('carrier', 'לא ידוע'),
                    'line_type': data.get('phone_type', 'לא ידוע')
                })
            
            return result if result['valid'] else None
            
        except Exception as e:
            print(f"Error parsing API response: {e}")
            return None

    def _try_alternative_lookup(self, phone_number: str) -> Optional[Dict]:
        """
        Try alternative phone lookup methods when TrueCaller API fails
        """
        try:
            # Use our existing methods as fallback
            results = {}
            
            # Method 1: Basic phone analysis
            results.update(self._basic_phone_analysis(phone_number))
            
            # Method 2: Use phonenumbers library
            results.update(self._parse_phone_info(phone_number))
            
            # Method 3: Israeli number specific analysis
            if phone_number.startswith('+972') or phone_number.startswith('972'):
                clean_number = phone_number.replace('+972', '').replace('972', '')
                results.update(self._analyze_israeli_number(clean_number))
            
            return results if results else None
            
        except Exception:
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

    def check_phone_via_truecaller_bot(self, phone_number: str, bot_token: str = None) -> Dict:
        """
        Main method to check phone number using real TrueCaller bot
        """
        try:
            # First try to get info from real TrueCaller bot
            truecaller_info = self.lookup_truecaller_bot(phone_number, bot_token)
            
            # If TrueCaller fails, use alternative methods
            if not truecaller_info:
                truecaller_info = self._try_alternative_lookup(phone_number)
            
            # Combine with basic analysis
            basic_info = self._basic_phone_analysis(phone_number)
            
            result = {
                'input_number': phone_number,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'truecaller_data': truecaller_info or {},
                'basic_data': basic_info or {},
                'success': truecaller_info is not None or basic_info is not None
            }
            
            return result
            
        except Exception as e:
            return {
                'input_number': phone_number,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    def format_phone_result(self, phone_result: Dict, original_number: str) -> str:
        """Format phone lookup results for display - handles new result format"""
        if not phone_result or not phone_result.get('success'):
            return "❌ לא הצלחתי לבדוק את המספר. אנא ודא שהמספר נכון."
        
        # Get data from TrueCaller or basic analysis
        phone_data = phone_result.get('truecaller_data') or phone_result.get('basic_data', {})
        
        if not phone_data:
            return "❌ לא נמצא מידע על המספר."
        
        # Build result message
        result = f"📱 **בדיקת מספר טלפון** (דרך בוט TrueCaller)\n\n"
        result += f"🔢 **מספר מקורי:** `{original_number}`\n"
        result += f"🌍 **מספר בינלאומי:** `{phone_data.get('number', phone_result.get('input_number', 'לא ידוע'))}`\n"
        
        if phone_data.get('valid'):
            result += f"✅ **תקינות:** מספר תקין\n"
        else:
            result += f"⚠️ **תקינות:** מספר לא תקין או לא מוכר\n"
        
        # Show caller name if available (TrueCaller style)
        if phone_data.get('name') and phone_data['name'] != 'לא ידוע':
            result += f"👤 **שם:** {phone_data['name']}\n"
        
        if phone_data.get('country_name'):
            flag = phone_data.get('country_flag', '')
            result += f"🏳️ **מדינה:** {flag} {phone_data['country_name']}\n"
        
        if phone_data.get('line_type'):
            result += f"📞 **סוג קו:** {phone_data['line_type']}\n"
        
        if phone_data.get('carrier') and phone_data['carrier'] != 'לא ידוע':
            result += f"📡 **ספק:** {phone_data['carrier']}\n"
        
        if phone_data.get('location') and phone_data['location'] != 'לא ידוע':
            result += f"📍 **מיקום:** {phone_data['location']}\n"
        
        # Show spam score if available
        if phone_data.get('spam_score', 0) > 0:
            spam_level = "🔴 גבוה" if phone_data['spam_score'] > 70 else "🟡 בינוני" if phone_data['spam_score'] > 30 else "🟢 נמוך"
            result += f"🚨 **דירוג ספאם:** {spam_level} ({phone_data['spam_score']}%)\n"
        
        # Show data source
        if phone_data.get('source'):
            result += f"🔍 **מקור:** {phone_data['source']}\n"
        
        # Add timestamp
        if phone_result.get('timestamp'):
            result += f"🕐 **זמן בדיקה:** {phone_result['timestamp']}\n"
        
        # Add disclaimer
        result += f"\n⚠️ **הערה חשובה:**\n"
        result += f"הבוט מנסה לפנות לבוט TrueCaller האמיתי בטלגרם לקבלת מידע.\n"
        result += f"במקרה שהבוט לא זמין, המידע מתקבל ממקורות חופשיים אחרים.\n"
        result += f"המידע עשוי להיות לא מדויק או לא עדכני."
        
        return result

# Initialize the checker
phone_checker = PhoneNumberChecker()