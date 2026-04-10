#!/usr/bin/env python3
import datetime
import time
from gtts import gTTS
import os

# --- Configuration ---
# Directory where your radio clips (and this timestamp clip) will be saved
AUDIO_OUTPUT_DIR = "calls"
FILENAME_SUFFIX = "-timestamp.mp3"
# --- End Configuration ---

def get_ordinal_suffix(day_num):
    """Returns the ordinal suffix for a day number (e.g., 1st, 2nd, 3rd, 4th)."""
    if 11 <= day_num <= 13:
        return 'th'
    suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
    return suffixes.get(day_num % 10, 'th')

def generate_timestamp_audio():
    """
    Generates a timestamped audio message and saves it as an MP3.
    """
    now = datetime.datetime.now()

    # Determine the "concluded" day (yesterday if script runs at/after midnight)
    # If you run this at noon, "yesterday" is still the concluded full day.
    concluded_day_date = now - datetime.timedelta(days=1)

    concluded_day_name = concluded_day_date.strftime("%A") # e.g., Thursday
    concluded_day_num = concluded_day_date.day
    concluded_month_name = concluded_day_date.strftime("%B") # e.g., May
    concluded_date_str = f"{concluded_month_name} {concluded_day_num}{get_ordinal_suffix(concluded_day_num)}" # e.g., May 8th

    current_time_str = now.strftime("%I:%M %p").lstrip('0') # e.g., 12:00 AM or 1:30 PM
    current_day_name = now.strftime("%A") # e.g., Friday
    current_day_num = now.day
    current_month_name = now.strftime("%B") # e.g., May
    current_date_str = f"{current_month_name} {current_day_num}{get_ordinal_suffix(current_day_num)}" # e.g., May 9th

    # Construct the text to be spoken
    text_to_speak = (
        f"This concludes {concluded_day_name}, {concluded_date_str}. "
        f"It is currently {current_time_str} on {current_day_name}, {current_date_str}."
    )

    print(f"Generating audio for: \"{text_to_speak}\"")

    try:
        # Create gTTS object
        tts = gTTS(text=text_to_speak, lang='en', slow=False)

        # Generate filename based on current timestamp
        current_epoch_time = int(time.time())
        output_filename = f"{current_epoch_time}{FILENAME_SUFFIX}"
        output_path = os.path.join(AUDIO_OUTPUT_DIR, output_filename)

        # Ensure output directory exists
        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

        # Save the audio file
        tts.save(output_path)
        print(f"Successfully saved timestamp audio to: {output_path}")

    except Exception as e:
        print(f"Error generating or saving audio: {e}")
        # You might want to add more robust error logging here for a cron job

if __name__ == "__main__":
    generate_timestamp_audio()
