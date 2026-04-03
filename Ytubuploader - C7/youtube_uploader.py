#!/usr/bin/env python3
"""
YouTube Video Uploader with AI-Powered Metadata Generation
Features:
- Extract random frames from videos
- Analyze frames using Ollama vision models
- Search YouTube for related high-view videos
- Generate optimized metadata
- Automatic frame cleanup after confirmation
"""

import os
import json
import re
import time
import threading
import random
import cv2
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image
import tempfile
from dotenv import load_dotenv
import subprocess

# Load environment variables
load_dotenv()

# YouTube API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Ollama import
from ollama import chat

# Configuration
CLIENT_SECRETS_FILE = r'C:\Users\ashok\Downloads\Python_Apps\client_secret.json'
TOKEN_FILE = 'token.json'
CHANNELS_FILE = r'C:\Users\ashok\Downloads\Python_Apps\Ytubuploader - Copy (2)\channels.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/yt-analytics.readonly']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
PROMPT_FILE = r'C:\Users\ashok\Downloads\Python_Apps\Ytubuploader\prompt.txt'
VIRAL_PROMPT_FILE = r'C:\Users\ashok\Downloads\Python_Apps\Ytubuploader\prompt_viral.txt'
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']

# Import viral optimizer
try:
    from viral_optimizer_fast import ViralSEOOptimizer, ViralMetricsTracker
    VIRAL_OPTIMIZER_AVAILABLE = True
except ImportError:
    try:
        from viral_optimizer import ViralSEOOptimizer, ViralMetricsTracker
        VIRAL_OPTIMIZER_AVAILABLE = True
    except ImportError:
        VIRAL_OPTIMIZER_AVAILABLE = False


class VideoFrameExtractor:
    """Extract random frames from video at different intervals"""
    
    @staticmethod
    def extract_random_frames(video_path, num_frames=8, output_dir=None):
        """
        Extract random frames from different intervals of the video
        Returns list of frame file paths
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        if total_frames < num_frames:
            num_frames = max(1, total_frames // 2)
        
        # Divide video into segments and pick random frame from each
        segment_size = total_frames // num_frames
        frame_positions = []
        
        for i in range(num_frames):
            start = i * segment_size
            end = (i + 1) * segment_size if i < num_frames - 1 else total_frames
            frame_pos = random.randint(start, max(start, end - 1))
            frame_positions.append(frame_pos)
        
        # Extract frames
        for idx, frame_pos in enumerate(frame_positions):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Save frame
                frame_path = os.path.join(output_dir, f"frame_{idx+1:03d}.jpg")
                pil_image = Image.fromarray(frame_rgb)
                pil_image.save(frame_path, quality=85)
                frames.append(frame_path)
        
        cap.release()
        return frames, duration


class OllamaImageAnalyzer:
    """Analyze video frames using Ollama vision models"""
    
    @staticmethod
    def analyze_frames(frame_paths, model="llama3.2-vision:latest"):
        """
        Analyze multiple frames and return content description
        """
        descriptions = []
        
        for frame_path in frame_paths:
            try:
                prompt = """Analyze this video frame and describe:
1. What is happening in the scene
2. Main subjects/objects visible
3. Setting/location
4. Any text or logos visible
5. Overall mood/atmosphere

Be concise but descriptive."""
                
                response = chat(
                    model=model,
                    messages=[{
                        'role': 'user',
                        'content': prompt,
                        'images': [frame_path]
                    }]
                )
                
                descriptions.append(response.message.content)
            except Exception as e:
                descriptions.append(f"Error analyzing frame: {str(e)}")
        
        return descriptions
    
    @staticmethod
    def summarize_content(descriptions, video_duration, model="kimi-k2.5:cloud"):
        """
        Summarize all frame descriptions into video content summary
        """
        combined_desc = "\n\n".join([f"Frame {i+1}: {desc}" for i, desc in enumerate(descriptions)])
        
        prompt = f"""Based on these {len(descriptions)} frames from a {video_duration:.1f} second video, provide:

FRAME DESCRIPTIONS:
{combined_desc}

Please provide:
1. Overall video topic/theme (be specific)
2. Main content category (e.g., tutorial, entertainment, educational, music, gaming, etc.)
3. Target audience
4. Key visual elements that would attract viewers
5. Suggested keywords based on visual content

Format your response clearly with headers."""
        
        response = chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        return response.message.content


class YouTubeSearcher:
    """Search YouTube for related high-view videos"""
    
    def __init__(self, youtube_service):
        self.youtube = youtube_service
    
    def search_related_videos(self, query, max_results=5, days_filter=None, region_code=None):
        """
        Search for related videos and return top performers
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            days_filter (int, optional): Filter results published in the last X days
            
        Returns:
            list: List of dictionaries containing video metadata
        """
        try:
            # Prepare search parameters
            search_params = {
                'q': query,
                'type': 'video',
                'part': 'id,snippet',
                'maxResults': max_results,
                'order': 'viewCount'  # Sort by view count
            }
            
            if region_code:
                search_params['regionCode'] = region_code
            
            # Add date filter if specified
            if days_filter and int(days_filter) > 0:
                # Calculate the date X days ago
                published_after = datetime.utcnow() - timedelta(days=int(days_filter))
                # Format to RFC 3339 timestamp (e.g., 1970-01-01T00:00:00Z)
                search_params['publishedAfter'] = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            search_response = self.youtube.search().list(**search_params).execute()
            
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            if not video_ids:
                return []
            
            return self._get_video_details(video_ids)
            
        except Exception as e:
            print(f"Error searching YouTube: {e}")
            return []

    def get_trending_videos(self, max_results=100, region_code='US'):
        """
        Get current top trending videos on YouTube
        """
        try:
            video_ids = []
            next_page_token = None
            
            while len(video_ids) < max_results:
                # Calculate how many more we need
                remaining = max_results - len(video_ids)
                limit = min(remaining, 50)  # API max is 50
                
                request = self.youtube.videos().list(

                    part='id',
                    chart='mostPopular',
                    regionCode=region_code,
                    maxResults=limit,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                new_ids = [item['id'] for item in response.get('items', [])]
                video_ids.extend(new_ids)

                
                next_page_token = response.get('nextPageToken')
                if not next_page_token or not new_ids:
                    break
            
            if not video_ids:
                return []
                
            return self._get_video_details(video_ids)
            
        except Exception as e:
            print(f"Error fetching trending videos: {e}")
            return []

    def get_video_categories(self, region_code='US'):
        """Fetch available video categories for a region"""
        try:
            response = self.youtube.videoCategories().list(
                part='snippet',
                regionCode=region_code
            ).execute()
            
            categories = {}
            for item in response.get('items', []):
                if item['snippet'].get('assignable', True):
                    categories[item['snippet']['title']] = item['id']
            return categories
        except Exception as e:
            print(f"Error fetching categories: {e}")
            return {}

    def get_trending_by_category(self, category_id, max_results=50, region_code='US'):
        """Get trending videos for a specific category"""
        try:
            request = self.youtube.videos().list(
                part='id',
                chart='mostPopular',
                regionCode=region_code,
                videoCategoryId=category_id,
                maxResults=max_results
            )
            response = request.execute()
            
            video_ids = [item['id'] for item in response.get('items', [])]
            if not video_ids:
                return []
                
            return self._get_video_details(video_ids)
        except Exception as e:
            print(f"Error fetching trending by category: {e}")
            return []

    def get_audience_analytics(self, start_date, end_date):
        """Fetch audience demographics and top videos from YouTube Analytics API"""
        try:
            from googleapiclient.discovery import build
            
            # Create an analytics service using the existing credentials
            credentials = self.youtube._http.credentials
            analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
            
            # Fetch demographics
            demographics_response = analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='viewerPercentage',
                dimensions='ageGroup,gender',
                sort='-viewerPercentage'
            ).execute()
            
            # Fetch geography
            geography_response = analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='views,estimatedMinutesWatched',
                dimensions='country',
                sort='-views',
                maxResults=10
            ).execute()
            
            # Fetch top videos by engagement (retention/duration)
            videos_response = analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='views,estimatedMinutesWatched,averageViewDuration',
                dimensions='video',
                sort='-views',
                maxResults=15
            ).execute()
            
            return {
                'demographics': demographics_response,
                'geography': geography_response,
                'top_videos': videos_response
            }
        except Exception as e:
            print(f"Error fetching audience analytics: {e}")
            return None

    def _get_video_details(self, video_ids):
        """Helper to get detailed video stats for a list of IDs"""
        try:
            # Process in chunks of 50 (API limit)
            all_results = []
            
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i:i+50]
                
                videos_response = self.youtube.videos().list(
                    part='statistics,snippet,contentDetails,recordingDetails',
                    id=','.join(chunk)
                ).execute()
                
                items = videos_response.get('items', [])
                
                # Collect channel IDs to fetch country
                channel_ids = list(set(item['snippet']['channelId'] for item in items if 'channelId' in item['snippet']))
                channel_country_map = {}
                
                if channel_ids:
                    try:
                        channels_response = self.youtube.channels().list(
                            part='snippet,brandingSettings,statistics',
                            id=','.join(channel_ids)
                        ).execute()
                        for ch in channels_response.get('items', []):
                            channel_country_map[ch['id']] = {
                                'country': ch['snippet'].get('country', 'N/A'),
                                'keywords': ch.get('brandingSettings', {}).get('channel', {}).get('keywords', ''),
                                'subscriber_count': int(ch.get('statistics', {}).get('subscriberCount', 0))
                            }
                    except Exception as e:
                        print(f"Error fetching channel details: {e}")

                for item in items:
                    stats = item['statistics']
                    snippet = item['snippet']
                    content_details = item['contentDetails']
                    recording_details = item.get('recordingDetails', {})
                    
                    # Parse duration (ISO 8601 format like PT1H2M10S)
                    duration_iso = content_details.get('duration', '')
                    duration_str = self._parse_duration(duration_iso)
                    
                    # Format published date
                    published_at = snippet.get('publishedAt', '')
                    try:
                        # Basic parsing of ISO format to readable date
                        pub_dt = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%SZ')
                        published_date = pub_dt.strftime('%Y-%m-%d')
                    except:
                        published_date = published_at.split('T')[0]
                    
                    channel_id = snippet.get('channelId')
                    
                    all_results.append({
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'views': int(stats.get('viewCount', 0)),
                        'likes': int(stats.get('likeCount', 0)),
                        'video_id': item['id'],
                        'tags': snippet.get('tags', []),
                        'category_id': snippet.get('categoryId', '22'),
                        'duration': duration_str,
                        'published_at': published_date,
                        'channel_title': snippet.get('channelTitle', ''),
                        'subscriber_count': channel_country_map.get(channel_id, {}).get('subscriber_count', 0) if isinstance(channel_country_map.get(channel_id), dict) else 0,
                        'country': channel_country_map.get(channel_id, {}).get('country', 'N/A') if isinstance(channel_country_map.get(channel_id), dict) else 'N/A',
                        'channel_tags': channel_country_map.get(channel_id, {}).get('keywords', '') if isinstance(channel_country_map.get(channel_id), dict) else '',
                        'location': recording_details.get('locationDescription', '')
                    })
            
            # Sort by view count descending
            all_results.sort(key=lambda x: x['views'], reverse=True)
            
            return all_results
            
        except Exception as e:
            print(f"Error getting video details: {e}")
            return []
            
    def _parse_duration(self, duration_iso):
        """Parse ISO 8601 duration (PT#H#M#S) to human readable string"""
        try:
            import re
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
            if not match:
                return duration_iso
                
            hours, minutes, seconds = match.groups()
            hours = int(hours) if hours else 0
            minutes = int(minutes) if minutes else 0
            seconds = int(seconds) if seconds else 0
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        except:
            return duration_iso


class YouTubeUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Uploader with AI Vision Analysis")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Variables
        self.video_files = []
        self.current_video_index = 0
        self.youtube_service = None
        self.is_uploading = False
        self.is_processing = False  # Track if processing is in progress
        self.prompt_template = self.load_prompt_template()
        self.extracted_frames = []  # Track extracted frames for cleanup
        self.youtube_searcher = None
        self.last_analysis = None  # Store frame analysis results
        self.last_search_results = None  # Store YouTube search results
        
        # Channel management variables
        self.channels = []  # List of channel configurations
        self.current_channel = None  # Currently selected channel
        self.channel_var = tk.StringVar()  # For channel dropdown
        
        # Load channels configuration
        self.load_channels()
        
        # Create UI
        self.create_ui()
        
        # Check for credentials
        self.check_credentials()
    
    def load_prompt_template(self):
        """Load the prompt template from file"""
        try:
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load prompt.txt: {e}")
            return ""
    
    def load_channels(self):
        """Load channels configuration from file"""
        try:
            if os.path.exists(CHANNELS_FILE):
                with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.channels = data.get('channels', [])
                    
                    # Set current channel to default or first channel
                    for channel in self.channels:
                        if channel.get('is_default', False):
                            self.current_channel = channel
                            break
                    
                    if not self.current_channel and self.channels:
                        self.current_channel = self.channels[0]
            else:
                # Check for existing token.json and offer migration
                if os.path.exists(TOKEN_FILE):
                    self.migrate_existing_channel()
                else:
                    self.channels = []
                    self.save_channels()
        except Exception as e:
            print(f"Error loading channels: {e}")
            self.channels = []
    
    def migrate_existing_channel(self):
        """Migrate existing token.json to a channel entry"""
        result = messagebox.askyesno(
            "Migrate Existing Channel",
            "Found existing YouTube credentials (token.json).\n\n"
            "Would you like to import this as your first channel?"
        )
        
        if result:
            channel = {
                'name': 'Default Channel',
                'token_file': 'token.json',
                'client_secrets': CLIENT_SECRETS_FILE,
                'is_default': True
            }
            self.channels = [channel]
            self.current_channel = channel
            self.save_channels()
            self.log("✓ Migrated existing credentials as 'Default Channel'")
        else:
            self.channels = []
            self.save_channels()
    
    def save_channels(self):
        """Save channels configuration to file"""
        try:
            data = {'channels': self.channels}
            with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving channels: {e}")
    
    def open_channel_manager(self):
        """Open channel management dialog"""
        manager = tk.Toplevel(self.root)
        manager.title("Manage YouTube Channels")
        manager.geometry("500x400")
        manager.transient(self.root)
        manager.grab_set()
        
        # Channel list frame
        list_frame = ttk.LabelFrame(manager, text="Your Channels", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Channel listbox
        self.channel_listbox = tk.Listbox(list_frame, height=10)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.channel_listbox.yview)
        self.channel_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.channel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate listbox
        self.refresh_channel_listbox()
        
        # Buttons frame
        btn_frame = ttk.Frame(manager)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Add Channel", command=lambda: self.add_channel(manager)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Remove Channel", command=lambda: self.delete_channel(manager)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Set as Default", command=lambda: self.set_default_channel(manager)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=manager.destroy).pack(side=tk.RIGHT)
        
        # Info label
        info_label = ttk.Label(manager, text="💡 Each channel uses separate YouTube credentials", foreground="gray")
        info_label.pack(pady=(0, 10))
    
    def refresh_channel_listbox(self):
        """Refresh the channel listbox in the manager"""
        if hasattr(self, 'channel_listbox'):
            self.channel_listbox.delete(0, tk.END)
            for channel in self.channels:
                name = channel['name']
                if channel.get('is_default', False):
                    name += " ⭐ (Default)"
                self.channel_listbox.insert(tk.END, name)
    
    def update_channel_dropdown(self):
        """Update the channel dropdown with current channels"""
        if hasattr(self, 'channel_combo'):
            channel_names = [ch['name'] for ch in self.channels]
            self.channel_combo['values'] = channel_names if channel_names else ['No channels configured']
            
            if self.current_channel:
                self.channel_var.set(self.current_channel['name'])
            elif channel_names:
                self.channel_var.set(channel_names[0])
            else:
                self.channel_var.set('No channels configured')
    
    def add_channel(self, manager_window=None):
        """Add a new YouTube channel"""
        # Get channel name and client secrets from user
        name_dialog = tk.Toplevel(manager_window if manager_window else self.root)
        name_dialog.title("Add New Channel")
        name_dialog.geometry("500x220")
        name_dialog.transient(manager_window if manager_window else self.root)
        name_dialog.grab_set()
        
        # Channel name
        ttk.Label(name_dialog, text="Channel Name:").pack(anchor=tk.W, padx=20, pady=(20, 5))
        name_entry = ttk.Entry(name_dialog, width=50)
        name_entry.pack(padx=20, pady=(0, 10))
        name_entry.focus_set()
        
        # Client secrets file
        ttk.Label(name_dialog, text="Client Secrets File (client_secrets.json):").pack(anchor=tk.W, padx=20, pady=(5, 5))
        
        secrets_frame = ttk.Frame(name_dialog)
        secrets_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        secrets_var = tk.StringVar(value=CLIENT_SECRETS_FILE)
        secrets_entry = ttk.Entry(secrets_frame, textvariable=secrets_var, width=40)
        secrets_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def browse_secrets():
            file_path = filedialog.askopenfilename(
                title="Select Client Secrets File",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir=os.path.dirname(CLIENT_SECRETS_FILE)
            )
            if file_path:
                secrets_var.set(file_path)
        
        ttk.Button(secrets_frame, text="Browse...", command=browse_secrets).pack(side=tk.LEFT, padx=(5, 0))
        
        def do_add():
            channel_name = name_entry.get().strip()
            client_secrets = secrets_var.get().strip()
            
            if not channel_name:
                messagebox.showwarning("Warning", "Please enter a channel name")
                return
            
            if not client_secrets or not os.path.exists(client_secrets):
                messagebox.showwarning("Warning", "Please select a valid client_secrets.json file")
                return
            
            # Check for duplicate names
            for ch in self.channels:
                if ch['name'].lower() == channel_name.lower():
                    messagebox.showwarning("Warning", f"A channel named '{channel_name}' already exists")
                    return
            
            # Generate token filename
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', channel_name.lower())
            token_file = f"token_{safe_name}.json"
            
            name_dialog.destroy()
            
            try:
                self.log(f"Adding new channel: {channel_name}")
                self.log(f"Using client secrets: {os.path.basename(client_secrets)}")
                self.log("Starting OAuth authentication...")
                
                # Authenticate for this channel with its specific client secrets
                youtube_service = get_authenticated_service(token_file, client_secrets)
                
                # Create channel entry
                channel = {
                    'name': channel_name,
                    'token_file': token_file,
                    'client_secrets': client_secrets,
                    'is_default': len(self.channels) == 0  # First channel is default
                }
                
                self.channels.append(channel)
                self.save_channels()
                
                # Set as current if it's the first
                if len(self.channels) == 1:
                    self.current_channel = channel
                    self.youtube_service = youtube_service
                    self.youtube_searcher = YouTubeSearcher(self.youtube_service)
                
                self.log(f"✅ Channel '{channel_name}' added successfully!")
                messagebox.showinfo("Success", f"Channel '{channel_name}' has been added!")
                
                # Refresh UI
                self.refresh_channel_listbox()
                self.update_channel_dropdown()
                
            except Exception as e:
                self.log(f"❌ Failed to add channel: {e}")
                messagebox.showerror("Error", f"Failed to add channel: {e}")
        
        btn_frame = ttk.Frame(name_dialog)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Add & Authenticate", command=do_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=name_dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key
        name_entry.bind('<Return>', lambda e: do_add())
    
    def delete_channel(self, manager_window=None):
        """Delete selected channel"""
        if not hasattr(self, 'channel_listbox'):
            return
        
        selection = self.channel_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to delete")
            return
        
        index = selection[0]
        channel = self.channels[index]
        
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{channel['name']}'?\n\n"
            "This will remove the channel configuration but keep the token file."
        )
        
        if result:
            # Remove from list
            del self.channels[index]
            
            # If this was the current channel, switch to another
            if self.current_channel == channel:
                if self.channels:
                    self.current_channel = self.channels[0]
                    self.current_channel['is_default'] = True
                else:
                    self.current_channel = None
                    self.youtube_service = None
            
            self.save_channels()
            self.refresh_channel_listbox()
            self.update_channel_dropdown()
            self.log(f"Deleted channel: {channel['name']}")
    
    def set_default_channel(self, manager_window=None):
        """Set selected channel as default"""
        if not hasattr(self, 'channel_listbox'):
            return
        
        selection = self.channel_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to set as default")
            return
        
        index = selection[0]
        
        # Clear existing default
        for ch in self.channels:
            ch['is_default'] = False
        
        # Set new default
        self.channels[index]['is_default'] = True
        self.save_channels()
        self.refresh_channel_listbox()
        
        self.log(f"Set '{self.channels[index]['name']}' as default channel")
        messagebox.showinfo("Success", f"'{self.channels[index]['name']}' is now the default channel")
    
    def on_channel_select(self, event=None):
        """Handle channel selection change"""
        selected_name = self.channel_var.get()
        
        if selected_name == 'No channels configured':
            return
        
        # Find the selected channel
        for channel in self.channels:
            if channel['name'] == selected_name:
                if self.current_channel != channel:
                    self.current_channel = channel
                    self.youtube_service = None  # Reset service
                    self.youtube_searcher = None
                    self.log(f"Switched to channel: {channel['name']}")
                    self.update_channel_status()
                break
    
    def update_channel_status(self):
        """Update the channel status label"""
        if hasattr(self, 'channel_status_label'):
            if not self.channels:
                self.channel_status_label.configure(text="⚠️ No channels configured", foreground="orange")
            elif self.youtube_service:
                self.channel_status_label.configure(text="✅ Authenticated", foreground="green")
            else:
                self.channel_status_label.configure(text="🔒 Not authenticated", foreground="gray")
        
        if hasattr(self, 'status_label') and self.current_channel:
            if self.youtube_service:
                self.status_label.configure(text=f"Ready - Channel: {self.current_channel['name']}")
            else:
                self.status_label.configure(text=f"Channel: {self.current_channel['name']} (click 'Authenticate YouTube')")

    
    def create_ui(self):
        """Create the user interface"""
        # Main container with notebook for tabs
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Video Selection & Upload
        self.upload_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.upload_tab, text="Upload Videos")
        self.create_upload_tab()
        
        # Tab 2: Frame Analysis & Preview
        self.analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_tab, text="Frame Analysis")
        self.create_analysis_tab()
        
        # Tab 3: Search Results
        self.search_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.search_tab, text="YouTube Search Results")
        self.create_search_tab()
        
        # Tab 4: File Renamer
        self.renamer_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.renamer_tab, text="📁 File Renamer")
        self.create_renamer_tab()
        
        # Tab 5: YT Analyzer
        self.analyzer_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.analyzer_tab, text="🔍 YT Analyzer")
        self.create_analyzer_tab()
    
    def create_upload_tab(self):
        """Create the upload tab UI"""
        frame = ttk.Frame(self.upload_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)
        
        # === File Selection Section ===
        file_frame = ttk.LabelFrame(frame, text="Video Selection", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="Browse Folder", command=self.browse_folder).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(file_frame, text="Select Files", command=self.select_files).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="Clear Selection", command=self.clear_selection).grid(row=0, column=2, padx=(5, 0))
        
        self.file_count_label = ttk.Label(file_frame, text="No files selected")
        self.file_count_label.grid(row=0, column=3, padx=(20, 0))
        
        # === Channel Selection Section ===
        channel_frame = ttk.LabelFrame(frame, text="YouTube Channel", padding="10")
        channel_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ttk.Label(channel_frame, text="Upload to:").grid(row=0, column=0, sticky=tk.W)
        
        # Channel dropdown
        channel_names = [ch['name'] for ch in self.channels] if self.channels else ['No channels configured']
        self.channel_combo = ttk.Combobox(channel_frame, textvariable=self.channel_var,
                                          values=channel_names,
                                          state="readonly", width=30)
        self.channel_combo.grid(row=0, column=1, padx=(5, 10), sticky=tk.W)
        self.channel_combo.bind('<<ComboboxSelected>>', self.on_channel_select)
        
        # Set initial value
        if self.current_channel:
            self.channel_var.set(self.current_channel['name'])
        elif channel_names:
            self.channel_var.set(channel_names[0])
        
        ttk.Button(channel_frame, text="📺 Manage Channels", command=self.open_channel_manager).grid(row=0, column=2, padx=(0, 10))
        
        # Channel status label
        self.channel_status_label = ttk.Label(channel_frame, text="", foreground="gray")
        self.channel_status_label.grid(row=0, column=3, padx=(10, 0))
        self.update_channel_status()
        
        # === Settings Section ===
        settings_frame = ttk.LabelFrame(frame, text="Upload Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Privacy setting
        ttk.Label(settings_frame, text="Privacy:").grid(row=0, column=0, sticky=tk.W)
        self.privacy_var = tk.StringVar(value="private")
        privacy_combo = ttk.Combobox(settings_frame, textvariable=self.privacy_var, 
                                     values=["private", "unlisted", "public"], 
                                     state="readonly", width=15)
        privacy_combo.grid(row=0, column=1, padx=(5, 20), sticky=tk.W)
        
        # Category setting
        ttk.Label(settings_frame, text="Category:").grid(row=0, column=2, sticky=tk.W)
        self.category_var = tk.StringVar(value="22")
        category_combo = ttk.Combobox(settings_frame, textvariable=self.category_var,
                                      values=["22 - People & Blogs", "24 - Entertainment", 
                                             "27 - Education", "28 - Science & Technology"],
                                      state="readonly", width=20)
        category_combo.grid(row=0, column=3, padx=(5, 20), sticky=tk.W)
        
        # AI Model setting for Viral Mode
        ttk.Label(settings_frame, text="AI Model:").grid(row=0, column=4, sticky=tk.W)
        self.model_var = tk.StringVar(value="kimi-k2.5:cloud")
        model_combo = ttk.Combobox(settings_frame, textvariable=self.model_var,
                                   values=["kimi-k2.5:cloud (Viral - Cloud)", "llama3.2 (Fast - Local)", "mistral (Fast - Local)", "llama3.2-vision:latest (Vision - GPU)"],
                                   state="readonly", width=28)
        model_combo.grid(row=0, column=5, padx=(5, 0), sticky=tk.W)
        
        # Frame extraction settings
        ttk.Label(settings_frame, text="Frames to Extract:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.frame_count_var = tk.IntVar(value=8)
        frame_spin = ttk.Spinbox(settings_frame, from_=5, to=10, textvariable=self.frame_count_var, width=5)
        frame_spin.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(settings_frame, text="Vision Model:").grid(row=1, column=2, sticky=tk.W, pady=(10, 0))
        self.vision_model_var = tk.StringVar(value="moondream")
        vision_combo = ttk.Combobox(settings_frame, textvariable=self.vision_model_var,
                                    values=["moondream", "kimi-k2.5:cloud", "llama3.2-vision:latest"],
                                    state="readonly", width=20)
        vision_combo.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # Viral Mode Toggle
        self.viral_mode_var = tk.BooleanVar(value=True)
        viral_check = ttk.Checkbutton(settings_frame, text="🔥 VIRAL MODE (Millions of Views)", 
                                      variable=self.viral_mode_var)
        viral_check.grid(row=1, column=4, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        # === Video List Section ===
        list_frame = ttk.LabelFrame(frame, text="Selected Videos", padding="10")
        list_frame.grid(row=3, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Video listbox with scrollbar
        self.video_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, width=50)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.video_listbox.yview)
        self.video_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.video_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind selection event
        self.video_listbox.bind('<<ListboxSelect>>', self.on_video_select)
        
        # === Metadata Editor Section ===
        metadata_frame = ttk.LabelFrame(frame, text="Video Metadata (AI-Generated)", padding="10")
        metadata_frame.grid(row=3, column=1, sticky="nsew", pady=(0, 10))
        metadata_frame.columnconfigure(0, weight=1)
        metadata_frame.rowconfigure(1, weight=0)
        metadata_frame.rowconfigure(3, weight=1)
        metadata_frame.rowconfigure(5, weight=0)
        
        # Title
        ttk.Label(metadata_frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.title_text = tk.Text(metadata_frame, height=2, wrap=tk.WORD)
        self.title_text.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # Description
        ttk.Label(metadata_frame, text="Description:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.desc_text = scrolledtext.ScrolledText(metadata_frame, height=8, wrap=tk.WORD)
        self.desc_text.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        
        # Tags
        ttk.Label(metadata_frame, text="Tags (comma-separated):").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.tags_text = tk.Text(metadata_frame, height=3, wrap=tk.WORD)
        self.tags_text.grid(row=5, column=0, sticky="ew")
        
        # === Action Buttons ===
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        ttk.Button(button_frame, text="1. Extract & Analyze Frames", 
                  command=self.extract_and_analyze).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="2. Search YouTube", 
                  command=self.search_youtube_related).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="3. Generate Metadata", 
                  command=self.generate_metadata_from_analysis).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="4. Upload Video", 
                  command=self.upload_selected).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Authenticate YouTube", 
                  command=self.authenticate_youtube).pack(side=tk.LEFT)
        
        # === Progress Section ===
        progress_frame = ttk.LabelFrame(frame, text="Progress & Logs", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        # Log text
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=6, state='disabled')
        self.log_text.grid(row=2, column=0, sticky="ew", pady=(5, 0))
    
    def create_analysis_tab(self):
        """Create the frame analysis tab"""
        frame = ttk.Frame(self.analysis_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame display area
        self.frames_canvas = tk.Canvas(frame, bg='gray90')
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.frames_canvas.yview)
        self.frames_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.frames_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame for images
        self.frames_container = ttk.Frame(self.frames_canvas)
        self.frames_canvas.create_window((0, 0), window=self.frames_container, anchor="nw")
        
        # Analysis results text
        self.analysis_text = scrolledtext.ScrolledText(frame, height=10, wrap=tk.WORD)
        self.analysis_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
    
    def create_search_tab(self):
        """Create the YouTube search results tab with advanced filtering"""
        main_frame = ttk.Frame(self.search_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Search Controls ===
        control_frame = ttk.LabelFrame(main_frame, text="Search Filters", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Row 1: Search Query
        query_frame = ttk.Frame(control_frame)
        query_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(query_frame, text="Search Query:").pack(side=tk.LEFT)
        self.search_query_var = tk.StringVar()
        entry = ttk.Entry(query_frame, textvariable=self.search_query_var, width=50)
        entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        entry.bind('<Return>', lambda e: self.search_youtube_tab())
        
        # Row 2: Filters and Button
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(fill=tk.X)
        
        # Days Filter
        ttk.Label(filter_frame, text="Published in last:").pack(side=tk.LEFT)
        self.search_days_var = tk.StringVar(value="30")
        days_spin = ttk.Spinbox(filter_frame, from_=0, to=3650, textvariable=self.search_days_var, width=5)
        days_spin.pack(side=tk.LEFT, padx=5)
        ttk.Label(filter_frame, text="days (0 = any time)").pack(side=tk.LEFT)

        # Country Filter
        ttk.Label(filter_frame, text="Country:").pack(side=tk.LEFT, padx=(10, 0))
        self.search_region_var = tk.StringVar()
        countries = [
            'All', 'US', 'IN', 'GB', 'CA', 'AU', 'JP', 'DE', 'FR', 'BR', 'MX', 'RU', 'KR'
        ]
        self.region_combo = ttk.Combobox(filter_frame, textvariable=self.search_region_var, values=countries, width=5)
        self.region_combo.set('All')
        self.region_combo.pack(side=tk.LEFT, padx=5)

        # Location Filter
        ttk.Label(filter_frame, text="Location:").pack(side=tk.LEFT, padx=(10, 0))
        self.search_location_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.search_location_var, width=15).pack(side=tk.LEFT, padx=5)
        
        # Search Button
        ttk.Button(filter_frame, text="🔍 Search YouTube", command=self.search_youtube_tab).pack(side=tk.RIGHT)
        
        # === Results Treeview ===
        # Columns: Title, Views, Duration, Date, Channel, Country, Location
        columns = ('Title', 'Views', 'Duration', 'Date', 'Channel', 'Country', 'Location', 'Video ID')
        self.search_tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=10)
        
        # Configure column headings with sorting
        columns_config = [
            ('Title', 'Title'),
            ('Views', 'Views'),
            ('Duration', 'Duration'),
            ('Date', 'Upload Date'),
            ('Channel', 'Channel'),
            ('Date', 'Upload Date'),
            ('Channel', 'Channel'),
            ('Country', 'Country'),
            ('Location', 'Location'),
            ('Video ID', 'Video ID')
        ]
        
        for col, text in columns_config:
            self.search_tree.heading(col, text=text, 
                command=lambda c=col: self.treeview_sort_column(self.search_tree, c, False))
        
        self.search_tree.column('Title', width=300)
        self.search_tree.column('Views', width=80)
        self.search_tree.column('Duration', width=80)
        self.search_tree.column('Date', width=100)
        self.search_tree.column('Channel', width=150)
        self.search_tree.column('Country', width=60)
        self.search_tree.column('Location', width=100)
        self.search_tree.column('Video ID', width=0, stretch=tk.NO) # Hidden ID column
        
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=scrollbar.set)
        
        self.search_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar.place(in_=self.search_tree, relx=1.0, relheight=1.0, bordermode="outside")
        
        # Bind selection
        self.search_tree.bind('<<TreeviewSelect>>', self.on_search_result_select)
        self.search_tree.bind('<Button-3>', self.show_tree_context_menu)
        
        # === Detail View ===
        detail_frame = ttk.LabelFrame(main_frame, text="Video Details", padding="10")
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Toolbar for Copy Buttons
        toolbar = ttk.Frame(detail_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(toolbar, text="📋 Copy Title", 
                   command=lambda: self.copy_detail('title')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="📋 Copy Description", 
                   command=lambda: self.copy_detail('description')).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📋 Copy Tags", 
                   command=lambda: self.copy_detail('tags')).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📋 Copy URL", 
                   command=lambda: self.copy_detail('url')).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📋 Copy Channel Tags", 
                   command=lambda: self.copy_detail('channel_tags')).pack(side=tk.LEFT, padx=5)
        
        # Open in Browser Button
        ttk.Button(toolbar, text="🌐 Open Video", 
                   command=self.open_current_video).pack(side=tk.LEFT, padx=5)
                   
        # Copy All to Upload Button
        ttk.Button(toolbar, text="🚀 Copy All to Upload", 
                   command=self.copy_all_to_upload, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        
        self.search_details_text = scrolledtext.ScrolledText(detail_frame, height=10, wrap=tk.WORD)
        self.search_details_text.pack(fill=tk.BOTH, expand=True)
        
        # Create Context Menu
        self.tree_context_menu = tk.Menu(self.root, tearoff=0)
        self.tree_context_menu.add_command(label="Open in Browser", command=self.open_tree_video)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Copy Video URL", command=self.copy_tree_url)
        self.tree_context_menu.add_command(label="Copy Video Title", command=self.copy_tree_title)
        self.tree_context_menu.add_command(label="Copy Video ID", command=self.copy_tree_id)
    
    def create_renamer_tab(self):
        """Create the file renamer tab UI"""
        frame = ttk.Frame(self.renamer_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize renamer variables
        self.renamer_file_list = []  # List of (full_path, creation_time)
        self.renamer_preview_data = []  # List of (original_path, new_name)
        self.renamer_base_name = tk.StringVar()
        self.renamer_start_seq = tk.StringVar(value="1")
        
        # === Control Panel ===
        control_frame = ttk.LabelFrame(frame, text="Rename Settings", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Row 1: File selection buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(btn_frame, text="📂 Select Files", 
                   command=self.renamer_select_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="📁 Select Folder", 
                   command=self.renamer_select_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Clear", 
                   command=self.renamer_clear).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⬆️ Up", 
                   command=self.renamer_move_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⬇️ Down", 
                   command=self.renamer_move_down).pack(side=tk.LEFT, padx=5)
        
        self.renamer_file_count = ttk.Label(btn_frame, text="No files selected")
        self.renamer_file_count.pack(side=tk.LEFT, padx=(20, 0))
        
        # Row 2: Base name and sequence
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(fill=tk.X)
        
        ttk.Label(settings_frame, text="Base Name:").pack(side=tk.LEFT)
        base_entry = ttk.Entry(settings_frame, textvariable=self.renamer_base_name, width=30)
        base_entry.pack(side=tk.LEFT, padx=(5, 20))
        base_entry.bind("<KeyRelease>", self.renamer_update_preview)
        
        ttk.Label(settings_frame, text="Start #:").pack(side=tk.LEFT)
        seq_entry = ttk.Entry(settings_frame, textvariable=self.renamer_start_seq, width=5)
        seq_entry.pack(side=tk.LEFT, padx=(5, 20))
        seq_entry.bind("<KeyRelease>", self.renamer_update_preview)
        
        ttk.Button(settings_frame, text="✏️ Rename Files", 
                   command=self.renamer_execute).pack(side=tk.RIGHT)
        ttk.Button(settings_frame, text="🔄 Refresh Preview", 
                   command=self.renamer_generate_preview).pack(side=tk.RIGHT, padx=5)
        
        # === Preview Treeview ===
        preview_frame = ttk.LabelFrame(frame, text="Preview (sorted by creation date)", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        columns = ('original', 'date', 'new_name')
        self.renamer_tree = ttk.Treeview(preview_frame, columns=columns, show='headings')
        
        self.renamer_tree.heading('original', text='Original File')
        self.renamer_tree.heading('date', text='Creation Date')
        self.renamer_tree.heading('new_name', text='New Filename')
        
        self.renamer_tree.column('original', width=300)
        self.renamer_tree.column('date', width=150)
        self.renamer_tree.column('new_name', width=300)
        
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.renamer_tree.yview)
        self.renamer_tree.configure(yscrollcommand=scrollbar.set)
        
        self.renamer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === Single File Rename Section ===
        single_frame = ttk.LabelFrame(frame, text="Single File Rename", padding="10")
        single_frame.pack(fill=tk.X)
        
        self.single_file_path = tk.StringVar()
        self.single_new_name = tk.StringVar()
        
        ttk.Label(single_frame, text="File:").grid(row=0, column=0, sticky=tk.W, pady=2)
        single_path_entry = ttk.Entry(single_frame, textvariable=self.single_file_path, width=50)
        single_path_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        ttk.Button(single_frame, text="Browse", 
                   command=self.single_browse_file).grid(row=0, column=2, padx=5)
        
        ttk.Label(single_frame, text="New Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        single_name_entry = ttk.Entry(single_frame, textvariable=self.single_new_name, width=50)
        single_name_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        ttk.Button(single_frame, text="Rename", 
                   command=self.single_rename_file, style="Accent.TButton").grid(row=1, column=2, padx=5)
        
        # Status Bar
        self.renamer_status = ttk.Label(frame, text="Ready", foreground="gray")
        self.renamer_status.pack(anchor=tk.W, pady=(5, 0))
    def create_analyzer_tab(self):
        """Create the YT Analyzer tab UI"""
        frame = ttk.Frame(self.analyzer_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        self.analyzer_notebook = ttk.Notebook(frame)
        self.analyzer_notebook.pack(fill=tk.BOTH, expand=True)

        self.channel_discovery_tab = ttk.Frame(self.analyzer_notebook)
        self.analyzer_notebook.add(self.channel_discovery_tab, text="Channel Discovery")
        self._create_channel_discovery_tab(self.channel_discovery_tab)

        self.global_trends_tab = ttk.Frame(self.analyzer_notebook)
        self.analyzer_notebook.add(self.global_trends_tab, text="Global Trends")
        self._create_global_trends_tab(self.global_trends_tab)

        self.audience_insights_tab = ttk.Frame(self.analyzer_notebook)
        self.analyzer_notebook.add(self.audience_insights_tab, text="Audience Insights")
        self._create_audience_insights_tab(self.audience_insights_tab)

    def _create_channel_discovery_tab(self, parent_frame):
        frame = parent_frame
        
        # === Search Parameters ===
        search_frame = ttk.LabelFrame(frame, text="1. Search Parameters", padding="10")
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Topic Input
        ttk.Label(search_frame, text="Niche / Topic (Leave blank for All Topics):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.yt_query_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.yt_query_var, width=40).grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        
        # Specific Channel Input
        ttk.Label(search_frame, text="Specific Channel (Overrides Niche):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.yt_channel_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.yt_channel_var, width=40).grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        
        # Days Filter
        ttk.Label(search_frame, text="Channel Created Within (Days Ago):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.yt_days_var = tk.StringVar(value="30")
        days_combo = ttk.Combobox(search_frame, textvariable=self.yt_days_var, values=["All Time", "1", "3", "7", "14", "30", "90", "180", "365"], width=13)
        days_combo.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)        
        
        # Min Subs Filter
        ttk.Label(search_frame, text="Minimum Subscribers:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.yt_min_subs_var = tk.StringVar(value="0")
        ttk.Entry(search_frame, textvariable=self.yt_min_subs_var, width=15).grid(row=3, column=1, padx=5, pady=2, sticky=tk.W)

        # Max Results Filter
        ttk.Label(search_frame, text="Display Max Results (Leave blank for all):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.yt_max_results_var = tk.StringVar(value="")
        ttk.Entry(search_frame, textvariable=self.yt_max_results_var, width=15).grid(row=4, column=1, padx=5, pady=2, sticky=tk.W)

        # Search Button
        ttk.Button(search_frame, text="🔍 Find Top Channels", command=self.analyzer_search_channels, style="Accent.TButton").grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        # === Channel Candidates Table ===
        candidates_frame = ttk.LabelFrame(frame, text="2. Channel Candidates", padding="10")
        candidates_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        columns = ('channel', 'subs', 'views', 'created')
        self.yt_candidates_tree = ttk.Treeview(candidates_frame, columns=columns, show='headings', height=5)
        self.yt_candidates_tree.heading('channel', text='Channel Name')
        self.yt_candidates_tree.heading('subs', text='Subscribers')
        self.yt_candidates_tree.heading('views', text='Lifetime Views')
        self.yt_candidates_tree.heading('created', text='Created Date')
        self.yt_candidates_tree.column('subs', width=90)
        self.yt_candidates_tree.column('views', width=110)
        self.yt_candidates_tree.column('created', width=90)
        
        scrollbar = ttk.Scrollbar(candidates_frame, orient="vertical", command=self.yt_candidates_tree.yview)
        self.yt_candidates_tree.configure(yscrollcommand=scrollbar.set)
        
        self.yt_candidates_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar.place(in_=self.yt_candidates_tree, relx=1.0, relheight=1.0, bordermode="outside")
        
        # Bind double-click to open channel
        self.yt_candidates_tree.bind("<Double-1>", self.open_selected_candidate_channel)
        
        # Action buttons frame
        candidates_btn_frame = ttk.Frame(candidates_frame)
        candidates_btn_frame.pack(pady=(5, 0))
        
        ttk.Button(candidates_btn_frame, text="📋 Copy Description", command=self.copy_candidate_description).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(candidates_btn_frame, text="📋 Copy Tags", command=self.copy_candidate_tags).pack(side=tk.LEFT, padx=5)
        ttk.Button(candidates_btn_frame, text="🌐 Open Selected Channel", command=self.open_selected_candidate_channel).pack(side=tk.LEFT, padx=5)
        ttk.Button(candidates_btn_frame, text="🚀 Apply Grover's Mock (Find Best)", command=self.analyzer_run_grover_mock, style="Accent.TButton").pack(side=tk.LEFT, padx=5)

        # Candidate Details Text Area
        self.yt_candidate_details_text = scrolledtext.ScrolledText(candidates_frame, height=4, wrap=tk.WORD, font=('Consolas', 10), bg='#1e1e1e', fg='#00ff00')
        self.yt_candidate_details_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Bind the select event
        self.yt_candidates_tree.bind('<<TreeviewSelect>>', self.on_candidate_select)
        self.current_candidate_data = None
        
        # === Detailed Analytics Panel ===
        details_frame = ttk.LabelFrame(frame, text="3. Top Performing Channel Details & Top Videos", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True)

        # PanedWindow to split Left (Details) and Right (Videos List)
        details_paned = ttk.PanedWindow(details_frame, orient=tk.HORIZONTAL)
        details_paned.pack(fill=tk.BOTH, expand=True)
        
        # ==========================================
        # LEFT PANE: Channel Details + Video Details
        # ==========================================
        left_pane = ttk.Frame(details_paned)
        details_paned.add(left_pane, weight=1)
        
        # --- PACK FROM BOTTOM UP: VIDEO BUTTONS & DETAILS ---
        # 1. Video Action Buttons (Bottom row FIRST)
        vid_btn_frame2 = ttk.Frame(left_pane)
        vid_btn_frame2.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 5))
        ttk.Button(vid_btn_frame2, text="🌐 Open Video", command=self.open_selected_video).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(vid_btn_frame2, text="🎵 Download MP3", command=self.download_video_mp3).pack(side=tk.LEFT, padx=2)
        ttk.Button(vid_btn_frame2, text="🚀 Copy All to Upload", command=self.copy_all_to_upload, style="Accent.TButton").pack(side=tk.LEFT, padx=2)

        # 2. Video Action Buttons (Top row SECOND)
        vid_btn_frame1 = ttk.Frame(left_pane)
        vid_btn_frame1.pack(side=tk.BOTTOM, fill=tk.X, pady=(2, 2))
        ttk.Button(vid_btn_frame1, text="📋 Copy Title", command=self.copy_video_title).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(vid_btn_frame1, text="📋 Copy Desc", command=self.copy_video_description).pack(side=tk.LEFT, padx=2)
        ttk.Button(vid_btn_frame1, text="📋 Copy Tags", command=self.copy_video_tags).pack(side=tk.LEFT, padx=2)
        ttk.Button(vid_btn_frame1, text="📋 Copy URL", command=self.copy_video_url).pack(side=tk.LEFT, padx=2)

        # 3. Selected Video Details Text
        self.yt_video_details_text = scrolledtext.ScrolledText(left_pane, height=8, wrap=tk.WORD, font=('Consolas', 10), bg='#1e1e1e', fg='#00ff00')
        self.yt_video_details_text.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # 4. Selected Video Details Label
        video_lbl = ttk.Label(left_pane, text="Selected Video Details (click a video on the right):", font=('', 9, 'bold'))
        video_lbl.pack(side=tk.BOTTOM, anchor=tk.W, pady=(5, 2))

        # --- PACK FROM TOP DOWN: CHANNEL DETAILS ---
        # Header Label
        channel_lbl = ttk.Label(left_pane, text="Channel Details:", font=('', 9, 'bold'))
        channel_lbl.pack(side=tk.TOP, anchor=tk.W, pady=(0, 2))
        
        # Details Text
        self.yt_channel_details_text = scrolledtext.ScrolledText(left_pane, height=8, wrap=tk.WORD, font=('Consolas', 10), bg='#1e1e1e', fg='#00ff00')
        self.yt_channel_details_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Channel Action Buttons
        chan_btn_frame = ttk.Frame(left_pane)
        chan_btn_frame.pack(side=tk.TOP, fill=tk.X, pady=(2, 10))
        ttk.Button(chan_btn_frame, text="📋 Copy Desc", command=lambda: self.copy_to_clipboard(self.current_yt_winner.get('description', '')) if hasattr(self, 'current_yt_winner') else None).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(chan_btn_frame, text="📋 Copy Tags", command=lambda: self.copy_to_clipboard(','.join(self.current_yt_winner.get('tags', []))) if hasattr(self, 'current_yt_winner') else None).pack(side=tk.LEFT, padx=2)
        ttk.Button(chan_btn_frame, text="🌐 Open Channel", command=self.open_yt_winner_channel).pack(side=tk.LEFT, padx=2)

        # ==========================================
        # RIGHT PANE: Top Videos List (Treeview)
        # ==========================================
        right_pane = ttk.Frame(details_paned)
        details_paned.add(right_pane, weight=2)  # Give right pane more space for columns
        
        ttk.Label(right_pane, text="Top Videos (Scrollable list):", font=('', 9, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        
        vid_columns = ('title', 'views', 'duration', 'date')
        vid_tree_frame = ttk.Frame(right_pane)
        vid_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.yt_videos_tree = ttk.Treeview(vid_tree_frame, columns=vid_columns, show='headings')
        self.yt_videos_tree.heading('title', text='Title')
        self.yt_videos_tree.heading('views', text='Views')
        self.yt_videos_tree.heading('duration', text='Duration')
        self.yt_videos_tree.heading('date', text='Upload Date')
        self.yt_videos_tree.column('title', width=200)
        self.yt_videos_tree.column('views', width=80)
        self.yt_videos_tree.column('duration', width=60)
        self.yt_videos_tree.column('date', width=80)
        
        v_scroll = ttk.Scrollbar(vid_tree_frame, orient="vertical", command=self.yt_videos_tree.yview)
        self.yt_videos_tree.configure(yscrollcommand=v_scroll.set)
        
        self.yt_videos_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Video data storage: dict keyed by treeview iid for foolproof lookup
        self._video_data_by_iid = {}
        self.current_yt_videos_data = []
        self.current_video_data = None
        
        # Event bindings
        self.yt_videos_tree.bind('<<TreeviewSelect>>', self.on_video_select)
        self.yt_videos_tree.bind('<ButtonRelease-1>', self.on_video_select)
        
        # Right-click context menu for Top Videos
        self.video_context_menu = tk.Menu(self.root, tearoff=0)
        self.video_context_menu.add_command(label="📋 Copy Title", command=self.copy_video_title)
        self.video_context_menu.add_command(label="📋 Copy Description", command=self.copy_video_description)
        self.video_context_menu.add_command(label="📋 Copy Tags", command=self.copy_video_tags)
        self.video_context_menu.add_separator()
        self.video_context_menu.add_command(label="📋 Copy URL", command=self.copy_video_url)
        self.video_context_menu.add_command(label="🌐 Open Video", command=self.open_selected_video)
        self.video_context_menu.add_separator()
        self.video_context_menu.add_command(label="🚀 Copy All to Upload", command=self.copy_all_to_upload)
        self.video_context_menu.add_separator()
        self.video_context_menu.add_command(label="🎵 Download MP3", command=self.download_video_mp3)
        self.yt_videos_tree.bind("<Button-3>", self.show_video_context_menu)
        
        # Status
        self.analyzer_status = ttk.Label(frame, text="Ready", foreground="gray")
        self.analyzer_status.pack(anchor=tk.W, pady=(5, 0))

    def _create_global_trends_tab(self, parent_frame):
        """Create the Global Trends sub-tab"""
        frame = parent_frame
        
        # Controls Frame
        controls_frame = ttk.LabelFrame(frame, text="Global Trends Settings", padding="10")
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls_frame, text="Region Code:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.trending_region_var = tk.StringVar(value="US")
        ttk.Entry(controls_frame, textvariable=self.trending_region_var, width=10).grid(row=0, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(controls_frame, text="Category:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        self.trending_category_var = tk.StringVar(value="All Categories")
        self.trending_category_combo = ttk.Combobox(controls_frame, textvariable=self.trending_category_var, state="readonly", width=30)
        self.trending_category_combo.grid(row=0, column=3, padx=5, sticky=tk.W)
        self.trending_category_combo.set("All Categories")
        
        ttk.Label(controls_frame, text="Keyword/Tag (Optional):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.trending_keyword_var = tk.StringVar()
        ttk.Entry(controls_frame, textvariable=self.trending_keyword_var, width=30).grid(row=1, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(controls_frame, text="Max Results:").grid(row=1, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        self.trending_max_results_var = tk.StringVar(value="50")
        ttk.Entry(controls_frame, textvariable=self.trending_max_results_var, width=10).grid(row=1, column=3, padx=5, sticky=tk.W)
        
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=(10, 0), sticky=tk.W)
        
        ttk.Button(btn_frame, text="🔄 Load Categories", command=self.load_youtube_categories).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="🔥 Get Videos", command=self.fetch_global_trending, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        
        # PanedWindow to separate Treeview and Details
        paned = ttk.PanedWindow(frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Results Tree
        results_frame = ttk.LabelFrame(paned, text="Trending/Search Videos", padding="10")
        paned.add(results_frame, weight=2)
        
        columns = ('title', 'channel', 'views', 'published')
        self.trending_tree = ttk.Treeview(results_frame, columns=columns, show='headings')
        self.trending_tree.heading('title', text='Title', command=lambda: self.treeview_sort_column(self.trending_tree, 'title', False))
        self.trending_tree.heading('channel', text='Channel', command=lambda: self.treeview_sort_column(self.trending_tree, 'channel', False))
        self.trending_tree.heading('views', text='Views', command=lambda: self.treeview_sort_column(self.trending_tree, 'views', False))
        self.trending_tree.heading('published', text='Published Date', command=lambda: self.treeview_sort_column(self.trending_tree, 'published', False))
        self.trending_tree.column('title', width=300)
        self.trending_tree.column('channel', width=150)
        self.trending_tree.column('views', width=100)
        self.trending_tree.column('published', width=100)
        
        scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.trending_tree.yview)
        self.trending_tree.configure(yscrollcommand=scroll.set)
        
        self.trending_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.trending_video_data_by_iid = {}
        self.trending_tree.bind('<<TreeviewSelect>>', self.on_trending_select)
        
        # Right-click context menu for Trending Videos
        self.trending_context_menu = tk.Menu(self.root, tearoff=0)
        self.trending_context_menu.add_command(label="📋 Copy Title", command=self.copy_trending_title)
        self.trending_context_menu.add_command(label="📋 Copy Description", command=self.copy_trending_description)
        self.trending_context_menu.add_command(label="📋 Copy Tags", command=self.copy_trending_tags)
        self.trending_context_menu.add_separator()
        self.trending_context_menu.add_command(label="📋 Copy URL", command=self.copy_trending_url)
        self.trending_context_menu.add_command(label="🌐 Open in Browser", command=self.open_trending_video)
        self.trending_tree.bind("<Button-3>", self.show_trending_context_menu)

        # Details Pane
        details_frame = ttk.LabelFrame(paned, text="Selected Video Details", padding="10")
        paned.add(details_frame, weight=1)

        # Toolbar for Copy Buttons
        toolbar = ttk.Frame(details_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(toolbar, text="📋 Copy Title", command=self.copy_trending_title).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="📋 Copy Description", command=self.copy_trending_description).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📋 Copy Tags", command=self.copy_trending_tags).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📋 Copy URL", command=self.copy_trending_url).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🌐 Open Video", command=self.open_trending_video).pack(side=tk.LEFT, padx=5)

        self.trending_details_text = scrolledtext.ScrolledText(details_frame, height=6, wrap=tk.WORD, font=('Consolas', 10), bg='#1e1e1e', fg='#00ff00')
        self.trending_details_text.pack(fill=tk.BOTH, expand=True)
        
        self.trending_status = ttk.Label(frame, text="Ready", foreground="gray")
        self.trending_status.pack(anchor=tk.W, pady=(5, 0))

        # Store category mapping id -> name
        self.category_mapping = {}

    def _create_audience_insights_tab(self, parent_frame):
        """Create the Audience Insights sub-tab"""
        frame = parent_frame
        
        controls = ttk.LabelFrame(frame, text="Audience Analytics Controls", padding="10")
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls, text="Date Range (Days):").pack(side=tk.LEFT, padx=(0, 5))
        self.analytics_days_var = tk.StringVar(value="30")
        ttk.Combobox(controls, textvariable=self.analytics_days_var, values=["7", "30", "90", "365"], width=10, state="readonly").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls, text="📊 Fetch Insights", command=self.fetch_audience_insights, style="Accent.TButton").pack(side=tk.LEFT, padx=10)
        
        info_label = ttk.Label(controls, text="Note: Requires channel authentication with Analytics scopes.", foreground="orange")
        info_label.pack(side=tk.LEFT, padx=10)
        
        self.analytics_text = scrolledtext.ScrolledText(frame, height=20, wrap=tk.WORD, font=('Consolas', 10), bg='#1e1e1e', fg='#00ff00')
        self.analytics_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.analytics_status = ttk.Label(frame, text="Ready", foreground="gray")
        self.analytics_status.pack(anchor=tk.W, pady=(5, 0))

    def load_youtube_categories(self):
        """Fetch categories from API and update drop down"""
        self.trending_status.configure(text="Loading categories...")
        self.root.update()
        
        # Read Tk variables in the main thread
        region = self.trending_region_var.get().strip() or "US"
        
        def run_load(region_code):
            searcher = self.youtube_searcher
            if not searcher:
                api_key = os.getenv("YOUTUBE_API_KEY")
                if not api_key:
                    self.root.after(0, lambda: messagebox.showwarning("Warning", "Please authenticate with YouTube first (Upload tab), or provide YOUTUBE_API_KEY in .env."))
                    self.root.after(0, lambda: self.trending_status.configure(text="Ready"))
                    return
                try:
                    temp_service = build('youtube', 'v3', developerKey=api_key)
                    searcher = YouTubeSearcher(temp_service)
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showwarning("Error", f"Failed to initialize YouTube API with key: {e}"))
                    self.root.after(0, lambda: self.trending_status.configure(text="Ready"))
                    return
            
            cats = searcher.get_video_categories(region_code=region_code)
            
            if cats:
                # Add "All Categories" mapping
                self.category_mapping = {"All Categories": None}
                self.category_mapping.update(cats)
                
                cat_names = list(self.category_mapping.keys())
                self.root.after(0, lambda: self._update_categories_combo(cat_names))
                self.root.after(0, lambda: self.trending_status.configure(text=f"Loaded {len(cats)} categories."))
            else:
                self.root.after(0, lambda: self.trending_status.configure(text="No categories found or API error."))
                
        threading.Thread(target=run_load, args=(region,), daemon=True).start()

    def _update_categories_combo(self, names):
        self.trending_category_combo['values'] = names
        if names:
            self.trending_category_combo.set("All Categories")

    def fetch_global_trending(self):
        """Fetch trending videos for the region/category"""
        self.trending_status.configure(text="Fetching videos...")
        self.root.update()
        
        # Read Tk variables in the main thread
        region = self.trending_region_var.get().strip() or "US"
        cat_name = self.trending_category_var.get()
        cat_id = self.category_mapping.get(cat_name)
        keyword = self.trending_keyword_var.get().strip()
        
        try:
            max_res = int(self.trending_max_results_var.get().strip())
        except ValueError:
            max_res = 50
        
        def run_fetch(region_code, c_id, kw, max_results_limit):
            searcher = self.youtube_searcher
            if not searcher:
                api_key = os.getenv("YOUTUBE_API_KEY")
                if not api_key:
                    self.root.after(0, lambda: messagebox.showwarning("Warning", "Please authenticate with YouTube first (Upload tab), or provide YOUTUBE_API_KEY in .env."))
                    self.root.after(0, lambda: self.trending_status.configure(text="Ready"))
                    return
                try:
                    temp_service = build('youtube', 'v3', developerKey=api_key)
                    searcher = YouTubeSearcher(temp_service)
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showwarning("Error", f"Failed to initialize YouTube API with key: {e}"))
                    self.root.after(0, lambda: self.trending_status.configure(text="Ready"))
                    return
            
            if kw:
                videos = searcher.search_related_videos(query=kw, max_results=max_results_limit, days_filter=30, region_code=region_code)
            elif c_id:
                videos = searcher.get_trending_by_category(category_id=c_id, max_results=max_results_limit, region_code=region_code)
            else:
                videos = searcher.get_trending_videos(max_results=max_results_limit, region_code=region_code)
                
            self.root.after(0, lambda: self.trending_tree.delete(*self.trending_tree.get_children()))
            self.root.after(0, lambda: self.trending_video_data_by_iid.clear())
            
            if videos:
                def update_ui():
                    for v in videos:
                        iid = self.trending_tree.insert('', tk.END, values=(
                            v['title'], v['channel_title'], f"{v['views']:,}", v['published_at']
                        ))
                        self.trending_video_data_by_iid[iid] = v
                    self.trending_status.configure(text=f"Found {len(videos)} videos.")
                self.root.after(0, update_ui)
            else:
                self.root.after(0, lambda: self.trending_status.configure(text="No videos found."))
                
        threading.Thread(target=run_fetch, args=(region, cat_id, keyword, max_res), daemon=True).start()

    def on_trending_select(self, event):
        """Update the details text with tags and description when a trending video is selected"""
        selection = self.trending_tree.selection()
        if not selection:
            return
            
        iid = selection[0]
        data = self.trending_video_data_by_iid.get(iid)
        
        self.trending_details_text.delete(1.0, tk.END)
        
        if data:
            self.trending_details_text.insert(tk.END, f"Title: {data.get('title', 'N/A')}\n")
            self.trending_details_text.insert(tk.END, f"Channel: {data.get('channel_title', 'N/A')}\n")
            
            tags = data.get('tags', [])
            tags_str = ", ".join(tags) if tags else "None"
            self.trending_details_text.insert(tk.END, f"Tags: {tags_str}\n\n")
            
            self.trending_details_text.insert(tk.END, "--- Description ---\n")
            self.trending_details_text.insert(tk.END, data.get('description', 'No description available.'))

    def treeview_sort_column(self, tv, col, reverse):
        """Sort treeview contents when a column header is clicked."""
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        
        # Try to sort numerically if possible (e.g., for views)
        try:
            l.sort(key=lambda t: float(t[0].replace(',', '')), reverse=reverse)
        except ValueError:
            # Fall back to string sort
            l.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # Reverse sort next time
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def _get_selected_trending_video(self):
        selection = self.trending_tree.selection()
        if not selection:
            return None
        return self.trending_video_data_by_iid.get(selection[0])

    def show_trending_context_menu(self, event):
        item = self.trending_tree.identify_row(event.y)
        if item:
            self.trending_tree.selection_set(item)
            self.on_trending_select(event)
            self.trending_context_menu.post(event.x_root, event.y_root)

    def open_trending_video(self):
        data = self._get_selected_trending_video()
        if data:
            vid_id = data.get('video_id') or data.get('id')
            if vid_id:
                video_url = f"https://www.youtube.com/watch?v={vid_id}"
                webbrowser.open(video_url)

    def copy_trending_title(self):
        data = self._get_selected_trending_video()
        if data and 'title' in data:
            self.copy_to_clipboard(data['title'])
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")
            
    def copy_trending_description(self):
        data = self._get_selected_trending_video()
        if data and 'description' in data:
            self.copy_to_clipboard(data['description'])
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")
            
    def copy_trending_tags(self):
        data = self._get_selected_trending_video()
        if data and 'tags' in data:
            self.copy_to_clipboard(','.join(data['tags']))
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")
            
    def copy_trending_url(self):
        data = self._get_selected_trending_video()
        if data:
            vid_id = data.get('video_id') or data.get('id')
            if vid_id:
                self.copy_to_clipboard(f"https://www.youtube.com/watch?v={vid_id}")
            else:
                messagebox.showinfo("Error", "Video URL not found.")
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")

    def fetch_audience_insights(self):
        """Fetch and display YouTube Analytics insights"""
        self.analytics_status.configure(text="Fetching analytics...")
        self.analytics_text.delete(1.0, tk.END)
        self.analytics_text.insert(tk.END, "Querying YouTube Analytics API...\n")
        self.root.update()
        
        # Read Tk variables in the main thread
        days_str = self.analytics_days_var.get()
        
        def run_fetch(d_str):
            if not self.youtube_searcher:
                self.root.after(0, lambda: messagebox.showwarning("Warning", "Authenticate a Channel first."))
                self.root.after(0, lambda: self.analytics_status.configure(text="Ready"))
                return
                
            try:
                days = int(d_str)
            except ValueError:
                days = 30
                
            # YouTube Analytics requires YYYY-MM-DD
            # Typically data is delayed by 2 days
            end_date = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d')
            start_date = (datetime.utcnow() - timedelta(days=days+2)).strftime('%Y-%m-%d')
            
            self.root.after(0, lambda: self.analytics_text.insert(tk.END, f"Timeframe: {start_date} to {end_date}\n\n"))
            
            response = self.youtube_searcher.get_audience_analytics(start_date, end_date)
            
            if response:
                def update_ui():
                    # Parse demographics
                    demo = response.get('demographics', {})
                    self.analytics_text.insert(tk.END, "--- TOP DEMOGRAPHICS (Age & Gender) ---\n")
                    for row in demo.get('rows', []):
                        age, gender, percent = row[0], row[1], row[2]
                        if percent > 0:
                            self.analytics_text.insert(tk.END, f"{gender.title():<8} | {age:<12} | {percent:.2f}%\n")
                            
                    # Parse geography
                    geo = response.get('geography', {})
                    self.analytics_text.insert(tk.END, "\n--- TOP GEOGRAPHIES by Views ---\n")
                    for row in geo.get('rows', []):
                        country, views, minutes = row[0], row[1], row[2]
                        self.analytics_text.insert(tk.END, f"{country:<4} | Views: {int(views):<8} | Watch Time (min): {int(minutes)}\n")
                        
                    # Parse top videos
                    top_vids = response.get('top_videos', {})
                    self.analytics_text.insert(tk.END, "\n--- TOP VIDEOS (Engagement) ---\n")
                    for idx, row in enumerate(top_vids.get('rows', [])):
                        vid_id, views, minutes, avg_duration = row[0], row[1], row[2], row[3]
                        self.analytics_text.insert(tk.END, f"{idx+1}. Video ID: {vid_id:<12} | Views: {int(views):<8} | Avg View Duration (sec): {int(avg_duration)}\n")
                        
                    self.analytics_status.configure(text="Analytics loaded successfully.")
                self.root.after(0, update_ui)
            else:
                self.root.after(0, lambda: self.analytics_text.insert(tk.END, "HTTP Error: Make sure your channel is re-authenticated to grant the yt-analytics.readonly scope. You may also not have enough analytics data.\n"))
                self.root.after(0, lambda: self.analytics_status.configure(text="Failed to fetch analytics."))

        threading.Thread(target=run_fetch, args=(days_str,), daemon=True).start()
    def analyzer_search_channels(self):
        """Search for YouTube channels based on topic or specific name"""
        analyzer_youtube_service = self.youtube_service
        if not analyzer_youtube_service:
            api_key = os.getenv("YOUTUBE_API_KEY")
            if not api_key:
                messagebox.showwarning("Warning", "Please authenticate with YouTube first (Upload tab), or provide YOUTUBE_API_KEY in .env.")
                return
            try:
                analyzer_youtube_service = build('youtube', 'v3', developerKey=api_key)
            except Exception as e:
                messagebox.showwarning("Error", f"Failed to initialize YouTube API with key: {e}")
                return
            
        topic = self.yt_query_var.get().strip()
        specific_channel = self.yt_channel_var.get().strip()
        days_str = self.yt_days_var.get().strip()
        min_subs_str = getattr(self, 'yt_min_subs_var', tk.StringVar(value="0")).get().strip()
        max_res_str = getattr(self, 'yt_max_results_var', tk.StringVar(value="")).get().strip()
        
        try:
            if days_str.lower() in ["all time", "all", ""]:
                days = None
            else:
                days = int(days_str)
        except ValueError:
            days = 30
            
        try:
            min_subs = int(min_subs_str) if min_subs_str else 0
        except ValueError:
            min_subs = 0
            
        try:
            display_max = int(max_res_str) if max_res_str else None
        except ValueError:
            display_max = None
            
        self.analyzer_status.configure(text="Searching channels...")
        
        def do_search():
            try:
                # Clear existing
                self.root.after(0, lambda: self.yt_candidates_tree.delete(*self.yt_candidates_tree.get_children()))
                
                results = []
                # 1. Gather Channel IDs (either from search query or specific channel)
                if specific_channel:
                    # Search specifically for the channel
                    search_response = analyzer_youtube_service.search().list(
                        q=specific_channel, type='channel', part='id,snippet', maxResults=5
                    ).execute()
                    
                    channel_ids = [item['id']['channelId'] for item in search_response.get('items', [])]
                    
                else:
                    # Search by topic for recent popular videos, then get their channels
                    query = topic if topic else "viral"
                    
                    search_kwargs = {
                        'q': query,
                        'type': 'video',
                        'part': 'snippet',
                        'order': 'viewCount',
                        'maxResults': 50
                    }
                    if days is not None:
                        search_kwargs['publishedAfter'] = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
                        
                    search_response = analyzer_youtube_service.search().list(**search_kwargs).execute()
                    
                    # Extract unique channel IDs
                    channel_ids = list(set([item['snippet']['channelId'] for item in search_response.get('items', [])]))

                if not channel_ids:
                    self.root.after(0, lambda: self.analyzer_status.configure(text="No channels found."))
                    return
                    
                # 2. Fetch full stats for these channels
                channel_data = []
                for i in range(0, len(channel_ids), 50):
                    chunk = channel_ids[i:i+50]
                    stats_response = analyzer_youtube_service.channels().list(
                        part='snippet,statistics,brandingSettings', id=','.join(chunk)
                    ).execute()
                    
                    for ch in stats_response.get('items', []):
                        stats = ch.get('statistics', {})
                        snippet = ch.get('snippet', {})
                        branding = ch.get('brandingSettings', {}).get('channel', {})
                        
                        channel_data.append({
                            'id': ch['id'],
                            'title': snippet.get('title', ''),
                            'description': snippet.get('description', ''),
                            'subs': int(stats.get('subscriberCount', 0)),
                            'views': int(stats.get('viewCount', 0)),
                            'video_count': int(stats.get('videoCount', 0)),
                            'country': snippet.get('country', 'N/A'),
                            'tags': branding.get('keywords', '').replace('"', '').split() if branding.get('keywords') else [],
                            'created': snippet.get('publishedAt', '').split('T')[0] if snippet.get('publishedAt') else 'N/A'
                        })
                
                # Filter out ones with no subs (hidden sub counts return 0 sometimes) and enforce min_subs
                filtered_channel_data = []
                now = datetime.utcnow()
                for ch in channel_data:
                    # Parse creation date and check if it's within the requested days
                    created_date_str = ch.get('created', '')
                    is_new_enough = True
                    if days is not None and created_date_str and created_date_str != 'N/A':
                        try:
                            # snippet.publishedAt gives format like 2024-03-01
                            ch_date = datetime.strptime(created_date_str, '%Y-%m-%d')
                            if (now - ch_date).days > days:
                                is_new_enough = False
                        except ValueError:
                            pass

                    if ch['subs'] > 0 and ch['subs'] >= min_subs and is_new_enough:
                        filtered_channel_data.append(ch)
                
                channel_data = filtered_channel_data
                
                # Sort by view count
                channel_data.sort(key=lambda x: x['views'], reverse=True)
                
                # Store for Grover's mock (apply max results filter)
                if display_max is not None and display_max > 0:
                    self.analyzer_channel_data = channel_data[:display_max]
                else:
                    self.analyzer_channel_data = channel_data
                
                for ch in self.analyzer_channel_data:
                    self.root.after(0, lambda c=ch: self.yt_candidates_tree.insert('', tk.END, values=(
                        c['title'], f"{c['subs']:,}", f"{c['views']:,}", c.get('created', 'N/A')
                    )))
                
                self.root.after(0, lambda: self.analyzer_status.configure(text=f"Found {len(self.analyzer_channel_data)} candidate channels."))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Channel search failed: {e}"))
                self.root.after(0, lambda: self.analyzer_status.configure(text="Search failed."))

        threading.Thread(target=do_search, daemon=True).start()

    def open_selected_candidate_channel(self, event=None):
        """Open the selected channel in the browser"""
        selection = self.yt_candidates_tree.selection()
        if not selection:
            messagebox.showinfo("Select Channel", "Please select a channel from the candidates list first.")
            return
            
        # Get the item values
        item = self.yt_candidates_tree.item(selection[0])
        channel_title = item['values'][0]
        
        # Find the correct channel ID from our stored data
        if hasattr(self, 'analyzer_channel_data'):
            for ch in self.analyzer_channel_data:
                if ch['title'] == channel_title:
                    webbrowser.open(f"https://www.youtube.com/channel/{ch['id']}")
                    break

    def on_candidate_select(self, event):
        """Handle selection of a channel from the candidates list to populate its details and top videos."""
        selection = self.yt_candidates_tree.selection()
        if not selection:
            return
            
        item = self.yt_candidates_tree.item(selection[0])
        channel_title = item['values'][0]
        
        if hasattr(self, 'analyzer_channel_data'):
            for ch in self.analyzer_channel_data:
                if ch['title'] == channel_title:
                    self.current_candidate_data = ch
                    self.current_yt_winner = ch  # Also set as winner so channel-level copy buttons work
                    
                    out_text = f"DESCRIPTION:\n{ch.get('description', '')}\n\n"
                    out_text += f"TAGS:\n{', '.join(ch.get('tags', [])) if ch.get('tags') else 'None'}\n"
                    
                    self.yt_candidate_details_text.delete('1.0', tk.END)
                    self.yt_candidate_details_text.insert('1.0', out_text)
                    
                    # Fetch top videos for this channel in a background thread
                    self.analyzer_status.configure(text=f"Fetching top videos for {ch['title']}...")
                    threading.Thread(target=self._fetch_candidate_videos, args=(ch,), daemon=True).start()
                    break

    def _fetch_candidate_videos(self, channel):
        """Fetch top videos for a selected candidate channel and populate the Top Videos treeview."""
        try:
            analyzer_youtube_service = self.youtube_service
            if not analyzer_youtube_service:
                api_key = os.getenv("YOUTUBE_API_KEY")
                if not api_key:
                    self.root.after(0, lambda: self.analyzer_status.configure(text="No API key available for video fetch."))
                    return
                analyzer_youtube_service = build('youtube', 'v3', developerKey=api_key)
            
            # Get uploaded videos playlist ID
            content_response = analyzer_youtube_service.channels().list(
                part='contentDetails', id=channel['id']
            ).execute()
            
            videos = []
            if content_response.get('items'):
                uploads_id = content_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                
                # Fetch recent 15 videos
                playlist_response = analyzer_youtube_service.playlistItems().list(
                    part='snippet,contentDetails', playlistId=uploads_id, maxResults=15
                ).execute()
                
                video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
                
                # Fetch full video stats
                if video_ids:
                    videos_response = analyzer_youtube_service.videos().list(
                        part='snippet,statistics,contentDetails', id=','.join(video_ids)
                    ).execute()
                    
                    for v in videos_response.get('items', []):
                        duration_iso = v['contentDetails'].get('duration', 'PT0S')
                        if not self.youtube_searcher:
                            self.youtube_searcher = YouTubeSearcher(analyzer_youtube_service)
                        elif self.youtube_searcher.youtube != analyzer_youtube_service:
                            self.youtube_searcher = YouTubeSearcher(analyzer_youtube_service)
                        duration_str = self.youtube_searcher._parse_duration(duration_iso)
                        
                        pub_at = v['snippet'].get('publishedAt', '')
                        try:
                            pub_dt = datetime.strptime(pub_at, '%Y-%m-%dT%H:%M:%SZ')
                            pub_str = pub_dt.strftime('%Y-%m-%d')
                        except:
                            pub_str = pub_at.split('T')[0]
                            
                        videos.append({
                            'title': v['snippet']['title'],
                            'views': int(v['statistics'].get('viewCount', 0)),
                            'duration': duration_str,
                            'date': pub_str,
                            'description': v['snippet'].get('description', ''),
                            'tags': v['snippet'].get('tags', []),
                            'url': f"https://www.youtube.com/watch?v={v['id']}"
                        })
                        
                    # Sort by recent date
                    videos.sort(key=lambda x: x['date'], reverse=True)
            
            # Populate the Top Videos treeview
            self.current_yt_videos_data = list(videos)
            
            def populate_videos(vids):
                self.yt_videos_tree.delete(*self.yt_videos_tree.get_children())
                self._video_data_by_iid = {}
                for i, v in enumerate(vids):
                    iid = f"vid_{i}"
                    self.yt_videos_tree.insert('', tk.END, iid=iid, values=(
                        v['title'], f"{v['views']:,}", v['duration'], v['date']
                    ))
                    self._video_data_by_iid[iid] = v
            
            self.root.after(0, lambda: populate_videos(videos))
            self.root.after(0, lambda: self.analyzer_status.configure(text=f"Loaded {len(videos)} videos for {channel['title']}"))
            
        except Exception as e:
            self.root.after(0, lambda: self.analyzer_status.configure(text=f"Video fetch failed: {e}"))

    def copy_candidate_description(self):
        """Copy the selected candidate's description."""
        if hasattr(self, 'current_candidate_data') and self.current_candidate_data:
            self.copy_to_clipboard(self.current_candidate_data.get('description', ''))
            
    def copy_candidate_tags(self):
        """Copy the selected candidate's tags."""
        if hasattr(self, 'current_candidate_data') and self.current_candidate_data:
            self.copy_to_clipboard(','.join(self.current_candidate_data.get('tags', [])))

    def analyzer_run_grover_mock(self):
        """Mock Grover's Algorithm to select the best channel and fetch detailed insights"""
        if not hasattr(self, 'analyzer_channel_data') or not self.analyzer_channel_data:
            messagebox.showwarning("Warning", "Please search for channels first.")
            return
            
        analyzer_youtube_service = self.youtube_service
        if not analyzer_youtube_service:
            api_key = os.getenv("YOUTUBE_API_KEY")
            if not api_key:
                messagebox.showwarning("Warning", "Please authenticate with YouTube first (Upload tab), or provide YOUTUBE_API_KEY in .env.")
                return
            try:
                analyzer_youtube_service = build('youtube', 'v3', developerKey=api_key)
            except Exception as e:
                messagebox.showwarning("Error", f"Failed to initialize YouTube API with key: {e}")
                return
            
        self.analyzer_status.configure(text="Applying Grover's Mock Algorithm...")
        self.yt_channel_details_text.delete('1.0', tk.END)
        self.yt_channel_details_text.insert('1.0', "Initializing quantum superposition states...\n\nApplying Oracle phase inversion based on 'high growth' condition...\n\nApplying Diffusion operator to amplify probability amplitude...\n\nCollapsing wave function...\n\n...")
        
        def analyze():
            try:
                # Mock algorithm: just pick the one with highest views/subs ratio (growth indicator)
                # But heavily weight total views to ensure it's a big channel
                best_channel = None
                best_score = -1
                
                for ch in self.analyzer_channel_data:
                    # Score: views * log(subs)
                    score = ch['views']
                    if ch['subs'] > 0:
                        import math
                        score = ch['views'] * math.log(ch['subs'])
                        
                    if score > best_score:
                        best_score = score
                        best_channel = ch
                
                time.sleep(1.5) # Dramatic effect for quantum collapse
                
                if not best_channel:
                    self.root.after(0, lambda: self.analyzer_status.configure(text="Analysis failed: No valid channels."))
                    return
                
                self.current_yt_winner = best_channel
                
                # Fetch recent videos for this channel
                self.root.after(0, lambda: self.yt_channel_details_text.insert(tk.END, f"\n\nWinner found! Fetching deep analytics for: {best_channel['title']}..."))
                
                # Get uploaded videos playlist ID
                content_response = analyzer_youtube_service.channels().list(
                    part='contentDetails', id=best_channel['id']
                ).execute()
                
                videos = []
                if content_response.get('items'):
                    uploads_id = content_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                    
                    # Fetch recent 10 videos
                    playlist_response = analyzer_youtube_service.playlistItems().list(
                        part='snippet,contentDetails', playlistId=uploads_id, maxResults=15
                    ).execute()
                    
                    video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
                    
                    # Fetch full video stats
                    if video_ids:
                        videos_response = analyzer_youtube_service.videos().list(
                            part='snippet,statistics,contentDetails', id=','.join(video_ids)
                        ).execute()
                        
                        for v in videos_response.get('items', []):
                            # Calculate an approximate duration
                            duration_iso = v['contentDetails'].get('duration', 'PT0S')
                            if not self.youtube_searcher:
                                self.youtube_searcher = YouTubeSearcher(analyzer_youtube_service)
                            elif self.youtube_searcher.youtube != analyzer_youtube_service:
                                self.youtube_searcher = YouTubeSearcher(analyzer_youtube_service)
                            duration_str = self.youtube_searcher._parse_duration(duration_iso)
                            
                            pub_at = v['snippet'].get('publishedAt', '')
                            try:
                                pub_dt = datetime.strptime(pub_at, '%Y-%m-%dT%H:%M:%SZ')
                                pub_str = pub_dt.strftime('%Y-%m-%d')
                            except:
                                pub_str = pub_at.split('T')[0]
                                
                            videos.append({
                                'title': v['snippet']['title'],
                                'views': int(v['statistics'].get('viewCount', 0)),
                                'duration': duration_str,
                                'date': pub_str,
                                'description': v['snippet'].get('description', ''),
                                'tags': v['snippet'].get('tags', []),
                                'url': f"https://www.youtube.com/watch?v={v['id']}"
                            })
                            
                        # Sort by recent date
                        videos.sort(key=lambda x: x['date'], reverse=True)
                
                # Calculate Revenue
                # RPG estimate: $1.5 to $4.0 depending on niche. Let's average to $2.5 per 1000 views.
                rpm = 2.50 
                # Estimate monthly volume assuming 'views' are lifetime, we figure 10% is recent month if active
                est_monthly_views = best_channel['views'] * 0.10
                monthly_revenue = (est_monthly_views / 1000) * rpm
                
                # Format the text display
                out_text = f"🏆 WINNING CHANNEL: {best_channel['title']}\n"
                out_text += f"{'='*50}\n"
                out_text += f"📊 SUBSCRIBERS: {best_channel['subs']:,}\n"
                out_text += f"👁️ LIFETIME VIEWS: {best_channel['views']:,}\n"
                out_text += f"📅 CREATED DATE: {best_channel.get('created', 'N/A')}\n"
                out_text += f"🎬 TOTAL VIDEOS: {best_channel['video_count']:,}\n"
                out_text += f"💰 EST. RPM: ${rpm:.2f} per 1k views\n"
                out_text += f"💵 EST. MONTHLY REVENUE: ${monthly_revenue:,.2f}\n"
                
                # If they have over 1k subs and 4k watch hours (we guess based on views), they are monetized
                is_monetized = best_channel['subs'] >= 1000 and best_channel['views'] > 1000000
                monetization_status = "✅ Active" if is_monetized else "❌ Not eligible"
                out_text += f"💳 MONETIZATION STATUS: {monetization_status}\n"
                out_text += f"{'='*50}\n"
                out_text += f"📝 DESCRIPTION:\n{best_channel['description'][:500]}...\n\n"
                out_text += f"🏷️ CHANNEL TAGS:\n{', '.join(best_channel['tags']) if best_channel['tags'] else 'None found'}\n"
                
                self.root.after(0, lambda t=out_text: self.yt_channel_details_text.delete('1.0', tk.END))
                self.root.after(0, lambda t=out_text: self.yt_channel_details_text.insert('1.0', t))
                
                # Populate videos
                self.current_yt_videos_data = list(videos)
                
                def populate_videos_grover(vids):
                    self.yt_videos_tree.delete(*self.yt_videos_tree.get_children())
                    self._video_data_by_iid = {}
                    for i, v in enumerate(vids):
                        iid = f"vid_{i}"
                        self.yt_videos_tree.insert('', tk.END, iid=iid, values=(
                            v['title'], f"{v['views']:,}", v['duration'], v['date']
                        ))
                        self._video_data_by_iid[iid] = v
                
                self.root.after(0, lambda: populate_videos_grover(videos))
                
                self.root.after(0, lambda: self.analyzer_status.configure(text=f"Analysis complete on {best_channel['title']}"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Analysis failed: {e}"))
                self.root.after(0, lambda: self.analyzer_status.configure(text="Analysis failed."))
                
        threading.Thread(target=analyze, daemon=True).start()

    def open_yt_winner_channel(self):
        """Open the winner channel in browser"""
        if hasattr(self, 'current_yt_winner') and self.current_yt_winner:
            webbrowser.open(f"https://www.youtube.com/channel/{self.current_yt_winner['id']}")
            
    def on_video_select(self, event):
        """Handle selection of a video from the Top Videos treeview."""
        vid = self._get_selected_video()
        if vid:
            out_text = f"TITLE:\n{vid['title']}\n\n"
            out_text += f"URL:\n{vid['url']}\n\n"
            out_text += f"TAGS:\n{', '.join(vid['tags']) if vid['tags'] else 'None'}\n\n"
            out_text += f"DESCRIPTION:\n{vid['description']}\n"
            
            self.yt_video_details_text.delete('1.0', tk.END)
            self.yt_video_details_text.insert('1.0', out_text)

    def show_video_context_menu(self, event):
        """Show right-click context menu on Top Videos treeview."""
        row_id = self.yt_videos_tree.identify_row(event.y)
        if row_id:
            self.yt_videos_tree.selection_set(row_id)
            self.on_video_select(event)
            self.video_context_menu.post(event.x_root, event.y_root)

    def _get_selected_video(self):
        """Get the currently selected video data using iid-based lookup.
        Reads the selection directly — no event dependency, no title matching."""
        selection = self.yt_videos_tree.selection()
        if not selection:
            return None
        iid = selection[0]
        # Direct iid lookup - foolproof
        if hasattr(self, '_video_data_by_iid') and iid in self._video_data_by_iid:
            return self._video_data_by_iid[iid]
        return None

    def copy_video_title(self):
        vid = self._get_selected_video()
        if vid:
            self.copy_to_clipboard(vid['title'])
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")
            
    def copy_video_description(self):
        vid = self._get_selected_video()
        if vid:
            self.copy_to_clipboard(vid['description'])
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")
            
    def copy_video_tags(self):
        vid = self._get_selected_video()
        if vid:
            self.copy_to_clipboard(','.join(vid['tags']))
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")
            
    def copy_video_url(self):
        vid = self._get_selected_video()
        if vid:
            self.copy_to_clipboard(vid['url'])
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")
            
    def copy_channel_tags(self):
        if hasattr(self, 'current_yt_winner') and self.current_yt_winner:
            self.copy_to_clipboard(','.join(self.current_yt_winner.get('tags', [])))
            
    def open_selected_video(self):
        vid = self._get_selected_video()
        if vid:
            webbrowser.open(vid['url'])
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")
            
    def copy_all_to_upload(self):
        vid = self._get_selected_video()
        if vid:
            text = f"{vid['title']}\n\n{vid['description']}\n\n{','.join(vid['tags'])}"
            self.copy_to_clipboard(text)
        else:
            messagebox.showinfo("Select Video", "Please select a video first.")

    def download_video_mp3(self):
        """Download the selected video as MP3 using yt-dlp."""
        vid = self._get_selected_video()
        if not vid:
            messagebox.showinfo("Select Video", "Please select a video first.")
            return
            
        url = vid.get('url', '')
        title = vid.get('title', 'audio')
        if not url:
            messagebox.showwarning("Error", "No video URL available.")
            return
            
        # Ask user for download folder
        download_dir = filedialog.askdirectory(title="Select folder to save MP3")
        if not download_dir:
            return
            
        self.analyzer_status.configure(text=f"Downloading MP3: {title}...")
        
        def do_download():
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                self.root.after(0, lambda: self.analyzer_status.configure(text=f"✅ MP3 downloaded: {title}"))
                self.root.after(0, lambda: messagebox.showinfo("Download Complete", f"MP3 saved to:\n{download_dir}"))
                
            except ImportError:
                self.root.after(0, lambda: messagebox.showerror("Missing Package", "yt-dlp is not installed.\nRun: pip install yt-dlp"))
                self.root.after(0, lambda: self.analyzer_status.configure(text="Download failed: yt-dlp not installed."))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download MP3:\n{e}"))
                self.root.after(0, lambda: self.analyzer_status.configure(text=f"Download failed: {e}"))
        
        threading.Thread(target=do_download, daemon=True).start()
            
    def renamer_select_files(self):
        """Select files for bulk rename"""
        files = filedialog.askopenfilenames(title="Select files to rename")
        if not files:
            return
        
        self.renamer_file_list = []
        for f in files:
            ctime = self.get_file_creation_time(f)
            self.renamer_file_list.append((f, ctime))
        
        # Sort by creation date
        self.renamer_file_list.sort(key=lambda x: x[1])
        
        # Set base name from last file
        if self.renamer_file_list:
            last_file = self.renamer_file_list[-1][0]
            name_stem = os.path.splitext(os.path.basename(last_file))[0]
            self.renamer_base_name.set(name_stem)
        
        self.renamer_generate_preview()
    
    def renamer_select_folder(self):
        """Select all files from a folder"""
        folder = filedialog.askdirectory(title="Select folder with files to rename")
        if not folder:
            return
        
        self.renamer_file_list = []
        for f in os.listdir(folder):
            full_path = os.path.join(folder, f)
            if os.path.isfile(full_path):
                ctime = self.get_file_creation_time(full_path)
                self.renamer_file_list.append((full_path, ctime))
        
        # Sort by creation date
        self.renamer_file_list.sort(key=lambda x: x[1])
        
        # Set base name from last file
        if self.renamer_file_list:
            last_file = self.renamer_file_list[-1][0]
            name_stem = os.path.splitext(os.path.basename(last_file))[0]
            self.renamer_base_name.set(name_stem)
        
        self.renamer_generate_preview()
    
    def renamer_clear(self):
        """Clear the renamer file list"""
        self.renamer_file_list = []
        self.renamer_preview_data = []
        self.renamer_tree.delete(*self.renamer_tree.get_children())
        self.renamer_base_name.set("")
        self.renamer_file_count.configure(text="No files selected")
        self.renamer_status.configure(text="Cleared", foreground="gray")
    
    def renamer_move_up(self):
        """Move selected file up in the rename sequence"""
        selection = self.renamer_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        # Find index in treeview which matches index in renamer_file_list
        idx = self.renamer_tree.index(item)
        
        if idx > 0:
            # Swap in file list
            self.renamer_file_list[idx], self.renamer_file_list[idx-1] = self.renamer_file_list[idx-1], self.renamer_file_list[idx]
            
            # Refresh preview
            self.renamer_generate_preview()
            
            # Reselect item
            children = self.renamer_tree.get_children()
            if len(children) > idx - 1:
                new_item = children[idx - 1]
                self.renamer_tree.selection_set(new_item)
                self.renamer_tree.focus(new_item)
                self.renamer_tree.see(new_item)

    def renamer_move_down(self):
        """Move selected file down in the rename sequence"""
        selection = self.renamer_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        idx = self.renamer_tree.index(item)
        
        if idx < len(self.renamer_file_list) - 1:
            # Swap in file list
            self.renamer_file_list[idx], self.renamer_file_list[idx+1] = self.renamer_file_list[idx+1], self.renamer_file_list[idx]
            
            # Refresh preview
            self.renamer_generate_preview()
            
            # Reselect item
            children = self.renamer_tree.get_children()
            if len(children) > idx + 1:
                new_item = children[idx + 1]
                self.renamer_tree.selection_set(new_item)
                self.renamer_tree.focus(new_item)
                self.renamer_tree.see(new_item)
    
    def get_file_creation_time(self, filepath):
        """Get file creation time safely"""
        try:
            return os.path.getctime(filepath)
        except OSError:
            return 0
    
    def renamer_update_preview(self, event=None):
        """Update preview when base name or sequence changes"""
        self.renamer_generate_preview()
    
    def renamer_generate_preview(self):
        """Generate rename preview in the treeview"""
        self.renamer_tree.delete(*self.renamer_tree.get_children())
        self.renamer_preview_data = []
        
        base = self.renamer_base_name.get().strip()
        
        try:
            current_seq = int(self.renamer_start_seq.get())
        except ValueError:
            return
        
        if not base or not self.renamer_file_list:
            return
        
        for original_path, ctime in self.renamer_file_list:
            original_name = os.path.basename(original_path)
            
            # Format date
            from datetime import datetime as dt
            date_str = dt.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Construct new name
            ext = os.path.splitext(original_path)[1]
            new_name = f"{base}_{current_seq}{ext}"
            
            # Store for execution
            self.renamer_preview_data.append((original_path, new_name))
            
            # Display
            self.renamer_tree.insert("", tk.END, values=(original_name, date_str, new_name))
            
            current_seq += 1
        
        self.renamer_file_count.configure(text=f"{len(self.renamer_file_list)} files selected")
        self.renamer_status.configure(text=f"Preview ready. Start # = {self.renamer_start_seq.get()}", foreground="blue")
    
    def renamer_execute(self):
        """Execute the bulk rename operation"""
        if not self.renamer_preview_data:
            messagebox.showwarning("No Files", "Please select files first.")
            return
        
        if not messagebox.askyesno("Confirm Rename", 
                f"Rename {len(self.renamer_preview_data)} files?\n\nThis cannot be undone easily."):
            return
        
        count = 0
        errors = 0
        
        for original_path, new_name in self.renamer_preview_data:
            directory = os.path.dirname(original_path)
            new_path = os.path.join(directory, new_name)
            
            if os.path.exists(new_path) and new_path != original_path:
                self.log(f"⚠️ Skipped: {new_name} already exists")
                errors += 1
                continue
            
            try:
                os.rename(original_path, new_path)
                count += 1
            except Exception as e:
                self.log(f"❌ Error renaming {os.path.basename(original_path)}: {e}")
                errors += 1
        
        msg = f"✅ Successfully renamed {count} files."
        if errors > 0:
            msg += f"\n⚠️ {errors} files skipped due to errors."
        
        self.log(msg)
        messagebox.showinfo("Rename Complete", msg)
        
        # Clear
        self.renamer_clear()
    
    def single_browse_file(self):
        """Browse for a single file to rename"""
        file_path = filedialog.askopenfilename(title="Select file to rename")
        if file_path:
            self.single_file_path.set(file_path)
            # Pre-fill new name with current name
            self.single_new_name.set(os.path.basename(file_path))
    
    def single_rename_file(self):
        """Rename a single file"""
        old_path = self.single_file_path.get().strip()
        new_name = self.single_new_name.get().strip()
        
        if not old_path or not os.path.exists(old_path):
            messagebox.showwarning("Error", "Please select a valid file.")
            return
        
        if not new_name:
            messagebox.showwarning("Error", "Please enter a new name.")
            return
        
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)
        
        if os.path.exists(new_path) and new_path != old_path:
            messagebox.showwarning("Error", f"A file named '{new_name}' already exists.")
            return
        
        try:
            os.rename(old_path, new_path)
            self.log(f"✅ Renamed: {os.path.basename(old_path)} → {new_name}")
            messagebox.showinfo("Success", f"File renamed successfully!")
            self.single_file_path.set("")
            self.single_new_name.set("")
        except Exception as e:
            self.log(f"❌ Error: {e}")
            messagebox.showerror("Error", f"Failed to rename: {e}")
    
    def log(self, message):
        """Add message to log"""
        self.log_text.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        self.root.update_idletasks()
    
    def check_credentials(self):
        """Check if YouTube credentials exist"""
        if not os.path.exists(CLIENT_SECRETS_FILE):
            messagebox.showwarning("Warning", 
                f"client_secret.json not found at:\n{CLIENT_SECRETS_FILE}\n\n"
                "Please download it from Google Cloud Console.")
    
    def browse_folder(self):
        """Browse for folder containing videos"""
        folder = filedialog.askdirectory()
        if folder:
            self.video_files = []
            for ext in SUPPORTED_VIDEO_FORMATS:
                self.video_files.extend(Path(folder).glob(f"*{ext}"))
            self.video_files = [str(f) for f in self.video_files]
            self.update_video_list()
    
    def select_files(self):
        """Select individual video files"""
        files = filedialog.askopenfilenames(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm"),
                      ("All files", "*.*")]
        )
        if files:
            self.video_files = list(files)
            self.update_video_list()
    
    def clear_selection(self):
        """Clear all selected videos and cleanup frames"""
        self.cleanup_frames()
        self.video_files = []
        self.update_video_list()
        self.title_text.delete('1.0', tk.END)
        self.desc_text.delete('1.0', tk.END)
        self.tags_text.delete('1.0', tk.END)
        self.analysis_text.delete('1.0', tk.END)
    
    def cleanup_frames(self):
        """Delete extracted frame files"""
        for frame_path in self.extracted_frames:
            try:
                if os.path.exists(frame_path):
                    os.remove(frame_path)
                    self.log(f"Deleted frame: {os.path.basename(frame_path)}")
            except Exception as e:
                self.log(f"Error deleting frame {frame_path}: {e}")
        
        self.extracted_frames = []
        
        # Clear frame display
        for widget in self.frames_container.winfo_children():
            widget.destroy()
    
    def update_video_list(self):
        """Update the video listbox"""
        self.video_listbox.delete(0, tk.END)
        for video in self.video_files:
            self.video_listbox.insert(tk.END, os.path.basename(video))
        self.file_count_label.configure(text=f"{len(self.video_files)} files selected")
        self.log(f"Selected {len(self.video_files)} video(s)")
    
    def on_video_select(self, event):
        """Handle video selection change"""
        # Prevent selection change during processing
        if self.is_processing:
            self.log("⚠ Processing in progress - please wait before selecting another video")
            return
        
        selection = self.video_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.video_files):
                video_path = self.video_files[index]
                self.log(f"Selected: {os.path.basename(video_path)}")
    
    def get_selected_video(self):
        """Get currently selected video path"""
        selection = self.video_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.video_files):
                return self.video_files[index]
        return None
    
    def extract_and_analyze(self):
        """Extract frames and analyze them with Ollama"""
        video_path = self.get_selected_video()
        if not video_path:
            messagebox.showwarning("Warning", "Please select a video first")
            return
        
        # Check if already processing
        if self.is_processing:
            messagebox.showwarning("Warning", "Processing already in progress. Please wait.")
            return
        
        # Set processing flag
        self.is_processing = True
        self.video_listbox.configure(state='disabled')
        self.log("🔒 Video selection locked - processing in progress...")
        
        def process():
            try:
                # Cleanup previous frames
                self.root.after(0, self.cleanup_frames)
                
                # Step 1: Extract frames
                self.root.after(0, lambda: self.status_label.configure(text="Extracting frames..."))
                self.root.after(0, lambda: self.log(f"Extracting {self.frame_count_var.get()} frames from video..."))
                
                num_frames = self.frame_count_var.get()
                frames, duration = VideoFrameExtractor.extract_random_frames(video_path, num_frames)
                self.extracted_frames = frames
                
                self.root.after(0, lambda: self.log(f"✓ Extracted {len(frames)} frames"))
                self.root.after(0, lambda: self.display_frames(frames))
                
                # Step 2: Analyze frames with Ollama
                self.root.after(0, lambda: self.status_label.configure(text="Analyzing frames with AI..."))
                self.root.after(0, lambda: self.log("Analyzing frames with Ollama vision model..."))
                
                vision_model = self.vision_model_var.get()
                descriptions = OllamaImageAnalyzer.analyze_frames(frames, vision_model)
                
                # Display analysis
                analysis_text = "\n\n".join([f"Frame {i+1}:\n{desc}" for i, desc in enumerate(descriptions)])
                self.root.after(0, lambda: self.analysis_text.delete('1.0', tk.END))
                self.root.after(0, lambda: self.analysis_text.insert('1.0', analysis_text))
                
                self.root.after(0, lambda: self.log("✓ Frame analysis complete"))
                self.root.after(0, lambda: self.status_label.configure(text="Frame analysis complete. Ready to search YouTube."))
                
                # Store analysis for later use
                self.last_analysis = {
                    'descriptions': descriptions,
                    'duration': duration,
                    'video_path': video_path
                }
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Error: {str(e)}"))
                self.root.after(0, lambda: self.status_label.configure(text="Error occurred"))
                messagebox.showerror("Error", f"Failed to extract/analyze frames: {e}")
            finally:
                # Always unlock when done (success or error)
                self.is_processing = False
                self.root.after(0, lambda: self.video_listbox.configure(state='normal'))
                self.root.after(0, lambda: self.log("🔓 Video selection unlocked - processing complete"))
        
        threading.Thread(target=process, daemon=True).start()
    
    def display_frames(self, frame_paths):
        """Display extracted frames in the analysis tab"""
        # Clear previous frames and photo references
        for widget in self.frames_container.winfo_children():
            widget.destroy()
        if not hasattr(self, 'photo_references'):
            self.photo_references = []
        self.photo_references.clear()
        
        # Display new frames
        for i, frame_path in enumerate(frame_paths):
            try:
                # Load and resize image
                img = Image.open(frame_path)
                img.thumbnail((200, 200))
                
                # Convert to PhotoImage
                photo = tk.PhotoImage(file=frame_path)
                
                # Create label with image
                label = tk.Label(self.frames_container, image=photo, text=f"Frame {i+1}", compound=tk.BOTTOM, bg='gray90')
                self.photo_references.append(photo)  # Keep reference to prevent garbage collection
                label.grid(row=i // 4, column=i % 4, padx=5, pady=5)
            except Exception as e:
                print(f"Error displaying frame {frame_path}: {e}")
    
    def search_youtube_related(self):
        """Search YouTube for related high-view videos"""
        if not hasattr(self, 'last_analysis'):
            messagebox.showwarning("Warning", "Please extract and analyze frames first")
            return
        
        if not self.youtube_service:
            messagebox.showwarning("Warning", "Please authenticate with YouTube first")
            return
        
        def search():
            try:
                self.root.after(0, lambda: self.status_label.configure(text="Searching YouTube..."))
                self.root.after(0, lambda: self.log("Searching YouTube for related high-view videos..."))
                
                # Create search query from analysis
                descriptions = self.last_analysis['descriptions']
                
                # Use first description as search query (simplified)
                search_query = descriptions[0][:100] if descriptions else "video"
                
                # Initialize searcher
                if not self.youtube_searcher:
                    self.youtube_searcher = YouTubeSearcher(self.youtube_service)
                
                # Search
                results = self.youtube_searcher.search_related_videos(search_query, max_results=5)
                
                # Display results
                self.root.after(0, lambda: self.display_search_results(results))
                
                self.root.after(0, lambda: self.log(f"✓ Found {len(results)} related videos"))
                self.root.after(0, lambda: self.status_label.configure(text="YouTube search complete. Ready to generate metadata."))
                
                # Store results
                self.last_search_results = results
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Search error: {str(e)}"))
                messagebox.showerror("Error", f"YouTube search failed: {e}")
        
        threading.Thread(target=search, daemon=True).start()
    
    def search_youtube_tab(self):
        """Handle search from the dedicated search tab"""
        query = self.search_query_var.get().strip()
        days = self.search_days_var.get().strip()
        
        # Get filter values
        try:
            region = self.search_region_var.get()
            location_query = self.search_location_var.get().strip()
        except:
             # Default if variables not initialized yet
            region = 'All'
            location_query = ''
        
        if not self.youtube_service:
            messagebox.showwarning("Warning", "Please authenticate with YouTube first")
            return
            
        region_code = region if region != 'All' else 'US'

        # Run search in thread
        self.status_label.configure(text=f"Searching...")
        
        def run_search():
            try:
                if not self.youtube_searcher:
                    self.youtube_searcher = YouTubeSearcher(self.youtube_service)
                
                results = []
                if query:
                    # Standard search (query + location context if needed)
                    full_query = f"{query} {location_query}".strip()
                    results = self.youtube_searcher.search_related_videos(full_query, max_results=20, days_filter=days, region_code=region_code)
                    self.root.after(0, lambda: self.status_label.configure(text=f"Found {len(results)} videos for '{full_query}'"))
                    
                elif location_query:
                    # Location only -> Search for location in region
                    self.root.after(0, lambda: self.status_label.configure(text=f"Searching for '{location_query}' in {region_code}..."))
                    results = self.youtube_searcher.search_related_videos(location_query, max_results=50, days_filter=days, region_code=region_code)
                    self.root.after(0, lambda: self.status_label.configure(text=f"Found {len(results)} videos for '{location_query}'"))
                    
                else:
                    # Trending
                    self.root.after(0, lambda: self.status_label.configure(text=f"Fetching trending videos for {region_code}..."))
                    results = self.youtube_searcher.get_trending_videos(max_results=100, region_code=region_code)
                    self.root.after(0, lambda: self.status_label.configure(text=f"Found {len(results)} trending videos"))
                
                self.root.after(0, lambda: self.display_search_results(results))
                
                # Store results for detail view reference
                self.current_search_results = results
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Search failed: {e}"))
                self.root.after(0, lambda: self.status_label.configure(text="Search failed"))
        
        threading.Thread(target=run_search, daemon=True).start()


    def treeview_sort_column(self, tv, col, reverse):
        """Sort treeview content by column"""
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        
        try:
            def convert(val):
                if val == 'N/A': return -1
                if col == 'Views':
                    return int(val.replace(',', ''))
                elif col == 'Duration':
                    parts = val.split(':')
                    if len(parts) == 3:
                        return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                    elif len(parts) == 2:
                        return int(parts[0])*60 + int(parts[1])
                    return 0
                return val.lower()
            
            l.sort(key=lambda t: convert(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
            
        for index, (_, k) in enumerate(l):
            tv.move(k, '', index)
            
        # Update heading to reverse sort next time
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def display_search_results(self, results):
        """Display YouTube search results in the treeview"""
        # Clear previous results
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        if not results:
            self.search_details_text.delete('1.0', tk.END)
            self.search_details_text.insert('1.0', "No results found.")
            return

        # Add new results
        for result in results:
            self.search_tree.insert('', tk.END, values=(
                result['title'],
                f"{result['views']:,}",
                result.get('duration', 'N/A'),
                result.get('published_at', 'N/A'),
                result.get('channel_title', 'N/A'),
                result.get('country', 'N/A'),
                result.get('location', 'N/A'),
                result['video_id']
            ))
            
    def on_search_result_select(self, event):
        """Show details when a search result is selected"""
        selection = self.search_tree.selection()
        if not selection or not hasattr(self, 'current_search_results'):
            return
            
        item_id = selection[0]
        item_values = self.search_tree.item(item_id, 'values')
        # Check if we have enough values (in case of old data/cache)
        # Columns: Title, Views, Duration, Date, Channel, Country, Location, ID
        # Index:   0      1      2         3     4        5        6         7
        if len(item_values) > 7:
            video_id = item_values[7]
        elif len(item_values) > 6:
            video_id = item_values[6]
        else:
            video_id = item_values[5]
        
        # Find full result object
        selected_video = next((r for r in self.current_search_results if r['video_id'] == video_id), None)
        
        if selected_video:
            # Format details with Country and Location
            country_info = f"Country: {selected_video.get('country', 'N/A')}"
            location_info = ""
            if selected_video.get('location'):
                location_info = f"Location: {selected_video['location']}\n"
                
            details = (
                f"Title: {selected_video['title']}\n"
                f"Channel: {selected_video.get('channel_title', 'N/A')} | {country_info}\n"
                f"{location_info}"
                f"Views: {selected_video['views']:,} | Likes: {selected_video['likes']:,}\n"
                f"Published: {selected_video.get('published_at', 'N/A')} | Duration: {selected_video.get('duration', 'N/A')}\n\n"
                f"Description:\n{selected_video['description']}\n\n"
                f"Description:\n{selected_video['description']}\n\n"
                f"Tags: {', '.join(selected_video.get('tags', []))}\n\n"
                f"Channel Tags: {selected_video.get('channel_tags', 'N/A')}"
            )
            
            self.search_details_text.delete('1.0', tk.END)
            self.search_details_text.insert('1.0', details)
            
            # Store selected video for copy buttons
            self.selected_detail_video = selected_video

    def show_tree_context_menu(self, event):
        """Show context menu on right click"""
        item = self.search_tree.identify_row(event.y)
        if item:
            self.search_tree.selection_set(item)
            self.on_search_result_select(None) # Update details
            self.tree_context_menu.post(event.x_root, event.y_root)

    def copy_to_clipboard(self, text):
        """Helper to copy text to clipboard"""
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update() # Required to finalize clipboard update
            self.status_label.configure(text="Copied to clipboard!")
            
    def get_selected_tree_video(self):
        """Get the video object currently selected in the tree"""
        selection = self.search_tree.selection()
        if not selection or not hasattr(self, 'current_search_results'):
            return None
            
        item_id = selection[0]
        item_values = self.search_tree.item(item_id, 'values')
        video_id = item_values[5]
        
        return next((r for r in self.current_search_results if r['video_id'] == video_id), None)

    def copy_tree_url(self):
        video = self.get_selected_tree_video()
        if video:
            self.copy_to_clipboard(f"https://www.youtube.com/watch?v={video['video_id']}")
            
    def copy_tree_title(self):
        video = self.get_selected_tree_video()
        if video:
            self.copy_to_clipboard(video['title'])
            
    def copy_tree_id(self):
        video = self.get_selected_tree_video()
        if video:
            self.copy_to_clipboard(video['video_id'])
            
    def copy_detail(self, target):
        """Copy specific detail from the currently displayed video"""
        if not hasattr(self, 'selected_detail_video') or not self.selected_detail_video:
            messagebox.showinfo("Info", "Please select a video first")
            return
            
        video = self.selected_detail_video
        
        if target == 'title':
            self.copy_to_clipboard(video.get('title', ''))
        elif target == 'description':
            self.copy_to_clipboard(video.get('description', ''))
        elif target == 'tags':
            self.copy_to_clipboard(','.join(video.get('tags', [])))
        elif target == 'url':
            self.copy_to_clipboard(f"https://www.youtube.com/watch?v={video.get('video_id', '')}")
        elif target == 'channel_tags':
            self.copy_to_clipboard(video.get('channel_tags', ''))

    def open_current_video(self):
        """Open the currently displayed video in the default browser"""
        if not hasattr(self, 'selected_detail_video') or not self.selected_detail_video:
            messagebox.showinfo("Info", "Please select a video first")
            return
            
        video_id = self.selected_detail_video.get('video_id')
        if video_id:
            url = f"https://www.youtube.com/watch?v={video_id}"
            webbrowser.open(url)
            self.status_label.configure(text=f"Opening: {url}")
            
    def open_tree_video(self):
        """Open the video selected in the tree context menu"""
        video = self.get_selected_tree_video()
        if video:
            url = f"https://www.youtube.com/watch?v={video['video_id']}"
            webbrowser.open(url)
            self.status_label.configure(text=f"Opening: {url}")
            
    def copy_all_to_upload(self):
        """Copy all metadata from selected video to Upload tab fields"""
        if not hasattr(self, 'selected_detail_video') or not self.selected_detail_video:
            messagebox.showinfo("Info", "Please select a video first")
            return
            
        video = self.selected_detail_video
        
        # Confirm action
        if not messagebox.askyesno("Confirm Copy", 
                "This will overwrite existing Title, Description, and Tags in the Upload tab.\n\nContinue?"):
            return
            
        # Update Upload Tab fields
        # Title
        self.title_text.delete('1.0', tk.END)
        self.title_text.insert('1.0', video.get('title', ''))
        
        # Description
        self.desc_text.delete('1.0', tk.END)
        self.desc_text.insert('1.0', video.get('description', ''))
        
        # Tags
        tags = ', '.join(video.get('tags', []))
        self.tags_text.delete('1.0', tk.END)
        self.tags_text.insert('1.0', tags)
        
        # Switch to Upload Tab (index 0)
        self.notebook.select(0)
        
        self.status_label.configure(text=f"Copied metadata from '{video.get('title', '')}'")
        messagebox.showinfo("Success", "Metadata copied to Upload tab!")
    
    def generate_metadata_from_analysis(self):
        """Generate metadata based on frame analysis and YouTube search results"""
        if not hasattr(self, 'last_analysis'):
            messagebox.showwarning("Warning", "Please extract and analyze frames first")
            return
        
        def generate():
            try:
                self.root.after(0, lambda: self.status_label.configure(text="Generating metadata..."))
                
                # Check if viral mode is enabled
                viral_mode = getattr(self, 'viral_mode_var', tk.BooleanVar(value=False)).get()
                
                if viral_mode:
                    self.root.after(0, lambda: self.log("🔥 VIRAL MODE ACTIVATED - Generating million-view metadata..."))
                else:
                    self.root.after(0, lambda: self.log("Generating optimized metadata from analysis..."))
                
                # Get analysis data
                descriptions = self.last_analysis['descriptions']
                duration = self.last_analysis['duration']
                video_path = self.last_analysis['video_path']
                video_topic = self.get_video_info(video_path)
                
                # Summarize content
                content_summary = OllamaImageAnalyzer.summarize_content(
                    descriptions, duration, self.model_var.get()
                )
                
                # Get search results data if available
                search_data = ""
                search_results = []
                if hasattr(self, 'last_search_results') and self.last_search_results:
                    search_results = self.last_search_results
                    top_video = search_results[0]
                    search_data = f"""
Top Related Video Data:
- Title: {top_video['title']}
- Views: {top_video['views']:,}
- Tags: {', '.join(top_video['tags'][:10]) if top_video['tags'] else 'N/A'}
"""
                
                if viral_mode and VIRAL_OPTIMIZER_AVAILABLE:
                    # Use viral optimization
                    self.root.after(0, lambda: self.log("Generating 10 viral title options..."))
                    
                    # Generate viral titles
                    viral_titles = ViralSEOOptimizer.generate_viral_titles(
                        video_topic, content_summary, num_titles=10
                    )
                    
                    # Extract viral keywords
                    viral_keywords = ViralSEOOptimizer.extract_viral_keywords(
                        content_summary, video_topic, search_results
                    )
                    
                    # Generate viral description
                    self.root.after(0, lambda: self.log("Creating viral-optimized description..."))
                    viral_description = ViralSEOOptimizer.generate_viral_description(
                        video_topic, viral_titles, viral_keywords, search_data, duration
                    )
                    
                    # Generate viral hashtags
                    viral_hashtags = ViralSEOOptimizer.generate_viral_hashtags(
                        video_topic, viral_keywords
                    )
                    
                    # Parse the best title from viral titles
                    metadata = self.parse_viral_metadata(
                        viral_titles, viral_description, viral_hashtags, viral_keywords
                    )
                    
                    # Add viral optimization info
                    metadata['viral_info'] = {
                        'titles': viral_titles,
                        'posting_time': ViralSEOOptimizer.get_optimal_posting_time(),
                        'engagement_strategy': ViralSEOOptimizer.generate_engagement_strategy(video_topic),
                        'thumbnail_suggestions': ViralSEOOptimizer.create_thumbnail_suggestions(video_topic, content_summary)
                    }
                    
                    # Show viral optimization details
                    self.show_viral_optimization_details(metadata['viral_info'])
                    
                else:
                    # Standard metadata generation
                    prompt = f"""Based on the following video analysis and successful YouTube video data, create optimized YouTube metadata:

VIDEO CONTENT ANALYSIS:
{content_summary}

{search_data}

Please provide:
1. An attention-grabbing title (under 100 characters, include power words)
2. A detailed description (first 2 lines are critical for SEO, include timestamps if applicable)
3. 10-15 SEO keywords/tags (comma-separated)
4. 5-10 relevant hashtags

Make the metadata SEO-optimized and designed to attract views. Use the successful video data as inspiration but make it unique."""
                    
                    response = chat(
                        model=self.model_var.get(),
                        messages=[{'role': 'user', 'content': prompt}]
                    )
                    
                    metadata = self.parse_metadata_response(response.message.content)
                
                # Populate fields
                self.root.after(0, lambda: self.populate_metadata(metadata))
                self.root.after(0, lambda: self.log("✓ Metadata generated successfully"))
                
                if viral_mode:
                    self.root.after(0, lambda: self.status_label.configure(text="🔥 VIRAL metadata ready! Review and upload for millions of views!"))
                else:
                    self.root.after(0, lambda: self.status_label.configure(text="Metadata generated. Review and upload."))
                
                # Ask user to confirm before deleting frames
                self.root.after(0, self.confirm_and_cleanup)
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Metadata generation error: {str(e)}"))
                messagebox.showerror("Error", f"Failed to generate metadata: {e}")
        
        threading.Thread(target=generate, daemon=True).start()
    
    def parse_metadata_response(self, content):
        """Parse AI response to extract metadata fields"""
        metadata = {
            'title': '',
            'description': '',
            'tags': []
        }
        
        # Extract title
        title_match = re.search(r'(?:Title|1\.?)[\s:]*([^\n]+)', content, re.IGNORECASE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        # Extract description
        desc_patterns = [
            r'(?:Description|2\.?)[\s:]*([\s\S]*?)(?=Keywords|Tags|3\.?|$)',
            r'Description[\s:]*\n([\s\S]*?)(?=\n\n|\Z)',
        ]
        for pattern in desc_patterns:
            desc_match = re.search(pattern, content, re.IGNORECASE)
            if desc_match:
                metadata['description'] = desc_match.group(1).strip()
                break
        
        # Extract tags
        tag_patterns = [
            r'(?:Keywords|Tags|3\.?)[\s:]*([\s\S]*?)(?=Hashtags|4\.?|$)',
            r'[\s\S]*?([\w\s,]+)(?=Hashtags|$)',
        ]
        for pattern in tag_patterns:
            tag_match = re.search(pattern, content, re.IGNORECASE)
            if tag_match:
                tags_text = tag_match.group(1)
                # Split by commas or newlines
                tags = re.split(r'[,\n]', tags_text)
                metadata['tags'] = [tag.strip() for tag in tags if tag.strip() and len(tag.strip()) > 2][:15]
                break
        
        # If no tags found, use defaults
        if not metadata['tags']:
            metadata['tags'] = ['video', 'youtube', 'content']
        
        return metadata
    
    def confirm_and_cleanup(self):
        """Ask user to confirm metadata and cleanup frames"""
        if messagebox.askyesno("Confirm", "Metadata generated successfully!\n\nDo you want to delete the extracted frame images?\n(This will free up disk space)"):
            self.cleanup_frames()
            self.log("✓ Frame images deleted")
    
    def populate_metadata(self, metadata):
        """Populate metadata fields"""
        self.title_text.delete('1.0', tk.END)
        self.title_text.insert('1.0', metadata['title'])
        
        self.desc_text.delete('1.0', tk.END)
        self.desc_text.insert('1.0', metadata['description'])
        
        self.tags_text.delete('1.0', tk.END)
        self.tags_text.insert('1.0', ', '.join(metadata['tags']))
    
    def parse_viral_metadata(self, viral_titles, viral_description, viral_hashtags, viral_keywords):
        """Parse viral optimization output into metadata dict"""
        metadata = {
            'title': '',
            'description': '',
            'tags': viral_keywords[:15]  # Use top 15 keywords as tags
        }
        
        # Extract the recommended title (usually the first one or marked as RECOMMENDED)
        title_lines = viral_titles.split('\n')
        for line in title_lines:
            if 'RECOMMENDED' in line.upper() or line.strip().startswith('1.'):
                # Extract title after number or recommendation marker
                title_match = re.search(r'(?:\d+\.\s*|RECOMMENDED:?\s*)(.+)', line)
                if title_match:
                    metadata['title'] = title_match.group(1).strip()
                    break
        
        # If no title found, use first non-empty line
        if not metadata['title']:
            for line in title_lines:
                clean_line = line.strip()
                if clean_line and not clean_line.startswith('#') and len(clean_line) > 10:
                    metadata['title'] = clean_line
                    break
        
        # Build description with viral content
        desc_parts = [viral_description]
        
        # Add hashtags section
        if viral_hashtags:
            desc_parts.append(f"\n\nVIRAL HASHTAGS:\n{' '.join(viral_hashtags)}")
        
        # Add keywords section
        if viral_keywords:
            desc_parts.append(f"\n\nSEO KEYWORDS:\n{', '.join(viral_keywords[:20])}")
        
        metadata['description'] = '\n'.join(desc_parts)
        
        return metadata
    
    def show_viral_optimization_details(self, viral_info):
        """Show viral optimization details in a popup window"""
        try:
            # Create popup window
            popup = tk.Toplevel(self.root)
            popup.title("🔥 VIRAL OPTIMIZATION DETAILS")
            popup.geometry("700x800")
            popup.transient(self.root)
            popup.grab_set()
            
            # Create scrolled text widget
            text_widget = scrolledtext.ScrolledText(popup, wrap=tk.WORD, padx=10, pady=10)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Build content
            content = []
            content.append("=" * 60)
            content.append("🔥 VIRAL OPTIMIZATION STRATEGY 🔥")
            content.append("=" * 60)
            content.append("")
            
            # All 10 titles
            if 'titles' in viral_info:
                content.append("📌 ALL 10 VIRAL TITLE OPTIONS:")
                content.append("-" * 40)
                content.append(viral_info['titles'])
                content.append("")
            
            # Posting time
            if 'posting_time' in viral_info:
                content.append("⏰ OPTIMAL POSTING TIME:")
                content.append("-" * 40)
                for key, value in viral_info['posting_time'].items():
                    content.append(f"  {key.upper()}: {value}")
                content.append("")
            
            # Engagement strategy
            if 'engagement_strategy' in viral_info:
                content.append("💬 ENGAGEMENT STRATEGY:")
                content.append("-" * 40)
                strategy = viral_info['engagement_strategy']
                for key, value in strategy.items():
                    if key != 'cross_platform':
                        content.append(f"  {key}: {value}")
                
                if 'cross_platform' in strategy:
                    content.append("\n  Cross-Platform Promotion:")
                    for platform in strategy['cross_platform']:
                        content.append(f"    • {platform}")
                content.append("")
            
            # Thumbnail suggestions
            if 'thumbnail_suggestions' in viral_info:
                content.append("🎨 THUMBNAIL OPTIMIZATION:")
                content.append("-" * 40)
                thumb = viral_info['thumbnail_suggestions']
                if 'text_suggestions' in thumb:
                    content.append("  Text Options:")
                    for text in thumb['text_suggestions']:
                        content.append(f"    • {text}")
                if 'color_scheme' in thumb:
                    content.append(f"\n  Color Scheme: {thumb['color_scheme']}")
                if 'elements' in thumb:
                    content.append("\n  Key Elements:")
                    for element in thumb['elements']:
                        content.append(f"    • {element}")
                content.append("")
            
            content.append("=" * 60)
            content.append("💡 TIPS FOR MILLION VIEWS:")
            content.append("=" * 60)
            content.append("  • Post at optimal time for maximum reach")
            content.append("  • Use the most engaging title from the list")
            content.append("  • Create thumbnail with suggested elements")
            content.append("  • Pin the engagement comment immediately")
            content.append("  • Share on all platforms within 1 hour")
            content.append("  • Reply to first 20 comments quickly")
            content.append("  • Create community post before upload")
            content.append("  • Cross-promote on TikTok/Instagram Reels")
            content.append("")
            content.append("🎯 TARGET: 1,000+ subscribers/day & millions of views!")
            content.append("=" * 60)
            
            # Insert content
            text_widget.insert('1.0', '\n'.join(content))
            text_widget.configure(state='disabled')
            
            # Close button
            ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=10)
            
            self.log("✓ Viral optimization details displayed")
            
        except Exception as e:
            self.log(f"Error showing viral details: {e}")
    
    def get_video_info(self, video_path):
        """Extract basic info from video filename"""
        filename = os.path.basename(video_path)
        name_without_ext = os.path.splitext(filename)[0]
        # Clean up the name (replace underscores, dashes with spaces)
        clean_name = re.sub(r'[_-]', ' ', name_without_ext)
        return clean_name
    
    def authenticate_youtube(self):
        """Authenticate with YouTube API for the selected channel"""
        # Check if a channel is selected
        if not self.current_channel:
            messagebox.showwarning("Warning", 
                "No channel selected. Please add a channel first using 'Manage Channels'.")
            return
        
        try:
            self.status_label.configure(text=f"Authenticating with {self.current_channel['name']}...")
            token_file = self.current_channel.get('token_file', TOKEN_FILE)
            client_secrets = self.current_channel.get('client_secrets', CLIENT_SECRETS_FILE)
            self.youtube_service = get_authenticated_service(token_file, client_secrets)
            self.youtube_searcher = YouTubeSearcher(self.youtube_service)
            self.update_channel_status()
            self.log(f"✅ YouTube authentication successful for '{self.current_channel['name']}'")
            messagebox.showinfo("Success", f"Successfully authenticated with '{self.current_channel['name']}'!")
        except Exception as e:
            self.log(f"Authentication error: {e}")
            messagebox.showerror("Error", f"Authentication failed: {e}")
    
    def upload_selected(self):
        """Upload currently selected video"""
        video_path = self.get_selected_video()
        if not video_path:
            messagebox.showwarning("Warning", "Please select a video to upload")
            return
        
        if not self.youtube_service:
            messagebox.showwarning("Warning", "Please authenticate with YouTube first")
            return
        
        # Get metadata
        title = self.title_text.get('1.0', tk.END).strip()
        description = self.desc_text.get('1.0', tk.END).strip()
        tags_text = self.tags_text.get('1.0', tk.END).strip()
        tags = [t.strip() for t in tags_text.split(',') if t.strip()]
        
        # Extract category ID
        category = self.category_var.get().split(' - ')[0]
        privacy = self.privacy_var.get()
        
        # Validate
        if not title:
            messagebox.showwarning("Warning", "Please enter a title")
            return
        
        def do_upload():
            try:
                self.root.after(0, lambda: self.status_label.configure(text=f"Uploading: {os.path.basename(video_path)}..."))
                self.root.after(0, lambda: self.log(f"Starting upload: {os.path.basename(video_path)}"))
                
                video_id = upload_video(
                    self.youtube_service,
                    video_path,
                    title,
                    description,
                    tags,
                    category=category,
                    privacy=privacy
                )
                
                self.root.after(0, lambda: self.log(f"✅ Uploaded successfully! Video ID: {video_id}"))
                self.root.after(0, lambda: self.status_label.configure(text="Upload completed"))
                self.root.after(0, lambda: self.progress_var.set(100))
                
                # Cleanup frames after successful upload
                self.root.after(0, self.cleanup_frames)
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Upload failed: {e}"))
                self.root.after(0, lambda: self.status_label.configure(text="Upload failed"))
                messagebox.showerror("Error", f"Upload failed: {e}")
        
        threading.Thread(target=do_upload, daemon=True).start()


def get_authenticated_service(token_file=None, client_secrets_file=None):
    """Handles OAuth2 flow and returns YouTube service object
    
    Args:
        token_file: Optional path to the token file. Defaults to TOKEN_FILE constant.
        client_secrets_file: Optional path to the client secrets file. Defaults to CLIENT_SECRETS_FILE constant.
    """
    if token_file is None:
        token_file = TOKEN_FILE
    
    if client_secrets_file is None:
        client_secrets_file = CLIENT_SECRETS_FILE
    
    creds = None
    
    # Load existing token if available
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # If no valid credentials, do the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=8080)
        
        # Save token for future runs
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def upload_video(youtube, file_path, title, description, tags, category='22', privacy='private'):
    """Uploads video to YouTube"""
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category
        },
        'status': {
            'privacyStatus': privacy,
            'selfDeclaredMadeForKids': False
        }
    }
    
    # Upload video file
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )
    
    # Execute upload
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")
    
    print(f"✅ Upload Complete! Video ID: {response['id']}")
    print(f"🔗 URL: https://youtu.be/{response['id']}")
    return response['id']


def main():
    root = tk.Tk()
    app = YouTubeUploaderApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
