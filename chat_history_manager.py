import os
import csv
import uuid
from datetime import datetime
from typing import List, Dict, Optional

CHAT_HISTORY_DIR = "chat_history"
MAX_CHAT_HISTORY = 10

def initialize_chat_history_dir():
    """Create the chat history directory if it doesn't exist"""
    if not os.path.exists(CHAT_HISTORY_DIR):
        os.makedirs(CHAT_HISTORY_DIR)

def save_chat_history(chat_id: str, messages: List[Dict]) -> bool:
    """
    Save chat history to a CSV file
    
    Args:
        chat_id (str): Unique identifier for the chat
        messages (List[Dict]): List of message dictionaries
    
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        initialize_chat_history_dir()
        
        # Check if we've reached the limit
        if len(get_all_chat_files()) >= MAX_CHAT_HISTORY:
            # Don't save if we've reached the limit
            return False
            
        filename = os.path.join(CHAT_HISTORY_DIR, f"chat_{chat_id}.csv")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'content', 'role', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for message in messages:
                writer.writerow({
                    'id': message.get('id', str(uuid.uuid4())),
                    'content': message.get('content', ''),
                    'role': message.get('role', ''),
                    'timestamp': message.get('timestamp', datetime.now().isoformat())
                })
        
        return True
    except Exception as e:
        print(f"Error saving chat history: {e}")
        return False

def load_chat_history(chat_id: str) -> Optional[List[Dict]]:
    """
    Load chat history from a CSV file
    
    Args:
        chat_id (str): Unique identifier for the chat
    
    Returns:
        Optional[List[Dict]]: List of message dictionaries or None if not found
    """
    try:
        filename = os.path.join(CHAT_HISTORY_DIR, f"chat_{chat_id}.csv")
        
        if not os.path.exists(filename):
            return None
            
        messages = []
        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                messages.append({
                    'id': row['id'],
                    'content': row['content'],
                    'role': row['role'],
                    'timestamp': row['timestamp']
                })
        
        return messages
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return None

def get_all_chat_files() -> List[str]:
    """
    Get all chat history files
    
    Returns:
        List[str]: List of chat file names
    """
    try:
        initialize_chat_history_dir()
        files = os.listdir(CHAT_HISTORY_DIR)
        return [f for f in files if f.startswith('chat_') and f.endswith('.csv')]
    except Exception as e:
        print(f"Error getting chat files: {e}")
        return []

def is_chat_history_full() -> bool:
    """
    Check if chat history storage is full
    
    Returns:
        bool: True if storage is full, False otherwise
    """
    return len(get_all_chat_files()) >= MAX_CHAT_HISTORY

def delete_oldest_chat() -> bool:
    """
    Delete the oldest chat file to make room for a new one
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        chat_files = get_all_chat_files()
        if not chat_files:
            return False
            
        # Sort by modification time to find the oldest
        chat_files_with_time = []
        for file in chat_files:
            filepath = os.path.join(CHAT_HISTORY_DIR, file)
            mod_time = os.path.getmtime(filepath)
            chat_files_with_time.append((file, mod_time))
            
        chat_files_with_time.sort(key=lambda x: x[1])  # Sort by modification time
        oldest_file = chat_files_with_time[0][0]
        
        # Delete the oldest file
        filepath = os.path.join(CHAT_HISTORY_DIR, oldest_file)
        os.remove(filepath)
        
        return True
    except Exception as e:
        print(f"Error deleting oldest chat: {e}")
        return False