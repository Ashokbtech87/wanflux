# YouTube Video Uploader

A Python desktop application for uploading videos to YouTube with multi-channel support.

## Features

- **Multi-Channel Support**: Add and manage multiple YouTube channels with separate credentials
- **Batch Video Upload**: Upload multiple videos at once
- **Frame Analysis**: Analyze video frames for thumbnails
- **YouTube Search**: Search for similar videos on YouTube
- **File Renamer**: Bulk and single file rename utility (chronological sorting)

## Requirements

- Python 3.8+
- Google API credentials (client_secrets.json)

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install google-api-python-client google-auth-oauthlib pillow opencv-python
   ```
3. Place your `client_secrets.json` in the project directory
4. Run the application:
   ```
   python youtube_uploader.py
   ```

## Usage

1. **Add a Channel**: Click "Manage Channels" → "Add Channel" → Select your client_secrets.json
2. **Authenticate**: Select channel and click "Authenticate YouTube"
3. **Upload**: Select videos and click "Upload Selected"

## Files

- `youtube_uploader.py` - Main application
- `channels.json` - Channel configurations
- `token_*.json` - OAuth tokens for each channel

## License

Private repository - All rights reserved
