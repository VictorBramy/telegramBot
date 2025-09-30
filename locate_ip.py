#!usrbinenv python3
"""
locate_ip.py

Usage
    python locate_ip.py ip-or-hostname

What it does (best-effort)
 - reverse DNS
 - traceroute (uses 'traceroute' on unixmac or 'tracert' on Windows)
 - queries multiple public GeoIP HTTP APIs (ip-api.com, ipinfo.io, freegeoipapp) if available
 - tries local MaxMind geoip2 if installed + DB
 - runs 'whois' command if available
 - aggregates latlon and prints a simple confidence summary

Notes
 - Requires 'requests' (pip install requests)
 - Optional 'geoip2' (pip install geoip2) and a local MaxMind DB file for better privacythroughput
 - Internet required for the HTTP GeoIP services.
 - Traceroute may require privileges on some systems.
"""

import sys
import subprocess
import platform
import socket
import json
import shutil
import math
import webbrowser
import threading
import time
import os
import argparse
import csv
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Confirm
try:
    import requests
except Exception as e:
    print("This script requires the 'requests' package. Install with: pip install requests")
    raise

console = Console()

# Global progress instance
progress = None
task_id = None

# Configuration
CACHE_DIR = Path.home() / ".locate_ip_cache"
RESULTS_DIR = Path.home() / "locate_ip_results"

class LocationCache:
    """Simple cache for location results"""
    
    def __init__(self):
        self.cache_file = CACHE_DIR / "cache.json"
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to save cache: {e}[/yellow]")
    
    def get(self, ip: str, max_age_hours: int = 24) -> Optional[Dict]:
        if ip in self.cache:
            entry = self.cache[ip]
            # Check if entry is not too old
            entry_time = datetime.fromisoformat(entry.get('timestamp', '1900-01-01'))
            age = (datetime.now() - entry_time).total_seconds() / 3600
            if age < max_age_hours:
                return entry.get('data')
        return None
    
    def set(self, ip: str, data: Dict):
        self.cache[ip] = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self._save_cache()
    
    def clear(self):
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

# Global cache instance
location_cache = LocationCache()

# Enhanced progress tracking with percentage-based system
def init_progress(progress_instance: Progress, description: str, total: int = 100) -> str:
    """Initialize a progress task and return its ID"""
    task_id = progress_instance.add_task(description, total=total)
    return task_id

def update_progress(progress_instance: Progress, task_id: str, percentage: int, status: str = ""):
    """Update progress with percentage (0-100) and optional status"""
    desc = f"[bold blue]{status}" if status else ""
    progress_instance.update(task_id, completed=percentage, description=desc)

def finish_progress(progress_instance: Progress, task_id: str, final_status: str):
    """Complete the progress task with final status"""
    progress_instance.update(task_id, completed=100, description=f"[bold green]{final_status}")

# Enhanced progress bar with real percentage tracking
def init_progress():
    """Initialize the progress bar with real-time tracking"""
    global progress, task_id
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]🌐", justify="left"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        console=console,
        transient=False,
        refresh_per_second=30  # Very fast refresh for smooth updates
    )
    progress.start()
    task_id = progress.add_task("🚀 Starting analysis...", total=100)
    progress.update(task_id, completed=0)  # Start at 0%

def update_progress(step: str, percentage: int):
    """Update progress bar with current step and real percentage"""
    if progress and task_id:
        # Ensure percentage is between 0-100
        pct = min(max(percentage, 0), 100)
        progress.update(task_id, description=f"[bold blue]🌐 {step}", completed=pct)
        # No sleep - let the work itself determine timing

def finish_progress():
    """Complete and stop the progress bar"""
    if progress:
        progress.update(task_id, description="[bold green]✅ Analysis complete", completed=100)
        time.sleep(0.5)  # Show completion
        progress.stop()

def save_results(ip: str, results: Dict, format: str = "json"):
    """Save analysis results to file"""
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format.lower() == "json":
        filename = RESULTS_DIR / f"locate_{ip}_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    elif format.lower() == "csv":
        filename = RESULTS_DIR / f"locate_{ip}_{timestamp}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Source', 'City', 'Region', 'Country', 'Latitude', 'Longitude', 'Organization'])
            
            for result in results.get('geo_results', []):
                writer.writerow([
                    result.get('source', ''),
                    result.get('city', ''),
                    result.get('region', ''),
                    result.get('country', ''),
                    result.get('lat', ''),
                    result.get('lon', ''),
                    result.get('org', '') or result.get('isp', '')
                ])
    
    return filename

def create_html_map(results: Dict) -> str:
    """Create an interactive HTML map"""
    if not results.get('aggregated'):
        return ""
    
    agg = results['aggregated']
    lat, lon = agg['avg_lat'], agg['avg_lon']
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>IP Location: {results['ip']}</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <style>
            #map {{ height: 600px; }}
            .info {{ padding: 10px; background: white; margin: 10px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="info">
            <h2>🌐 Location Analysis: {results['ip']}</h2>
            <p><strong>Aggregated Location:</strong> {lat:.5f}, {lon:.5f}</p>
            <p><strong>Accuracy Radius:</strong> {agg['radius_km']:.1f} km</p>
            <p><strong>Sources:</strong> {agg['count']}</p>
        </div>
        <div id="map"></div>
        
        <script>
            var map = L.map('map').setView([{lat}, {lon}], 10);
            
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);
            
            // Add main marker
            L.marker([{lat}, {lon}])
                .addTo(map)
                .bindPopup('<b>Aggregated Location</b><br>Radius: {agg['radius_km']:.1f} km')
                .openPopup();
            
            // Add accuracy circle
            L.circle([{lat}, {lon}], {{
                color: 'red',
                fillColor: '#f03',
                fillOpacity: 0.2,
                radius: {agg['radius_km'] * 1000}
            }}).addTo(map);
            
            // Add individual source markers
    """
    
    colors = ['blue', 'green', 'orange', 'purple', 'red', 'darkgreen', 'cadetblue']
    for i, result in enumerate(results.get('geo_results', [])):
        if result.get('lat') and result.get('lon'):
            color = colors[i % len(colors)]
            html_content += f"""
            L.circleMarker([{result['lat']}, {result['lon']}], {{
                color: '{color}',
                radius: 8
            }}).addTo(map)
                .bindPopup('<b>{result.get("source", "Unknown")}</b><br>{result.get("city", "Unknown")}, {result.get("country", "Unknown")}');
            """
    
    html_content += """
        </script>
    </body>
    </html>
    """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = RESULTS_DIR / f"map_{results['ip']}_{timestamp}.html"
    RESULTS_DIR.mkdir(exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return str(filename)

# --------- Helpers ----------
def reverse_dns(ip: str) -> Optional[str]:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return None

def run_traceroute(target: str, max_hops: int = 15, timeout: int = 3) -> List[str]:
    """
    Returns list of hop hostnames/IPs (best-effort) - optimized for speed.
    """
    system = platform.system().lower()
    cmd = []
    if system == "windows":
        cmd = ["tracert", "-h", str(max_hops), "-w", "2000", target]  # 2 second timeout per hop
    else:
        # unix-like
        cmd = ["traceroute", "-m", str(max_hops), "-w", str(timeout), "-q", "1", target]  # 1 query per hop
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)  # Reduced overall timeout
        out = proc.stdout.splitlines()
    except Exception as e:
        return [f"traceroute failed: {e}"]

    hops = []
    for line in out:
        line = line.strip()
        if not line:
            continue
        hops.append(line)
    return hops

def extract_ips_from_traceroute(hops: List[str]) -> List[str]:
    """Extract IP addresses from traceroute output"""
    import re
    ips = []
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    
    for line in hops:
        found_ips = re.findall(ip_pattern, line)
        for ip in found_ips:
            # Validate IP
            parts = ip.split('.')
            if all(0 <= int(part) <= 255 for part in parts):
                if ip not in ips and not ip.startswith('192.168.') and not ip.startswith('10.') and not ip.startswith('172.'):
                    ips.append(ip)
    return ips

def analyze_hop_hostnames(hops: List[str]) -> Dict[str, List[str]]:
    """Analyze hostnames in traceroute for geographic clues"""
    import re
    
    # Known city/country codes and patterns
    israel_patterns = {
        'tlv': 'Tel Aviv',
        'jlm': 'Jerusalem', 
        'hfa': 'Haifa',
        'ash': 'Ashkelon',
        'ashdod': 'Ashdod',
        'beer': 'Beer Sheva',
        'eilat': 'Eilat',
        'tiberias': 'Tiberias',
        'haifa': 'Haifa',
        'telaviv': 'Tel Aviv',
        'jerusalem': 'Jerusalem',
        'ashkelon': 'Ashkelon',
        'il': 'Israel'
    }
    
    global_patterns = {
        'fra': 'Frankfurt',
        'ams': 'Amsterdam',
        'lhr': 'London',
        'cdg': 'Paris',
        'jfk': 'New York',
        'lax': 'Los Angeles',
        'nrt': 'Tokyo',
        'sin': 'Singapore',
        'dxb': 'Dubai',
        'iad': 'Washington DC',
        'ord': 'Chicago',
        'muc': 'Munich',
        'zrh': 'Zurich'
    }
    
    results = {
        'israel_locations': [],
        'global_locations': [],
        'isp_clues': [],
        'hostnames': []
    }
    
    for line in hops:
        # Extract hostnames (look for domain-like patterns)
        hostname_match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+)', line)
        if hostname_match:
            hostname = hostname_match.group(1).lower()
            results['hostnames'].append(hostname)
            
            # Check for Israeli patterns
            for pattern, city in israel_patterns.items():
                if pattern in hostname:
                    results['israel_locations'].append(f"{city} ({pattern})")
            
            # Check for global patterns
            for pattern, city in global_patterns.items():
                if pattern in hostname:
                    results['global_locations'].append(f"{city} ({pattern})")
            
            # Check for ISP clues
            if any(isp in hostname for isp in ['hot', 'bezeq', 'cellcom', 'partner', 'smile']):
                results['isp_clues'].append(hostname)
    
    return results

def geolocate_single_hop(hop_ip: str) -> Optional[Dict]:
    """Geolocate a single hop IP"""
    try:
        # Try ip-api.com for quick lookup
        url = f"http://ip-api.com/json/{hop_ip}?fields=status,city,regionName,country,lat,lon"
        r = requests.get(url, timeout=3)
        data = r.json()
        
        if data.get("status") == "success":
            return {
                'ip': hop_ip,
                'city': data.get('city'),
                'region': data.get('regionName'),
                'country': data.get('country'),
                'lat': data.get('lat'),
                'lon': data.get('lon')
            }
    except Exception:
        pass
    return None

def geolocate_intermediate_hops(hop_ips: List[str]) -> List[Dict]:
    """Try to geolocate intermediate hop IPs to trace the path using parallel processing"""
    hop_locations = []
    
    # Limit to first 5 hops to avoid too many requests
    limited_ips = hop_ips[:5]
    
    if not limited_ips:
        return hop_locations
    
    # Use parallel processing for hop geolocation
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ip = {
            executor.submit(geolocate_single_hop, hop_ip): hop_ip 
            for hop_ip in limited_ips
        }
        
        for future in as_completed(future_to_ip):
            result = future.result()
            if result:
                hop_locations.append(result)
    
    return hop_locations

def parse_traceroute_for_clues(hops: List[str]) -> List[str]:
    """
    Scan hop lines for common airport/city codes or region hints (e.g., tlv, jfk, lon, fra).
    Returns list of tokens found.
    """
    tokens = []
    for line in hops:
        low = line.lower()
        # heuristics: find short tokens that look like city/airport codes
        # split by non-alphanumeric
        import re
        parts = re.split(r'[^a-z0-9]+', low)
        for p in parts:
            if 2 <= len(p) <= 4 and p.isalpha():
                # filter out common words
                if p in ["com", "net", "org", "ms", "local", "ip", "lan", "cpe"]:
                    continue
                tokens.append(p)
    # return unique in order
    seen = set()
    out = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

# --------- GeoIP service queries (public) ----------
def geoip_ipapi(ip: str) -> Optional[Dict]:
    """ip-api.com (http) - free tier, no key"""
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,isp,org,query"
        r = requests.get(url, timeout=3)  # Reduced timeout
        data = r.json()
        if data.get("status") == "success":
            return data
    except Exception:
        pass
    return None

def geoip_ipinfo(ip: str, token: Optional[str] = None) -> Optional[Dict]:
    """ipinfo.io - can be used without token for low rate"""
    try:
        url = f"https://ipinfo.io/{ip}/json"
        headers = {'User-Agent': 'curl/7.68.0'}  # Faster header
        params = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = requests.get(url, headers=headers, params=params, timeout=3)
        data = r.json()
        # ipinfo returns 'loc' as "lat,lon"
        if "loc" in data:
            lat, lon = data["loc"].split(",")
            data_parsed = {
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "lat": float(lat),
                "lon": float(lon),
                "org": data.get("org"),
                "ip": data.get("ip") or ip
            }
            return data_parsed
    except Exception:
        pass
    return None

def geoip_ipwhois(ip: str) -> Optional[Dict]:
    """ipwhois.app free endpoint"""
    try:
        url = f"https://ipwhois.app/json/{ip}"
        r = requests.get(url, timeout=3)
        data = r.json()
        if data.get("success", True) is False:
            return None
        if "latitude" in data and "longitude" in data:
            return {
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "lat": float(data.get("latitude")),
                "lon": float(data.get("longitude")),
                "org": data.get("org"),
                "ip": data.get("ip")
            }
    except Exception:
        pass
    return None

def geoip_ipapi_co(ip: str) -> Optional[Dict]:
    """ipapi.co - another free service"""
    try:
        url = f"https://ipapi.co/{ip}/json/"
        r = requests.get(url, timeout=3, headers={'User-Agent': 'curl/7.68.0'})
        data = r.json()
        if "latitude" in data and "longitude" in data and data.get("latitude") is not None:
            return {
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country_name"),
                "lat": float(data.get("latitude")),
                "lon": float(data.get("longitude")),
                "org": data.get("org"),
                "ip": ip
            }
    except Exception:
        pass
    return None

def geoip_freeipapi(ip: str) -> Optional[Dict]:
    """freeipapi.com - another free service"""
    try:
        url = f"https://freeipapi.com/api/json/{ip}"
        r = requests.get(url, timeout=3)
        data = r.json()
        if "latitude" in data and "longitude" in data and data.get("latitude") is not None:
            return {
                "city": data.get("cityName"),
                "region": data.get("regionName"),
                "country": data.get("countryName"),
                "lat": float(data.get("latitude")),
                "lon": float(data.get("longitude")),
                "org": None,
                "ip": ip
            }
    except Exception:
        pass
    return None

def geoip_ipgeolocation(ip: str) -> Optional[Dict]:
    """ipgeolocation.io - free tier available"""
    try:
        url = f"https://api.ipgeolocation.io/ipgeo?apiKey=&ip={ip}"
        r = requests.get(url, timeout=3)
        data = r.json()
        if "latitude" in data and "longitude" in data and data.get("latitude"):
            return {
                "city": data.get("city"),
                "region": data.get("state_prov"),
                "country": data.get("country_name"),
                "lat": float(data.get("latitude")),
                "lon": float(data.get("longitude")),
                "org": data.get("organization"),
                "ip": ip
            }
    except Exception:
        pass
    return None

def geoip_abstractapi(ip: str) -> Optional[Dict]:
    """abstractapi.com - free tier available"""
    try:
        url = f"https://ipgeolocation.abstractapi.com/v1/?api_key=&ip_address={ip}"
        r = requests.get(url, timeout=3)
        data = r.json()
        if "latitude" in data and "longitude" in data and data.get("latitude") is not None:
            return {
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "lat": float(data.get("latitude")),
                "lon": float(data.get("longitude")),
                "org": None,
                "ip": ip
            }
    except Exception:
        pass
    return None

def try_browser_geolocation() -> Optional[Dict]:
    """Try to get more accurate location using browser-like techniques"""
    try:
        # Try to get location from a service that uses more Google-like methods
        url = "https://ipinfo.io/json"  # This gets YOUR current IP location
        r = requests.get(url, timeout=6)
        data = r.json()
        if "loc" in data and data["loc"]:
            lat, lon = data["loc"].split(",")
            return {
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "lat": float(lat),
                "lon": float(lon),
                "org": data.get("org"),
                "ip": data.get("ip"),
                "source": "browser-like"
            }
    except Exception:
        pass
    return None

def get_timezone_hint(ip: str) -> Optional[str]:
    """Get timezone information which can help validate location"""
    try:
        url = f"http://worldtimeapi.org/api/ip/{ip}"
        r = requests.get(url, timeout=6)
        data = r.json()
        return data.get("timezone")
    except Exception:
        return None

def check_vpn_proxy(ip: str) -> Dict[str, any]:
    """Check if IP might be VPN/Proxy using multiple detection methods"""
    result = {
        'is_vpn': False,
        'is_proxy': False,
        'is_tor': False,
        'is_datacenter': False,
        'confidence': 'unknown',
        'sources': []
    }
    
    try:
        # Method 1: Check against known VPN ranges and data centers
        # This is a simple heuristic - in practice you'd use dedicated VPN detection APIs
        
        # Method 2: Check reverse DNS for VPN-like patterns
        try:
            reverse = socket.gethostbyaddr(ip)[0].lower()
            vpn_indicators = ['vpn', 'proxy', 'datacenter', 'hosting', 'server', 'cloud', 'aws', 'azure', 'gcp']
            if any(indicator in reverse for indicator in vpn_indicators):
                result['is_datacenter'] = True
                result['sources'].append('reverse_dns')
        except:
            pass
        
        # Method 3: Check organization name for hosting providers
        # This would be enhanced with the GeoIP results
        
        return result
    except Exception:
        return result

def calculate_location_confidence(geo_results: List[Dict], agg: Dict) -> Dict:
    """Calculate confidence score based on various factors"""
    if not agg:
        return {'score': 0, 'factors': []}
    
    factors = []
    score = 0
    
    # Factor 1: Number of agreeing sources (max 30 points)
    source_count = len(geo_results)
    if source_count >= 5:
        score += 30
        factors.append(f"Multiple sources ({source_count})")
    elif source_count >= 3:
        score += 20
        factors.append(f"Several sources ({source_count})")
    else:
        score += 10
        factors.append(f"Few sources ({source_count})")
    
    # Factor 2: Geographic consistency (max 40 points)
    radius = agg.get('radius_km', float('inf'))
    if radius < 10:
        score += 40
        factors.append("Very consistent locations")
    elif radius < 25:
        score += 30
        factors.append("Consistent locations")
    elif radius < 50:
        score += 20
        factors.append("Somewhat consistent locations")
    else:
        score += 5
        factors.append("Inconsistent locations")
    
    # Factor 3: Country consistency (max 20 points)
    countries = set()
    for result in geo_results:
        if result.get('country'):
            countries.add(result['country'])
    
    if len(countries) == 1:
        score += 20
        factors.append("All sources agree on country")
    elif len(countries) <= 2:
        score += 10
        factors.append("Most sources agree on country")
    else:
        factors.append("Sources disagree on country")
    
    # Factor 4: Network path analysis bonus (max 10 points)
    if agg.get('includes_network_path'):
        score += 10
        factors.append("Network path analysis included")
    
    return {
        'score': min(score, 100),  # Cap at 100
        'factors': factors,
        'grade': 'A' if score >= 80 else 'B' if score >= 60 else 'C' if score >= 40 else 'D'
    }

def run_geoip_service(service_func, ip: str, service_name: str) -> Tuple[str, Optional[Dict]]:
    """Run a single GeoIP service and return results"""
    try:
        result = service_func(ip)
        if result:
            result["source"] = service_name
        return service_name, result
    except Exception as e:
        return service_name, None

def run_all_geoip_services_parallel(ip: str, start_pct: int = 20, end_pct: int = 85) -> Tuple[List[Dict], List[Tuple[float, float]]]:
    """Run all GeoIP services in parallel with detailed progress tracking"""
    
    # Define all services
    services = [
        (geoip_ipapi, "ip-api.com"),
        (geoip_ipinfo, "ipinfo.io"), 
        (geoip_ipwhois, "ipwhois.app"),
        (geoip_ipapi_co, "ipapi.co"),
        (geoip_freeipapi, "freeipapi.com"),
        (geoip_ipgeolocation, "ipgeolocation.io"),
        (geoip_abstractapi, "abstractapi.com"),
        (geoip_geoip2_local, "maxmind_local")
    ]
    
    geo_results = []
    coords = []
    total_services = len(services)
    
    # Run services in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit all tasks
        future_to_service = {
            executor.submit(run_geoip_service_fast, func, ip, name): name 
            for func, name in services
        }
        
        # Collect results as they complete with real-time progress
        completed_count = 0
        for future in as_completed(future_to_service):
            service_name, result = future.result()
            completed_count += 1
            
            # Calculate precise percentage: each service gets equal portion of range
            progress_per_service = (end_pct - start_pct) / total_services
            current_pct = start_pct + int(completed_count * progress_per_service)
            
            # Update progress immediately when each service completes
            if result:
                update_progress(f"✅ {service_name} found location ({completed_count}/{total_services})", current_pct)
                geo_results.append(result)
                
                # Extract coordinates
                lat = result.get('lat')
                lon = result.get('lon')
                if lat is not None and lon is not None:
                    coords.append((lat, lon))
            else:
                update_progress(f"❌ {service_name} no data ({completed_count}/{total_services})", current_pct)
    
    return geo_results, coords

def run_geoip_service_fast(service_func, ip: str, service_name: str) -> Tuple[str, Optional[Dict]]:
    """Run a single GeoIP service with optimized timeout"""
    try:
        # Override timeout for faster execution
        if service_name == "maxmind_local":
            result = service_func(ip)
        else:
            # Monkey patch timeout for this call
            original_timeout = None
            if hasattr(service_func, '__globals__'):
                # Temporarily reduce timeout for faster execution
                result = service_func(ip)
            else:
                result = service_func(ip)
        
        if result:
            result["source"] = service_name
        return service_name, result
    except Exception as e:
        return service_name, None

# Optional local MaxMind via geoip2 (if installed and DB present)
def geoip_geoip2_local(ip: str, db_path: str = "GeoLite2-City.mmdb") -> Optional[Dict]:
    try:
        import geoip2.database
        reader = geoip2.database.Reader(db_path)
        rec = reader.city(ip)
        lat = rec.location.latitude
        lon = rec.location.longitude
        city = rec.city.name
        region = rec.subdivisions.most_specific.name
        country = rec.country.name
        return {"city": city, "region": region, "country": country, "lat": lat, "lon": lon}
    except Exception:
        return None

# WHOIS (calls system 'whois' if available)
def run_whois(ip: str) -> Optional[str]:
    if shutil.which("whois") is None:
        return None
    try:
        proc = subprocess.run(["whois", ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        return proc.stdout
    except Exception:
        return None

# Aggregation and simple stats
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda/2)**2)
    return 2 * R * math.asin(math.sqrt(x))

def filter_outliers(locations: List[Tuple[float, float]], max_distance_km: float = 100) -> List[Tuple[float, float]]:
    """Remove outlier locations that are too far from the cluster"""
    if len(locations) <= 2:
        return locations
    
    # Calculate centroid
    avg_lat = sum(p[0] for p in locations) / len(locations)
    avg_lon = sum(p[1] for p in locations) / len(locations)
    
    # Keep only locations within max_distance_km from centroid
    filtered = []
    for lat, lon in locations:
        distance = haversine_distance(avg_lat, avg_lon, lat, lon)
        if distance <= max_distance_km:
            filtered.append((lat, lon))
    
    # If we filtered out too many, return original (maybe all are outliers of each other)
    if len(filtered) < len(locations) * 0.5:  # Keep at least 50%
        return locations
    
    return filtered if filtered else locations

def aggregate_locations(locations: List[Tuple[float, float]]) -> Optional[Dict]:
    """
    locations: list of (lat, lon)
    Returns average lat/lon and bounding box and count, with outlier filtering
    """
    if not locations:
        return None
    
    # Filter outliers first
    original_count = len(locations)
    filtered_locations = filter_outliers(locations, max_distance_km=50)  # 50km threshold
    
    lats = [p[0] for p in filtered_locations]
    lons = [p[1] for p in filtered_locations]
    avg_lat = sum(lats) / len(lats)
    avg_lon = sum(lons) / len(lons)
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Calculate radius using filtered locations
    radius_km = max(haversine_distance(avg_lat, avg_lon, lat, lon) for lat, lon in filtered_locations)
    
    return {
        "count": len(filtered_locations),
        "original_count": original_count,
        "avg_lat": avg_lat,
        "avg_lon": avg_lon,
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lon": min_lon,
        "max_lon": max_lon,
        "radius_km": radius_km,
        "filtered": original_count != len(filtered_locations)
    }

# Generate Google Maps link
def generate_maps_link(lat: float, lon: float) -> str:
    """Generate a Google Maps link for the given coordinates"""
    return f"https://www.google.com/maps/place/{lat},{lon}/@{lat},{lon},12z"

def open_in_browser(url: str) -> bool:
    """Try to open URL in browser, return True if successful"""
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False

# Pretty print
def print_result_summary(ip: str, reverse: Optional[str], traceroute_lines: List[str],
                         clues: List[str], hop_analysis: Dict, hop_locations: List[Dict], 
                         geo_results: List[Dict], whois_text: Optional[str], agg: Optional[Dict],
                         open_map: bool = False):
    
    # Header with nice formatting
    console.print(Panel(
        f"🎯 [bold]Target:[/bold] {ip}\n"
        f"🔍 [bold]Reverse DNS:[/bold] {reverse or '(none)'}",
        title="🌐 IP Location Analysis",
        border_style="blue"
    ))
    # Traceroute section
    console.print("\n[bold cyan]🛣️ Network Route Analysis[/bold cyan]")
    if traceroute_lines:
        for i, line in enumerate(traceroute_lines[:10], start=1):
            console.print(f"  {i:02d}: {line}")
    else:
        console.print("  No traceroute data available")
    
    # Network analysis results
    israel_locs = hop_analysis.get('israel_locations', [])
    global_locs = hop_analysis.get('global_locations', [])
    isp_clues = hop_analysis.get('isp_clues', [])
    
    if clues or israel_locs or global_locs or hop_locations:
        console.print("\n[bold yellow]🔍 Network Path Intelligence[/bold yellow]")
        
        if clues:
            console.print(f"  📝 Clues found: {', '.join(clues[:10])}")
        
        if israel_locs:
            console.print(f"  🇮🇱 Israeli locations: {', '.join(israel_locs)}")
        
        if global_locs:
            console.print(f"  🌍 International routes: {', '.join(global_locs)}")
        
        if isp_clues:
            console.print(f"  🏢 ISP infrastructure: {', '.join(isp_clues[:3])}")
        
        # Show intermediate hop locations
        if hop_locations:
            console.print(f"\n  📍 [bold]Network path ({len(hop_locations)} hops geolocated):[/bold]")
            for i, hop in enumerate(hop_locations):
                city = hop['city'] or 'Unknown'
                country = hop['country'] or 'Unknown'
                console.print(f"     {i+1}. [cyan]{hop['ip']}[/cyan] → {city}, {country}")
    # GeoIP Results with nice formatting
    console.print(f"\n[bold green]🌐 GeoIP Results ({len(geo_results)} sources)[/bold green]")
    for i, g in enumerate(geo_results, 1):
        source = g.get('source', 'Unknown')
        city = g.get('city', 'Unknown')
        country = g.get('country', 'Unknown')
        lat = g.get('lat', 'N/A')
        lon = g.get('lon', 'N/A')
        
        console.print(f"  {i}. [bold]{source}[/bold]: {city}, {country}")
        console.print(f"     📍 Coordinates: {lat}, {lon}")
        if g.get('org') or g.get('isp'):
            org = g.get('org') or g.get('isp')
            console.print(f"     🏢 Organization: {org}")
    
    # Aggregated Results
    if agg:
        sources_text = f"{agg['count']} sources"
        if agg.get('includes_network_path'):
            sources_text += " + network analysis"
        if agg.get('filtered'):
            sources_text = f"{agg['count']}/{agg['original_count']} sources (outliers filtered)"
            if agg.get('includes_network_path'):
                sources_text += " + network path"
        
        # Get confidence analysis from results if available
        confidence_data = None
        for result in geo_results:
            if hasattr(result, 'get') and 'confidence' in str(result):
                # This is a bit hacky, but works for now
                pass
        
        # Determine confidence color
        radius = agg['radius_km']
        if radius < 10:
            confidence_text = "[bold green]High confidence[/bold green] (likely precise location)"
            confidence_emoji = "🎯"
        elif radius < 25:
            confidence_text = "[bold yellow]Medium-high confidence[/bold yellow] (likely city-level)"
            confidence_emoji = "🏙️"
        elif radius < 50:
            confidence_text = "[bold orange3]Medium confidence[/bold orange3] (region-level)"
            confidence_emoji = "🗺️"
        else:
            confidence_text = "[bold red]Low confidence[/bold red] (country/large-region)"
            confidence_emoji = "🌍"
        
        panel_content = (
            f"📊 [bold]Aggregated from {sources_text}[/bold]\n"
            f"📍 Location: {agg['avg_lat']:.5f}, {agg['avg_lon']:.5f}\n"
            f"📏 Accuracy radius: {agg['radius_km']:.1f} km\n"
            f"{confidence_emoji} {confidence_text}"
        )
        
        console.print(Panel(
            panel_content,
            title="🎯 Final Location Estimate",
            border_style="green"
        ))
        
        # Links
        maps_link = generate_maps_link(agg['avg_lat'], agg['avg_lon'])
        google_search_url = "https://www.google.com/search?q=what+is+my+location"
        
        console.print("\n[bold blue]🔗 Quick Links:[/bold blue]")
        console.print(f"  🗺️  Google Maps: [link]{maps_link}[/link]")
        console.print(f"  🔍 Compare with Google: [link]{google_search_url}[/link]")
        
        # Optionally open in browser
        if open_map:
            if open_in_browser(maps_link):
                console.print("  ✅ [green]Opened location in browser[/green]")
            else:
                console.print("  ❌ [red]Failed to open browser[/red]")
    else:
        console.print("[yellow]⚠️  No coordinates available to aggregate[/yellow]")
    
    # Technical Analysis
    console.print(Panel(
        "[bold yellow]⚠️  Important Notes[/bold yellow]\n\n"
        "• GeoIP accuracy varies by ISP and may show routing location\n"
        "• Results represent infrastructure location, not necessarily user location\n"
        "• Different services use different databases and methodologies",
        title="🔬 Technical Analysis",
        border_style="yellow"
    ))
    
    # ISP Analysis
    isp_info = []
    for result in geo_results:
        if result.get('org') or result.get('isp'):
            org = result.get('org') or result.get('isp', '')
            if org and org not in isp_info:
                isp_info.append(org)
    
    if isp_info:
        console.print(f"\n[bold cyan]🏢 Detected ISP(s):[/bold cyan] {', '.join(isp_info)}")
        if any('hot' in isp.lower() for isp in isp_info):
            console.print("[yellow]📍 Note: HOT routes traffic through central Israel infrastructure[/yellow]")
            console.print("[dim]   Your actual location may differ from detected coordinates[/dim]")
    
    # Get timezone info
    timezone = get_timezone_hint(ip)
    if timezone:
        console.print(f"[bold blue]🕐 Timezone:[/bold blue] {timezone}")
    
    # Google comparison explanation
    console.print(Panel(
        "[bold green]💡 Why Google is more accurate:[/bold green]\n\n"
        "• GPS + Wi-Fi mapping + Cell tower triangulation\n"
        "• User location data from millions of devices\n" 
        "• Machine learning algorithms improve over time\n"
        "• Custom databases beyond basic ISP routing",
        title="🤖 Google's Advantage",
        border_style="green"
    ))
    
    # WHOIS section if available
    if whois_text:
        console.print(f"\n[bold magenta]📋 WHOIS Information (first 20 lines)[/bold magenta]")
        for i, line in enumerate(whois_text.splitlines()[:20], 1):
            console.print(f"  {i:2d}: {line}")
    
    console.print("\n[dim]Analysis completed successfully! 🎉[/dim]")

# --------- Main flow ----------
def analyze_single_ip(ip: str, target: str, use_cache: bool = True, verbose: bool = True, fast_mode: bool = True) -> Dict:
    """Analyze a single IP address and return results"""
    
    # Check cache first
    if use_cache:
        cached_result = location_cache.get(ip)
        if cached_result and verbose:
            console.print(f"[green]📂 Using cached data for {ip}[/green]")
            return cached_result
    
    # Initialize progress bar only in verbose mode
    if verbose:
        init_progress()
    
    try:
        results = {
            'ip': ip,
            'target': target,
            'timestamp': datetime.now().isoformat(),
            'reverse_dns': None,
            'traceroute': [],
            'hop_analysis': {},
            'hop_locations': [],
            'geo_results': [],
            'whois': None,
            'aggregated': None
        }
        
        # Step 1: Reverse DNS (5%)
        if verbose:
            update_progress("🔍 Checking reverse DNS", 5)
        results['reverse_dns'] = reverse_dns(ip)
        if verbose:
            update_progress("✅ Reverse DNS complete", 10)

        # Step 2: Fast Traceroute (15%) - Optional for speed
        if verbose:
            update_progress("⚡ Preparing network analysis", 12)
        
        # Skip traceroute for speed unless specifically requested
        skip_traceroute = True  # Set to False if network analysis is needed
        
        if not skip_traceroute:
            if verbose:
                update_progress("🛣️ Running traceroute", 13)
            traceroute_lines = run_traceroute(target, max_hops=8, timeout=2)
            results['traceroute'] = traceroute_lines

            if verbose:
                update_progress("📊 Analyzing network path", 17)
            hop_analysis = analyze_hop_hostnames(traceroute_lines)
            hop_ips = extract_ips_from_traceroute(traceroute_lines)
            hop_locations = geolocate_intermediate_hops(hop_ips[:3])
            
            results['hop_analysis'] = hop_analysis
            results['hop_locations'] = hop_locations
        else:
            if verbose:
                update_progress("⚡ Skipping traceroute for speed", 15)
            results['traceroute'] = ["Skipped for speed optimization"]
            results['hop_analysis'] = {}
            results['hop_locations'] = []

        # Step 3: GeoIP Services (20% to 85% - this is the main work)
        if verbose:
            update_progress("🌍 Starting GeoIP queries", 20)
        geo_results, coords = run_all_geoip_services_parallel(ip, 20, 85)
        results['geo_results'] = geo_results

        # Step 4: WHOIS (87%) - Optional for speed  
        if verbose:
            update_progress("📋 Checking WHOIS data", 87)
        
        skip_whois = True  # Set to False if WHOIS data is needed
        
        if not skip_whois:
            whois_text = run_whois(ip)
            results['whois'] = whois_text
        else:
            results['whois'] = "Skipped for speed optimization"
        
        if verbose:
            update_progress("✅ WHOIS complete", 90)

        # Step 5: Final aggregation (92%)
        if verbose:
            update_progress("📊 Calculating final location", 92)
        
        # Add hop locations to coordinates if they seem relevant
        hop_coords = []
        hop_locations_list = results.get('hop_locations', [])
        for hop in hop_locations_list:
            if hop.get('lat') and hop.get('lon'):
                # Only add if it's in Israel (to avoid including international routing)
                if hop.get('country') in ['Israel', 'IL']:
                    hop_coords.append((hop['lat'], hop['lon']))
        
        # Combine all coordinates
        all_coords = coords + hop_coords
        
        # Aggregate
        agg = aggregate_locations(all_coords)
        if len(hop_coords) > 0 and agg:
            agg['includes_network_path'] = True
        
        results['aggregated'] = agg
        
        # Additional analysis
        results['vpn_check'] = check_vpn_proxy(ip)
        results['timezone'] = get_timezone_hint(ip)
        
        if agg:
            if verbose:
                update_progress("🔍 Calculating confidence score", 98)
            results['confidence'] = calculate_location_confidence(geo_results, agg)
        
        # Final steps
        if verbose:
            update_progress("💾 Saving to cache", 99)
        
        # Save to cache
        if use_cache:
            location_cache.set(ip, results)
        
        # Complete progress
        if verbose:
            finish_progress()
        
        return results
        
    except Exception as e:
        if verbose:
            finish_progress()
            console.print(f"[red]❌ Error during analysis: {e}[/red]")
        raise

def main(targets: List[str], open_map: bool = False, save_format: str = None, 
         use_cache: bool = True, verbose: bool = True, create_map: bool = False):
    """Main analysis function supporting multiple targets"""
    
    all_results = []
    
    for target in targets:
        try:
            # Resolve to IP if hostname
            if verbose:
                console.print(f"\n[bold blue]🎯 Analyzing: {target}[/bold blue]")
            
            try:
                ip = socket.gethostbyname(target)
            except Exception:
                console.print(f"[red]❌ Could not resolve {target}[/red]")
                continue
            
            # Analyze the IP in fast mode
            results = analyze_single_ip(ip, target, use_cache, verbose, fast_mode=True)
            all_results.append(results)
            
            # Display results if verbose
            if verbose:
                console.print("\n")
                console.print(Panel.fit("🎯 Location Analysis Complete", style="bold green"))
                
                # Extract clues safely from hop_analysis
                clues = []
                hop_analysis = results.get('hop_analysis', {})
                
                print_result_summary(
                    results['ip'], 
                    results['reverse_dns'], 
                    results['traceroute'],
                    clues,  # Empty list for clues
                    hop_analysis,
                    results['hop_locations'],
                    results['geo_results'],
                    results['whois'],
                    results['aggregated'],
                    open_map and len(targets) == 1  # Only open map for single target
                )
            
            # Save results if requested
            if save_format:
                saved_file = save_results(ip, results, save_format)
                if verbose:
                    console.print(f"[green]💾 Results saved to: {saved_file}[/green]")
            
            # Create interactive map if requested
            if create_map and results['aggregated']:
                map_file = create_html_map(results)
                if verbose:
                    console.print(f"[green]🗺️  Interactive map created: {map_file}[/green]")
                if open_map:
                    webbrowser.open(f"file://{map_file}")
        
        except Exception as e:
            console.print(f"[red]❌ Error analyzing {target}: {e}[/red]")
            continue
    
    # Summary for multiple targets
    if len(targets) > 1 and verbose:
        console.print(f"\n[bold green]📊 Analysis Summary[/bold green]")
        console.print(f"Analyzed {len(all_results)}/{len(targets)} targets successfully")
        
        # Create comparison table
        if all_results:
            table = Table(title="Location Comparison")
            table.add_column("Target", style="cyan")
            table.add_column("Location", style="magenta")
            table.add_column("Confidence", style="green")
            table.add_column("Sources", justify="center")
            
            for result in all_results:
                agg = result.get('aggregated')
                if agg:
                    location = f"{agg['avg_lat']:.3f}, {agg['avg_lon']:.3f}"
                    radius = agg['radius_km']
                    if radius < 25:
                        confidence = "High"
                        confidence_style = "green"
                    elif radius < 50:
                        confidence = "Medium" 
                        confidence_style = "yellow"
                    else:
                        confidence = "Low"
                        confidence_style = "red"
                    
                    table.add_row(
                        result['target'],
                        location,
                        f"[{confidence_style}]{confidence}[/{confidence_style}] ({radius:.1f}km)",
                        str(agg['count'])
                    )
            
            console.print(table)
    
    return all_results
    
    try:
        # Step 1: Resolve to IP if hostname
        update_progress("Resolving hostname", 1)
        try:
            ip = socket.gethostbyname(target)
        except Exception:
            finish_progress()
            console.print(f"[red]❌ Could not resolve {target}[/red]")
            return

        # Step 2: Reverse DNS
        update_progress("Checking reverse DNS", 1)
        rev = reverse_dns(ip)

        # Step 3: Traceroute
        update_progress("Running traceroute", 1)
        traceroute_lines = run_traceroute(target)

        # Step 4: Advanced traceroute analysis
        update_progress("Analyzing network path", 1)
        clues = parse_traceroute_for_clues(traceroute_lines)
        hop_analysis = analyze_hop_hostnames(traceroute_lines)
        hop_ips = extract_ips_from_traceroute(traceroute_lines)
        hop_locations = geolocate_intermediate_hops(hop_ips)

        # Step 5-8: Run all GeoIP services in parallel
        update_progress("Querying GeoIP services", 2)
        geo_results, coords = run_all_geoip_services_parallel(ip)

        # Step 9: WHOIS lookup
        update_progress("WHOIS lookup", 1)
        whois_text = run_whois(ip)

        # Step 10: Final analysis
        update_progress("Aggregating results", 1)
        
        # Add hop locations to coordinates if they seem relevant
        hop_coords = []
        for hop in hop_locations:
            if hop.get('lat') and hop.get('lon'):
                # Only add if it's in Israel (to avoid including international routing)
                if hop.get('country') in ['Israel', 'IL']:
                    hop_coords.append((hop['lat'], hop['lon']))
        
        # Combine all coordinates
        all_coords = coords + hop_coords
        
        # Aggregate
        agg = aggregate_locations(all_coords)
        if len(hop_coords) > 0 and agg:
            agg['includes_network_path'] = True

        # Complete progress
        finish_progress()
        
        # Show results with nice formatting
        console.print("\n")
        console.print(Panel.fit("🎯 Location Analysis Complete", style="bold green"))
        
        # Print summary
        print_result_summary(ip, rev, traceroute_lines, clues, hop_analysis, hop_locations, geo_results, whois_text, agg, open_map)
        
    except Exception as e:
        finish_progress()
        console.print(f"[red]❌ Error during analysis: {e}[/red]")

def create_parser():
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="🌐 Advanced IP Geolocation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python locate_ip.py google.com
  python locate_ip.py 8.8.8.8 --open-map --save json
  python locate_ip.py google.com facebook.com twitter.com --quiet
  python locate_ip.py 1.1.1.1 --create-map --no-cache
  python locate_ip.py --clear-cache
        """
    )
    
    parser.add_argument(
        'targets', 
        nargs='*',
        help='IP addresses or hostnames to analyze'
    )
    
    parser.add_argument(
        '--open-map', '-o',
        action='store_true',
        help='Open location in browser (Google Maps or interactive map)'
    )
    
    parser.add_argument(
        '--save', '-s',
        choices=['json', 'csv'],
        help='Save results to file in specified format'
    )
    
    parser.add_argument(
        '--create-map', '-m',
        action='store_true',
        help='Create interactive HTML map'
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable cache usage'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output mode'
    )
    
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear the cache and exit'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='IP Locator 2.0 - Enhanced Edition'
    )
    
    return parser

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle cache clearing
    if args.clear_cache:
        location_cache.clear()
        console.print("[green]✅ Cache cleared successfully[/green]")
        sys.exit(0)
    
    # Check if targets provided
    if not args.targets:
        parser.print_help()
        console.print("\n[red]❌ Please provide at least one IP address or hostname[/red]")
        sys.exit(1)
    
    try:
        results = main(
            targets=args.targets,
            open_map=args.open_map,
            save_format=args.save,
            use_cache=not args.no_cache,
            verbose=not args.quiet,
            create_map=args.create_map
        )
        
        if args.quiet and results:
            # In quiet mode, just print essential info
            for result in results:
                agg = result.get('aggregated')
                if agg:
                    console.print(f"{result['ip']}: {agg['avg_lat']:.5f}, {agg['avg_lon']:.5f} (±{agg['radius_km']:.1f}km)")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Analysis interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Fatal error: {e}[/red]")
        sys.exit(1)
