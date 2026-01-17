// DOM Elements
const addForm = document.getElementById('addForm');
const urlList = document.getElementById('urlList');
const emptyMessage = document.getElementById('emptyMessage');

// Load URLs on page load
document.addEventListener('DOMContentLoaded', loadURLs);

// Load URLs from server
async function loadURLs() {
    try {
        const response = await fetch('/api/urls');
        if (response.ok) {
            const urls = await response.json();
            displayURLs(urls);
        }
    } catch (error) {
        console.error('Error loading URLs:', error);
    }
}

// Display URLs in list
function displayURLs(urls) {
    const urlArray = Object.values(urls);
    
    if (urlArray.length === 0) {
        emptyMessage.style.display = 'block';
        urlList.innerHTML = '';
        return;
    }
    
    emptyMessage.style.display = 'none';
    urlList.innerHTML = '';
    
    urlArray.forEach(url => {
        const urlItem = document.createElement('div');
        urlItem.className = 'url-item';
        
        const isActive = url.is_active || url.monitoring;
        
        urlItem.innerHTML = `
            <div class="url-info">
                <div class="url-name">${url.url}</div>
                <div class="url-link">${url.url}</div>
                <div class="url-interval">Pings every ${url.interval} minute(s)</div>
                <span class="status ${isActive ? 'status-active' : 'status-inactive'}">
                    ${isActive ? 'Active' : 'Inactive'}
                </span>
            </div>
            <div>
                ${isActive ? 
                    `<button class="btn btn-stop" onclick="stopPing('${url.id}')">⏸ Stop</button>` :
                    `<button class="btn btn-start" onclick="startPing('${url.id}')">▶ Start</button>`
                }
                <button class="btn btn-delete" onclick="deleteURL('${url.id}')">🗑 Delete</button>
            </div>
        `;
        
        urlList.appendChild(urlItem);
    });
}

// Add new URL
addForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const urlInput = document.getElementById('url');
    const intervalSelect = document.getElementById('interval');
    
    const urlData = {
        url: urlInput.value.trim(),
        interval: parseInt(intervalSelect.value)
    };
    
    try {
        const response = await fetch('/api/urls', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(urlData)
        });
        
        if (response.ok) {
            urlInput.value = '';
            alert('URL added successfully!');
            loadURLs();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to add URL');
        }
    } catch (error) {
        alert('Network error. Please try again.');
    }
});

// Start pinging a URL
async function startPing(urlId) {
    try {
        const response = await fetch(`/api/urls/${urlId}/start`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('Pinging started!');
            loadURLs();
        } else {
            alert('Failed to start pinging');
        }
    } catch (error) {
        alert('Network error');
    }
}

// Stop pinging a URL
async function stopPing(urlId) {
    try {
        const response = await fetch(`/api/urls/${urlId}/stop`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('Pinging stopped!');
            loadURLs();
        } else {
            alert('Failed to stop pinging');
        }
    } catch (error) {
        alert('Network error');
    }
}

// Delete a URL
async function deleteURL(urlId) {
    if (!confirm('Delete this URL?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/urls/${urlId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('URL deleted!');
            loadURLs();
        } else {
            alert('Failed to delete URL');
        }
    } catch (error) {
        alert('Network error');
    }
}