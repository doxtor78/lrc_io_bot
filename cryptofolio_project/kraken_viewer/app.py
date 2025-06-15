from flask import Flask, render_template, jsonify
import os
import time
import requests
import base64
import hashlib
import hmac

app = Flask(__name__)

KRAKEN_API_KEY = os.environ.get('KRAKEN_API_KEY', 'YOUR_KRAKEN_API_KEY')
KRAKEN_API_SECRET = os.environ.get('KRAKEN_API_SECRET', 'YOUR_KRAKEN_API_SECRET')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/kraken-balances')
def kraken_balances():
    url = 'https://api.kraken.com/0/private/Balance'
    nonce = str(int(time.time() * 1000))
    post_data = {'nonce': nonce}
    post_data_str = '&'.join([f'{k}={v}' for k, v in post_data.items()])
    path = '/0/private/Balance'
    secret = base64.b64decode(KRAKEN_API_SECRET)
    hash_digest = hashlib.sha256((nonce + post_data_str).encode()).digest()
    hmac_digest = hmac.new(secret, (path.encode() + hash_digest), hashlib.sha512).digest()
    signature = base64.b64encode(hmac_digest)
    headers = {
        'API-Key': KRAKEN_API_KEY,
        'API-Sign': signature.decode(),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    response = requests.post(url, data=post_data, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'result' in data:
            balances = [{'asset': k, 'balance': v} for k, v in data['result'].items() if float(v) > 0]
            return jsonify({'success': True, 'balances': balances})
        else:
            return jsonify({'success': False, 'error': data.get('error', 'Unknown error')})
    else:
        return jsonify({'success': False, 'error': 'Failed to fetch from Kraken'})

if __name__ == '__main__':
    app.run(debug=True) 