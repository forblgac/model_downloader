const API_BASE = '/api/downloads';
let fetchInterval;
let notifiedDownloads = new Set(); // Track which completed downloads we've already notified about
const DEFAULT_FAVORITES = [
    "models/checkpoints",
    "models/loras",
    "models/controlnet",
    "models/unet",
    "models/clip",
    "models/vae",
    "models/downloads"
];

document.addEventListener('DOMContentLoaded', () => {
    // Request notification permission if needed
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }

    // Initialize favorites from local storage
    renderFavorites();

    // Setup form submission
    const form = document.getElementById('download-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const urlInput = document.getElementById('url');
        const destInput = document.getElementById('destination');
        const submitBtn = form.querySelector('button[type="submit"]');

        const url = urlInput.value.trim();
        const destination = destInput.value;

        if (!url) return;

        // Disable button while submitting
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Adding...';

        try {
            const response = await fetch(API_BASE, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    destination_folder: destination
                })
            });

            if (response.ok) {
                urlInput.value = '';
                // Immediately refresh list
                fetchDownloads();
            } else {
                alert('Failed to add download task.');
            }
        } catch (error) {
            console.error('Error adding download:', error);
            alert('Error adding download.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-download"></i> Start Download';
        }
    });

    // Setup move form submission
    const moveForm = document.getElementById('move-form');
    moveForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const sourceInput = document.getElementById('source_path');
        const destInput = document.getElementById('move_destination');
        const submitBtn = moveForm.querySelector('button[type="submit"]');

        const sourcePath = sourceInput.value.trim();
        const destination = destInput.value;

        if (!sourcePath) return;

        // Disable button while submitting
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Moving...';

        try {
            const response = await fetch('/api/move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    source_path: sourcePath,
                    destination_folder: destination
                })
            });

            const result = await response.json();

            if (response.ok) {
                alert(`Success: ${result.message}`);
                sourceInput.value = '';
            } else {
                alert(`Failed to move file: ${result.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error moving file:', error);
            alert('Error communicating with server.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-truck-fast"></i> Move File';
        }
    });

    // Setup tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            // Add active class to clicked button and target content
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // Start polling for updates
    fetchDownloads();
    fetchInterval = setInterval(fetchDownloads, 2000);
});

function getFavorites() {
    const favs = localStorage.getItem('downloadFavorites');
    if (favs) {
        return JSON.parse(favs);
    }
    return DEFAULT_FAVORITES;
}

function renderFavorites() {
    const favorites = getFavorites();
    const datalist = document.getElementById('favorites-list');
    if (!datalist) return;
    datalist.innerHTML = '';

    favorites.forEach(fav => {
        const option = document.createElement('option');
        option.value = fav;
        datalist.appendChild(option);
    });
}

window.saveFavorite = function (inputId) {
    const input = document.getElementById(inputId);
    const val = input.value.trim();
    if (!val) return;

    let favorites = getFavorites();
    if (!favorites.includes(val)) {
        favorites.push(val);
        localStorage.setItem('downloadFavorites', JSON.stringify(favorites));
        renderFavorites();

        // Brief visual feedback
        const btn = input.nextElementSibling;
        const origHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i>';
        btn.style.color = '#10b981';
        btn.style.borderColor = '#10b981';
        setTimeout(() => {
            btn.innerHTML = origHtml;
            btn.style.color = '';
            btn.style.borderColor = '';
        }, 1000);
    }
};

function triggerNotification(task) {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") {
        new Notification("Download Completed", {
            body: `${task.filename} has finished downloading.`,
            icon: "favicon.ico"
        });
    }
}

async function fetchDownloads() {
    try {
        const response = await fetch(API_BASE);
        if (!response.ok) throw new Error('Network response was not ok');

        const tasks = await response.json();
        renderDownloads(tasks);
    } catch (error) {
        console.error('Error fetching downloads:', error);
        // Don't clear the list on error, just log it. Server might be restarting.
    }
}

function renderDownloads(tasks) {
    const listContainer = document.getElementById('downloads-list');
    const template = document.getElementById('download-item-template');

    // If no tasks, show a message
    if (tasks.length === 0) {
        listContainer.innerHTML = '<div class="loading-spinner">No active or recent downloads.</div>';
        return;
    }

    // Create a map of existing elements by ID to update them in place rather than full re-render
    const existingElements = Array.from(listContainer.querySelectorAll('.download-item'));
    const existingIds = existingElements.map(el => parseInt(el.dataset.id));

    // Remove elements that are no longer in the tasks list
    const incomingIds = tasks.map(t => t.id);
    for (const el of existingElements) {
        if (!incomingIds.includes(parseInt(el.dataset.id))) {
            el.remove();
        }
    }

    // Ensure the loading spinner is gone
    const spinner = listContainer.querySelector('.loading-spinner');
    if (spinner) spinner.remove();

    tasks.forEach(task => {
        let el = listContainer.querySelector(`.download-item[data-id="${task.id}"]`);

        if (!el) {
            // Create new element from template
            const clone = template.content.cloneNode(true);
            el = clone.querySelector('.download-item');
            el.dataset.id = task.id;

            // Setup action buttons
            const deleteBtn = el.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', () => deleteDownload(task.id));

            const resumeBtn = el.querySelector('.resume-btn');
            resumeBtn.addEventListener('click', () => resumeDownload(task.id));

            // Append to DOM
            listContainer.appendChild(el);
        }

        // Update data in place
        updateElementData(el, task);

        // Trigger notification if newly completed
        if (task.status === 'COMPLETED' && !notifiedDownloads.has(task.id)) {
            triggerNotification(task);
            notifiedDownloads.add(task.id);
        } else if (task.status === 'FAILED' || task.status === 'CANCELLED') {
            // If it failed/cancelled, add it to set so we don't notify
            notifiedDownloads.add(task.id);
        }
    });
}

function updateElementData(el, task) {
    // Info
    el.querySelector('.filename').textContent = task.filename || 'Resolving filename...';
    el.querySelector('.url').textContent = task.url;
    el.querySelector('.destination').textContent = task.destination_folder;

    // Status Badge
    const badge = el.querySelector('.status-badge');
    badge.textContent = task.status;
    badge.className = `status-badge status-${task.status.toLowerCase()}`;

    // Add icon based on status
    const statusIconMap = {
        'PENDING': '<i class="fa-solid fa-clock"></i> ',
        'DOWNLOADING': '<i class="fa-solid fa-circle-notch fa-spin"></i> ',
        'COMPLETED': '<i class="fa-solid fa-check"></i> ',
        'FAILED': '<i class="fa-solid fa-triangle-exclamation"></i> ',
        'CANCELLED': '<i class="fa-solid fa-ban"></i> '
    };
    badge.innerHTML = (statusIconMap[task.status] || '') + task.status;

    // Progress
    const pct = parseFloat(task.progress_percent).toFixed(1);
    el.querySelector('.progress-fill').style.width = `${pct}%`;
    el.querySelector('.percentage').textContent = `${pct}%`;

    // Colors for completed progress bar
    const resumeBtn = el.querySelector('.resume-btn');
    if (task.status === 'COMPLETED') {
        el.querySelector('.progress-fill').style.background = 'linear-gradient(90deg, #10b981, #34d399)';
        el.querySelector('.progress-fill').style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.5)';
        resumeBtn.classList.add('hidden');
    } else if (task.status === 'FAILED' || task.status === 'CANCELLED') {
        el.querySelector('.progress-fill').style.background = '#64748b';
        el.querySelector('.progress-fill').style.boxShadow = 'none';
        el.querySelector('.percentage').textContent = task.status;
        resumeBtn.classList.remove('hidden');
    } else {
        resumeBtn.classList.add('hidden');
        el.querySelector('.progress-fill').style.background = 'linear-gradient(90deg, var(--accent-color), #818cf8)';
        el.querySelector('.progress-fill').style.boxShadow = '0 0 10px var(--accent-glow)';
    }

    // Error message
    const errorEl = el.querySelector('.error-message');
    if (task.error_message) {
        errorEl.textContent = `Error: ${task.error_message}`;
        errorEl.style.display = 'block';
    } else {
        errorEl.style.display = 'none';
    }
}

async function deleteDownload(id) {
    if (!confirm('Are you sure you want to cancel and remove this download?')) return;

    try {
        const response = await fetch(`${API_BASE}/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Refresh
            fetchDownloads();
        } else {
            alert('Failed to delete download.');
        }
    } catch (error) {
        console.error('Error deleting download:', error);
        alert('Error communicating with server.');
    }
}

async function resumeDownload(id) {
    // Optimistic UI update could go here, but for now we'll just show disabled/spin state or rely on polling
    try {
        const response = await fetch(`${API_BASE}/${id}/resume`, {
            method: 'POST'
        });

        if (response.ok) {
            // Force quick refresh
            fetchDownloads();
        } else {
            alert('Failed to resume download.');
        }
    } catch (error) {
        console.error('Error resuming download:', error);
        alert('Error communicating with server.');
    }
}
