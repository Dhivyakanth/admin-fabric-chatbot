"""
Translation module for the chatbot
Handles language detection and translation between English, Tamil, and Hindi
"""
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatTranslator:
    def __init__(self):
        """Initialize the translator"""
        self.translator = None
        self.translator_available = False
        self.translator_class = None
        self.supported_languages = {
            'en': 'English',
            'ta': 'Tamil',
            'hi': 'Hindi'
        }
    
    def _init_translator(self):
        """Initialize the translator with error handling - lazy initialization"""
        if self.translator_available:
            return True
            
        try:
            # Try deep-translator first (more reliable)
            from deep_translator import GoogleTranslator
            self.translator_class = GoogleTranslator
            self.translator_available = True
            logger.info("Deep translator initialized successfully")
            return True
        except ImportError as e:
            logger.warning(f"Deep translator not available: {e}")
            try:
                # Fallback to googletrans
                from googletrans import Translator
                self.translator = Translator()
                self.translator_available = True
                logger.info("Googletrans translator initialized successfully")
                return True
            except ImportError as e:
                logger.warning(f"Googletrans not available: {e}")
                logger.warning("No translation library available. Translation features will be disabled.")
                self.translator_available = False
                return False
            except Exception as e:
                logger.error(f"Error initializing googletrans translator: {e}")
                self.translator_available = False
                return False
        except Exception as e:
            logger.error(f"Error initializing deep-translator: {e}")
            # Even if we get an error, let's try to import it differently
            try:
                import deep_translator
                from deep_translator import GoogleTranslator
                self.translator_class = GoogleTranslator
                self.translator_available = True
                logger.info("Deep translator initialized successfully (alternative method)")
                return True
            except Exception as e2:
                logger.error(f"Alternative deep-translator initialization also failed: {e2}")
                self.translator_available = False
                return False
    
    def detect_language(self, text):
        """
        Detect the language of the given text
        
        Args:
            text (str): Text to detect language for
            
        Returns:
            dict: Dictionary with language code and confidence
        """
        # Lazy initialization
        if not self.translator_available:
            self._init_translator()
            
        if not self.translator_available:
            return {
                'language': 'en',
                'confidence': 0.0
            }
            
        try:
            # Language detection not implemented in deep-translator, so we'll just return default
            return {
                'language': 'en',
                'confidence': 0.0
            }
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return {
                'language': 'en',
                'confidence': 0.0
            }
    
    def translate_text(self, text, target_language):
        """
        Translate text to the target language
        
        Args:
            text (str): Text to translate
            target_language (str): Target language code ('en', 'ta', 'hi')
            
        Returns:
            str: Translated text or original text if translation fails
        """
        # Lazy initialization
        if not self.translator_available:
            self._init_translator()
            
        # If target language is not supported or is English, return original
        if not self.translator_available or target_language not in self.supported_languages or target_language == 'en':
            return text
            
        try:
            if self.translator_class:
                # Using deep-translator
                translator = self.translator_class(source='en', target=target_language)
                translation = translator.translate(text)
                logger.info(f"Translated text from en to {target_language}")
                return translation
            elif self.translator:
                # Using googletrans
                translation = self.translator.translate(text, dest=target_language)
                logger.info(f"Translated text from en to {target_language}")
                return translation.text
            else:
                return text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails
    
    def translate_to_english(self, text):
        """
        Translate text to English
        
        Args:
            text (str): Text to translate to English
            
        Returns:
            str: Translated text or original text if translation fails
        """
        # Lazy initialization
        if not self.translator_available:
            self._init_translator()
            
        if not self.translator_available:
            return text
            
        try:
            if self.translator_class:
                # Using deep-translator
                translator = self.translator_class(source='auto', target='en')
                translation = translator.translate(text)
                logger.info("Translated text to English")
                return translation
            elif self.translator:
                # Using googletrans
                translation = self.translator.translate(text, dest='en')
                logger.info("Translated text to English")
                return translation.text
            else:
                return text
        except Exception as e:
            logger.error(f"Translation to English error: {e}")
            return text  # Return original text if translation fails
    
    def get_supported_languages(self):
        """
        Get list of supported languages
        
        Returns:
            dict: Dictionary of supported languages
        """
        return self.supported_languages

# Create a global instance with lazy initialization
def get_chat_translator():
    """Get or create the global chat translator instance"""
    global _chat_translator_instance
    if _chat_translator_instance is None:
        _chat_translator_instance = ChatTranslator()
    return _chat_translator_instance

_chat_translator_instance = None

# Convenience functions with lazy initialization
def translate_to_user_language(text, user_language):
    """Translate text to user's language"""
    translator = get_chat_translator()
    # Trigger initialization
    translator._init_translator()
    return translator.translate_text(text, user_language)

def translate_to_english(text):
    """Translate text to English"""
    translator = get_chat_translator()
    # Trigger initialization
    translator._init_translator()
    return translator.translate_to_english(text)

def detect_language(text):
    """Detect language of text"""
    translator = get_chat_translator()
    # Trigger initialization
    translator._init_translator()
    return translator.detect_language(text)

# Prevent execution when imported
if __name__ == "__main__":
    print("Translator module loaded successfully. Available for import.")
    translator = get_chat_translator()
    # Trigger initialization to check availability
    translator._init_translator()
    print(f"Translation available: {translator.translator_available}")