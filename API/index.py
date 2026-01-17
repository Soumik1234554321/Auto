from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
import time
import requests
from urllib.parse import urlparse
import uuid

app = Flask(__name__, 
           static_folder='../static',
           template_folder='../templates')
CORS(app)

# File to store URLs
URLS_FILE = 'urls.json'

# Store in-memory for serverless (will reset on cold start)
active_checks = {}

def load_urls():
    """Load URLs from file"""
    try:
        if os.path.exists(URLS_FILE):
            with open(URLS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading URLs: {e}")
    return {}

def save_urls(urls_data):
    """Save URLs to file"""
    try:
        with open(URLS_FILE, 'w') as f:
            json.dump(urls_data, f)
        return True
    except Exception as e:
        print(f"Error saving URLs: {e}")
        return False

def is_valid_url(url):
    """Simple URL validation"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def check_url_status(url):
    """Check a single URL status"""
    try:
        start_time = time.time()
        response = requests.get(
            url, 
            timeout=10,
            headers={'User-Agent': 'URL-Monitor/1.0'}
        )
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            'status': 'up' if response.status_code < 400 else 'down',
            'status_code': response.status_code,
            'response_time': response_time,
            'timestamp': time.time()
        }
    except Exception as e:
        return {
            'status': 'down',
            'status_code': 0,
            'response_time': 0,
            'error': str(e),
            'timestamp': time.time()
        }

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/urls', methods=['GET'])
def get_urls():
    """Get all URLs"""
    urls_data = load_urls()
    return jsonify(urls_data)

@app.route('/api/urls', methods=['POST'])
def add_url():
    """Add a new URL"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        interval = data.get('interval', 5)
        name = data.get('name', url)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not is_valid_url(url):
            return jsonify({'error': 'Invalid URL. Please include http:// or https://'}), 400
        
        if interval < 1:
            interval = 1
        
        urls_data = load_urls()
        
        # Generate unique ID
        url_id = str(uuid.uuid4())
        
        # Initial status check
        status_info = check_url_status(url)
        
        urls_data[url_id] = {
            'id': url_id,
            'name': name,
            'url': url,
            'interval': interval,
            'monitoring': False,
            'last_check': status_info,
            'created_at': time.time()
        }
        
        if save_urls(urls_data):
            return jsonify({
                'message': 'URL added successfully',
                'id': url_id,
                'data': urls_data[url_id]
            }), 201
        return jsonify({'error': 'Failed to save URL'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/urls/<url_id>', methods=['DELETE'])
def delete_url(url_id):
    """Delete a URL"""
    try:
        urls_data = load_urls()
        if url_id in urls_data:
            del urls_data[url_id]
            if save_urls(urls_data):
                return jsonify({'message': 'URL deleted successfully'}), 200
        return jsonify({'error': 'URL not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/urls/<url_id>/check', methods=['POST'])
def check_url(url_id):
    """Check a URL immediately"""
    try:
        urls_data = load_urls()
        if url_id not in urls_data:
            return jsonify({'error': 'URL not found'}), 404
        
        url_info = urls_data[url_id]
        status_info = check_url_status(url_info['url'])
        
        # Update last check
        urls_data[url_id]['last_check'] = status_info
        save_urls(urls_data)
        
        return jsonify({
            'message': 'Status checked',
            'status': status_info
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/urls/check-all', methods=['POST'])
def check_all_urls():
    """Check all URLs at once"""
    try:
        urls_data = load_urls()
        results = {}
        
        for url_id, url_info in urls_data.items():
            status_info = check_url_status(url_info['url'])
            urls_data[url_id]['last_check'] = status_info
            results[url_id] = status_info
        
        save_urls(urls_data)
        
        return jsonify({
            'message': 'All URLs checked',
            'results': results
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/urls/<url_id>/monitoring', methods=['PUT'])
def update_monitoring(url_id):
    """Toggle monitoring status"""
    try:
        data = request.json
        monitoring = data.get('monitoring', False)
        
        urls_data = load_urls()
        if url_id not in urls_data:
            return jsonify({'error': 'URL not found'}), 404
        
        urls_data[url_id]['monitoring'] = monitoring
        save_urls(urls_data)
        
        return jsonify({
            'message': f'Monitoring {"enabled" if monitoring else "disabled"}',
            'monitoring': monitoring
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'service': 'URL Ping Monitor'
    }), 200

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

# For Vercel serverless
if __name__ == '__main__':
    app.run(debug=False)
else:
    # Export for Vercel
    handler = app
