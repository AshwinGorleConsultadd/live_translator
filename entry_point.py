#!/usr/bin/env python3
"""
Live Audio Translator - Main Entry Point

This is the main orchestrator that connects all the translation pipeline steps:
1. Audio Capture & Streaming (AssemblyAI)
2. Translation (Argos Translate)
3. Text-to-Speech (Coqui TTS)
4. Audio Output (SoundDevice)

Usage:
    python entry_point.py

Configuration:
    - Set your AssemblyAI API key in the ASSEMBLYAI_API_KEY variable
    - Adjust source and target languages as needed
    - Modify TTS model if required
"""

import threading
import time
import signal
import sys
from typing import Optional

# Import our modules
from logging_config import setup_logging, get_logger
from step1_audio_capture import create_audio_capture_manager
from step2_translation import create_translation_manager
from step3_tts import create_tts_manager
from step4_audio_output import create_audio_output_manager

# Configuration
ASSEMBLYAI_API_KEY = "d8f2f5ddd28646bebe9ccd876bc14773"  # Replace with your API key
SOURCE_LANGUAGE = "en"  # English
TARGET_LANGUAGE = "es"  # Spanish
TTS_MODEL = "tts_models/en/ljspeech/tacotron2-DDC"  # Default English TTS model

class LiveTranslator:
    """Main orchestrator for the live translation pipeline."""
    
    def __init__(self):
        """Initialize the live translator."""
        self.logger = get_logger('main')
        self.is_running = False
        
        # Initialize all managers
        self.audio_capture = None
        self.translator = None
        self.tts = None
        self.audio_output = None
        
        # Threading
        self.translation_thread = None
        self.tts_thread = None
        
        # TTS muting controls
        self.is_tts_playing = False
        self.mic_paused = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _translation_callback(self, text: str, is_finalized: bool):
        """Callback for when transcription is received."""
        # DOUBLE-CHECK: Only process finalized, meaningful phrases
        if (is_finalized and 
            text.strip() and 
            len(text.strip()) > 2 and  # Minimum 3 characters
            not text.strip().lower() in ['um', 'uh', 'ah', 'er']):  # Filter out filler words
            
            self.logger.info(f"1️⃣ SPEECH → ENGLISH: '{text}'")
            # Queue for translation
            if self.translator:
                self.translator.queue_translation(text)
        else:
            self.logger.debug(f"🚫 SKIPPING: '{text}' (finalized: {is_finalized})")
    
    def _translation_to_tts_callback(self, translated_text: str):
        """Callback for when translation is completed."""
        self.logger.info(f"2️⃣ ENGLISH → SPANISH: '{translated_text}'")
        # Queue for TTS
        if self.tts:
            self.tts.queue_tts(translated_text)
    
    def _tts_callback(self, audio_path: str):
        """Callback for when TTS audio is generated."""
        self.logger.info(f"3️⃣ SPANISH AUDIO READY → Playing through speakers")
        
        # PAUSE MICROPHONE when TTS starts playing
        self.is_tts_playing = True
        if self.audio_capture and not self.mic_paused:
            self.audio_capture.pause_streaming()
            self.mic_paused = True
            self.logger.info("🔇 MICROPHONE PAUSED - TTS playing")
        
        # Queue for audio output
        if self.audio_output:
            self.audio_output.queue_audio(audio_path)
    
    def _audio_callback(self, message: str):
        """Callback for audio playback events."""
        # Debug: Log all audio messages
        self.logger.debug(f"Audio callback received: '{message}'")
        
        # Resume microphone when TTS playback finishes
        if "finished playing" in message.lower() and self.is_tts_playing:
            self.is_tts_playing = False
            if self.audio_capture and self.mic_paused:
                self.audio_capture.resume_streaming()
                self.mic_paused = False
                self.logger.info("🎤 MICROPHONE RESUMED - TTS finished")
    
    def initialize(self):
        """Initialize all components."""
        try:
            self.logger.info("Initializing Live Audio Translator...")
            
            # Initialize audio capture
            self.logger.info("Initializing audio capture...")
            self.audio_capture = create_audio_capture_manager(
                ASSEMBLYAI_API_KEY, 
                self._translation_callback
            )
            
            # Initialize translation
            self.logger.info("Initializing translation...")
            self.translator = create_translation_manager(
                SOURCE_LANGUAGE, 
                TARGET_LANGUAGE,
                self._translation_to_tts_callback
            )
            
            # Initialize TTS
            self.logger.info("Initializing TTS...")
            self.tts = create_tts_manager(
                TTS_MODEL,
                self._tts_callback
            )
            
            # Initialize audio output
            self.logger.info("Initializing audio output...")
            self.audio_output = create_audio_output_manager(
                audio_callback=self._audio_callback
            )
            
            self.logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False
    
    def _translation_worker(self):
        """Worker thread for processing translations."""
        self.logger.info("Translation worker started")
        
        while self.is_running:
            try:
                if self.translator:
                    self.translator.process_translation_queue()
                time.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                self.logger.error(f"Error in translation worker: {e}")
        
        self.logger.info("Translation worker stopped")
    
    def _tts_worker(self):
        """Worker thread for processing TTS."""
        self.logger.info("TTS worker started")
        
        while self.is_running:
            try:
                if self.tts:
                    self.tts.process_tts_queue()
                time.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                self.logger.error(f"Error in TTS worker: {e}")
        
        self.logger.info("TTS worker stopped")
    
    def start(self):
        """Start the live translation system."""
        if not self.initialize():
            self.logger.error("Failed to initialize, cannot start")
            return False
        
        try:
            self.logger.info("Starting Live Audio Translator...")
            self.is_running = True
            
            # Start worker threads
            self.translation_thread = threading.Thread(target=self._translation_worker, daemon=True)
            self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            
            self.translation_thread.start()
            self.tts_thread.start()
            
            # Start audio output playback thread
            if self.audio_output:
                self.audio_output.start_playback_thread()
            
            # Start audio capture (this will block)
            self.logger.info("Starting audio capture...")
            self.logger.info("Speak into your microphone. Press Ctrl+C to stop.")
            
            if self.audio_capture:
                self.audio_capture.start_streaming()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting live translator: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Stop the live translation system."""
        self.logger.info("Stopping Live Audio Translator...")
        self.is_running = False
        
        # Stop audio capture
        if self.audio_capture:
            self.audio_capture.stop_streaming()
        
        # Stop audio output
        if self.audio_output:
            self.audio_output.stop_playback_thread()
        
        # Wait for worker threads to finish
        if self.translation_thread and self.translation_thread.is_alive():
            self.translation_thread.join(timeout=2.0)
        
        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=2.0)
        
        # Cleanup TTS temp files
        if self.tts:
            self.tts.cleanup_temp_files()
        
        self.logger.info("Live Audio Translator stopped")

def test_individual_components():
    """Test each component individually."""
    logger = get_logger('main')
    
    logger.info("Testing individual components...")
    
    try:
        # Test audio capture
        logger.info("Testing audio capture...")
        from step1_audio_capture import test_audio_capture
        test_audio_capture()
        
    except Exception as e:
        logger.error(f"Audio capture test failed: {e}")
    
    try:
        # Test translation
        logger.info("Testing translation...")
        from step2_translation import test_translation
        test_translation()
        
    except Exception as e:
        logger.error(f"Translation test failed: {e}")
    
    try:
        # Test TTS
        logger.info("Testing TTS...")
        from step3_tts import test_tts
        test_tts()
        
    except Exception as e:
        logger.error(f"TTS test failed: {e}")
    
    try:
        # Test audio output
        logger.info("Testing audio output...")
        from step4_audio_output import test_audio_output
        test_audio_output()
        
    except Exception as e:
        logger.error(f"Audio output test failed: {e}")

def main():
    """Main entry point."""
    # Setup logging
    loggers = setup_logging()
    logger = loggers['main']
    
    logger.info("=" * 60)
    logger.info("Live Audio Translator Starting...")
    logger.info("=" * 60)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            logger.info("Running individual component tests...")
            test_individual_components()
            return
        elif sys.argv[1] == "help":
            print("Usage:")
            print("  python entry_point.py          # Run live translator")
            print("  python entry_point.py test     # Test individual components")
            print("  python entry_point.py help     # Show this help")
            return
    
    # Create and start the live translator
    translator = LiveTranslator()
    
    try:
        success = translator.start()
        if not success:
            logger.error("Failed to start live translator")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        translator.stop()
        logger.info("Live Audio Translator shutdown complete")

if __name__ == "__main__":
    main()
