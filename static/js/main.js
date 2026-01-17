document.addEventListener('DOMContentLoaded', function() {
    const API_BASE = '/api';
    let urls = {};

    // DOM Elements
    const addUrlForm = document.getElementById('addUrlForm');
    const urlsList = document.getElementById('urlsList');
    const checkAllBtn = document.getElementById('checkAll');
    const upCount = document.getElementById('upCount');
    const downCount = document.getElementById('downCount');
    const totalCount = document.getElementById('totalCount');
    const loading = document.getElementById('loading');

    // Initialize
    loadUrls();

    // Form Submission
    addUrlForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const name = document.getElementById('urlName').value;
        const url = document.getElementById('url').value;
        const interval = parseInt(document.getElementById('interval').value);
        
        if (!url) {
            alert('Please enter a URL');
            return;
        }

        showLoading();
        try {
            const response = await fetch(`${API_BASE}/urls`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url, interval })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Clear form
                addUrlForm.reset();
                document.getElementById('interval').value = 5;
                
                // Reload URLs
                loadUrls();
                showNotification('URL added successfully!', 'success');
            } else {
                throw new Error(data.error || 'Failed to add URL');
            }
        } catch (error) {
            showNotification(error.message, 'error');
        } finally {
            hideLoading();
        }
    });

    // Check All URLs
    checkAllBtn.addEventListener('click', async function() {
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/urls/check-all`, {
                method: 'POST'
            });
            
            if (response.ok) {
                loadUrls();
                showNotification('All URLs checked!', 'success');
            } else {
                throw new Error('Failed to check URLs');
            }
        } catch (error) {
            showNotification(error.message, 'error');
        } finally {
            hideLoading();
        }
    });

    // Load URLs
    async function loadUrls() {
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/urls`);
            urls = await response.json();
            
            renderUrls();
            updateStats();
        } catch (error) {
            showNotification('Failed to load URLs', 'error');
            console.error('Error loading URLs:', error);
        } finally {
            hideLoading();
        }
    }

    // Render URLs List
    function renderUrls() {
        if (Object.keys(urls).length === 0) {
            urlsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-link fa-3x"></i>
                    <p>No URLs added yet. Add your first URL above!</p>
                </div>
            `;
            return;
        }

        urlsList.innerHTML = '';
        
        Object.values(urls).forEach(url => {
            const lastCheck = url.last_check || {};
            const isUp = lastCheck.status === 'up';
            const lastChecked = lastCheck.timestamp ? 
                new Date(lastCheck.timestamp * 1000).toLocaleString() : 
                'Never checked';
            
            const urlItem = document.createElement('div');
            urlItem.className = `url-item ${isUp ? '' : 'down'}`;
            urlItem.innerHTML = `
                <div class="url-info">
                    <h3>${url.name || url.url}</h3>
                    <p>${url.url}</p>
                    <p><small>Interval: ${url.interval} min | Last checked: ${lastChecked}</small></p>
                    ${lastCheck.response_time ? `<p><small>Response: ${lastCheck.response_time}ms</small></p>` : ''}
                </div>
                <div class="url-status">
                    <div class="status-indicator ${isUp ? '' : 'down'}"></div>
                    <span class="status-text">${isUp ? 'UP' : 'DOWN'}</span>
                    <div class="url-actions">
                        <button class="btn btn-small btn-secondary" onclick="checkUrl('${url.id}')">
                            <i class="fas fa-sync-alt"></i> Check Now
                        </button>
                        <button class="btn btn-small btn-danger" onclick="deleteUrl('${url.id}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            `;
            urlsList.appendChild(urlItem);
        });
    }

    // Check Single URL
    window.checkUrl = async function(urlId) {
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/urls/${urlId}/check`, {
                method: 'POST'
            });
            
            if (response.ok) {
                loadUrls();
                showNotification('URL checked!', 'success');
            } else {
                throw new Error('Failed to check URL');
            }
        } catch (error) {
            showNotification(error.message, 'error');
        } finally {
            hideLoading();
        }
    };

    // Delete URL
    window.deleteUrl = async function(urlId) {
        if (!confirm('Are you sure you want to delete this URL?')) {
            return;
        }

        showLoading();
        try {
            const response = await fetch(`${API_BASE}/urls/${urlId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                loadUrls();
                showNotification('URL deleted!', 'success');
            } else {
                throw new Error('Failed to delete URL');
            }
        } catch (error) {
            showNotification(error.message, 'error');
        } finally {
            hideLoading();
        }
    };

    // Update Statistics
    function updateStats() {
        const urlList = Object.values(urls);
        const upUrls = urlList.filter(url => {
            const lastCheck = url.last_check || {};
            return lastCheck.status === 'up';
        });
        const downUrls = urlList.filter(url => {
            const lastCheck = url.last_check || {};
            return lastCheck.status === 'down' || !lastCheck.status;
        });

        upCount.textContent = upUrls.length;
        downCount.textContent = downUrls.length;
        totalCount.textContent = urlList.length;
    }

    // Show/Hide Loading
    function showLoading() {
        loading.style.display = 'flex';
    }

    function hideLoading() {
        loading.style.display = 'none';
    }

    // Show Notification
    function showNotification(message, type) {
        // Remove existing notification
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#48bb78' : '#f56565'};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
        
        // Add animation keyframes
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Auto-refresh every 30 seconds
    setInterval(loadUrls, 30000);
});
