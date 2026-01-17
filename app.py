from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
import time
import threading
import requests
from datetime import datetime
import logging
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File to store URLs
URLS_FILE = 'urls.json'

# Active monitoring threads
active_monitors = {}

def load_urls():
    """Load URLs from file - only essential data"""
    try:
        if os.path.exists(URLS_FILE):
            with open(URLS_FILE, 'r') as f:
                return json.load(f)
    except:
        return {}
    return {}

def save_urls(urls_data):
    """Save URLs with minimal data"""
    try:
        # Keep only: id, name, url, interval, monitoring
        cleaned_data = {}
        for url_id, data in urls_data.items():
            cleaned_data[url_id] = {
                'id': data.get('id'),
                'name': data.get('name', data.get('url', '')),
                'url': data.get('url', ''),
                'interval': data.get('interval', 5),
                'monitoring': data.get('monitoring', False)
                # No timestamps, no status codes, no response times
            }
        
        with open(URLS_FILE, 'w') as f:
            json.dump(cleaned_data, f)
        return True
    except:
        return False

def is_valid_url(url):
    """Simple URL validation"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def ping_url(url_id, url, interval):
    """Background pinging - no data storage"""
    while url_id in active_monitors and active_monitors[url_id]['active']:
        try:
            requests.get(url, timeout=5, headers={
                'User-Agent': 'Simple-Ping-Monitor/1.0'
            })
        except:
            pass  # Don't store any data
        
        # Sleep for interval
        time.sleep(interval * 60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/urls', methods=['GET'])
def get_urls():
    """Get URLs - minimal data only"""
    urls_data = load_urls()
    # Add simple monitoring status
    for url_id in urls_data:
        urls_data[url_id]['is_active'] = url_id in active_monitors
    return jsonify(urls_data)

@app.route('/api/urls', methods=['POST'])
def add_url():
    """Add URL - minimal data"""
    data = request.json
    url = data.get('url', '').strip()
    interval = data.get('interval', 5)
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    if not is_valid_url(url):
        return jsonify({'error': 'Invalid URL'}), 400
    
    if interval < 1:
        interval = 1
    
    urls_data = load_urls()
    
    # Generate simple ID
    url_id = f"url_{len(urls_data) + 1}_{int(time.time())}"
    
    # Store minimal data
    urls_data[url_id] = {
        'id': url_id,
        'url': url,
        'interval': interval,
        'monitoring': False
    }
    
    if save_urls(urls_data):
        return jsonify({'message': 'URL added', 'id': url_id}), 201
    return jsonify({'error': 'Save failed'}), 500

@app.route('/api/urls/<url_id>', methods=['DELETE'])
def delete_url(url_id):
    """Delete URL"""
    # Stop if active
    if url_id in active_monitors:
        active_monitors[url_id]['active'] = False
        del active_monitors[url_id]
    
    urls_data = load_urls()
    if url_id in urls_data:
        del urls_data[url_id]
        if save_urls(urls_data):
            return jsonify({'message': 'Deleted'}), 200
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/urls/<url_id>/start', methods=['POST'])
def start_monitoring(url_id):
    """Start monitoring - no data storage"""
    urls_data = load_urls()
    
    if url_id not in urls_data:
        return jsonify({'error': 'Not found'}), 404
    
    # Stop if already running
    if url_id in active_monitors:
        active_monitors[url_id]['active'] = False
        time.sleep(0.5)
    
    # Start thread
    url_info = urls_data[url_id]
    active_monitors[url_id] = {'active': True}
    
    thread = threading.Thread(
        target=ping_url,
        args=(url_id, url_info['url'], url_info['interval'])
    )
    thread.daemon = True
    thread.start()
    
    # Update status only
    urls_data[url_id]['monitoring'] = True
    save_urls(urls_data)
    
    return jsonify({'message': 'Started'}), 200

@app.route('/api/urls/<url_id>/stop', methods=['POST'])
def stop_monitoring(url_id):
    """Stop monitoring"""
    if url_id in active_monitors:
        active_monitors[url_id]['active'] = False
        del active_monitors[url_id]
    
    urls_data = load_urls()
    if url_id in urls_data:
        urls_data[url_id]['monitoring'] = False
        save_urls(urls_data)
    
    return jsonify({'message': 'Stopped'}), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    # Restart monitoring on server start
    urls_data = load_urls()
    for url_id, url_info in urls_data.items():
        if url_info.get('monitoring', False):
            active_monitors[url_id] = {'active': True}
            thread = threading.Thread(
                target=ping_url,
                args=(url_id, url_info['url'], url_info['interval'])
            )
            thread.daemon = True
            thread.start()
    
    # Start app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)