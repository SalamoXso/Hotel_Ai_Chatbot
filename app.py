import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from models import db, User, Conversation, Memory
from nlp_utils import preprocess_input, analyze_sentiment, detect_intent, extract_entities
from werkzeug.security import check_password_hash, generate_password_hash
from flask_migrate import Migrate
import re
import requests
from models import Room ,Reservation,User ,db # Import the Room model
from datetime import datetime
from nlp_utils import calculate_total_price  # Import the function
from nlp_utils import get_available_rooms  # Import the function


# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://postgres:HelloHackers1994%40%2A@localhost:5432/hotel_chatbot_ai_db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "mysecretkey")

db.init_app(app)
migrate = Migrate(app, db)

# Initialize APScheduler for background tasks
scheduler = BackgroundScheduler()

# Llama API configuration
base_url = "https://api.llama-api.com"
api_key = os.getenv("LLAMA_API_KEY")  # Ensure this is set in your .env file

# Check for follow-ups
def check_follow_ups():
    with app.app_context():  # Ensure database operations run within Flask's context
        conversations = Conversation.query.filter(Conversation.follow_up_date <= datetime.now()).all()
        for conversation in conversations:
            send_follow_up_message(conversation.user_id)

# Send follow-up message
def send_follow_up_message(user_id):
    user = db.session.get(User, user_id)
    message = "Just checking in! Do you need help with anything else for your upcoming reservation?"
    send_message_to_user(user, message)

# Placeholder function for sending messages
def send_message_to_user(user, message):
    print(f"Follow-up sent to {user.username}: {message}")

# Schedule follow-up task
scheduler.add_job(func=check_follow_ups, trigger="interval", days=1)
scheduler.start()

# Routes
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")

    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data['username']
            email = data['email']
            password = data['password']

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({"error": "Username already exists. Please choose another one."}), 400

            hashed_password = generate_password_hash(password)
            user = User(username=username, email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()

            return jsonify({"message": "User registered successfully!"}), 200

        except Exception as e:
            print(f"Error during registration: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        user = User.query.filter_by(username=data['username']).first()
        if user and check_password_hash(user.password, data['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return jsonify({"message": "Login successful!"}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({"status": "logged_in", "user_id": session['user_id']}), 200
    else:
        return jsonify({"status": "not_logged_in"}), 401

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    user = db.session.get(User, user_id)

    # Retrieve the last conversation
    last_conversation = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.created_at.desc()).first()

    # Generate an initial message from the chatbot
    initial_message = f"Hi {user.username}! Welcome back! 😊<br><br>"
    if last_conversation:
        # Analyze the last conversation and generate a summary
        summary = generate_conversation_summary(last_conversation.message, last_conversation.response)
        initial_message += f"Last time, we talked about {summary}.<br><br>How can I assist you today?"
    else:
        initial_message += "How can I assist you with your hotel reservation today?"

    return render_template('dashboard.html', username=user.username, initial_message=initial_message)

def generate_conversation_summary(user_message, bot_response):
    """
    Generate a conversational summary using the Llama API.
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3.2-11b-vision",  # Replace with your desired model
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Summarize the following conversation in a conversational tone, focusing on the key points discussed. Do not include phrases like 'Bot addresses' or 'User inquires.'"},
                {"role": "user", "content": f"User: {user_message}\nBot: {bot_response}"}
            ],
            "temperature": 0.5,
            "max_tokens": 1000
        }
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[ERROR] Failed to generate summary: {e}")
        return f"your last message: '{user_message}'"

@app.route('/chat', methods=['POST'])
def chat():
    try:
        if 'user_id' not in session:
            return jsonify({"error": "You must be logged in to chat"}), 403

        data = request.json
        user_input = preprocess_input(data.get("message"))  # Preprocess input

        # Retrieve user data
        user_id = session['user_id']
        user = db.session.get(User, user_id)

        # Detect intent and extract entities
        intent = detect_intent(user_input)  # Detect intent
        entities = extract_entities(user_input)  # Extract entities (e.g., check-in date, room type)

        # Store key reservation details in memory
        if intent in ["book_room", "modify_reservation"]:
            for key, value in entities.items():
                memory = Memory(user_id=user_id, key=key, value=value)
                db.session.add(memory)
            db.session.commit()

        # Retrieve stored memory
        memories = Memory.query.filter_by(user_id=user_id).all()
        memory_context = {memory.key: memory.value for memory in memories}

        # Retrieve conversation history for context
        conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.created_at.desc()).limit(5).all()
        conversation_history = [{"role": "user", "content": conv.message} for conv in conversations] + [{"role": "assistant", "content": conv.response} for conv in conversations]

        # Generate dynamic system message
        system_message = f"You are a hotel reservation assistant. The user's name is {user.username}."
        if memory_context.get("preferred_hotel_chain"):
            system_message += f" Their preferred hotel chain is {memory_context['preferred_hotel_chain']}."
        if memory_context.get("room_type"):
            system_message += f" They prefer {memory_context['room_type']} rooms."

        # Add context for specific intents
        if intent == "book_room":
            system_message += " The user wants to book a room. Provide options and confirm details."
        elif intent == "modify_reservation":
            system_message += " The user wants to modify their reservation. Ask for the new details."

        # Prepare messages for Llama API
        messages = [{"role": "system", "content": system_message}] + conversation_history + [{"role": "user", "content": user_input}]

        # Stream the AI response and save the conversation
        def generate():
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama3.2-11b-vision",  # Replace with your desired model
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 1000,
                "stream": True  # Enable streaming
            }
            full_response = ""  # Accumulate the full response
            with requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, stream=True) as response:
                response.raise_for_status()
                buffer = ""
                for chunk in response.iter_content(chunk_size=None):
                    if chunk:
                        buffer += chunk.decode("utf-8")
                        if buffer.endswith(('.', '!', '?', '\n')) or len(buffer) > 50:
                            # Extract the bot's response content from the streaming data
                            try:
                                data = json.loads(buffer.replace("data: ", "").strip())
                                if "choices" in data and len(data["choices"]) > 0:
                                    content = data["choices"][0]["delta"].get("content", "")
                                    if content:
                                        full_response += content
                            except json.JSONDecodeError:
                                pass
                            yield buffer
                            buffer = ""

            # Ensure database operations run within Flask's application context
            with app.app_context():  # Push a new application context for DB operations
                try:
                    conversation = Conversation(
                        user_id=user_id,
                        message=user_input,
                        response=full_response.strip(),  # Save only the bot's response content
                        created_at=datetime.utcnow()
                    )
                    db.session.add(conversation)
                    db.session.commit()
                    print(f"[DEBUG] Conversation saved: {conversation.id}")
                except Exception as e:
                    print(f"[ERROR] Failed to save conversation: {e}")
                    db.session.rollback()

        return Response(generate(), mimetype='text/plain')  # Use text/plain for streaming

    except Exception as e:
        print(f"[ERROR] Chat processing error: {e}")
        return jsonify({"error": "An error occurred while processing the chat."}), 500

@app.route('/conversation_history', methods=['GET'])
def conversation_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.created_at.desc()).all()

    conversation_history = []
    for conversation in conversations:
        conversation_history.append({
            "message": conversation.message,
            "response": conversation.response,
            "date": conversation.created_at.strftime("%Y-%m-%d %H:%M:%S")  # Format the date
        })

    return render_template('conversation_history.html', conversation_history=conversation_history)
# Add these routes to app.py

@app.route('/check_availability', methods=['POST'])
def check_availability():
    """
    Check room availability based on user input.
    """
    try:
        data = request.json
        check_in_date = datetime.strptime(data.get("check_in_date"), "%Y-%m-%d")
        check_out_date = datetime.strptime(data.get("check_out_date"), "%Y-%m-%d")

        # Query available rooms
        available_rooms = get_available_rooms(check_in_date, check_out_date)

        # Format response
        response = {
            "available_rooms": [
                {
                    "id": room.id,
                    "room_type": room.room_type,
                    "description": room.description,
                    "price_per_night": room.price_per_night,
                    "max_guests": room.max_guests,
                    "amenities": room.amenities
                }
                for room in available_rooms
            ]
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"[ERROR] Availability check failed: {e}")
        return jsonify({"error": "Failed to check availability."}), 500

@app.route('/book_room', methods=['POST'])
def book_room():
    """
    Book a room for the user.
    """
    try:
        if 'user_id' not in session:
            return jsonify({"error": "You must be logged in to book a room."}), 403

        data = request.json
        user_id = session['user_id']
        room_id = data.get("room_id")
        check_in_date = datetime.strptime(data.get("check_in_date"), "%Y-%m-%d")
        check_out_date = datetime.strptime(data.get("check_out_date"), "%Y-%m-%d")

        # Get room details
        room = Room.query.get(room_id)
        if not room or not room.availability:
            return jsonify({"error": "Room not available."}), 400

        # Calculate total price
        total_price = calculate_total_price(room, check_in_date, check_out_date)

        # Create reservation
        reservation = Reservation(
            user_id=user_id,
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            total_price=total_price
        )
        db.session.add(reservation)
        db.session.commit()

        return jsonify({"message": "Room booked successfully!", "reservation_id": reservation.id}), 200

    except Exception as e:
        print(f"[ERROR] Booking failed: {e}")
        return jsonify({"error": "Failed to book the room."}), 500

@app.route('/view_reservations', methods=['GET'])
def view_reservations():
    """
    View all reservations for the logged-in user.
    """
    if 'user_id' not in session:
        return jsonify({"error": "You must be logged in to view reservations."}), 403

    user_id = session['user_id']
    reservations = Reservation.query.filter_by(user_id=user_id).all()

    response = {
        "reservations": [
            {
                "id": reservation.id,
                "room_type": reservation.room.room_type,
                "check_in_date": reservation.check_in_date.strftime("%Y-%m-%d"),
                "check_out_date": reservation.check_out_date.strftime("%Y-%m-%d"),
                "total_price": reservation.total_price,
                "status": reservation.status
            }
            for reservation in reservations
        ]
    }

    return jsonify(response), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)