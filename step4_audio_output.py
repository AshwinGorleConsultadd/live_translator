import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import time
import os
from typing import Optional, Callable
from logging_config import get_logger

logger = get_logger('audio_output')

class AudioOutputManager:
    """Manages audio output streaming to speakers."""
    
    def __init__(self, sample_rate: int = 22050, channels: int = 1,
                 audio_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the audio output manager.
        
        Args:
            sample_rate: Audio sample rate
            channels: Number of audio channels
            audio_callback: Function to call when audio playback starts/ends
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_callback = audio_callback
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.playback_thread = None
        self.stop_playback = False
        
        # Initialize audio device
        self._init_audio_device()
    
    def _init_audio_device(self):
        """Initialize audio device and check capabilities."""
        try:
            logger.info("Initializing audio output device...")
            
            # Get default output device info
            device_info = sd.query_devices(kind='output')
            logger.info(f"Default output device: {device_info['name']}")
            logger.info(f"Sample rate range: {device_info['default_samplerate']}")
            
            # Test audio device
            test_audio = np.zeros(int(self.sample_rate * 0.1), dtype=np.float32)
            sd.play(test_audio, samplerate=self.sample_rate)
            sd.wait()
            
            logger.info("Audio output device initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize audio device: {e}")
            raise
    
    def play_audio_file(self, audio_path: str) -> bool:
        """
        Play an audio file through speakers.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            True if playback successful, False otherwise
        """
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return False
        
        try:
            logger.info(f"Playing audio file: {audio_path}")
            
            # Load audio file
            audio_data, sample_rate = sf.read(audio_path, dtype='float32')
            
            # Resample if necessary
            if sample_rate != self.sample_rate:
                logger.info(f"Resampling from {sample_rate} to {self.sample_rate}")
                from scipy import signal
                audio_data = signal.resample(audio_data, 
                                          int(len(audio_data) * self.sample_rate / sample_rate))
            
            # Ensure correct number of channels
            if len(audio_data.shape) == 1:
                audio_data = audio_data.reshape(-1, 1)
            elif audio_data.shape[1] != self.channels:
                if self.channels == 1:
                    audio_data = np.mean(audio_data, axis=1, keepdims=True)
                else:
                    logger.warning(f"Channel mismatch: expected {self.channels}, got {audio_data.shape[1]}")
            
            # Play audio
            self.is_playing = True
            if self.audio_callback:
                self.audio_callback(f"Started playing: {audio_path}")
            
            sd.play(audio_data, samplerate=self.sample_rate)
            sd.wait()  # Wait for playback to complete
            
            self.is_playing = False
            if self.audio_callback:
                self.audio_callback(f"Finished playing: {audio_path}")
            
            logger.debug(f"Audio playback completed: {audio_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error playing audio file {audio_path}: {e}")
            self.is_playing = False
            return False
    
    def queue_audio(self, audio_path: str):
        """
        Queue audio file for playback.
        
        Args:
            audio_path: Path to the audio file
        """
        if audio_path and os.path.exists(audio_path):
            logger.info(f"Queuing audio for playback: {audio_path}")
            self.audio_queue.put(audio_path)
    
    def start_playback_thread(self):
        """Start the audio playback thread."""
        if self.playback_thread is None or not self.playback_thread.is_alive():
            self.stop_playback = False
            self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.playback_thread.start()
            logger.info("Audio playback thread started")
    
    def stop_playback_thread(self):
        """Stop the audio playback thread."""
        self.stop_playback = True
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
        logger.info("Audio playback thread stopped")
    
    def _playback_worker(self):
        """Worker thread for processing audio queue."""
        logger.info("Audio playback worker started")
        
        while not self.stop_playback:
            try:
                audio_path = self.audio_queue.get(timeout=1.0)
                self.play_audio_file(audio_path)
                
                # Clean up the audio file after playing
                try:
                    os.remove(audio_path)
                except Exception as e:
                    logger.warning(f"Could not clean up audio file {audio_path}: {e}")
                    
            except queue.Empty:
                continue  # No audio to play
            except Exception as e:
                logger.error(f"Error in playback worker: {e}")
        
        logger.info("Audio playback worker stopped")
    
    def get_audio_devices(self) -> list:
        """
        Get list of available audio output devices.
        
        Returns:
            List of audio device information
        """
        try:
            devices = sd.query_devices()
            device_list = []
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:  # Only output devices
                    device_list.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_output_channels'],
                        'sample_rate': device['default_samplerate']
                    })
            return device_list
        except Exception as e:
            logger.error(f"Error getting audio devices: {e}")
            return []
    
    def set_audio_device(self, device_index: int):
        """
        Set the audio output device.
        
        Args:
            device_index: Index of the audio device to use
        """
        try:
            sd.default.device[1] = device_index  # Set output device
            logger.info(f"Set audio output device to index {device_index}")
        except Exception as e:
            logger.error(f"Error setting audio device: {e}")

def create_audio_output_manager(sample_rate: int = 22050, channels: int = 1,
                               audio_callback: Optional[Callable[[str], None]] = None):
    """
    Create an audio output manager instance.
    
    Args:
        sample_rate: Audio sample rate
        channels: Number of audio channels
        audio_callback: Function to call when audio playback starts/ends
        
    Returns:
        AudioOutputManager instance
    """
    return AudioOutputManager(sample_rate, channels, audio_callback)

def test_audio_output():
    """Test function for audio output module."""
    logger.info("Testing audio output module...")
    
    def test_callback(message: str):
        logger.info(f"Test callback - {message}")
    
    try:
        manager = create_audio_output_manager(audio_callback=test_callback)
        
        # List available devices
        devices = manager.get_audio_devices()
        logger.info("Available audio devices:")
        for device in devices:
            logger.info(f"  {device['index']}: {device['name']} "
                       f"(channels: {device['channels']}, sample_rate: {device['sample_rate']})")
        
        # Test with a simple tone (if no audio file available)
        logger.info("Testing audio output with generated tone...")
        
        # Generate a simple test tone
        duration = 2.0  # seconds
        frequency = 440  # Hz (A note)
        t = np.linspace(0, duration, int(manager.sample_rate * duration), False)
        test_audio = np.sin(frequency * 2 * np.pi * t).astype(np.float32)
        
        # Save test audio to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, test_audio, manager.sample_rate)
            test_audio_path = tmp_file.name
        
        # Test playback
        success = manager.play_audio_file(test_audio_path)
        
        # Clean up
        os.remove(test_audio_path)
        
        if success:
            logger.info("Audio output test completed successfully")
        else:
            logger.error("Audio output test failed")
        
    except Exception as e:
        logger.error(f"Audio output test failed: {e}")

if __name__ == "__main__":
    test_audio_output()
