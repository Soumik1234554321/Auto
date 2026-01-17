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
import atexit

app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File to store URLs
URLS_FILE = 'urls.json'

# Active monitoring threads
active_monitors = {}
stop_event = threading.Event()

def load_urls():
    """Load URLs from file - only essential data"""
    try:
        if os.path.exists(URLS_FILE):
            with open(URLS_FILE, 'r') as f:
                data = json.load(f)
                # Clean up any old data structure
                cleaned_data = {}
                for url_id, url_data in data.items():
                    if isinstance(url_data, dict):
                        cleaned_data[url_id] = {
                            'id': url_id,
                            'url': url_data.get('url', ''),
                            'interval': url_data.get('interval', 5),
                            'monitoring': url_data.get('monitoring', False)
                        }
                return cleaned_data
    except Exception as e:
        logger.error(f"Error loading URLs: {e}")
        return {}
    return {}

def save_urls(urls_data):
    """Save URLs with minimal data"""
    try:
        # Keep only essential data
        cleaned_data = {}
        for url_id, data in urls_data.items():
            cleaned_data[url_id] = {
                'id': url_id,
                'url': data.get('url', ''),
                'interval': data.get('interval', 5),
                'monitoring': data.get('monitoring', False)
            }
        
        with open(URLS_FILE, 'w') as f:
            json.dump(cleaned_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving URLs: {e}")
        return False

def is_valid_url(url):
    """Simple URL validation"""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def ping_worker(url_id, url, interval):
    """Background worker for pinging URLs"""
    logger.info(f"Starting ping worker for {url} (ID: {url_id})")
    
    while not stop_event.is_set() and url_id in active_monitors:
        try:
            # Ping the URL
            start_time = time.time()
            response = requests.get(
                url, 
                timeout=10,
                headers={'User-Agent': 'URL-Ping-Monitor/1.0'},
                allow_redirects=True
            )
            elapsed_time = time.time() - start_time
            
            logger.debug(f"Pinged {url} - Status: {response.status_code} - Time: {elapsed_time:.2f}s")
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to ping {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error pinging {url}: {e}")
        
        # Wait for the interval
        for _ in range(interval * 60 * 10):  # Check every 0.1 second
            if stop_event.is_set() or url_id not in active_monitors:
                break
            time.sleep(0.1)
    
    logger.info(f"Stopped ping worker for {url} (ID: {url_id})")

def stop_all_monitors():
    """Stop all monitoring threads"""
    logger.info("Stopping all monitors...")
    stop_event.set()
    active_monitors.clear()
    time.sleep(1)  # Give threads time to stop

def start_monitoring_thread(url_id, url_info):
    """Start a monitoring thread for a URL"""
    if url_id in active_monitors:
        return False
    
    active_monitors[url_id] = {
        'active': True,
        'url': url_info['url'],
        'interval': url_info['interval']
    }
    
    thread = threading.Thread(
        target=ping_worker,
        args=(url_id, url_info['url'], url_info['interval']),
        daemon=True
    )
    thread.start()
    return True

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/urls', methods=['GET'])
def get_urls():
    """Get all URLs"""
    urls_data = load_urls()
    # Add monitoring status
    for url_id in urls_data:
        urls_data[url_id]['is_active'] = url_id in active_monitors
    return jsonify(urls_data)

@app.route('/api/urls', methods=['POST'])
def add_url():
    """Add a new URL"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        url = data.get('url', '').strip()
        interval = data.get('interval', 5)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not is_valid_url(url):
            return jsonify({'error': 'Invalid URL format. Use http:// or https://'}), 400
        
        # Ensure interval is valid
        try:
            interval = int(interval)
            if interval < 1:
                interval = 1
            elif interval > 1440:  # Max 24 hours
                interval = 1440
        except:
            interval = 5
        
        urls_data = load_urls()
        
        # Check if URL already exists
        for existing_id, existing_data in urls_data.items():
            if existing_data.get('url') == url:
                return jsonify({'error': 'URL already exists', 'id': existing_id}), 400
        
        # Generate unique ID
        url_id = f"url_{int(time.time())}_{len(urls_data)}"
        
        # Add URL
        urls_data[url_id] = {
            'id': url_id,
            'url': url,
            'interval': interval,
            'monitoring': False
        }
        
        if save_urls(urls_data):
            return jsonify({
                'message': 'URL added successfully',
                'id': url_id,
                'url': url,
                'interval': interval
            }), 201
        else:
            return jsonify({'error': 'Failed to save URL'}), 500
            
    except Exception as e:
        logger.error(f"Error adding URL: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/urls/<url_id>', methods=['DELETE'])
def delete_url(url_id):
    """Delete a URL"""
    try:
        # Stop monitoring if active
        if url_id in active_monitors:
            del active_monitors[url_id]
        
        urls_data = load_urls()
        
        if url_id in urls_data:
            del urls_data[url_id]
            if save_urls(urls_data):
                return jsonify({'message': 'URL deleted successfully'}), 200
            else:
                return jsonify({'error': 'Failed to save changes'}), 500
        else:
            return jsonify({'error': 'URL not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting URL: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/urls/<url_id>/start', methods=['POST'])
def start_monitoring(url_id):
    """Start monitoring a URL"""
    try:
        urls_data = load_urls()
        
        if url_id not in urls_data:
            return jsonify({'error': 'URL not found'}), 404
        
        # Start monitoring
        if start_monitoring_thread(url_id, urls_data[url_id]):
            # Update monitoring status
            urls_data[url_id]['monitoring'] = True
            save_urls(urls_data)
            
            return jsonify({
                'message': 'Monitoring started',
                'id': url_id,
                'url': urls_data[url_id]['url']
            }), 200
        else:
            return jsonify({'error': 'Monitoring already active'}), 400
            
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/urls/<url_id>/stop', methods=['POST'])
def stop_monitoring(url_id):
    """Stop monitoring a URL"""
    try:
        # Stop monitoring
        if url_id in active_monitors:
            del active_monitors[url_id]
        
        # Update monitoring status
        urls_data = load_urls()
        if url_id in urls_data:
            urls_data[url_id]['monitoring'] = False
            save_urls(urls_data)
        
        return jsonify({
            'message': 'Monitoring stopped',
            'id': url_id
        }), 200
            
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        urls_data = load_urls()
        return jsonify({
            'status': 'healthy',
            'total_urls': len(urls_data),
            'active_monitors': len(active_monitors),
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/api/ping', methods=['POST'])
def ping_now():
    """Ping a URL immediately"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not is_valid_url(url):
            return jsonify({'error': 'Invalid URL'}), 400
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            elapsed_time = time.time() - start_time
            
            return jsonify({
                'success': True,
                'status_code': response.status_code,
                'response_time': round(elapsed_time, 3),
                'url': url
            }), 200
        except requests.exceptions.RequestException as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'url': url
            }), 200
            
    except Exception as e:
        logger.error(f"Error in ping_now: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== INITIALIZATION ====================

def initialize_app():
    """Initialize the application"""
    logger.info("Initializing URL Ping Monitor...")
    
    # Create URLs file if it doesn't exist
    if not os.path.exists(URLS_FILE):
        with open(URLS_FILE, 'w') as f:
            json.dump({}, f)
        logger.info(f"Created {URLS_FILE}")
    
    # Load URLs and restart monitoring
    urls_data = load_urls()
    active_count = 0
    
    for url_id, url_info in urls_data.items():
        if url_info.get('monitoring', False):
            if start_monitoring_thread(url_id, url_info):
                active_count += 1
                logger.info(f"Restarted monitoring for {url_info['url']}")
    
    logger.info(f"Application initialized. {active_count} monitors active.")
    
    # Register cleanup function
    atexit.register(stop_all_monitors)

# ==================== MAIN ====================

if __name__ == '__main__':
    # Initialize the app
    initialize_app()
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running in Vercel
    is_vercel = os.environ.get('VERCEL') == '1'
    
    if is_vercel:
        # For Vercel, we need to export the app
        logger.info("Running in Vercel environment")
    else:
        # For local/Termux
        logger.info(f"Starting server on port {port}")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
else:
    # For Vercel deployment
    initialize_app()