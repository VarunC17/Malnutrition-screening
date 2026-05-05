from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
import cv2
import numpy as np
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_nutrivision_key_2026'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Mock User Database
USERS = {
    "admin": "password123",
    "doctor": "health2026"
}

class MalnutritionDetector:
    def __init__(self):
        print("Model initialized (Mock)")
        
    def analyze(self, image_path, custom_seed=None):
        img = cv2.imread(image_path)
        if img is None:
            return {"error": "Invalid image"}
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Magic Demo Seeds for Guaranteed Outcomes
        magic_seeds = {
            "DEMO_HEALTHY": "Healthy",
            "DEMO_MILD": "Mild Malnutrition",
            "DEMO_SEVERE": "Severe Malnutrition"
        }
        
        if custom_seed and custom_seed.upper() in magic_seeds:
            prediction = magic_seeds[custom_seed.upper()]
            # Set a stable seed based just on the string to keep metrics consistent
            np.random.seed(sum(ord(c) for c in custom_seed.upper()))
        else:
            # Combine image data with custom seed for highly specific reproducible results
            base_val = int(np.sum(img_rgb))
            if custom_seed:
                seed_val = (base_val + sum(ord(c) for c in str(custom_seed))) % 10000
            else:
                seed_val = base_val % 10000
                
            np.random.seed(seed_val)
            
            categories = ["Healthy", "Mild Malnutrition", "Severe Malnutrition"]
            weights = [0.6, 0.3, 0.1]
            prediction = np.random.choice(categories, p=weights)
        
        confidence = float(np.random.uniform(0.85, 0.99)) # Boosted confidence for demo
        
        if prediction == "Healthy":
            bmi = np.random.uniform(18.5, 24.9)
            muac = np.random.uniform(12.5, 16.0)
            status_class = "Healthy"
        elif prediction == "Mild Malnutrition":
            bmi = np.random.uniform(16.0, 18.4)
            muac = np.random.uniform(11.5, 12.4)
            status_class = "Mild"
        else:
            bmi = np.random.uniform(12.0, 15.9)
            muac = np.random.uniform(9.0, 11.4)
            status_class = "Severe"
            
        stunting_risk = "Low" if status_class == "Healthy" else ("Moderate" if status_class == "Mild" else "High")
        
        return {
            "status": prediction,
            "status_class": status_class,
            "confidence": f"{confidence*100:.1f}",
            "metrics": {
                "bmi_estimate": f"{bmi:.1f}",
                "muac_estimate": f"{muac:.1f} cm",
                "stunting_risk": stunting_risk
            }
        }

detector = MalnutritionDetector()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and USERS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            session['history'] = [] # Initialize empty history
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials. Please try again.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username'), history=session.get('history', []))

@app.route('/analyze', methods=['POST'])
def analyze():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized access"}), 401
        
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        custom_seed = request.form.get('seed', '').strip()
        
        # Run AI analysis
        results = detector.analyze(filepath, custom_seed=custom_seed if custom_seed else None)
        
        # Add to history if successful
        if "error" not in results:
            scan_record = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": results["status"],
                "confidence": results["confidence"],
                "status_class": results["status_class"]
            }
            # Keep last 5 scans in session
            history = session.get('history', [])
            history.insert(0, scan_record)
            session['history'] = history[:5]
            session.modified = True
            
        return jsonify({
            "image_url": f"/{filepath}",
            "analysis": results,
            "scan_record": scan_record if "error" not in results else None
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
