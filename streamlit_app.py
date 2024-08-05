import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import SRTFormatter
import os
import subprocess
import re

# Function to modify the YouTube URL if it's a shorts URL
def modify_youtube_url(youtube_url):
    if "shorts/" in youtube_url:
        video_id = youtube_url.split("shorts/")[-1]
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    return youtube_url

# Function to download audio
def download_audio(youtube_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        audio_file = ydl.prepare_filename(info_dict)
        return os.path.splitext(audio_file)[0], os.path.splitext(audio_file)[0] + '.mp3'

# Function to fetch transcription
def fetch_transcription(youtube_url):
    video_id = youtube_url.split('v=')[-1]
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
    
    formatter = SRTFormatter()
    srt_transcript = formatter.format_transcript(transcript)
    
    return srt_transcript

# Function to save transcription to SRT
def save_transcription_to_srt(transcription, srt_file):
    with open(srt_file, 'w', encoding='utf-8') as f:
        f.write(transcription)

# Function to create a preview image using subtitle styling
def create_preview_image(font_size, font_color, bg_color, ratio):
    width, height = ratio_to_dimensions(ratio)
    image_file = "preview_image.png"
    preview_text = "Sample Subtitle Text\\nSubtitle Line 2"
    srt_content = "1\n00:00:00,000 --> 00:00:05,000\n" + preview_text
    
    with open("preview.srt", "w") as f:
        f.write(srt_content)
    
    subprocess.run([
        'ffmpeg', '-f', 'lavfi', '-i', f'color=c={bg_color}:s={width}x{height}', '-vf', 
        f"subtitles=preview.srt:force_style='Alignment=10,FontSize={font_size},PrimaryColour=&H{font_color}&'",
        '-frames:v', '1', image_file
    ])
    
    os.remove("preview.srt")
    return image_file

# Function to create the final lyrics video
def create_lyrics_video(audio_file, srt_file, output_file, font_size, font_color, bg_color, ratio, start_time, end_time):
    width, height = ratio_to_dimensions(ratio)
    image_file = "background_image.png"
    create_background_image(bg_color, image_file, f"{width}x{height}")

    trim_option = f"-ss {start_time} -to {end_time}" if start_time and end_time else ""

    subprocess.run([
        'ffmpeg', '-loop', '1', '-i', image_file, '-i', audio_file, 
        '-vf', f"subtitles={srt_file}:force_style='Alignment=10,FontSize={font_size},PrimaryColour=&H{font_color}&'", 
        '-c:v', 'libx264', '-c:a', 'aac', '-strict', 'experimental', '-b:a', '192k', '-shortest', 
        '-pix_fmt', 'yuv420p'] + 
        (trim_option.split() if trim_option else []) +
        [output_file]
    )

# Function to create a black image with specified background color
def create_background_image(bg_color, image_file="background_image.png", size="1280x720"):
    subprocess.run(['ffmpeg', '-f', 'lavfi', '-i', f'color=c={bg_color}:s={size}', '-frames:v', '1', image_file])

# Function to convert ratio to dimensions
def ratio_to_dimensions(ratio):
    if ratio == '16:9':
        return '1280', '720'
    elif ratio == '1:1':
        return '720', '720'
    elif ratio == '9:16':
        return '720', '1280'

# Function to validate time format
def validate_time_format(time_str):
    pattern = re.compile(r'^\d+:\d{2}$')
    return bool(pattern.match(time_str))

# Function to convert time format to seconds
def time_to_seconds(time_str):
    minutes, seconds = map(float, time_str.split(':'))
    return minutes * 60 + seconds

# Dictionary of color options compatible with FFmpeg
color_options = {
    "White": "FFFFFF",
    "Black": "000000",
    "Red": "FF0000",
    "Green": "00FF00",
    "Blue": "0000FF",
    "Yellow": "FFFF00",
    "Cyan": "00FFFF",
    "Magenta": "FF00FF",
    "Gray": "808080",
    "Orange": "FFA500"
}

# Streamlit app
st.title("YouTube Lyrics Video Creator")

# Create full-width container
with st.container():
    # Create two columns with equal width
    col1, col2 = st.columns([1, 1])

    # Column 1: Settings
    with col1:
        youtube_url = st.text_input("Enter YouTube URL", "")
        youtube_url = modify_youtube_url(youtube_url)

        font_size = st.slider("Font Size", min_value=10, max_value=100, value=24)
        font_color = st.selectbox("Font Color", list(color_options.keys()))
        bg_color = st.selectbox("Background Color", list(color_options.keys()))
        ratio = st.selectbox("Aspect Ratio", ['16:9', '1:1', '9:16'])

        # Add trim options
        st.subheader("Trim Video (Optional)")
        start_time = st.text_input("Start Time (mm:ss)", "")
        end_time = st.text_input("End Time (mm:ss)", "")

    # Column 2: Preview and Video
    with col2:
        # Create preview image based on settings
        preview_image_file = create_preview_image(font_size, color_options[font_color], color_options[bg_color], ratio)
        
        # Display preview image
        preview_placeholder = st.empty()
        preview_placeholder.image(preview_image_file, caption="Preview of Video Settings", use_column_width=True)
        
        # Cleanup preview image
        os.remove(preview_image_file)

        message_placeholder = st.empty()  # Create a placeholder for messages

        if youtube_url:
            if st.button("Create Lyrics Video"):
                # Validate time inputs
                if (start_time and not validate_time_format(start_time)) or (end_time and not validate_time_format(end_time)):
                    message_placeholder.error("Invalid time format. Please use mm:ss format (e.g., 1:30).")
                else:
                    message_placeholder.write("Downloading audio...")
                    original_name, audio_file = download_audio(youtube_url)
                    message_placeholder.write(f"Audio downloaded: {audio_file}")

                    message_placeholder.write("Fetching transcription...")
                    transcription = fetch_transcription(youtube_url)
                    if not transcription:
                        message_placeholder.write("No transcriptions available. Exiting.")
                    else:
                        srt_file = "transcription.srt"
                        save_transcription_to_srt(transcription, srt_file)
                        message_placeholder.write(f"Transcription saved: {srt_file}")

                        output_file = f"{original_name} (Lyrical Video).mp4"
                        message_placeholder.write("Creating lyrics video...")
                        
                        # Convert time to seconds for FFmpeg
                        start_seconds = time_to_seconds(start_time) if start_time else None
                        end_seconds = time_to_seconds(end_time) if end_time else None
                        
                        create_lyrics_video(audio_file, srt_file, output_file, font_size, color_options[font_color], color_options[bg_color], ratio, start_seconds, end_seconds)
                        message_placeholder.write("Lyrics video created successfully.")
                        
                        # Replace preview with the final video
                        preview_placeholder.video(output_file)

                        # Cleanup temporary files
                        os.remove(audio_file)
                        os.remove(srt_file)
                        os.remove("background_image.png")
                        message_placeholder.write("Your video is ready!")
        else:
            message_placeholder.write("")
