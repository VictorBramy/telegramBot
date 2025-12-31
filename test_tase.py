import requests

# Try TASE API
url = 'https://api.tase.co.il/api/MarketData/Securities'
headers = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0'
}

try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f'TASE API Status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'Data received: {len(data)} items')
        # Find Phoenix
        for item in data[:5]:
            print(f"Sample: {item}")
    else:
        print(f'Response: {r.text[:200]}')
except Exception as e:
    print(f'Error: {e}')
