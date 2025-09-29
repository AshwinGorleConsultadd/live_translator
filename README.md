# Live Audio Translator

A real-time audio translation system that captures speech, transcribes it using AssemblyAI, translates it offline using Argos Translate, converts it to speech using Coqui TTS, and plays it through speakers.

## Features

- **Real-time Audio Capture**: Uses microphone input with AssemblyAI streaming transcription
- **Offline Translation**: Fast local translation using Argos Translate (no internet required after setup)
- **Text-to-Speech**: High-quality speech synthesis using Coqui TTS
- **Low Latency**: Optimized for real-time performance
- **Modular Design**: Each component can be tested independently
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Architecture

The system follows a pipeline architecture with four main steps:

1. **Audio Capture** (`step1_audio_capture.py`): Captures microphone audio and streams to AssemblyAI
2. **Translation** (`step2_translation.py`): Translates transcribed text using Argos Translate
3. **Text-to-Speech** (`step3_tts.py`): Converts translated text to audio using Coqui TTS
4. **Audio Output** (`step4_audio_output.py`): Plays generated audio through speakers

## Installation

### Prerequisites

- Python 3.8 or higher
- Microphone and speakers/headphones
- AssemblyAI API key

### Setup

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Get AssemblyAI API Key**:
   - Sign up at [AssemblyAI](https://www.assemblyai.com/)
   - Get your API key from the dashboard
   - Update the `ASSEMBLYAI_API_KEY` variable in `entry_point.py`

4. **Download Translation Models** (first run will download automatically):
   ```bash
   python step2_translation.py
   ```

5. **Download TTS Models** (first run will download automatically):
   ```bash
   python step3_tts.py
   ```

## Usage

### Running the Live Translator

```bash
python entry_point.py
```

The system will:
1. Initialize all components
2. Start listening to your microphone
3. Transcribe speech in real-time
4. Translate finalized phrases
5. Convert to speech and play through speakers

Press `Ctrl+C` to stop.

### Testing Individual Components

Test each component separately:

```bash
python entry_point.py test
```

Or test individual components:

```bash
python step1_audio_capture.py    # Test audio capture
python step2_translation.py     # Test translation
python step3_tts.py            # Test text-to-speech
python step4_audio_output.py   # Test audio output
```

## Configuration

### Languages

Edit `entry_point.py` to change source and target languages:

```python
SOURCE_LANGUAGE = "en"  # English
TARGET_LANGUAGE = "es"  # Spanish
```

### TTS Model

Change the TTS model in `entry_point.py`:

```python
TTS_MODEL = "tts_models/en/ljspeech/tacotron2-DDC"  # Default English
```

For multilingual support, consider:
- `tts_models/multilingual/multi-dataset/your_tts` (multilingual)
- `tts_models/es/css10/vits` (Spanish)

### Audio Settings

Modify audio settings in the respective modules:

- **Sample Rate**: Default 16000 Hz for capture, 22050 Hz for output
- **Channels**: Default mono (1 channel)
- **Audio Device**: Automatically detects default device

## Available Languages

### Argos Translate Languages

Common language pairs available:
- English ↔ Spanish (`en` ↔ `es`)
- English ↔ French (`en` ↔ `fr`)
- English ↔ German (`en` ↔ `de`)
- English ↔ Italian (`en` ↔ `it`)
- English ↔ Portuguese (`en` ↔ `pt`)
- And many more...

To see all available languages:
```python
from step2_translation import get_available_languages
languages = get_available_languages()
for lang in languages:
    print(f"{lang[0]} -> {lang[1]}: {lang[2]} -> {lang[3]}")
```

### TTS Languages

TTS models are available for many languages. Check available models:
```python
from step3_tts import get_multilingual_models
models = get_multilingual_models()
print(models)
```

## Troubleshooting

### Common Issues

1. **Microphone not working**:
   - Check microphone permissions
   - Verify microphone is not being used by another application
   - Test with: `python step1_audio_capture.py`

2. **Translation not working**:
   - Ensure internet connection for initial model download
   - Check if language pair is supported
   - Test with: `python step2_translation.py`

3. **TTS not working**:
   - Check if TTS model is downloaded
   - Verify audio output device
   - Test with: `python step3_tts.py`

4. **Audio output issues**:
   - Check speaker/headphone connection
   - Verify audio device settings
   - Test with: `python step4_audio_output.py`

### Logging

Logs are saved in the `logs/` directory with timestamps. Check logs for detailed error information.

### Performance Tips

1. **Lower Latency**:
   - Use faster TTS models
   - Reduce audio buffer sizes
   - Use SSD storage for temp files

2. **Better Quality**:
   - Use higher quality TTS models
   - Ensure good microphone quality
   - Use appropriate language models

## File Structure

```
translator/
├── entry_point.py              # Main orchestrator
├── logging_config.py          # Logging configuration
├── step1_audio_capture.py     # Audio capture and transcription
├── step2_translation.py       # Translation using Argos Translate
├── step3_tts.py              # Text-to-speech using Coqui TTS
├── step4_audio_output.py     # Audio output and playback
├── requirements.txt          # Python dependencies
├── README.md                # This file
└── logs/                    # Log files (created automatically)
```

## Dependencies

- `assemblyai`: Real-time speech transcription
- `argostranslate`: Offline translation
- `TTS`: Text-to-speech synthesis
- `sounddevice`: Audio I/O
- `soundfile`: Audio file handling
- `numpy`: Numerical operations
- `scipy`: Signal processing (for resampling)

## License

This project is open source. Please ensure you comply with the licenses of the individual components:
- AssemblyAI: Check their terms of service
- Argos Translate: MIT License
- Coqui TTS: MPL 2.0 License

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the system.
