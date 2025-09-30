"""
Network Tools Module
Port scanning, ping tests, and network utilities
"""

import socket
import asyncio
import time
from typing import List, Tuple, Dict
import concurrent.futures
import threading

class NetworkTools:
    """Network analysis tools"""
    
    def __init__(self):
        self.common_ports = {
            21: "FTP",
            22: "SSH", 
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            993: "IMAPS",
            995: "POP3S",
            1433: "MSSQL",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            6379: "Redis",
            8080: "HTTP-Alt",
            8443: "HTTPS-Alt",
            9200: "Elasticsearch"
        }
    
    def scan_port(self, target: str, port: int, timeout: float = 1.0) -> Tuple[int, bool, str]:
        """
        Scan a single port on target host
        Returns: (port, is_open, service_name)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((target, port))
            sock.close()
            
            is_open = result == 0
            service = self.common_ports.get(port, "Unknown")
            
            return port, is_open, service
            
        except socket.gaierror:
            # Host not found
            return port, False, "Host Error"
        except Exception:
            return port, False, "Error"
    
    async def scan_ports_async(self, target: str, ports: List[int], max_workers: int = 50) -> Dict:
        """
        Asynchronously scan multiple ports
        """
        start_time = time.time()
        open_ports = []
        closed_ports = []
        
        # Use ThreadPoolExecutor for concurrent scanning
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all port scan tasks
            future_to_port = {
                executor.submit(self.scan_port, target, port): port 
                for port in ports
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_port):
                port, is_open, service = future.result()
                
                if is_open:
                    open_ports.append({
                        'port': port,
                        'service': service,
                        'status': 'open'
                    })
                else:
                    closed_ports.append({
                        'port': port,
                        'service': service, 
                        'status': 'closed'
                    })
        
        scan_time = time.time() - start_time
        
        return {
            'target': target,
            'scan_time': round(scan_time, 2),
            'total_ports': len(ports),
            'open_ports': sorted(open_ports, key=lambda x: x['port']),
            'closed_count': len(closed_ports),
            'success': True
        }
    
    def get_common_ports(self) -> List[int]:
        """Get list of common ports to scan"""
        return list(self.common_ports.keys())
    
    def get_port_ranges(self, range_type: str = "common") -> List[int]:
        """
        Get different port ranges for scanning
        """
        if range_type == "common":
            return self.get_common_ports()
        elif range_type == "top100":
            # Top 100 most common ports
            return [
                7, 9, 13, 21, 22, 23, 25, 26, 37, 53, 79, 80, 81, 88, 106, 110, 111,
                113, 119, 135, 139, 143, 144, 179, 199, 389, 427, 443, 444, 445,
                465, 513, 514, 515, 543, 544, 548, 554, 587, 631, 646, 873, 990,
                993, 995, 1025, 1026, 1027, 1028, 1029, 1110, 1433, 1720, 1723,
                1755, 1900, 2000, 2001, 2049, 2121, 2717, 3000, 3128, 3306, 3389,
                3986, 4899, 5000, 5009, 5051, 5060, 5101, 5190, 5357, 5432, 5631,
                5666, 5800, 5900, 6000, 6001, 6646, 7070, 8000, 8008, 8009, 8080,
                8081, 8443, 8888, 9100, 9999, 10000, 32768, 49152, 49153, 49154,
                49155, 49156, 49157
            ]
        elif range_type == "quick":
            # Quick scan - most important ports
            return [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3389, 8080]
        elif range_type == "full":
            # Full port scan - ALL ports 1-65535 (WARNING: This is VERY slow!)
            return list(range(1, 65536))
        elif range_type == "web":
            # Web services focused scan
            return [80, 443, 8000, 8008, 8080, 8081, 8443, 8888, 3000, 3001, 4000, 4001, 5000, 5001, 9000, 9001]
        else:
            return self.get_common_ports()
    
    async def ping_host(self, target: str) -> Dict:
        """
        Simple ping test using socket connect
        """
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            
            # Try to connect to port 80 (most likely to be open)
            result = sock.connect_ex((target, 80))
            sock.close()
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                'target': target,
                'reachable': result == 0,
                'response_time': round(response_time, 2),
                'success': True
            }
            
        except socket.gaierror:
            return {
                'target': target,
                'reachable': False,
                'error': 'Host not found',
                'success': False
            }
        except Exception as e:
            return {
                'target': target,
                'reachable': False,
                'error': str(e),
                'success': False
            }

def format_port_scan_result(result: Dict) -> str:
    """
    Format port scan results for Telegram message with enhanced UX
    """
    if not result.get('success'):
        return f"❌ **שגיאה בסריקת {result['target']}**\n{result.get('error', 'שגיאה לא ידועה')}"
    
    target = result['target']
    scan_time = result['scan_time']
    total_ports = result['total_ports']
    open_ports = result['open_ports']
    closed_count = result['closed_count']
    
    # Calculate percentage and create visual progress
    open_count = len(open_ports)
    open_percentage = (open_count / total_ports * 100) if total_ports > 0 else 0
    
    # Create visual progress bar
    bar_length = 10
    filled_length = int(bar_length * open_count // total_ports) if total_ports > 0 else 0
    bar = "🟩" * filled_length + "🟥" * (bar_length - filled_length)
    
    # Build response message with better formatting
    response = f"🎯 **תוצאות סריקה ל-** `{target}`\n\n"
    
    # Summary stats with visual elements
    response += f"📊 **סיכום סריקה:**\n"
    response += f"⏱️ זמן: `{scan_time}s` | 🎯 נסרקו: `{total_ports:,}`\n"
    response += f"� פתוחים: `{open_count}` | 🔴 סגורים: `{closed_count}`\n"
    response += f"� אחוז פתוחים: `{open_percentage:.1f}%`\n\n"
    
    # Visual progress bar
    response += f"� **התפלגות:** {bar}\n\n"
    
    if open_ports:
        response += "🚪 **פורטים פתוחים שנמצאו:**\n"
        
        # Group ports by service type for better readability
        web_ports = []
        email_ports = []
        db_ports = []
        other_ports = []
        
        for port_info in open_ports[:20]:  # Increased limit to 20
            port = port_info['port']
            service = port_info['service']
            
            if port in [80, 443, 8000, 8080, 8443, 8888, 3000, 5000]:
                web_ports.append(f"`{port}` {service}")
            elif port in [25, 110, 143, 465, 587, 993, 995]:
                email_ports.append(f"`{port}` {service}")
            elif port in [3306, 5432, 1433, 6379, 27017]:
                db_ports.append(f"`{port}` {service}")
            else:
                other_ports.append(f"`{port}` {service}")
        
        # Display grouped results
        if web_ports:
            response += f"🌐 **Web Services:** {', '.join(web_ports)}\n"
        if email_ports:
            response += f"📧 **Email Services:** {', '.join(email_ports)}\n"
        if db_ports:
            response += f"🗄️ **Databases:** {', '.join(db_ports)}\n"
        if other_ports:
            response += f"🔧 **Other Services:** {', '.join(other_ports)}\n"
        
        if len(open_ports) > 20:
            response += f"\n➕ **ועוד {len(open_ports) - 20} פורטים נוספים**\n"
    else:
        response += "🔒 **לא נמצאו פורטים פתוחים**\n\n"
        response += "💡 **טיפים:**\n"
        response += "• נסה סריקה מקיפה יותר (`top100`)\n"
        response += "• בדוק אם השרת מגיב (`/ping`)\n"
        response += "• ודא שהכתובת נכונה\n"
    
    # Security note with better formatting
    response += f"\n🛡️ **אבטחה:** סריקה לצרכי אבחון בלבד"
    
    return response

def format_ping_result(result: Dict) -> str:
    """
    Format ping results for Telegram message
    """
    if not result.get('success'):
        return f"❌ **שגיאה ב-ping ל-{result['target']}**\n{result.get('error', 'שגיאה לא ידועה')}"
    
    target = result['target']
    reachable = result['reachable']
    
    if reachable:
        response_time = result['response_time']
        return f"🏓 **Ping ל-{target}:**\n✅ **זמין** - {response_time}ms"
    else:
        return f"🏓 **Ping ל-{target}:**\n❌ **לא זמין**"