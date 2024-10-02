import sqlite3
from dotenv import load_dotenv
import os
import google.generativeai as genai
from IPython.display import Image
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from config import *
from database import *
from models import *
from flask import Flask
from routes import api_blueprint  # Import the blueprint

# Load the API key from the .env file
load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Initialization of models
sentiment_model = SentimentModel(model_name="gemini-1.5-flash", generation_config=generation_config, system_instruction=sentiment_sys_instruct)
socratic_model = SocraticModel(model_name="gemini-1.5-pro", generation_config=generation_config, system_instruction=socratic_sys_instruct)
feynman_model = FeynmanModel(model_name="gemini-1.5-pro", generation_config=generation_config, system_instruction=feynman_sys_instruct)
custom_model = CustomModel(model_name="gemini-1.5-pro", generation_config=generation_config, system_instruction=cusotm_sys_instruct)

# Create web application instance
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.register_blueprint(api_blueprint)  # Register the blueprint

# Initialize the database
init_db()

# Initial model settings
current_model = socratic_model
socratic_score = 0  # Initialize score
feynman_score = 0  # Initialize score

@app.route('/chat', methods=['POST'])
def chat():
    global current_model, socratic_score, feynman_score
    
    user_prompt = request.json.get("prompt")  # Assuming JSON input
    # Sentiment analysis result
    result = sentiment_model.get_result_sentiment(user_prompt)

    # Response Generation and saving chat in history.
    ai_response = current_model.get_response(user_prompt)
    save_chat_history("socratic", user_prompt, ai_response)  # Save chat history with category.

    # Update score and switch the model
    if current_model == socratic_model:
        socratic_score = socratic_model.update_score(result, socratic_score, "socratic")
        if socratic_score < -2:
            current_model = feynman_model
            socratic_score = 0  # Reset score for next model

    elif current_model == feynman_model:
        feynman_score = feynman_model.update_score(result, feynman_score, "feynman")
        if feynman_score < -2:
            current_model = socratic_model
            feynman_score = 0  # Reset score for next model

    return jsonify({"response": ai_response})

# Start the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
