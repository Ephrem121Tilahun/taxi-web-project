from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import os
import sqlite3
from sqlalchemy.testing.pickleable import User
from twilio.rest import Client
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
import random
import time
import threading
from flask_compress import Compress
from flask_caching import Cache



'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''


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



# Retrieve Twilio credentials from environment variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
your_phone_number = os.getenv('YOUR_PHONE_NUMBER')



url="https://yourdomain.com/emergency_call.xml"  # Ensure this is publicly accessible


# Single taxi data
taxis = {
    'taxi_2': {'lat': 56.7268, 'lng': -111.3871, 'status': 'On a ride'},  # Fort McMurray
}








@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# For adding profile images to the comment section
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(model_class=Base)
db.init_app(app)



#feed back


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=False)




with app.app_context():
    db.create_all()


@app.route('/')
def index():
    feedbacks = Feedback.query.all()
    return render_template('index.html', feedbacks=feedbacks)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    rating = request.form.get('rating')
    comment = request.form.get('comments')
    if rating and comment:
        feedback = Feedback(rating=rating, comment=comment)
        db.session.add(feedback)
        db.session.commit()
    return redirect(url_for('index'))







#real time location

def update_taxi_locations():
    while True:
        time.sleep(5)  # Update every 5 seconds
        # Simulate random movement around the current location for taxi_2
        taxis['taxi_2']['lat'] += random.uniform(-0.001, 0.001)  # Slight latitude change
        taxis['taxi_2']['lng'] += random.uniform(-0.001, 0.001)  # Slight longitude change
        print(taxis)
        socketio.emit('update_location', taxis, broadcast=True)  # Broadcast updated location

@socketio.on('connect')
def handle_connect():
    emit('update_location', taxis)  # Send current location to the new client



# Create Twilio client
twilio_client = Client(account_sid, auth_token)

# booking
@app.route('/booking')
def booking():
    return render_template('booking.html')


@app.route('/book', methods=['GET', 'POST'])
def book():
    name = request.form['name']
    phone = request.form['phone']
    pickup_location = request.form['pickup_location']
    dropoff_location = request.form['dropoff_location']

    # Logic to send SMS to the driver (replace with actual driver number)
    driver_phone = '+17809722321'  # Replace with the driver's phone number
    message = f"New Booking:\nName: {name}\nPhone: {phone}\nPickup: {pickup_location}\nDropoff: {dropoff_location}"

    # Send the SMS
    twilio_client.messages.create(
        to=driver_phone,
        from_=twilio_phone_number,
        body=message
    )

    return redirect(url_for('get_all_posts'))  # Redirect back to the index page after booking



@app.route('/send-emergency-message', methods=['POST'])
def send_emergency_message():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    custom_message = data.get('customMessage', '')  # Get custom message, default to empty if not provided

    # Construct the message with the user's location and custom message
    message_body = f"Emergency! User's location: https://maps.google.com/?q={latitude},{longitude}\nCustom Message: {custom_message}"

        # Send the message using Twilio
    message = twilio_client.messages.create(
        body=message_body,
        from_=twilio_phone_number,
        to=your_phone_number
    )

    return jsonify({'status': 'Emergency message sent successfully!'}), 200






# Endpoint to initiate a call

@app.route('/make_call', methods=['POST'])
def make_call():
    try:
        # Create call
        call = twilio_client.calls.create(
            from_=twilio_phone_number,  # Twilio phone number
            to=your_phone_number,  # Your phone number
            url="http://demo.twilio.com/docs/voice.xml"  # Twilio demo XML to say "hello"
        )
        return jsonify({'message': 'Call initiated!', 'sid': call.sid})
    except Exception as e:
        return jsonify({'message': 'Error initiating call', 'error': str(e)}), 500







@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select)
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, current_user=current_user)



@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    return render_template("contact.html", current_user=current_user)


#comment area
# Function to create a comments table if it doesn't exist
def create_table():
    conn = sqlite3.connect('comments.db')  # Connect to the SQLite database (or create it if it doesn't exist)
    c = conn.cursor()  # Create a cursor object to execute SQL queries
    # Create a table for comments with an auto-incrementing ID
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment TEXT NOT NULL
                )''')
    conn.commit()  # Commit the changes to the database
    conn.close()




@app.route('/comments')  # Changed route to '/comments'
def comments_page():  # Renamed the function to 'comments_page'
    # Fetch all the comments from the database to display them
    conn = sqlite3.connect('comments.db')
    c = conn.cursor()
    c.execute("SELECT * FROM comments")
    comments = c.fetchall()  # Fetch all rows from the comments table
    conn.close()
    return render_template('index.html', comments=comments)  # Changed template to 'comments.html'

# Route to handle form submissions
@app.route('/submit', methods=['POST'])
def submit_comment():
    comment = request.form['comment']  # Get the submitted comment from the form
    if comment:  # Check if the comment is not empty
        # Insert the new comment into the database
        conn = sqlite3.connect('comments.db')
        c = conn.cursor()
        c.execute("INSERT INTO comments (comment) VALUES (?)", (comment,))
        conn.commit()
        conn.close()
    return redirect(url_for('comments_page'))  # Redirect back to the comments page





if __name__ == '__main__':
    # Start background thread to update taxi location
    threading.Thread(target=update_taxi_locations, daemon=True).start()
    socketio.run(app, allow_unsafe_werkzeug=True, debug=False)  # Allow unsafe Werkzeug