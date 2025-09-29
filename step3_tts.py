import torch
import numpy as np
import threading
import queue
import tempfile
import os
from typing import Optional, Callable
from TTS.api import TTS
from logging_config import get_logger

logger = get_logger('tts')

class TTSManager:
    """Manages text-to-speech conversion using Coqui TTS."""
    
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC", 
                 tts_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the TTS manager.
        
        Args:
            model_name: Name of the TTS model to use
            tts_callback: Function to call with path to generated audio file
        """
        self.model_name = model_name
        self.tts_callback = tts_callback
        self.tts_queue = queue.Queue()
        self.tts_model = None
        self.is_initialized = False
        self.temp_dir = tempfile.mkdtemp(prefix="tts_audio_")
        self._init_tts()
    
    def _init_tts(self):
        """Initialize the TTS model."""
        try:
            logger.info(f"Initializing TTS model: {self.model_name}")
            
            # Check if CUDA is available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")
            
            # Initialize TTS model
            self.tts_model = TTS(model_name=self.model_name).to(device)
            
            self.is_initialized = True
            logger.info("TTS model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS model: {e}")
            self.is_initialized = False
            raise
    
    def text_to_speech(self, text: str) -> Optional[str]:
        """
        Convert text to speech and save as audio file.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Path to generated audio file or None if failed
        """
        if not self.is_initialized:
            logger.error("TTS model not initialized")
            return None
        
        if not text.strip():
            logger.warning("Empty text provided for TTS")
            return None
        
        try:
            logger.info(f"Converting to speech: '{text}'")
            
            # Generate unique filename
            import time
            timestamp = int(time.time() * 1000)
            audio_filename = f"tts_output_{timestamp}.wav"
            audio_path = os.path.join(self.temp_dir, audio_filename)
            
            # Generate speech
            self.tts_model.tts_to_file(text=text, file_path=audio_path)
            
            logger.info(f"TTS audio generated: {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"TTS conversion error: {e}")
            return None
    
    def queue_tts(self, text: str):
        """
        Queue text for TTS processing.
        
        Args:
            text: Text to convert to speech
        """
        if text.strip():
            logger.info(f"Queuing text for TTS: '{text}'")
            self.tts_queue.put(text)
    
    def process_tts_queue(self):
        """Process the TTS queue."""
        try:
            text = self.tts_queue.get(timeout=1.0)
            audio_path = self.text_to_speech(text)
            
            if audio_path and self.tts_callback:
                self.tts_callback(audio_path)
                
        except queue.Empty:
            pass  # No text to process
        except Exception as e:
            logger.error(f"Error processing TTS queue: {e}")
    
    def get_tts_audio(self, timeout: float = 1.0) -> Optional[str]:
        """
        Get TTS audio file from the queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Path to audio file or None if timeout
        """
        try:
            text = self.tts_queue.get(timeout=timeout)
            return self.text_to_speech(text)
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error getting TTS audio: {e}")
            return None
    
    def cleanup_temp_files(self):
        """Clean up temporary audio files."""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
    
    def get_available_models(self) -> list:
        """
        Get list of available TTS models.
        
        Returns:
            List of available model names
        """
        try:
            return TTS.list_models()
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []

def create_tts_manager(model_name: str = "tts_models/en/ljspeech/tacotron2-DDC",
                      tts_callback: Optional[Callable[[str], None]] = None):
    """
    Create a TTS manager instance.
    
    Args:
        model_name: Name of the TTS model to use
        tts_callback: Function to call with path to generated audio file
        
    Returns:
        TTSManager instance
    """
    return TTSManager(model_name, tts_callback)

def get_multilingual_models() -> list:
    """
    Get list of multilingual TTS models.
    
    Returns:
        List of multilingual model names
    """
    try:
        all_models = TTS.list_models()
        multilingual_models = [model for model in all_models if 'multilingual' in model.lower()]
        return multilingual_models
    except Exception as e:
        logger.error(f"Error getting multilingual models: {e}")
        return []

def test_tts():
    """Test function for TTS module."""
    logger.info("Testing TTS module...")
    
    def test_callback(audio_path: str):
        logger.info(f"Test callback - Audio generated: {audio_path}")
        if os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            logger.info(f"Audio file size: {file_size} bytes")
    
    try:
        # Test with default model
        manager = create_tts_manager(tts_callback=test_callback)
        
        # Test TTS conversion
        test_texts = [
            "Hello, this is a test of text to speech conversion.",
            "The translation system is working correctly.",
            "This audio was generated using Coqui TTS."
        ]
        
        for text in test_texts:
            logger.info(f"Testing TTS conversion of: '{text}'")
            audio_path = manager.text_to_speech(text)
            if audio_path:
                logger.info(f"Audio generated successfully: {audio_path}")
            else:
                logger.error("Failed to generate audio")
        
        logger.info("TTS test completed successfully")
        
        # Clean up
        manager.cleanup_temp_files()
        
    except Exception as e:
        logger.error(f"TTS test failed: {e}")

if __name__ == "__main__":
    test_tts()
