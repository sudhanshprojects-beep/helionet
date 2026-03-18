from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# ThingSpeak API credentials
THINGSPEAK_READ_API_KEY = "70YPGMDEDRNTOZ79"
THINGSPEAK_CHANNEL_ID = "3303937"
THINGSPEAK_WRITE_API_KEY = "7NO12C75KUYKJDDG"
READ_URL = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds.json?api_key={THINGSPEAK_READ_API_KEY}&results=1"
WRITE_URL = "https://api.thingspeak.com/update"

# Global variables for scheduled maintenance
scheduled_maintenance = None
cleaning_active = False

def get_ldr_data():
    """Fetch LDR sensor data from ThingSpeak"""
    try:
        response = requests.get(READ_URL, timeout=5)
        data = response.json()
        if 'feeds' in data and len(data['feeds']) > 0:
            ldr_value = float(data['feeds'][0]['field1'])
            return ldr_value
    except Exception as e:
        print(f"Error fetching LDR data: {e}")
    return None

def send_cleaning_command(action):
    """Send cleaning command to ThingSpeak"""
    try:
        payload = {
            'api_key': THINGSPEAK_WRITE_API_KEY,
            'field1': action  # 1 for start, 0 for stop
        }
        response = requests.get(WRITE_URL, params=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending command: {e}")
    return False

def auto_clean_if_dirty():
    """Check LDR value and initiate cleaning if dirty"""
    ldr_value = get_ldr_data()
    if ldr_value is not None:
        # If LDR value is low (< 400), solar panel is dirty
        if ldr_value < 400:
            send_cleaning_command(1)  # Start cleaning
            return True, ldr_value
    return False, ldr_value

def scheduled_maintenance_task(start_time):
    """Run scheduled maintenance at specified time"""
    global cleaning_active
    while True:
        now = datetime.now()
        if now.hour == start_time.hour and now.minute == start_time.minute:
            cleaning_active = True
            send_cleaning_command(1)  # Start cleaning
            print(f"Scheduled cleaning started at {now}")
            
            # Wait 1 hour then stop
            time.sleep(3600)
            cleaning_active = False
            send_cleaning_command(0)  # Stop cleaning
            print(f"Scheduled cleaning stopped at {datetime.now()}")
            
            # Wait for next day
            time.sleep(60)
        time.sleep(30)

@app.route('/')
def home():
    ldr_value = get_ldr_data()
    is_dirty = ldr_value < 400 if ldr_value else False
    
    return render_template('home.html', 
                         ldr_value=ldr_value,
                         is_dirty=is_dirty,
                         scheduled_time=scheduled_maintenance)

@app.route('/api/ldr-status')
def ldr_status():
    """Get current LDR status"""
    ldr_value = get_ldr_data()
    is_dirty = ldr_value < 400 if ldr_value else False
    return jsonify({
        'ldr_value': ldr_value,
        'is_dirty': is_dirty,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/clean-now', methods=['POST'])
def clean_now():
    """Manually trigger cleaning"""
    success = send_cleaning_command(1)
    return jsonify({'success': success, 'message': 'Cleaning initiated'})

@app.route('/api/stop-cleaning', methods=['POST'])
def stop_cleaning():
    """Stop cleaning"""
    success = send_cleaning_command(0)
    return jsonify({'success': success, 'message': 'Cleaning stopped'})

@app.route('/api/schedule-maintenance', methods=['POST'])
def schedule_maintenance():
    """Schedule maintenance for a specific time"""
    global scheduled_maintenance
    data = request.get_json()
    time_str = data.get('time')  # Format: HH:MM
    
    try:
        hour, minute = map(int, time_str.split(':'))
        scheduled_maintenance = time_str
        
        # Start maintenance thread
        start_time = datetime.now().replace(hour=hour, minute=minute, second=0)
        thread = threading.Thread(target=scheduled_maintenance_task, args=(start_time,), daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Maintenance scheduled for {time_str}',
            'scheduled_time': time_str
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ml-recommendation')
def ml_recommendation():
    """ML-based maintenance recommendation"""
    # Dummy ML data - suggests optimal maintenance times based on usage patterns
    recommendations = {
        'optimal_times': ['06:00 AM', '02:00 PM', '08:00 PM'],
        'frequency': 'Daily',
        'estimated_dirt_accumulation': 45,  # percentage
        'confidence': 0.92,
        'reason': 'Based on historical weather patterns and solar irradiance data',
        'next_recommended_maintenance': '06:00 AM',
        'cleaning_duration': '1 hour',
        'efficiency_gain': '15-20%'
    }
    return jsonify(recommendations)

if __name__ == '__main__':
    app.run(debug=True, port=5000)