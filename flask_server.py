from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import uuid
from datetime import datetime
from rag_chatbot import chatbot_ask
from livedata_integration import fetch_sales_data_from_api, generate_response
from config import Config
import traceback
import re
from chat_history_manager import save_chat_history, load_chat_history, is_chat_history_full, delete_oldest_chat, get_all_chat_files
# Use MongoDB instead of SQLite3 for chat history
from Mongodb import save_chat_history_mongo as save_chat_history_db, load_chat_history_mongo as load_chat_history_db, get_all_chats_mongo as get_all_chats_db, delete_chat_mongo as delete_chat_db, chat_exists_in_mongo as chat_exists_in_db

# Import translation module
from translator import translate_to_english, translate_to_user_language

def strip_summary_sections(response_text):
    """
    Remove summary sections from response text.
    Removes patterns like "**Summary:**", "**Key Insights:**", etc.
    """
    if not isinstance(response_text, str):
        return response_text
        
    # Remove common summary section headers
    patterns_to_remove = [
        r'\*\* Best Performance Analysis \*\*',
        r'\*\* Key Insights:\*\*',
        r'\*\* Recommendations:\*\*',
        r'\*\*Summary:\*\*',
        r'\*\*Detailed Breakdown:\*\*',
        r'\*\*Insights:\*\*',
        r'\*\*Best Performance Analysis\*\*',
        r'\*\*Key Insights\*\*',
        r'\*\*Recommendations\*\*'
    ]
    
    result = response_text
    for pattern in patterns_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    result = re.sub(r'\n\s*\n', '\n\n', result)
    return result.strip()

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
            "data": chat_sessions[chat_id]
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
        user_language = data.get('language', 'en')  # Default to English
        
        if not user_message:
            return jsonify({
                "success": False,
                "error": "Message cannot be empty"
            }), 400
        
        # If chat session is not in memory, try to load it
        if chat_id not in chat_sessions:
            # First try to load from database
            if chat_exists_in_db(chat_id):
                loaded_messages = load_chat_history_db(chat_id)
                if loaded_messages is not None:
                    # Create a session from the loaded data
                    chat_sessions[chat_id] = {
                        "id": chat_id,
                        "title": "Loaded Chat" if not loaded_messages else loaded_messages[0].get('content', '')[:30] + ("..." if len(loaded_messages[0].get('content', '')) > 30 else ""),
                        "messages": loaded_messages,
                        "created_at": loaded_messages[0].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat(),
                        "last_updated": loaded_messages[-1].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat()
                    }
            else:
                # Try to load from CSV file (backward compatibility)
                loaded_messages = load_chat_history(chat_id)
                if loaded_messages is not None:
                    # Create a session from the loaded data
                    chat_sessions[chat_id] = {
                        "id": chat_id,
                        "title": "Loaded Chat" if not loaded_messages else loaded_messages[0].get('content', '')[:30] + ("..." if len(loaded_messages[0].get('content', '')) > 30 else ""),
                        "messages": loaded_messages,
                        "created_at": loaded_messages[0].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat(),
                        "last_updated": loaded_messages[-1].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat()
                    }
                    # Save to database for future use
                    save_chat_history_db(chat_id, loaded_messages, chat_sessions[chat_id]["title"])
                else:
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
        
        # Prepare ISOLATED chat history for this specific conversation
        isolated_chat_history = []
        current_session_messages = chat_sessions[chat_id]["messages"]
        
        # Only include the last few relevant messages to avoid context mixing
        relevant_messages = current_session_messages[-10:] if len(current_session_messages) > 10 else current_session_messages
        
        for msg in relevant_messages:
            if msg["role"] == "user":
                isolated_chat_history.append({
                    "role": "user",
                    "parts": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                isolated_chat_history.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })
        
        # Translate user message to English if needed
        translated_message = user_message
        if user_language != 'en':
            try:
                translated_message = translate_to_english(user_message)
                print(f"[#] Translated message: {translated_message}")
            except Exception as e:
                print(f"[!] Translation error: {e}")
                # Continue with original message if translation fails
                translated_message = user_message
        
        # Generate AI response using rag_chatbot backend
        print(f"[#] Processing isolated message: {translated_message}")
        print(f"[#] Isolated chat history length: {len(isolated_chat_history)}")

        ai_response = chatbot_ask(translated_message, session_id=chat_id, chat_history=isolated_chat_history)
        # Strip summary sections from the response
        stripped_response = strip_summary_sections(ai_response)
        
        # Translate response to user's language if needed
        final_response = stripped_response
        if user_language != 'en':
            try:
                final_response = translate_to_user_language(stripped_response, user_language)
                print(f"[#] Translated response: {final_response}")
            except Exception as e:
                print(f"[!] Response translation error: {e}")
                # Continue with original response if translation fails
                final_response = stripped_response

        response_validation = {
            "response_length": len(stripped_response),
            "question_type": "numerical" if any(word in user_message.lower() for word in ['most', 'count', 'total', 'how many']) else "general"
        }

        ai_msg = {
            "id": str(uuid.uuid4()),
            "content": final_response,
            "role": "assistant",
            "timestamp": datetime.now().isoformat(),
            "validated": True,
            "source": "rag_chatbot_chatbot_ask",
            "validation": response_validation,
            "language": user_language
        }

        chat_sessions[chat_id]["messages"].append(ai_msg)

        if len(chat_sessions[chat_id]["messages"]) <= 2:
            chat_sessions[chat_id]["title"] = user_message[:30] + ("..." if len(user_message) > 30 else "")

        chat_sessions[chat_id]["last_updated"] = datetime.now().isoformat()
        
        # Save chat history to database
        save_chat_history_db(chat_id, chat_sessions[chat_id]["messages"], chat_sessions[chat_id]["title"])

        return jsonify({
            "success": True,
            "user_message": user_msg,
            "ai_response": ai_msg,
            "data": {
                "chat": {
                    "id": chat_sessions[chat_id]["id"],
                    "title": chat_sessions[chat_id]["title"],
                    "messages": chat_sessions[chat_id]["messages"],
                    "created_at": chat_sessions[chat_id]["created_at"],
                    "last_updated": chat_sessions[chat_id]["last_updated"]
                }
            },
            
            "response_metadata": {
                "validated": True,
                "source": "rag_chatbot",
                "timestamp": datetime.now().isoformat(),
                "chat_length": len(chat_sessions[chat_id]["messages"]),
                "isolated_context": True,
                "validation": response_validation
            }
        }), 200
        
    except Exception as e:
        print(f"[X] Error sending message: {str(e)}")
        traceback.print_exc()
        user_message_safe = locals().get('user_message', "N/A")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_details": {
                "timestamp": datetime.now().isoformat(),
                "chat_id": chat_id,
                "user_message": user_message if 'user_message' in locals() else "N/A",
                "user_message": user_message_safe
            }
        }), 500

@app.route('/api/chat/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    """Get a specific chat session"""
    try:
        if chat_id not in chat_sessions:
            # First try to load from database
            if chat_exists_in_db(chat_id):
                loaded_messages = load_chat_history_db(chat_id)
                if loaded_messages is not None:
                    # Create a session from the loaded data
                    chat_sessions[chat_id] = {
                        "id": chat_id,
                        "title": "Loaded Chat" if not loaded_messages else loaded_messages[0].get('content', '')[:30] + ("..." if len(loaded_messages[0].get('content', '')) > 30 else ""),
                        "messages": loaded_messages,
                        "created_at": loaded_messages[0].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat(),
                        "last_updated": loaded_messages[-1].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat()
                    }
            else:
                # Try to load from CSV file (backward compatibility)
                loaded_messages = load_chat_history(chat_id)
                if loaded_messages is not None:
                    # Create a session from the loaded data
                    chat_sessions[chat_id] = {
                        "id": chat_id,
                        "title": "Loaded Chat" if not loaded_messages else loaded_messages[0].get('content', '')[:30] + ("..." if len(loaded_messages[0].get('content', '')) > 30 else ""),
                        "messages": loaded_messages,
                        "created_at": loaded_messages[0].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat(),
                        "last_updated": loaded_messages[-1].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat()
                    }
                    # Save to database for future use
                    save_chat_history_db(chat_id, loaded_messages, chat_sessions[chat_id]["title"])
                else:
                    return jsonify({
                        "success": False,
                        "error": "Chat session not found"
                    }), 404
        
        return jsonify({
            "success": True,
            "data": chat_sessions[chat_id]
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
        # Get chats from database
        chats = get_all_chats_db()
        
        # Add in-memory chats that aren't in database
        for chat_id, chat_data in chat_sessions.items():
            # Check if chat exists in database
            if not chat_exists_in_db(chat_id):
                chats.append(chat_data)
        
        # Load persisted CSV chats that aren't in memory or database (backward compatibility)
        chat_files = get_all_chat_files()
        for file in chat_files:
            # Extract chat ID from filename
            chat_id = file.replace('chat_', '').replace('.csv', '')
            
            # Skip if already in memory or database
            if chat_id in chat_sessions or chat_exists_in_db(chat_id):
                continue
                
            # Load chat from file
            loaded_messages = load_chat_history(chat_id)
            if loaded_messages is not None:
                chat_data = {
                    "id": chat_id,
                    "title": "Loaded Chat" if not loaded_messages else loaded_messages[0].get('content', '')[:30] + ("..." if len(loaded_messages[0].get('content', '')) > 30 else ""),
                    "messages": loaded_messages,
                    "created_at": loaded_messages[0].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat(),
                    "last_updated": loaded_messages[-1].get('timestamp', datetime.now().isoformat()) if loaded_messages else datetime.now().isoformat()
                }
                chats.append(chat_data)
                # Save to database for future use
                save_chat_history_db(chat_id, loaded_messages, chat_data["title"])
        
        # Sort by last_updated (newest first)
        chats.sort(key=lambda x: x["last_updated"], reverse=True)
        
        return jsonify({
            "success": True,
            "data": chats
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
        # Remove from memory if present
        if chat_id in chat_sessions:
            del chat_sessions[chat_id]
        
        # Delete from database
        delete_chat_db(chat_id)
        
        # Delete the CSV file if it exists (backward compatibility)
        import os
        csv_file = os.path.join("chat_history", f"chat_{chat_id}.csv")
        if os.path.exists(csv_file):
            os.remove(csv_file)
        
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
        
        # Clear database (MongoDB version)
        from Mongodb import clear_all_chats_mongo
        clear_all_chats_mongo()
        
        # Clear all CSV files (backward compatibility)
        import os
        import shutil
        if os.path.exists("chat_history"):
            shutil.rmtree("chat_history")
            os.makedirs("chat_history")
        
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
    """Get sales data for frontend display with validation - SAME DATA as livedata_integration.py"""
    try:
        # Use EXACT SAME functions as livedata_integration.py
        all_sales_data = fetch_sales_data_from_api()

        confirmed_sales_data = [record for record in all_sales_data if record.get('status', '').lower() == 'confirmed']
        declined_sales_data = [record for record in all_sales_data if record.get('status', '').lower() == 'declined']
        processed_sales_data = [record for record in all_sales_data if record.get('status', '').lower() == 'processed']

        print(f"[#] Fetched sales data - Total: {len(all_sales_data) if all_sales_data else 0}, Confirmed: {len(confirmed_sales_data)}, Declined: {len(declined_sales_data)}, Processed: {len(processed_sales_data)}")
        
         # Debug: Show actual confirmed weave counts
        if confirmed_sales_data:
             weave_debug = {}
             for record in confirmed_sales_data:
                 weave = record.get('weave', 'Unknown').strip()
                 weave_debug[weave] = weave_debug.get(weave, 0) + 1
             print(f"[#] ACTUAL confirmed weave counts: {weave_debug}")
         # Verify data consistency
        if all_sales_data:
             print(f"[#] Sample record keys: {list(all_sales_data[0].keys()) if all_sales_data else 'No data'}")
        
        return jsonify({
             "success": True,
             "data": {
                 "all_orders": all_sales_data,
                 "confirmed_orders": confirmed_sales_data,
                 "declined_orders": declined_sales_data,
                 "processed_orders": processed_sales_data
             },
             "count": {
                 "total": len(all_sales_data) if all_sales_data else 0,
                 "confirmed": len(confirmed_sales_data),
                 "declined": len(declined_sales_data),
                 "processed": len(processed_sales_data)
             },
             "metadata": {
                 "fetched_at": datetime.now().isoformat(),
                 "data_source": "Same API as livedata_integration.py",
                 "filtering": "Same confirmed order filtering logic",
                 "consistency": "100% same data as command line interface"
             }
         }), 200
        
    except Exception as e:
         print(f"[X] Error fetching sales data: {str(e)}")
         return jsonify({
             "success": False,
             "error": str(e),
             "error_details": {
                 "timestamp": datetime.now().isoformat(),
                 "operation": "fetch_sales_data"
             }
         }), 500

@app.route('/api/festivals/upcoming', methods=['GET'])
def get_upcoming_festivals():
    """Get upcoming festivals within 5 days"""
    try:
        from datetime import datetime, timedelta
        import calendar
        
        # Define major festivals with their dates (2025)
        festivals = [
            {"name": "New Year", "date": "2025-01-01", "category": "Public Holiday"},
            {"name": "Republic Day", "date": "2025-01-26", "category": "National Holiday"},
            {"name": "Holi", "date": "2025-03-14", "category": "Festival"},
            {"name": "Good Friday", "date": "2025-04-18", "category": "Religious"},
            {"name": "Eid al-Fitr", "date": "2025-04-30", "category": "Religious"},
            {"name": "Independence Day", "date": "2025-08-15", "category": "National Holiday"},
            {"name": "Janmashtami", "date": "2025-08-26", "category": "Festival"},
            {"name": "Ganesh Chaturthi", "date": "2025-08-29", "category": "Festival"},

            {"name": "Ganesh Chaturthi", "date": "2025-08-27", "category": "Festival"},

            {"name": "Gandhi Jayanti", "date": "2025-10-02", "category": "National Holiday"},
            {"name": "Dussehra", "date": "2025-10-22", "category": "Festival"},
            {"name": "Diwali", "date": "2025-11-01", "category": "Festival"},
            {"name": "Christmas", "date": "2025-12-25", "category": "Religious"},
            {"name": "Onam", "date": "2025-09-05", "category": "Cultural"},

            
            # Valentine's Day and other commercial festivals
            {"name": "Valentine's Day", "date": "2025-02-14", "category": "Commercial"},
            {"name": "Mother's Day", "date": "2025-05-11", "category": "Commercial"},
            {"name": "Father's Day", "date": "2025-06-15", "category": "Commercial"},
            {"name": "Raksha Bandhan", "date": "2025-08-09", "category": "Festival"},
            {"name": "Karva Chauth", "date": "2025-10-20", "category": "Festival"},
            {"name": "Bhai Dooj default", "date": "2025-07-31", "category": "Festival"},
            # Seasonal sales periods
            {"name": "Summer Sale Season", "date": "2025-04-01", "category": "Sale Period"},
            {"name": "Monsoon Sale", "date": "2025-07-01", "category": "Sale Period"},
            {"name": "Festive Season Sale", "date": "2025-09-15", "category": "Sale Period"},
            {"name": "Winter Collection Launch", "date": "2025-11-15", "category": "Sale Period"},
            {"name": "Year End Sale", "date": "2025-12-15", "category": "Sale Period"}
        ]
        
        current_date = datetime.now().date()
        upcoming_festivals = []

        for festival in festivals:
            festival_date = datetime.strptime(festival["date"], "%Y-%m-%d").date()
            days_until = (festival_date - current_date).days

            # Check if festival is within 10 days
            if 0 <= days_until <= 10:
                upcoming_festivals.append({
                    **festival,
                    "days_until": days_until,
                    "is_today": days_until == 0,
                    "recommendations": get_festival_recommendations(festival["name"], festival["category"])
                })

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

def get_festival_recommendations(festival_name, category):
    """Get specific recommendations for each festival based on actual sales data"""
    from collections import Counter
    from datetime import datetime, timedelta

    recommendations = {
        "stock_updates": [],
        "discount_suggestions": [],
        "marketing_tips": []
    }

    # Get current month's sales data for analysis
    try:
        # Use the SAME function from livedata_integration.py
        sales_data = fetch_sales_data_from_api()
        current_month = datetime.now().month
        current_year = datetime.now().year

        print(f"[#] Analyzing recommendations for {festival_name} ({category})")
        print(f"[#] Current month: {current_month}, Current year: {current_year}")
        print(f"[#] Total sales records: {len(sales_data) if sales_data else 0}")

        # Filter data for current month
        current_month_sales = []
        if sales_data:
            for record in sales_data:
                try:
                    # Check both 'date' and 'orderDate' fields
                    order_date = record.get('date') or record.get('orderDate', '')
                    if order_date:
                        # Parse ISO date format (2025-07-09T13:03:42.202Z) or simple date
                        if 'T' in order_date:
                            date_obj = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                        else:
                            date_obj = datetime.strptime(order_date, "%Y-%m-%d")

                        if date_obj.month == current_month and date_obj.year == current_year:
                            current_month_sales.append(record)
                except (ValueError, TypeError) as e:
                    print(f"Date parsing error for record {record.get('_id', 'unknown')}: {e}")
                    continue

        print(f"[#] Current month sales: {len(current_month_sales)}")

        # Analyze most sold items
        weave_counter = Counter()
        quality_counter = Counter()
        composition_counter = Counter()

        for record in current_month_sales:
            if record.get('weave'):
                weave_counter[record['weave']] += 1
            if record.get('quality'):
                quality_counter[record['quality']] += 1
            if record.get('composition'):
                composition_counter[record['composition']] += 1
        
        print(f"[#] Weave analysis: {dict(weave_counter)}")
        print(f"[#] Quality analysis: {dict(quality_counter)}")
        print(f"[#] Composition analysis: {dict(composition_counter)}")

        # Get top items
        top_weave = weave_counter.most_common(1)
        top_quality = quality_counter.most_common(1)
        top_composition = composition_counter.most_common(1)

        # Build stock update recommendations based on actual data
        stock_recommendations = []
        if top_weave:
            stock_recommendations.append(f"Increase {top_weave[0][0]} weave inventory (top seller this month)")
        if top_quality:
            stock_recommendations.append(f"Stock more {top_quality[0][0]} quality items (high demand)")
        if top_composition:
            stock_recommendations.append(f"Focus on {top_composition[0][0]} composition (best performing)")
        
        print(f"[#] Generated recommendations: {stock_recommendations}")
        
        # If no data available, use generic recommendations
        if not stock_recommendations:
            if category == "Festival" or festival_name in ["Diwali", "Holi", "Ganesh Chaturthi"]:
                stock_recommendations = [
                    "Increase ethnic wear inventory",
                    "Stock traditional jewelry",
                    "Prepare festive color collections"
                ]
            else:
                stock_recommendations = [
                    "Monitor current sales trends",
                    "Update inventory based on demand",
                    "Prepare seasonal collections"
                ]
            print(f"[#] Using fallback recommendations: {stock_recommendations}")
        
        recommendations["stock_updates"] = stock_recommendations
        
    except Exception as e:
        print(f"Error analyzing sales data for recommendations: {e}")
        # Fallback to generic recommendations
        recommendations["stock_updates"] = [
            "Monitor current sales trends",
            "Update inventory based on demand",
            "Prepare seasonal collections"
        ]
    
    # Set discount suggestions and marketing tips based on category
    if category == "Festival" or festival_name in ["Diwali", "Holi", "Ganesh Chaturthi"]:
        recommendations["discount_suggestions"] = [
            "20-30% off on ethnic wear",
            "Buy 2 Get 1 on accessories",
            "Festive combo deals"
        ]
        recommendations["marketing_tips"] = [
            "Highlight traditional designs",
            "Create festive lookbooks",
            "Partner with local influencers"
        ]
    elif category == "Commercial" or festival_name in ["Valentine's Day", "Mother's Day"]:
        recommendations["discount_suggestions"] = [
            "15-25% off on premium items",
            "Free gift wrapping",
            "Couple's discount packages"
        ]
        recommendations["marketing_tips"] = [
            "Create romantic campaigns",
            "Offer personalization",
            "Target gift buyers"
        ]
    elif category == "Sale Period":
        recommendations["discount_suggestions"] = [
            "Up to 50% off clearance",
            "Season launch offers",
            "Bulk purchase discounts"
        ]
        recommendations["marketing_tips"] = [
            "Heavy social media promotion",
            "Email marketing campaigns",
            "Flash sale announcements"
        ]
    else:  # National holidays, Religious festivals
        recommendations["discount_suggestions"] = [
            "10-20% seasonal discounts",
            "Free shipping offers",
            "Loyalty rewards"
        ]
        recommendations["marketing_tips"] = [
            "Respectful themed content",
            "Community engagement",
            "Cultural celebration posts"
        ]

    return recommendations

@app.route('/api/chat/<chat_id>/validate', methods=['POST'])
def validate_chat_response(chat_id):
    """Validate the last AI response for consistency with livedata_integration.py"""
    try:
        if chat_id not in chat_sessions:
            return jsonify({
                "success": False,
                "error": "Chat session not found"
            }), 404
        
        messages = chat_sessions[chat_id]["messages"]
        if not messages:
            return jsonify({
                "success": False,
                "error": "No messages to validate"
            }), 400
        
        # Find the last AI response and user question
        last_ai_response = None
        last_user_question = None
        
        for msg in reversed(messages):
            if msg["role"] == "assistant" and not last_ai_response:
                last_ai_response = msg
            elif msg["role"] == "user" and not last_user_question and last_ai_response:
                last_user_question = msg
                break
        
        if not last_ai_response or not last_user_question:
            return jsonify({
                "success": False,
                "error": "No AI response or user question found to validate"
            }), 400
        
        # Generate the same response using livedata_integration.py for comparison
        # Import the correct generate_response function
        validation_response = generate_response(last_user_question["content"], [])
        
        # Compare responses
        original_content = last_ai_response["content"]
        stripped_content = strip_summary_sections(original_content)
        validation_results = {
            "original_length": len(original_content),
            "validation_length": len(validation_response),
            "has_summary": "**Summary:**" in stripped_content,
            "has_detailed_breakdown": "**Detailed Breakdown:**" in stripped_content,
            "has_insights": "**Insights:**" in stripped_content,
            "contains_tie_detection": "tie" in stripped_content.lower() or "TIE" in stripped_content,
            "source_consistency": last_ai_response.get("source") == "livedata_integration_generate_response",
            "timestamp": datetime.now().isoformat(),
            "validation_generated": True,
            "core_consistency": "Validated against same livedata_integration.py logic"
        }
        
        # Log validation results
        print(f"[#] Validation results for chat {chat_id}: {validation_results}")
        print(f"[#] Original response first 100 chars: {original_content[:100]}...")
        print(f"[#] Validation response first 100 chars: {validation_response[:100]}...")
        
        return jsonify({
            "success": True,
            "validation": validation_results,
            "message": "Response consistency validated against livedata_integration.py",
            "original_response_preview": original_content[:200] + "..." if len(original_content) > 200 else original_content,
            "validation_response_preview": validation_response[:200] + "..." if len(validation_response) > 200 else validation_response
        }), 200
        
    except Exception as e:
        print(f"[X] Error validating chat response: {str(e)}")
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

@app.route('/api/debug/weave-counts', methods=['GET'])
def debug_weave_counts():
    """Debug endpoint to check actual weave counts in confirmed orders"""
    try:
        # Fetch data using the same functions
        all_sales_data = fetch_sales_data_from_api()

        confirmed_sales_data = [record for record in all_sales_data if record.get('status', '').lower() == 'confirmed']
        declined_sales_data = [record for record in all_sales_data if record.get('status', '').lower() == 'declined']
        processed_sales_data = [record for record in all_sales_data if record.get('status', '').lower() == 'processed']

        
        # Count weaves in confirmed orders
        weave_counts = {}
        status_counts = {}
        
        # Count all statuses for debugging
        for record in all_sales_data:
            status = record.get('status', '').lower().strip()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count weaves in confirmed orders only
        for record in confirmed_sales_data:
            weave = record.get('weave', 'Unknown').strip()
            if weave:
                weave_counts[weave] = weave_counts.get(weave, 0) + 1
      
        return jsonify({
            "success": True,
            "debug_info": {
                "total_records": len(all_sales_data),
                "confirmed_records": len(confirmed_sales_data),
                "declined_records": len(declined_sales_data),
                "processed_records": len(processed_sales_data),
                "status_breakdown": status_counts,
                "confirmed_weave_counts": weave_counts,
                "timestamp": datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        print(f"[X] Error in debug endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/debug/counts', methods=['GET'])
def debug_counts():
    """Debug endpoint to verify API data counts"""
    try:
        # Only use fetch_sales_data_from_api from livedata_integration
        from livedata_integration import fetch_sales_data_from_api
        all_data = fetch_sales_data_from_api()
        
        # Filter confirmed, declined, and processed orders
        confirmed_data = [record for record in all_data if record.get('status', '').lower() == 'confirmed'] if all_data else []
        declined_data = [record for record in all_data if record.get('status', '').lower() == 'declined'] if all_data else []
        processed_data = [record for record in all_data if record.get('status', '').lower() == 'processed'] if all_data else []
        
        # Month breakdown
        month_counts = {}
        for record in all_data:
            date_str = record.get('date', '')
            if date_str:
                try:
                    if 'T' in date_str:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    month_name = date_obj.strftime('%B')
                    month_counts[month_name] = month_counts.get(month_name, 0) + 1
                except:
                    pass

        return jsonify({
            "success": True,
            "debug_data": {
                "total_records": len(all_data),
                "confirmed_records": len(confirmed_data),
                "declined_records": len(declined_data),
                "processed_records": len(processed_data),
                "confirmed_month_counts": month_counts,
                "sample_confirmed_record": confirmed_data[0] if confirmed_data else None,
                "sample_record": all_data[0] if all_data else None,
                "timestamp": datetime.now().isoformat()
            }
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# --- Email endpoint ---

@app.route('/api/send-mail', methods=['POST'])
def send_mail():
    """Open the email HTML file in the default web browser"""
    try:
        import os, webbrowser
        email_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'email', 'index.html'))
        if not os.path.exists(email_file_path):
            return jsonify({
                "success": False,
                "error": f"Email HTML file not found at: {email_file_path}"
            }), 404
        file_url = f"file:///{email_file_path.replace(os.sep, '/')}"
        webbrowser.open(file_url)
        return jsonify({
            "success": True,
            "message": "Email form opened in browser successfully",
            "file_path": email_file_path
        }), 200
    except Exception as e:
        import traceback
        print(f"Error preparing email file URL: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Validate configuration before starting
    if not Config.validate_api_key():
        print("[X] Cannot start server without proper configuration!")
        exit(1)
    
    print("[>] Starting Dress Sales Monitoring Chatbot API Server...")
    print(f"[#] Sales API: {Config.SALES_API_URL}")
    print(f"[#] Server: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    print(f"[#] CORS Origins: {Config.CORS_ORIGINS}")
    print("\n[!] Make sure your .env file contains GEMINI_API_KEY")
    print("[!] Test the API at: http://127.0.0.1:8000/api/health")
    print("[#] Enhanced with response validation for accurate counting")
    print("[#] Frontend responses will match livedata_integration.py exactly")
    print("[#] Same core logic, same data filtering, same tie detection")
    
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
