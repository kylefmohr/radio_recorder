import subprocess
import tempfile
import os
import re
import math # Added for math.ceil
import pathlib

TWO_HOURS_IN_SECONDS = 2 * 60 * 60

# Default directory where radio clips are saved
audio_clip_file_path = os.path.join(os.getcwd(), "calls")
os.makedirs(audio_clip_file_path, exist_ok=True) # Ensure the directory exists

def check_mp3(filepath):
    """Checks if a file is a valid MP3 using the file command."""
    try:
        result = subprocess.run(['file', filepath], capture_output=True, text=True, check=True)
        # Use a regex to look for "Audio file" and "MPEG" to be more robust.
        return bool(re.search(r"MPEG ADTS|MPEG audio|Audio file.*MP3", result.stdout, re.IGNORECASE))
    except subprocess.CalledProcessError as e:
        print(f"Error checking {filepath}: {e.stderr if e.stderr else e.stdout}")
        return False
    except FileNotFoundError:
        print("The 'file' command (or 'ffprobe') was not found. Please ensure it's installed and in your PATH.")
        # Depending on strictness, you might want to raise an exception or return False
        return False # Assuming if 'file' is not found, we can't validate

def get_mp3_duration(filepath):
    """Gets the duration of an MP3 file in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            capture_output=True, text=True, check=False # check=False to handle errors manually
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        else:
            print(f"Error getting duration for {filepath}: {result.stderr.strip() if result.stderr else 'No output'}")
            return None
    except FileNotFoundError:
        print("`ffprobe` command not found. This is typically resolved by installing `ffmpeg` which includes ffprobe. Please ensure ffmpeg is installed and in your PATH.")
        return None
    except ValueError:
        print(f"Could not parse duration from ffprobe output for {filepath}.")
        return None

def split_mp3(input_file, segment_duration_seconds, output_dir="."):
    """Splits an MP3 file into segments of specified duration."""
    total_duration = get_mp3_duration(input_file)
    if total_duration is None:
        print(f"Cannot split {input_file} as its duration could not be determined.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    base_name, ext = os.path.splitext(os.path.basename(input_file))
    num_segments = math.ceil(total_duration / segment_duration_seconds)

    print(f"Splitting {input_file} into {num_segments} segments of up to {segment_duration_seconds / 3600:.2f} hours each.")

    for i in range(num_segments):
        start_time = i * segment_duration_seconds
        segment_filename = os.path.join(output_dir, f"{base_name}_part_{i+1}{ext}")
        
        # Use -t for duration. For the last segment, if it's shorter, ffmpeg will stop at EOF.
        # Use -map_metadata 0 to copy metadata from the input file to the output segments.
        command = [
            "ffmpeg", "-i", input_file,
            "-ss", str(start_time),
            "-t", str(segment_duration_seconds),
            "-c", "copy", # Re-encode if needed: "-codec:a", "libmp3lame", "-q:a", "2",
            "-map_metadata", "0", # Copy metadata
            segment_filename
        ]
        
        try:
            print(f"Creating segment: {segment_filename} (starting at {start_time}s)")
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Successfully created {segment_filename}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating segment {segment_filename}:")
            print(f"FFmpeg STDOUT: {e.stdout}")
            print(f"FFmpeg STDERR: {e.stderr}")
            # Optionally, decide if you want to stop splitting on error or continue
            # return
        except FileNotFoundError:
            print("ffmpeg command not found. Please ensure ffmpeg is installed and in your PATH.")
            return # Stop if ffmpeg is not found

    print("Splitting complete.")


def concatenate_mp3s(input_dir, output_file="output.mp3"):
    """Concatenates valid MP3 files in a directory using ffmpeg."""
    tmpfile_path = None # Initialize to ensure it's defined for finally block
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding='utf-8') as tmpfile:
            tmpfile_path = tmpfile.name
            valid_mp3_files = []
            # Ensure input_dir exists
            if not os.path.isdir(input_dir):
                print(f"Error: Input directory '{input_dir}' not found.")
                return False # Indicate failure

            print(f"Scanning directory: {input_dir}")
            filenames = sorted(os.listdir(input_dir)) # Sort filenames directly
            if not filenames:
                print(f"No files found in {input_dir}.")
                # return False # No files means no valid MP3s

            for filename in filenames:
                if filename.lower().endswith(".mp3"): # Case-insensitive check
                    filepath = os.path.join(input_dir, filename)
                    # Make sure it's a file, not a directory named .mp3
                    if not os.path.isfile(filepath):
                        print(f"Skipping non-file entry: {filepath}")
                        continue

                    if check_mp3(filepath):
                        valid_mp3_files.append(filepath)
                        print(f"Found valid MP3: {filepath}")
                    else:
                        # It's better not to auto-delete files based on 'check_mp3' failure alone
                        # as 'check_mp3' might not be foolproof. Let user manage invalid files.
                        print(f"Warning: {filepath} may not be a valid MP3 or could not be verified. Skipping.")

            if not valid_mp3_files:
                print("No valid MP3 files found to concatenate.")
                return False # Indicate failure

            for file_path in valid_mp3_files:
                 # Ensure paths with spaces or special characters are handled
                 # ffmpeg's concat demuxer requires paths to be escaped or quoted if they contain special characters.
                 # The 'file' directive expects single quotes around the path.
                 # It's crucial that file_path itself doesn't contain single quotes, or they must be escaped.
                 # Python's os.path.abspath might be good here for canonical paths.
                 safe_file_path = os.path.abspath(file_path).replace("'", "'\\''") # Basic escaping for single quotes
                 tmpfile.write(f"file '{safe_file_path}'\n")
            
            tmpfile.flush() # Ensure content is written before ffmpeg reads it

            # Ensure output_file path is absolute or relative to CWD as intended
            abs_output_file = os.path.abspath(output_file)
            print(f"Attempting to concatenate to: {abs_output_file}")

            # Check if output_file already exists and prompt for overwrite, or handle as needed
            if os.path.exists(abs_output_file):
                overwrite = input(f"Output file '{abs_output_file}' already exists. Overwrite? (y/n): ").lower()
                if overwrite != 'y':
                    print("Concatenation aborted by user.")
                    return False

            ffmpeg_command = [
                "ffmpeg", "-y", # Overwrite output files without asking
                "-f", "concat",
                "-safe", "0", # Allows unsafe file paths, use with caution
                "-i", tmpfile.name,
                "-c", "copy",
                abs_output_file
            ]
            print(f"Executing FFmpeg: {' '.join(ffmpeg_command)}")

            process = subprocess.run(
                ffmpeg_command,
                check=True, capture_output=True, text=True
            )
            print(f"Concatenation complete. Output file: {abs_output_file}")
            return True

    except FileNotFoundError:
        print("ffmpeg command not found. Please ensure ffmpeg is installed and in your PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print("Error during ffmpeg concatenation:")
        print(f"FFmpeg STDOUT: {e.stdout}")
        print(f"FFmpeg STDERR: {e.stderr}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during concatenation: {e}")
        return False
    finally:
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)


def delete_files_with_consent(input_dir):
    """Deletes all MP3 files in the specified directory after confirmation."""
    if not os.path.isdir(input_dir):
        print(f"Cannot delete files: Input directory '{input_dir}' not found.")
        return

    answer = input(f"Do you want to delete all source .mp3 files in '{input_dir}'? (y/n) ")
    if answer.lower() == "y":
        deleted_count = 0
        error_count = 0
        for filename in os.listdir(input_dir):
            if filename.lower().endswith(".mp3"): # Case-insensitive
                filepath = os.path.join(input_dir, filename)
                if os.path.isfile(filepath): # Ensure it's a file
                    try:
                        os.remove(filepath)
                        print(f"Deleted: {filepath}")
                        deleted_count += 1
                    except OSError as e:
                        print(f"Error deleting {filepath}: {e}")
                        error_count += 1
        print(f"Source file deletion: {deleted_count} deleted, {error_count} errors.")
    else:
        print("Source files not deleted.")


if __name__ == "__main__":
    input_directory = audio_clip_file_path  # Use the defined path for input MP3 files
    # Output file will be in the script's current working directory
    output_filename = "output.mp3"

    if not os.path.exists(input_directory):
        os.makedirs(input_directory, exist_ok=True)

    concatenation_succeeded = concatenate_mp3s(input_directory, output_filename)

    if concatenation_succeeded and os.path.exists(output_filename):
        duration = get_mp3_duration(output_filename)
        if duration is not None:
            print(f"Total duration of '{output_filename}': {duration / 3600:.2f} hours ({duration:.0f} seconds).")
            if duration > TWO_HOURS_IN_SECONDS:
                print(f"'{output_filename}' is longer than 2 hours.")
                choice = input("Do you want to break it up into 2-hour segments? (y/n): ").lower()
                if choice == 'y':
                    output_dir = os.path.dirname(os.path.abspath(output_filename)) # Get directory of output.mp3
                    split_mp3(output_filename, TWO_HOURS_IN_SECONDS, output_dir)
                    print(f"Original file '{output_filename}' has been kept.")
                else:
                    print("Original file will not be split.")
            else:
                print(f"'{output_filename}' is not longer than 2 hours, no splitting offered.")
        else:
            print(f"Could not determine duration of '{output_filename}'. Skipping split check.")
        # Ask to delete source files only if concatenation was successful
        delete_files_with_consent(input_directory)
    elif os.path.exists(output_filename): # Concatenation reported failure but file exists
        print(f"Warning: Concatenation reported failure, but '{output_filename}' exists. Check file integrity.")
    else: # Concatenation failed and no output file
        print(f"Concatenation failed and '{output_filename}' was not created. Source files will not be deleted automatically.")
