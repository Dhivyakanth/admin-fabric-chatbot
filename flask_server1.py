from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import uuid
import os
import webbrowser
from datetime import datetime
from livedata_integration import generate_response, fetch_sales_data_from_api
from config import Config
from notification import get_upcoming_festivals_data, get_festival_recommendations
import traceback

app = Flask(__name__)

# Configure CORS with specific origins
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

# In-memory storage for chat sessions (in production, use a database)
chat_sessions = {}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        config_info = Config.get_config_info()
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "config": config_info
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/chat/new', methods=['POST'])
def create_new_chat():
    """Create a new chat session"""
    try:
        chat_id = str(uuid.uuid4())
        chat_sessions[chat_id] = {
            "id": chat_id,
            "title": "New Chat",
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "chat_id": chat_id,
            "chat": chat_sessions[chat_id]
        }), 201
        
    except Exception as e:
        print(f"Error creating new chat: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chat/<chat_id>/message', methods=['POST'])
def send_message(chat_id):
    """Send a message to a specific chat"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                "success": False,
                "error": "Message cannot be empty"
            }), 400
        
        if chat_id not in chat_sessions:
            return jsonify({
                "success": False,
                "error": "Chat session not found"
            }), 404
        
        # Add user message to chat history
        user_msg = {
            "id": str(uuid.uuid4()),
            "content": user_message,
            "role": "user",
            "timestamp": datetime.now().isoformat()
        }
        
        chat_sessions[chat_id]["messages"].append(user_msg)
        
        # Prepare chat history for the AI
        chat_history = []
        for msg in chat_sessions[chat_id]["messages"]:
            if msg["role"] == "user":
                chat_history.append({
                    "role": "user",
                    "parts": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                chat_history.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })
        
        # Generate AI response using your existing function
        ai_response = generate_response(user_message, chat_history)
        
        # Add AI response to chat history
        ai_msg = {
            "id": str(uuid.uuid4()),
            "content": ai_response,
            "role": "assistant",
            "timestamp": datetime.now().isoformat()
        }
        
        chat_sessions[chat_id]["messages"].append(ai_msg)
        
        # Update chat title if this is the first message
        if len(chat_sessions[chat_id]["messages"]) <= 2:
            chat_sessions[chat_id]["title"] = user_message[:30] + ("..." if len(user_message) > 30 else "")
        
        chat_sessions[chat_id]["last_updated"] = datetime.now().isoformat()
        
        return jsonify({
            "success": True,
            "user_message": user_msg,
            "ai_response": ai_msg,
            "chat": chat_sessions[chat_id]
        }), 200
        
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chat/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    """Get a specific chat session"""
    try:
        if chat_id not in chat_sessions:
            return jsonify({
                "success": False,
                "error": "Chat session not found"
            }), 404
        
        return jsonify({
            "success": True,
            "chat": chat_sessions[chat_id]
        }), 200
        
    except Exception as e:
        print(f"Error getting chat: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chats', methods=['GET'])
def get_all_chats():
    """Get all chat sessions"""
    try:
        chats = list(chat_sessions.values())
        # Sort by last_updated (newest first)
        chats.sort(key=lambda x: x["last_updated"], reverse=True)
        
        return jsonify({
            "success": True,
            "chats": chats
        }), 200
        
    except Exception as e:
        print(f"Error getting chats: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chat/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    """Delete a specific chat session"""
    try:
        if chat_id not in chat_sessions:
            return jsonify({
                "success": False,
                "error": "Chat session not found"
            }), 404
        
        del chat_sessions[chat_id]
        
        return jsonify({
            "success": True,
            "message": "Chat deleted successfully"
        }), 200
        
    except Exception as e:
        print(f"Error deleting chat: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chats/clear', methods=['DELETE'])
def clear_all_chats():
    """Clear all chat sessions - useful for testing"""
    try:
        global chat_sessions
        chat_sessions.clear()
        
        return jsonify({
            "success": True,
            "message": "All chat sessions cleared successfully"
        }), 200
        
    except Exception as e:
        print(f"Error clearing all chats: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/sales/data', methods=['GET'])
def get_sales_data():
    """Get sales data for frontend display"""
    try:
        sales_data = fetch_sales_data_from_api()
        
        return jsonify({
            "success": True,
            "data": sales_data,
            "count": len(sales_data) if sales_data else 0
        }), 200
        
    except Exception as e:
        print(f"Error fetching sales data: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/festivals/upcoming', methods=['GET'])
def get_upcoming_festivals():
    """Get upcoming festivals within specified days"""
    try:
        # Get query parameter for days ahead (default: 10)
        days_ahead = request.args.get('days', 10, type=int)
        
        # Get upcoming festivals from notification module
        upcoming_festivals = get_upcoming_festivals_data(days_ahead)
        
        # Get sales data for recommendations
        sales_data = fetch_sales_data_from_api()
        
        # Add recommendations to each festival
        for festival in upcoming_festivals:
            festival["recommendations"] = get_festival_recommendations(
                festival["name"], 
                festival["category"], 
                sales_data
            )
        
        return jsonify({
            "success": True,
            "upcoming_festivals": upcoming_festivals,
            "count": len(upcoming_festivals)
        }), 200
        
    except Exception as e:
        print(f"Error fetching upcoming festivals: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/send-mail', methods=['POST'])
def send_mail():
    """Open the email HTML file in the default web browser"""
    try:
        # Get the absolute path to the email directory
        email_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'email', 'index.html'))
        
        # Check if the file exists
        if not os.path.exists(email_file_path):
            return jsonify({
                "success": False,
                "error": f"Email HTML file not found at: {email_file_path}"
            }), 404
        
        # Convert to file:// URL for proper browser opening
        file_url = f"file:///{email_file_path.replace(os.sep, '/')}"
        
        # Open the email HTML file in the default web browser
        webbrowser.open(file_url)
        
        return jsonify({
            "success": True,
            "message": "Email form opened in browser successfully",
            "file_path": email_file_path
        }), 200
        
    except Exception as e:
        print(f"Error preparing email file URL: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    # Validate configuration before starting
    if not Config.validate_api_key():
        print("❌ Cannot start server without proper configuration!")
        exit(1)
    
    print("🚀 Starting Dress Sales Monitoring Chatbot API Server...")
    print(f"📊 Sales API: {Config.SALES_API_URL}")
    print(f"🌐 Server: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    print(f"🔄 CORS Origins: {Config.CORS_ORIGINS}")
    print("\n💡 Make sure your .env file contains GEMINI_API_KEY")
    print("💡 Test the API at: http://127.0.0.1:8000/api/health")
    
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
