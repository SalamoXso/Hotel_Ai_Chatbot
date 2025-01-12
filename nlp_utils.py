import re
from symspellpy import SymSpell
import os
from models import Room  # Import the Room model
from datetime import datetime

# Suppress TensorFlow warnings (if TensorFlow is still used elsewhere)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Initialize SymSpell for spelling correction
sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
sym_spell.load_dictionary("frequency_dictionary_en_82_765.txt", term_index=0, count_index=1)

def get_available_rooms(check_in_date, check_out_date):
    """
    Query the database for available rooms between the given dates.
    """
    # Convert string dates to datetime objects if necessary
    if isinstance(check_in_date, str):
        check_in_date = datetime.strptime(check_in_date, "%Y-%m-%d")
    if isinstance(check_out_date, str):
        check_out_date = datetime.strptime(check_out_date, "%Y-%m-%d")

    # Query rooms that are available and not booked during the specified dates
    available_rooms = Room.query.filter(
        Room.availability == True  # Only available rooms
    ).all()

    return available_rooms

def calculate_total_price(room, check_in_date, check_out_date):
    """
    Calculate the total price for a room based on the number of nights.
    """
    # Convert string dates to datetime objects if necessary
    if isinstance(check_in_date, str):
        check_in_date = datetime.strptime(check_in_date, "%Y-%m-%d")
    if isinstance(check_out_date, str):
        check_out_date = datetime.strptime(check_out_date, "%Y-%m-%d")

    # Calculate the number of nights
    nights = (check_out_date - check_in_date).days

    # Calculate the total price
    total_price = room.price_per_night * nights

    return total_price

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    text = " ".join(text.split())
    return text

def correct_spelling(text):
    suggestions = sym_spell.lookup_compound(text, max_edit_distance=2)
    return suggestions[0].term

def preprocess_input(user_input):
    cleaned_text = clean_text(user_input)
    corrected_text = correct_spelling(cleaned_text)
    return corrected_text

# Updated sentiment analysis (optional for hotel reservations)
def analyze_sentiment(text):
    if "sad" in text or "disappointed" in text:
        return "Negative"
    elif "happy" in text or "excited" in text:
        return "Positive"
    else:
        return "Neutral"

# Updated intent detection for hotel reservations
def detect_intent(text):
    if "book" in text or "reserve" in text:
        return "book_room"
    elif "cancel" in text:
        return "cancel_reservation"
    elif "modify" in text or "change" in text:
        return "modify_reservation"
    elif "availability" in text or "check" in text:
        return "check_availability"
    else:
        return "general_inquiry"

# Updated entity extraction for hotel reservations
def extract_entities(text):
    entities = {}
    # Extract dates (e.g., "check-in on 2023-10-15")
    date_pattern = r"(\d{4}-\d{2}-\d{2})"
    dates = re.findall(date_pattern, text)
    if dates:
        entities["check_in_date"] = dates[0]
        if len(dates) > 1:
            entities["check_out_date"] = dates[1]
    
    # Extract room type (e.g., "suite", "double room")
    room_types = ["single", "double", "suite", "deluxe"]
    for room_type in room_types:
        if room_type in text:
            entities["room_type"] = room_type
            break
    
    # Extract location (e.g., "New York")
    location_pattern = r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b"
    locations = re.findall(location_pattern, text)
    if locations:
        entities["location"] = locations[0]
    
    return entities

# Example usage
if __name__ == "__main__":
    user_input = "I want to book a suite in New York from 2023-10-15 to 2023-10-20."
    
    # Preprocess user input
    preprocessed_text = preprocess_input(user_input)
    
    # Get sentiment
    sentiment = analyze_sentiment(preprocessed_text)
    print(f"Sentiment: {sentiment}")
    
    # Get intent
    intent = detect_intent(preprocessed_text)
    print(f"Intent: {intent}")
    
    # Extract entities
    entities = extract_entities(preprocessed_text)
    print(f"Entities: {entities}")


# Add this to nlp_utils.py
def get_available_rooms(check_in_date, check_out_date):
    """
    Query the database for available rooms between the given dates.
    """
    available_rooms = Room.query.filter_by(availability=True).all()
    return available_rooms

def calculate_total_price(room, check_in_date, check_out_date):
    """
    Calculate the total price for a room based on the number of nights.
    """
    nights = (check_out_date - check_in_date).days
    return room.price_per_night * nights

def suggest_rooms(user_input):
    """
    Suggest rooms based on user input (e.g., budget, preferences).
    """
    # Extract preferences from user input
    budget = re.search(r"\$(\d+)", user_input)
    budget = float(budget.group(1)) if budget else None

    # Query rooms within the budget
    if budget:
        rooms = Room.query.filter(Room.price_per_night <= budget).all()
    else:
        rooms = Room.query.all()

    return rooms    