import requests
import hmac
import hashlib
import time
import json

# Bybit API credentials
BYBIT_API_KEY = '3hqwkcMjnyhnFUd6XE'
BYBIT_API_SECRET = 'OQVX53FdiY4LMztOZAzYxD3UjS93mFpV3XfK'

def bybit_request(endpoint, params=None):
    """Make a request to Bybit API with detailed logging."""
    url = f'https://api.bybit.com/v5/{endpoint}'
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    if params:
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    else:
        query_string = ""
    
    string_to_sign = timestamp + BYBIT_API_KEY + recv_window + query_string
    
    signature = hmac.new(
        BYBIT_API_SECRET.encode('utf-8'),
        msg=string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    headers = {
        'X-BAPI-API-KEY': BYBIT_API_KEY,
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-RECV-WINDOW': recv_window,
        'X-BAPI-SIGN': signature,
    }
    
    print(f"Request URL: {url}")
    print(f"Request Params: {params}")
    print(f"Request Headers: {headers}")
    
    response = requests.get(url, headers=headers, params=params)
    
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    
    try:
        return response.json()
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None

def get_bybit_balances():
    """Fetch Bybit account balances."""
    response = bybit_request('account/wallet-balance', {'accountType': 'UNIFIED'})
    if response and 'retCode' in response and response['retCode'] == 0:
        balances = []
        for item in response['result']['list']:
            for coin in item['coin']:
                if float(coin['walletBalance']) > 0:
                    balances.append({
                        'asset': coin['coin'],
                        'amount': float(coin['walletBalance']),
                    })
        return balances
    return []

if __name__ == '__main__':
    print("Fetching Bybit balances...")
    bybit_balances = get_bybit_balances()
    print("\nBybit Balances:")
    for balance in bybit_balances:
        print(f"{balance['asset']}: {balance['amount']}") 