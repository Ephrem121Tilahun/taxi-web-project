from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import os
import sqlite3
import random
import time
import threading
from flask_compress import Compress
from flask_caching import Cache
from twilio.rest import Client
from dotenv import load_dotenv
from flask_socketio import SocketIO
from flask_migrate import Migrate
from models import db  # Import your db instance



app = Flask(__name__)
app.config['SECRET_KEY'] = "azxblcnxnczcvcxvxcvbxcbvwer445"

ckeditor = CKEditor(app)
Bootstrap5(app)
socketio = SocketIO(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

compress = Compress()
compress.init_app(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Load environment variables
load_dotenv()
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
your_phone_number = os.getenv('YOUR_PHONE_NUMBER')

# Single taxi data
taxis = {
    'taxi_2': {'lat': 56.7268, 'lng': -111.3871, 'status': 'On a ride'},  # Fort McMurray
}

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id) # type: ignore

gravatar = Gravatar(app, size=100, rating='g', default='retro')

class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///posts.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(model_class=Base)
db.init_app(app)


migrate = Migrate(app, db)


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

# Combined index route
@app.route('/')
def index():
    feedbacks = Feedback.query.all()
    comments = fetch_comments()  # Fetch comments from the comments database
    return render_template('index.html', feedbacks=feedbacks, comments=comments)

def fetch_comments():
    conn = sqlite3.connect('comments.db')
    c = conn.cursor()
    c.execute("SELECT * FROM comments")
    comments = c.fetchall()
    conn.close()
    return comments

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    rating = request.form.get('rating')
    comment = request.form.get('comments')
    if rating and comment:
        feedback = Feedback(rating=rating, comment=comment)
        db.session.add(feedback)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/comments', methods=['POST'])
def submit_comment():
    comment = request.form['comment']
    if comment:
        conn = sqlite3.connect('comments.db')
        c = conn.cursor()
        c.execute("INSERT INTO comments (comment) VALUES (?)", (comment,))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))  # Redirect back to index to show comments

# Real-time location updates
def update_taxi_locations():
    while True:
        time.sleep(5)  # Update every 5 seconds
        taxis['taxi_2']['lat'] += random.uniform(-0.001, 0.001)
        taxis['taxi_2']['lng'] += random.uniform(-0.001, 0.001)
        socketio.emit('update_location', taxis, to='/')


@socketio.on('connect')
def handle_connect():
    socketio.emit('update_location', taxis)

# Twilio client
twilio_client = Client(account_sid, auth_token)

@app.route('/booking')
def booking():
    return render_template('booking.html')

@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    phone = request.form['phone']
    pickup_location = request.form['pickup_time']
    pickup_location = request.form['pickup_location']
    dropoff_location = request.form['dropoff_location']
    driver_phone = '+17809722321'  # Replace with actual driver number
    message = f"New Booking:\nName: {name}\nPhone: {phone}\nPick time: {pickup_time}\nPickup: {pickup_location}\nDropoff: {dropoff_location}" # type: ignore

    # Send the SMS
    twilio_client.messages.create(
        to=driver_phone,
        from_=twilio_phone_number,
        body=message
    )
    return redirect(url_for('index'))

@app.route('/send-emergency-message', methods=['POST'])
def send_emergency_message():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    custom_message = data.get('customMessage', '')
    message_body = f"Emergency! User's location: https://maps.google.com/?q={latitude},{longitude}\nCustom Message: {custom_message}"

    twilio_client.messages.create(
        body=message_body,
        from_=twilio_phone_number,
        to=your_phone_number
    )

    return jsonify({'status': 'Emergency message sent successfully!'}), 200

@app.route('/make_call', methods=['POST'])
def make_call():
    try:
        call = twilio_client.calls.create(
            from_=twilio_phone_number,
            to=your_phone_number,
            url="http://demo.twilio.com/docs/voice.xml"
        )
        return jsonify({'message': 'Call initiated!', 'sid': call.sid})
    except Exception as e:
        return jsonify({'message': 'Error initiating call', 'error': str(e)}), 500

@app.route('/about')
def about():
    return render_template('about.html')  # Ensure you have this template

@app.route('/contact')
def contact():
    return render_template('contact.html')  # Ensure you have this template


if __name__ == '__main__':
    threading.Thread(target=update_taxi_locations, daemon=True).start()
    socketio.run(app, allow_unsafe_werkzeug=True, debug=False)
