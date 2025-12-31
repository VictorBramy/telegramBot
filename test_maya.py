import requests
from bs4 import BeautifulSoup

def get_stock_price_from_maya(symbol_code):
    """
    Try to fetch from Maya TASE
    Symbol codes: Phoenix=5780, Leumi=5514, etc.
    """
    try:
        url = f'https://maya.tase.co.il/company/{symbol_code}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        print(f'Status: {response.status_code}')
        print(f'URL: {url}')
        if response.status_code == 200:
            print('Success! Got data')
            return True
        return False
    except Exception as e:
        print(f'Error: {e}')
        return False

# Test with Phoenix
print('Testing Phoenix (5780):')
get_stock_price_from_maya('5780')
