from typing import Callable, Optional
import assemblyai as aai
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    StreamingSessionParameters,
    TerminationEvent,
    TurnEvent,
)
import threading
import queue
from logging_config import get_logger

logger = get_logger('audio_capture')

class AudioCaptureManager:
    """Manages audio capture and streaming to AssemblyAI."""
    
    def __init__(self, api_key: str, transcription_callback: Optional[Callable[[str, bool], None]] = None, language_code: str = "en"):
        """
        Initialize the audio capture manager.
        
        Args:
            api_key: AssemblyAI API key
            transcription_callback: Function to call with transcribed text (text, is_finalized)
            language_code: Language code for speech recognition ("en" for English, "es" for Spanish)
        """
        self.api_key = api_key
        self.transcription_callback = transcription_callback
        self.language_code = language_code
        self.client = None
        self.is_streaming = False
        self.is_paused = False
        self.transcription_queue = queue.Queue()
        self.last_processed_text = ""  # Track last processed text to avoid duplicates
        
    def _on_begin(self, client, event: BeginEvent):
        """Handle session begin event."""
        logger.info(f"AssemblyAI session started: {event.id}")
        
    def _on_turn(self, client, event: TurnEvent):
        """Handle transcription turn event with language-specific processing."""
        
        # Skip processing if streaming is paused
        if self.is_paused:
            logger.debug("🚫 SKIPPING - Streaming paused (TTS playing)")
            return
        
        # Language-specific filtering
        if self.language_code == "es":
            # Spanish-specific filtering
            spanish_filler_words = ['eh', 'em', 'este', 'bueno', 'pues', 'entonces', 'o sea']
            min_length = 3  # Spanish words can be shorter
        else:
            # English-specific filtering
            spanish_filler_words = ['um', 'uh', 'ah', 'er', 'like', 'you know']
            min_length = 3
        
        # STRICT FILTERING: Only process finalized, formatted, meaningful phrases
        transcript_text = event.transcript.strip()
        
        if (event.end_of_turn and 
            event.turn_is_formatted and 
            transcript_text and 
            len(transcript_text) > min_length and  # Language-specific minimum length
            transcript_text != self.last_processed_text and  # Avoid duplicates
            not transcript_text.lower() in spanish_filler_words):  # Filter out language-specific filler words
            
            logger.info(f"✅ PROCESSING Finalized phrase ({self.language_code.upper()}): '{transcript_text}'")
            
            # Update last processed text
            self.last_processed_text = transcript_text
            
            # Add to queue for processing
            self.transcription_queue.put((transcript_text, True))
            
            # Call callback if provided
            if self.transcription_callback:
                self.transcription_callback(transcript_text, True)
        
        # DO NOT log partial transcripts - keep them silent
        
        # Enable formatting for better results
        if event.end_of_turn and not event.turn_is_formatted:
            params = StreamingSessionParameters(format_turns=True)
            client.set_params(params)
    
    def _on_terminated(self, client, event: TerminationEvent):
        """Handle session termination event."""
        logger.info(f"AssemblyAI session terminated: {event.audio_duration_seconds} seconds processed")
        self.is_streaming = False
    
    def _on_error(self, client, error: StreamingError):
        """Handle streaming error."""
        logger.error(f"AssemblyAI streaming error: {error}")
        self.is_streaming = False
    
    def start_streaming(self, sample_rate: int = 16000):
        """Start audio streaming to AssemblyAI with optimized settings for language."""
        try:
            # Optimize sample rate based on language
            if self.language_code == "es":
                # Spanish benefits from higher sample rate for better pronunciation recognition
                sample_rate = 44000  # Optimal for Spanish speech recognition
                logger.info(f"🎤 Starting Spanish audio capture at {sample_rate}Hz")
            else:
                # English works well with standard rate
                sample_rate = 44000
                logger.info(f"🎤 Starting English audio capture at {sample_rate}Hz")
            logger.info("Starting audio capture and streaming...")
            
            # Create streaming client
            self.client = StreamingClient(
                StreamingClientOptions(
                    api_key=self.api_key,
                    api_host="streaming.assemblyai.com",
                )
            )
            
            # Set up event handlers
            self.client.on(StreamingEvents.Begin, self._on_begin)
            self.client.on(StreamingEvents.Turn, self._on_turn)
            self.client.on(StreamingEvents.Termination, self._on_terminated)
            self.client.on(StreamingEvents.Error, self._on_error)
            
            # Connect to AssemblyAI with optimized language-specific configuration
            streaming_params = StreamingParameters(
                sample_rate=sample_rate,
                format_turns=True,
                # Configure for specific language input
                language_code=self.language_code,  # Use the configured language
                # Optimized pause detection for Spanish (longer pauses between words)
                end_utterance_silence_threshold=3000 if self.language_code == "es" else 4000,  # Spanish needs shorter pauses
                speech_completion_timeout=12000 if self.language_code == "es" else 10000,  # Spanish sentences can be longer
                # Additional Spanish-specific optimizations
                word_boost=["hola", "gracias", "por favor", "disculpe", "sí", "no", "cómo", "qué", "dónde", "cuándo", "por qué"] if self.language_code == "es" else [],
                # Enable punctuation for better Spanish recognition
                punctuate=True,
                # Enable profanity filter
                profanity_filter=False,
            )
            
            self.client.connect(streaming_params)
            
            self.is_streaming = True
            
            # Start streaming from microphone
            self.client.stream(
                aai.extras.MicrophoneStream(sample_rate=sample_rate)
            )
            
        except Exception as e:
            logger.error(f"Error starting audio streaming: {e}")
            self.is_streaming = False
            raise
    
    def stop_streaming(self):
        """Stop audio streaming."""
        try:
            logger.info("Stopping audio streaming...")
            if self.client:
                self.client.disconnect(terminate=True)
            self.is_streaming = False
        except Exception as e:
            logger.error(f"Error stopping audio streaming: {e}")
    
    def pause_streaming(self):
        """Pause audio streaming to prevent feedback loop."""
        if self.is_streaming and not self.is_paused:
            self.is_paused = True
            logger.info("🔇 Audio streaming paused")
    
    def resume_streaming(self):
        """Resume audio streaming after TTS finishes."""
        if self.is_streaming and self.is_paused:
            self.is_paused = False
            logger.info("🎤 Audio streaming resumed")
    
    def get_transcription(self, timeout: float = 1.0):
        """
        Get the next transcription from the queue.
        
        Args:
            timeout: Timeout in seconds for getting transcription
            
        Returns:
            Tuple of (text, is_finalized) or None if timeout
        """
        try:
            return self.transcription_queue.get(timeout=timeout)
        except queue.Empty:
            return None

def create_audio_capture_manager(api_key: str, transcription_callback: Optional[Callable[[str, bool], None]] = None, language_code: str = "en"):
    """
    Create an audio capture manager instance.
    
    Args:
        api_key: AssemblyAI API key
        transcription_callback: Function to call with transcribed text
        language_code: Language code for speech recognition ("en" for English, "es" for Spanish)
        
    Returns:
        AudioCaptureManager instance
    """
    return AudioCaptureManager(api_key, transcription_callback, language_code)

def test_audio_capture():
    """Test function for audio capture module."""
    logger.info("Testing audio capture module...")
    
    # You'll need to replace this with your actual API key
    api_key = "d8f2f5ddd28646bebe9ccd876bc14773"
    
    def test_callback(text: str, is_finalized: bool):
        logger.info(f"Test callback - Text: '{text}', Finalized: {is_finalized}")
    
    manager = create_audio_capture_manager(api_key, test_callback)
    
    try:
        logger.info("Starting test streaming (press Ctrl+C to stop)...")
        manager.start_streaming()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    finally:
        manager.stop_streaming()
        logger.info("Test completed")

if __name__ == "__main__":
    test_audio_capture()
