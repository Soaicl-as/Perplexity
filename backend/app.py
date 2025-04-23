from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import logging
import threading
import os
import time
from backend.instagram_bot import InstagramBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')

# Initialize Flask app
app = Flask(__name__, 
            static_folder='frontend/static', 
            template_folder='frontend/templates')
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global bot instance
bot_instance = None
bot_lock = threading.Lock()

# Progress tracking for mass DMs
dm_progress = {
    "running": False,
    "current": 0,
    "total": 0,
    "successful": 0,
    "failed": 0
}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    """Handle Instagram login"""
    global bot_instance
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required"})
    
    # Create a new bot instance if one doesn't exist
    with bot_lock:
        if bot_instance is None:
            bot_instance = InstagramBot(headless=True)
    
    # Attempt to log in
    result = bot_instance.login(username, password)
    
    if result["status"] == "success":
        session['logged_in'] = True
        session['username'] = username
        return jsonify({"status": "success"})
    elif result["status"] == "verification_required":
        return jsonify({"status": "verification_required"})
    else:
        return jsonify({"status": "error", "message": result.get("message", "Login failed")})

@app.route('/api/verify-complete', methods=['POST'])
def verify_complete():
    """Handle completion of manual verification"""
    global bot_instance
    
    if not bot_instance:
        return jsonify({"status": "error", "message": "No active session"})
    
    # Check if the user is now logged in
    if bot_instance.check_login_status():
        session['logged_in'] = True
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Verification not complete or failed"})

# Additional API endpoints for user extraction and DM sending
@app.route('/api/extract-users', methods=['POST'])
def extract_users():
    """Extract followers or following from a target account"""
    global bot_instance
    
    if not bot_instance or not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Not logged in"})
    
    data = request.json
    target_username = data.get('username')
    extraction_type = data.get('type', 'followers')  # 'followers' or 'following'
    max_count = int(data.get('max_count', 100))
    
    if not target_username:
        return jsonify({"status": "error", "message": "Target username is required"})
    
    # Extract the users
    if extraction_type == 'followers':
        result = bot_instance.get_user_followers(target_username, max_count=max_count)
    else:
        result = bot_instance.get_user_following(target_username, max_count=max_count)
    
    return jsonify(result)

@app.route('/api/send-mass-dm', methods=['POST'])
def send_mass_dm():
    """Start the mass DM process"""
    global bot_instance, dm_progress
    
    if not bot_instance or not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Not logged in"})
    
    # Check if a DM process is already running
    if dm_progress["running"]:
        return jsonify({"status": "error", "message": "A mass DM process is already running"})
    
    data = request.json
    usernames = data.get('usernames', [])
    message = data.get('message', '')
    min_delay = float(data.get('min_delay', 30))
    max_delay = float(data.get('max_delay', 60))
    
    if not usernames:
        return jsonify({"status": "error", "message": "No usernames provided"})
    
    if not message:
        return jsonify({"status": "error", "message": "Message cannot be empty"})
    
    # Reset progress
    dm_progress = {
        "running": True,
        "current": 0,
        "total": len(usernames),
        "successful": 0,
        "failed": 0
    }
    
    # Start the DM process in a separate thread
    threading.Thread(
        target=run_mass_dm, 
        args=(usernames, message, (min_delay, max_delay))
    ).start()
    
    return jsonify({"status": "started", "total": len(usernames)})

def run_mass_dm(usernames, message, delay_range):
    """Run the mass DM process in a background thread"""
    global bot_instance, dm_progress
    
    try:
        def progress_callback(data):
            global dm_progress
            
            if data["status"] == "success":
                dm_progress["successful"] += 1
            elif data["status"] == "failed":
                dm_progress["failed"] += 1
            
            dm_progress["current"] = data["current"]
            
            # Emit progress via Socket.IO
            socketio.emit('dm_progress_update', {
                "current": data["current"],
                "total": data["total"],
                "successful": dm_progress["successful"],
                "failed": dm_progress["failed"],
                "username": data.get("username", ""),
                "status": data["status"],
                "reason": data.get("reason", ""),
                "delay": data.get("delay", 0)
            })
        
        # Run the mass DM
        result = bot_instance.mass_dm(usernames, message, delay_range, progress_callback)
        
        # Update progress and emit completion
        dm_progress["running"] = False
        socketio.emit('dm_complete', result)
        
    except Exception as e:
        logger.error(f"Error in mass DM process: {str(e)}")
        dm_progress["running"] = False
        socketio.emit('dm_error', {"message": str(e)})

@socketio.on('connect')
def handle_connect():
    """Handle Socket.IO connection"""
    logger.info("Client connected")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
