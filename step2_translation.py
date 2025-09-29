import argostranslate.package
import argostranslate.translate
import threading
import queue
from typing import Optional, Callable, List
from logging_config import get_logger

logger = get_logger('translation')

class TranslationManager:
    """Manages offline translation using Argos Translate."""
    
    def __init__(self, source_lang: str = "en", target_lang: str = "es", 
                 translation_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the translation manager.
        
        Args:
            source_lang: Source language code (e.g., 'en' for English)
            target_lang: Target language code (e.g., 'es' for Spanish)
            translation_callback: Function to call with translated text
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translation_callback = translation_callback
        self.translation_queue = queue.Queue()
        self.is_initialized = False
        self._init_argos()
    
    def _init_argos(self):
        """Initialize Argos Translate with required packages."""
        try:
            logger.info(f"Initializing Argos Translate for {self.source_lang} -> {self.target_lang}")
            
            # Update package index
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            # Find the appropriate package
            package_to_install = None
            for package in available_packages:
                if (package.from_code == self.source_lang and 
                    package.to_code == self.target_lang):
                    package_to_install = package
                    break
            
            if package_to_install is None:
                logger.error(f"No translation package found for {self.source_lang} -> {self.target_lang}")
                logger.info("Available packages:")
                for package in available_packages:
                    logger.info(f"  {package.from_code} -> {package.to_code}")
                raise ValueError(f"No translation package available for {self.source_lang} -> {self.target_lang}")
            
            # Install the package if not already installed
            installed_packages = argostranslate.package.get_installed_packages()
            package_installed = any(
                pkg.from_code == package_to_install.from_code and 
                pkg.to_code == package_to_install.to_code
                for pkg in installed_packages
            )
            
            if not package_installed:
                logger.info(f"Installing translation package: {package_to_install.from_code} -> {package_to_install.to_code}")
                argostranslate.package.install_from_path(package_to_install.download())
            else:
                logger.info(f"Translation package already installed: {package_to_install.from_code} -> {package_to_install.to_code}")
            
            self.is_initialized = True
            logger.info("Argos Translate initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Argos Translate: {e}")
            self.is_initialized = False
            raise
    
    def translate_text(self, text: str) -> str:
        """
        Translate text from source language to target language.
        
        Args:
            text: Text to translate
            
        Returns:
            Translated text
        """
        if not self.is_initialized:
            logger.error("Translation manager not initialized")
            return text
        
        try:
            logger.info(f"Translating: '{text}'")
            translated = argostranslate.translate.translate(text, self.source_lang, self.target_lang)
            logger.info(f"Translated to: '{translated}'")
            return translated
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails
    
    def queue_translation(self, text: str):
        """
        Queue text for translation processing.
        
        Args:
            text: Text to translate
        """
        if text.strip():
            logger.info(f"Queuing text for translation: '{text}'")
            self.translation_queue.put(text)
    
    def process_translation_queue(self):
        """Process the translation queue."""
        try:
            text = self.translation_queue.get(timeout=1.0)
            translated = self.translate_text(text)
            
            # Call callback if provided
            if self.translation_callback:
                self.translation_callback(translated)
                
        except queue.Empty:
            pass  # No text to translate
        except Exception as e:
            logger.error(f"Error processing translation queue: {e}")
    
    def get_translation(self, timeout: float = 1.0) -> Optional[str]:
        """
        Get translated text from the queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Translated text or None if timeout
        """
        try:
            text = self.translation_queue.get(timeout=timeout)
            return self.translate_text(text)
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error getting translation: {e}")
            return None

def create_translation_manager(source_lang: str = "en", target_lang: str = "es",
                             translation_callback: Optional[Callable[[str], None]] = None):
    """
    Create a translation manager instance.
    
    Args:
        source_lang: Source language code
        target_lang: Target language code
        translation_callback: Function to call with translated text
        
    Returns:
        TranslationManager instance
    """
    return TranslationManager(source_lang, target_lang, translation_callback)

def get_available_languages() -> List[tuple]:
    """
    Get list of available language pairs for translation.
    
    Returns:
        List of (from_code, to_code, from_name, to_name) tuples
    """
    try:
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()
        
        languages = []
        for package in available_packages:
            languages.append((
                package.from_code,
                package.to_code,
                package.from_name,
                package.to_name
            ))
        
        return languages
    except Exception as e:
        logger.error(f"Error getting available languages: {e}")
        return []

def test_translation():
    """Test function for translation module."""
    logger.info("Testing translation module...")
    
    def test_callback(translated_text: str):
        logger.info(f"Test callback - Translated: '{translated_text}'")
    
    try:
        # Test with English to Spanish
        manager = create_translation_manager("en", "es", test_callback)
        
        # Test translations
        test_texts = [
            "Hello, how are you?",
            "This is a test message",
            "Good morning everyone"
        ]
        
        for text in test_texts:
            logger.info(f"Testing translation of: '{text}'")
            translated = manager.translate_text(text)
            logger.info(f"Result: '{translated}'")
            
        logger.info("Translation test completed successfully")
        
    except Exception as e:
        logger.error(f"Translation test failed: {e}")

if __name__ == "__main__":
    test_translation()
