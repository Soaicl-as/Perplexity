document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const loginSection = document.getElementById('login-section');
    const botSection = document.getElementById('bot-section');
    const loginForm = document.getElementById('login-form');
    const loginMessage = document.getElementById('login-message');
    const verificationSection = document.getElementById('verification-section');
    const verificationCompleteBtn = document.getElementById('verification-complete-btn');
    const loggedUsername = document.getElementById('logged-username');
    const logoutBtn = document.getElementById('logout-btn');
    const extractForm = document.getElementById('extract-form');
    const extractMessage = document.getElementById('extract-message');
    const dmForm = document.getElementById('dm-form');
    const dmMessage = document.getElementById('dm-message');
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const successfulCount = document.getElementById('successful-count');
    const failedCount = document.getElementById('failed-count');
    const activityLog = document.getElementById('activity-log');
    const usersModal = document.getElementById('users-modal');
    const usersList = document.getElementById('users-list');
    const closeModal = document.querySelector('.close');
    const selectAllBtn = document.getElementById('select-all-btn');
    const useSelectedBtn = document.getElementById('use-selected-btn');

    // Socket.IO Connection for real-time updates
    const socket = io();
    
    // Extracted users storage
    let extractedUsers = [];
    let selectedUsers = [];
    
    // Event Listeners
    loginForm.addEventListener('submit', handleLogin);
    verificationCompleteBtn.addEventListener('click', handleVerificationComplete);
    logoutBtn.addEventListener('click', handleLogout);
    extractForm.addEventListener('submit', handleExtractUsers);
    dmForm.addEventListener('submit', handleSendDM);
    
    // Socket event handlers for real-time progress updates
    socket.on('dm_progress_update', (data) => {
        updateProgress(data);
        addLogEntry(formatLogMessage(data), getLogClass(data.status));
    });
    
    socket.on('dm_complete', (data) => {
        addLogEntry(`Mass DM process completed. ${data.summary.successful} successful, ${data.summary.failed} failed.`, 'success');
    });
    
    // Core functionality
    function handleLogin(event) {
        event.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        showMessage(loginMessage, 'Logging in...', 'info');
        
        fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username, password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showMessage(loginMessage, 'Login successful!', 'success');
                loggedUsername.textContent = username;
                showBotSection();
            } else if (data.status === 'verification_required') {
                showMessage(loginMessage, 'Security verification required.', 'warning');
                verificationSection.classList.remove('hidden');
            } else {
                showMessage(loginMessage, `Login failed: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            showMessage(loginMessage, `Error: ${error.message}`, 'error');
        });
    }
    
    function handleExtractUsers(event) {
        event.preventDefault();
        
        const targetUsername = document.getElementById('target-username').value;
        const extractType = document.querySelector('input[name="extract-type"]:checked').value;
        const maxCount = document.getElementById('max-count').value;
        
        showMessage(extractMessage, `Extracting ${extractType} from ${targetUsername}...`, 'info');
        
        fetch('/api/extract-users', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                username: targetUsername,
                type: extractType,
                max_count: maxCount
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const users = data[extractType] || [];
                extractedUsers = users;
                
                showMessage(extractMessage, `Successfully extracted ${users.length} ${extractType}.`, 'success');
                showUsersModal(users);
            } else {
                showMessage(extractMessage, `Extraction failed: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            showMessage(extractMessage, `Error: ${error.message}`, 'error');
        });
    }
    
    function handleSendDM(event) {
        event.preventDefault();
        
        const message = document.getElementById('message').value;
        const maxDMs = parseInt(document.getElementById('max-dms').value);
        const minDelay = parseFloat(document.getElementById('min-delay').value);
        const maxDelay = parseFloat(document.getElementById('max-delay').value);
        
        // Validation checks
        if (selectedUsers.length === 0) {
            showMessage(dmMessage, 'No users selected. Please extract and select users first.', 'error');
            return;
        }
        
        // Limit users based on maxDMs
        const usernamesToMessage = selectedUsers.slice(0, maxDMs);
        
        showMessage(dmMessage, `Starting to send messages to ${usernamesToMessage.length} users...`, 'info');
        resetProgress();
        showProgressSection();
        
        fetch('/api/send-mass-dm', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                usernames: usernamesToMessage,
                message: message,
                min_delay: minDelay,
                max_delay: maxDelay
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'started') {
                addLogEntry(`Starting to send messages to ${data.total} users...`, 'info');
            } else {
                showMessage(dmMessage, `Failed to start: ${data.message}`, 'error');
                hideProgressSection();
            }
        })
        .catch(error => {
            showMessage(dmMessage, `Error: ${error.message}`, 'error');
            hideProgressSection();
        });
    }
    
    // Helper functions for UI updates and state management
    function showUsersModal(users) {
        // UI implementation for user selection modal
        usersList.innerHTML = '';
        selectedUsers = [];
        
        users.forEach(username => {
            const userItem = document.createElement('div');
            userItem.className = 'user-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = username;
            checkbox.id = `user-${username}`;
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    selectedUsers.push(username);
                } else {
                    selectedUsers = selectedUsers.filter(user => user !== username);
                }
            });
            
            const label = document.createElement('label');
            label.textContent = username;
            label.setAttribute('for', `user-${username}`);
            
            userItem.appendChild(checkbox);
            userItem.appendChild(label);
            usersList.appendChild(userItem);
        });
        
        usersModal.style.display = 'block';
    }
    
    function updateProgress(data) {
        const percent = (data.current / data.total) * 100;
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${data.current}/${data.total}`;
        
        if (data.successful !== undefined) {
            successfulCount.textContent = data.successful;
        }
        
        if (data.failed !== undefined) {
            failedCount.textContent = data.failed;
        }
    }
    
    function addLogEntry(message, type = 'info') {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        logEntry.textContent = `[${timestamp}] ${message}`;
        
        activityLog.appendChild(logEntry);
        activityLog.scrollTop = activityLog.scrollHeight;
    }
    
    // UI utility functions
    function showMessage(element, message, type) {
        element.textContent = message;
        element.className = `message ${type}`;
    }
    
    function showBotSection() {
        loginSection.classList.add('hidden');
        botSection.classList.remove('hidden');
    }
    
    function showProgressSection() {
        progressSection.style.display = 'block';
    }
    
    function resetProgress() {
        progressBar.style.width = '0%';
        progressText.textContent = '0/0';
        successfulCount.textContent = '0';
        failedCount.textContent = '0';
        activityLog.innerHTML = '';
    }
});
