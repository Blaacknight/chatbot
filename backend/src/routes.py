# routes.py
from flask import Blueprint, request, jsonify
from models import *
from abc import ABC, abstractmethod
from config import *
from dotenv import load_dotenv
import sqlite3
import os
import google.generativeai as genai
from IPython.display import Image
import requests
from flask_cors import CORS
from datetime import datetime, timedelta
from config import *
from database import *


# Load environment variables
load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Creating web application instance
api_blueprint = Blueprint("api", __name__)

# Initialization of models
sentiment_model = SentimentModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=sentiment_sys_instruct,
)
socratic_model = SocraticModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction=socratic_sys_instruct,
)
feynman_model = FeynmanModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction=feynman_sys_instruct,
)
custom_model = CustomModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction=cusotm_sys_instruct,
)

# Initialize scores
socratic_score = 0
feynman_score = 0
current_model = socratic_model  # Declare the current model globally

@api_blueprint.route("/api/get_user_input", methods=["POST"])
def get_user_input():
    global current_model, socratic_score, feynman_score  # Declare global for score modification

    data = request.get_json()  # Extract JSON data from the request
    user_prompt = data.get("user_input", "")  # Get the user input

    # Sentiment analysis result
    result = sentiment_model.get_result_sentiment(user_prompt)

    # Response generation and saving chat in history
    ai_response = current_model.get_response(user_prompt)
    save_chat_history("socratic", user_prompt, ai_response)

    # Update score and switch the model if necessary
    if current_model == socratic_model:
        socratic_score = socratic_model.update_score(result, socratic_score, "socratic")
        if socratic_score < -2:
            current_model = feynman_model
            socratic_score = 0  # Reset score for the next model

    elif current_model == feynman_model:
        feynman_score = feynman_model.update_score(result, feynman_score, "feynman")
        if feynman_score < -2:
            current_model = socratic_model
            feynman_score = 0  # Reset score for the next model

    # Get the class name of the current model
    current_model_name = current_model.__class__.__name__

    # Prepare response data
    response_data = {
        "received_input": user_prompt,
        "status": "success",
        "model": current_model_name,
        "ai_response": ai_response,
    }
    return jsonify(response_data), 200

@api_blueprint.route("/api/chat_history", methods=["GET"])
def get_chat_history():
    # Extract the category from the query parameters, defaulting to 'today' if not provided
    category = request.args.get("category", "today")

    # Retrieve chat history based on the requested category
    chat_history = get_chat_by_category(category)

    # If there's no history found, return an appropriate message
    if not chat_history:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"No chats found for category: {category}",
                }
            ),
            404,
        )

    # Format the retrieved history into a list of dictionaries for JSON response
    chat_data = [
        {
            "model": chat[0],
            "user_message": chat[1],
            "ai_response": chat[2],
            "timestamp": chat[3],
        }
        for chat in chat_history
    ]

    # Return the chat history in JSON format
    return jsonify({"status": "success", "chat_history": chat_data}), 200
