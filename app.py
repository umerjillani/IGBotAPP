from flask import Flask, request, jsonify, render_template
import json
from transformers import pipeline
import requests
import sqlite3
from dotenv import load_dotenv,set_key
from openai import OpenAI
import re
import logging
import time
import os
import threading


app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()
env_path = os.path.join(os.path.dirname(__file__), '.env')

# Initialize business ID verification
business_id_verified = False
verification_lock = threading.Lock()

# Instagram & OpenAI Config (Replace with your credentials)
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
INSTAGRAM_API_URL = "https://graph.instagram.com/v22.0"
INSTAGRAM_BUSINESS_ID = os.getenv("INSTAGRAM_BUSINESS_ID", "").strip()  # Get without quotes
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Cache for processed comments
processed_comments = set()

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Load pre-trained models
intent_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# Define intents and their characteristics
INTENT_CONFIG = {
    "simple_inquiry": {
        "max_tokens": 80,
        "cta": "Feel free to ask more details!"
    },
    "business_advice": {
        "max_tokens": 150,
        "cta": "Want me to elaborate on any specific strategy?"
    },
    "technical_help": {
        "max_tokens": 120,
        "cta": "Need more technical details? Just ask!"
    },
    "motivational": {
        "max_tokens": 100,
        "cta": "Ready to take the next step?"
    }
}

# Initialize SQLite database
conn = sqlite3.connect("chat_history.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        user_id TEXT,
        message_type TEXT,
        message_text TEXT,
        response_text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# ========================
# IMPROVED CORE FUNCTIONS
# ========================

def verify_and_update_business_id(candidate_id):
    global business_id_verified, INSTAGRAM_BUSINESS_ID
    
    with verification_lock:
        if business_id_verified:
            return

        # Check if candidate ID matches current value
        if candidate_id != INSTAGRAM_BUSINESS_ID:
            logger.info(f"Updating business ID from {INSTAGRAM_BUSINESS_ID} to {candidate_id}")
            
            # Update .env file without quotes
            set_key(env_path, "INSTAGRAM_BUSINESS_ID", candidate_id, quote_mode='never')
            
            # Update runtime variable
            INSTAGRAM_BUSINESS_ID = candidate_id
            load_dotenv(override=True)

        business_id_verified = True

def get_chat_history(user_id):
    """Retrieve the last 5 interactions for a user."""
    with sqlite3.connect("chat_history.db") as conn:
        try:
            return conn.execute("""
                SELECT message_text, response_text FROM interactions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 5
            """, (user_id,)).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return []

def store_interaction(user_id, message_type, message_text, response_text):
    """Store user interactions in the database."""
    with sqlite3.connect("chat_history.db") as conn:
        try:
            conn.execute("""
                INSERT INTO interactions (user_id, message_type, message_text, response_text)
                VALUES (?, ?, ?, ?)
            """, (user_id, message_type, message_text, response_text))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
                        
def analyze_conversation(text):
    """Enhanced intent and complexity analysis"""
    try:
        # First classify intent
        intent_result = intent_classifier(
            text,
            candidate_labels=list(INTENT_CONFIG.keys()),
            hypothesis_template="This message is about {}."
        )
        
        # Then analyze sentiment
        sentiment_result = sentiment_analyzer(text)[0]
        
        # Determine complexity
        word_count = len(text.split())
        complexity = "simple" if word_count <= 8 else "detailed"
        
        return {
            "primary_intent": intent_result["labels"][0],
            "confidence": intent_result["scores"][0],
            "sentiment": sentiment_result["label"],
            "sentiment_score": sentiment_result["score"],
            "complexity": complexity
        }
    except Exception as e:
        logger.error(f"Error analyzing conversation: {e}")
        return {
            "primary_intent": "simple_inquiry",
            "confidence": 1.0,
            "sentiment": "POSITIVE",
            "sentiment_score": 1.0,
            "complexity": "simple"
        }

def generate_response(user_id, user_message, is_comment=False, is_dm=False):
    """Intent-aware response generation"""
    try:
        # Analyze the message
        analysis = analyze_conversation(user_message)
        intent_config = INTENT_CONFIG[analysis["primary_intent"]]
        chat_history = get_chat_history(user_id)

        # Build dynamic prompt
        prompt = f"""You're GrowthGenius, an AI business advisor. Respond to this {analysis['complexity']} query:
        
        User Message: {user_message}
        
        Context:
        - Intent: {analysis['primary_intent']} ({analysis['confidence']:.0%} confidence)
        - Sentiment: {analysis['sentiment']} ({analysis['sentiment_score']:.0%} intensity)
        - History: {chat_history[-2:] if chat_history else 'No previous interaction'}
        
        Response Guidelines:
        - Length: {'Brief (1-2 sentences)' if analysis['complexity'] == 'simple' else 'Detailed'}
        - Tone: {'Encouraging' if analysis['sentiment'] == 'POSITIVE' else 'Supportive'}
        - Focus: {intent_config['cta']}
        """

        # Generate response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7 if analysis['complexity'] == 'detailed' else 0.3,
            max_tokens=intent_config['max_tokens']
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = re.sub(r"\b(GrowthGenius|Bot):?", "", response_text).strip()

        # Store interaction
        store_interaction(user_id, "comment" if is_comment else "dm", user_message, response_text)

        return response_text

    except Exception as e:
        logger.error(f"Response generation error: {e}")
        return "Let's continue this conversation! How can I assist you further?"

# ========================
# INSTAGRAM API HANDLERS
# ========================

def get_instagram_username(user_id):
    """Fetch Instagram username from user ID."""
    try:
        url = f"{INSTAGRAM_API_URL}/{user_id}"
        params = {"fields": "username", "access_token": ACCESS_TOKEN}
        response = requests.get(url, params=params).json()
        return response.get("username", user_id)
    except Exception as e:
        logger.error(f"Error fetching username: {e}")
        return user_id

def send_instagram_message(recipient_id, text):
    """Send a message via Instagram API."""
    try:
        if recipient_id == INSTAGRAM_BUSINESS_ID:
            logger.info("Ignoring DM to bot's own ID.")
            return

        url = f"{INSTAGRAM_API_URL}/me/messages"
        headers = {"Content-Type": "application/json"}
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        response = requests.post(url, headers=headers, json=payload, params={"access_token": ACCESS_TOKEN})
        response_json = response.json()

        if "error" in response_json:
            logger.error(f"API Error: {response_json['error']['message']}")
        else:
            logger.info(f"Successfully sent message to user {recipient_id}.")

    except Exception as e:
        logger.error(f"Error sending message: {e}")

def reply_to_comment(comment_id, text):
    """Reply to a comment on a post."""
    try:
        url = f"{INSTAGRAM_API_URL}/{comment_id}/replies"
        headers = {"Content-Type": "application/json"}
        payload = {"message": text}
        response = requests.post(url, headers=headers, json=payload, params={"access_token": ACCESS_TOKEN})
        response_json = response.json()

        if "error" in response_json:
            logger.error(f"API Error: {response_json['error']['message']}")
        else:
            logger.info(f"Successfully replied to comment {comment_id}.")

    except Exception as e:
        logger.error(f"Error replying to comment: {e}")

# ========================
# WEBHOOK HANDLERS
# ========================

@app.route('/')
def home():
    return "<p>Instagram AI Bot is Running</p>"

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        verify_token = os.getenv("VERIFY_TOKEN")
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == verify_token:
                logger.info("Webhook verified successfully.")
                return challenge, 200
            else:
                logger.warning("Webhook verification failed: Token mismatch.")
                return 'Verification token mismatch', 403
        return 'Missing parameters', 400
    
    elif request.method == 'POST':
        data = request.get_json()
        if data:
            logger.info("Received new webhook event.")
             # Log raw webhook data for debugging
            logger.info(f"Raw Webhook Data: {json.dumps(data, indent=2)}")  # 👈 ADD THIS LINE
            handle_event(data)
            return jsonify({'status': 'success'}), 200
        logger.warning("No data received in webhook.")
        return 'No data received', 400

# Add this function to update .env file
def update_business_id(new_id):
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # Read current .env content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update INSTAGRAM_BUSINESS_ID if exists
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('INSTAGRAM_BUSINESS_ID='):
            current_id = line.split('=')[1].strip()
            if current_id != new_id:
                lines[i] = f'INSTAGRAM_BUSINESS_ID={new_id}\n'
                updated = True
            break
    
    # Add if not exists
    if not updated and not any(line.startswith('INSTAGRAM_BUSINESS_ID=') for line in lines):
        lines.append(f'INSTAGRAM_BUSINESS_ID={new_id}\n')
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    # Reload environment
    load_dotenv(override=True)

def handle_event(data):
    """Handle incoming Instagram events with ID verification"""
    global business_id_verified
    
    if "entry" not in data:
        return

    for entry in data["entry"]:
        # ============================================
        # UPDATED BUSINESS ID VERIFICATION LOGIC
        # ============================================
        if not business_id_verified:
            # Check for bot's echo messages to identify its own ID
            if "messaging" in entry:
                for msg in entry["messaging"]:
                    if msg.get("message", {}).get("is_echo", False):
                        # CORRECTED: Get sender ID instead of recipient
                        bot_id = msg["sender"]["id"]
                        logger.info(f"Identified bot ID from echo message: {bot_id}")
                        verify_and_update_business_id(bot_id)
                        business_id_verified = True
                        break
        
        # ============================================
        # MAIN MESSAGE PROCESSING
        # ============================================
        try:
            # Process messages
            if "messaging" in entry:
                for message_data in entry["messaging"]:
                    process_message(message_data)
            
            # Process comments
            if "changes" in entry:
                for change in entry["changes"]:
                    if change["field"] == "comments":
                        process_comment(change["value"])
                        
        except Exception as e:
            logger.error(f"Error processing entry: {e}")
                                    
def process_message(message_data):
    """Process incoming direct messages."""
    try:
        sender_id = message_data["sender"]["id"]
        recipient_id = message_data["recipient"]["id"]
        
        # Log the sender and recipient IDs for debugging
        logger.info(f"Processing message from sender: {sender_id}, recipient: {recipient_id}")
        
        # Use verified business ID for self-check
        if sender_id == INSTAGRAM_BUSINESS_ID:
            logger.info(f"Ignoring bot's own message from {sender_id}")
            return

        # Ensure the message is intended for the bot
        if recipient_id != INSTAGRAM_BUSINESS_ID:
            logger.info(f"Ignoring message not intended for the bot. Recipient ID: {recipient_id}")
            return

        # Process the message if it contains text
        if "message" in message_data:
            message_text = message_data["message"].get("text")
            if message_text:
                logger.info(f"Processing message text: {message_text}")
                response_text = generate_response(sender_id, message_text, is_dm=True)
                send_instagram_message(sender_id, response_text)
            else:
                logger.info("Ignoring non-text message (e.g., attachment, like, etc.)")
        else:
            logger.info("Ignoring non-message event (e.g., read receipt, delivery, etc.)")

    except KeyError as e:
        logger.error(f"Message processing error: {e}")
        
def process_comment(comment_data):
    """Process incoming comments."""
    try:
        comment_id = comment_data["id"]
        user_id = comment_data["from"]["id"]
        username = get_instagram_username(user_id)
        comment_text = comment_data["text"]

        if user_id == INSTAGRAM_BUSINESS_ID:
            logger.info(f"Ignoring bot's own comment from user {username}.")
            return

        if comment_id in processed_comments:
            logger.info(f"Comment {comment_id} from user {username} already processed. Skipping...")
            return

        processed_comments.add(comment_id)

        # Generate concise response for public comment
        public_response = generate_response(user_id, comment_text, is_comment=True)
        reply_to_comment(comment_id, public_response)

        # Send follow-up DM
        dm_response = generate_response(user_id, f"Thanks for your comment! {comment_text}", is_dm=True)
        send_instagram_message(user_id, dm_response)

        logger.info(f"Successfully processed comment event from user {username}.")

    except KeyError as e:
        logger.error(f"Error processing comment: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)