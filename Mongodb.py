from pymongo import MongoClient
from datetime import datetime
import uuid
from typing import List, Dict, Optional

# MongoDB connection
uri = "mongodb+srv://hertzworkz:HertzworkZ@cluster0.7xrqojt.mongodb.net/KKP?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client["chatbot_db"]  # Use a proper database name

# Collections
chats_collection = db["chats"]
messages_collection = db["messages"]

# Create indexes for better performance
chats_collection.create_index("last_updated")
messages_collection.create_index("chat_id")

print("[OK] Connected to MongoDB:", db.name)

def initialize_mongodb():
    """Initialize MongoDB collections and indexes"""
    try:
        # Create indexes if they don't exist
        chats_collection.create_index("id", unique=True)
        chats_collection.create_index("last_updated")
        messages_collection.create_index("chat_id")
        messages_collection.create_index([("chat_id", 1), ("timestamp", 1)])
        print("[OK] MongoDB indexes created successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Error initializing MongoDB: {e}")
        return False

# Chat history functions
def save_chat_history_mongo(chat_id: str, messages: List[Dict], title: str = "New Chat") -> bool:
    """
    Save chat history to MongoDB
    
    Args:
        chat_id (str): Unique identifier for the chat
        messages (List[Dict]): List of message dictionaries
        title (str): Title for the chat
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        initialize_mongodb()
        current_time = datetime.now().isoformat()
        
        # Check if we've reached the limit (keeping same limit as SQLite implementation)
        chat_count = chats_collection.count_documents({})
        MAX_CHAT_HISTORY = 10
        
        if chat_count >= MAX_CHAT_HISTORY:
            # Delete the oldest chat to make room for a new one
            oldest_chat = chats_collection.find_one(sort=[("last_updated", 1)])
            if oldest_chat:
                delete_chat_mongo(oldest_chat["id"])
        
        # Update or insert chat record
        chat_data = {
            "id": chat_id,
            "title": title,
            "created_at": current_time,
            "last_updated": current_time
        }
        
        chats_collection.replace_one({"id": chat_id}, chat_data, upsert=True)
        
        # Delete existing messages for this chat
        messages_collection.delete_many({"chat_id": chat_id})
        
        # Insert messages
        if messages:
            message_docs = []
            for message in messages:
                message_doc = {
                    "id": message.get('id', str(uuid.uuid4())),
                    "chat_id": chat_id,
                    "content": message.get('content', ''),
                    "role": message.get('role', ''),
                    "timestamp": message.get('timestamp', current_time)
                }
                message_docs.append(message_doc)
            
            if message_docs:
                messages_collection.insert_many(message_docs)
        
        return True
    except Exception as e:
        print(f"Error saving chat history to MongoDB: {e}")
        return False

def load_chat_history_mongo(chat_id: str) -> Optional[List[Dict]]:
    """
    Load chat history from MongoDB
    
    Args:
        chat_id (str): Unique identifier for the chat
        
    Returns:
        Optional[List[Dict]]: List of message dictionaries or None if not found
    """
    try:
        initialize_mongodb()
        
        # Check if chat exists
        chat = chats_collection.find_one({"id": chat_id})
        if not chat:
            return None
        
        # Load messages
        messages_cursor = messages_collection.find({"chat_id": chat_id}).sort("timestamp", 1)
        messages = list(messages_cursor)
        
        # Convert ObjectId to string for JSON serialization
        for message in messages:
            if '_id' in message:
                del message['_id']
        
        return messages if messages else None
    except Exception as e:
        print(f"Error loading chat history from MongoDB: {e}")
        return None

def get_all_chats_mongo() -> List[Dict]:
    """
    Get all chat sessions from MongoDB
    
    Returns:
        List[Dict]: List of chat dictionaries
    """
    try:
        initialize_mongodb()
        
        # Get all chats sorted by last_updated (newest first)
        chats_cursor = chats_collection.find().sort("last_updated", -1)
        chats = list(chats_cursor)
        
        # Convert ObjectId to string and load messages for each chat
        result_chats = []
        for chat in chats:
            if '_id' in chat:
                del chat['_id']
            
            # Load messages for this chat
            messages = load_chat_history_mongo(chat["id"])
            chat["messages"] = messages if messages else []
            result_chats.append(chat)
        
        return result_chats
    except Exception as e:
        print(f"Error getting all chats from MongoDB: {e}")
        return []

def delete_chat_mongo(chat_id: str) -> bool:
    """
    Delete a specific chat from MongoDB
    
    Args:
        chat_id (str): Unique identifier for the chat
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        initialize_mongodb()
        
        # Delete messages first
        messages_collection.delete_many({"chat_id": chat_id})
        
        # Delete chat
        result = chats_collection.delete_one({"id": chat_id})
        
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting chat from MongoDB: {e}")
        return False

def clear_all_chats_mongo() -> bool:
    """
    Clear all chat sessions from MongoDB
    
    Returns:
        bool: True if clearing was successful, False otherwise
    """
    try:
        initialize_mongodb()
        
        # Delete all messages
        messages_collection.delete_many({})
        
        # Delete all chats
        chats_collection.delete_many({})
        
        return True
    except Exception as e:
        print(f"Error clearing all chats from MongoDB: {e}")
        return False

def chat_exists_in_mongo(chat_id: str) -> bool:
    """
    Check if a chat exists in MongoDB
    
    Args:
        chat_id (str): Unique identifier for the chat
        
    Returns:
        bool: True if chat exists, False otherwise
    """
    try:
        initialize_mongodb()
        return chats_collection.find_one({"id": chat_id}) is not None
    except Exception as e:
        print(f"Error checking if chat exists in MongoDB: {e}")
        return False
