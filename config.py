import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Dress Sales Monitoring Chatbot"""
    
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Sales Data API Configuration
    SALES_API_URL = "http://54.234.201.60:5000/chat/getFormData"
    
    # Flask Configuration
    FLASK_HOST = "127.0.0.1"
    FLASK_PORT = 8000
    FLASK_DEBUG = True
    
    # CORS Configuration
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080", "http://127.0.0.1:8080"]
    
    @classmethod
    def validate_api_key(cls):
        """Validate that the Gemini API key is set"""
        if not cls.GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY environment variable not set!")
            print("Please add your Gemini API key to the .env file:")
            print("GEMINI_API_KEY=your_api_key_here")
            return False
        return True
    
    @classmethod
    def get_config_info(cls):
        """Get configuration information for debugging"""
        return {
            "gemini_api_key_set": bool(cls.GEMINI_API_KEY),
            "sales_api_url": cls.SALES_API_URL,
            "flask_host": cls.FLASK_HOST,
            "flask_port": cls.FLASK_PORT,
            "cors_origins": cls.CORS_ORIGINS
        }
