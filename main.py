import requests
import os
import time
import tts
import datetime

MINUTES_BETWEEN_RUNS = 5 # May want to decrease this in areas that have a higher volume of radio chatter. 5 minutes has worked well for Wauwatosa PD radio

cookies = {
    # MUST SUPPLY YOUR OWN, see README.md
}

headers = {
    # MUST SUPPLY YOUR OWN, see README.md
}

data = {
    # MUST SUPPLY YOUR OWN, see README.md
}

def fetch_calls():
    try:
        minutes_ago = int(time.time()) - (60 * MINUTES_BETWEEN_RUNS)
        # basically, we're asking broadcastify "what are the radio broadcasts you've seen within the last `MINUTES_BETWEEN_RUNS` minutes? and we need an epoch timestamp to do that
        data['pos'] = minutes_ago

        response = requests.post('https://www.broadcastify.com/calls/apis/live-calls', cookies=cookies, headers=headers, data=data)
        response.raise_for_status()

        for call in response.json().get('calls', []):
            if os.path.exists(f'calls/{call["filename"]}.mp3'):
                continue

            print(f'Downloading {call["filename"]}')
            url = "https://calls.broadcastify.com/" + str(call["hash"]) + "/" + str(call["systemId"]) + "/" + call["filename"] + ".mp3"
            r = requests.get(url)
            r.raise_for_status()

            if not os.path.exists('calls'):
                os.makedirs('calls')
            with open(f'calls/{call["filename"]}.mp3', 'wb') as f:
                f.write(r.content)

        print('Done fetching calls')
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    print(f"Starting call fetcher. Will run every {MINUTES_BETWEEN_RUNS} minutes. Press Ctrl+C to stop.")
    print("TTS timestamps will be generated daily at midnight local time.")
    
    # Initialize to the current day so it waits for the next midnight to run.
    last_tts_date = datetime.date.today()
    
    try:
        while True:
            current_date = datetime.date.today()
            
            # Run TTS generation if the day has changed (midnight crossed)
            if current_date != last_tts_date:
                print("Midnight crossed! Running scheduled TTS generation...")
                tts.generate_timestamp_audio()
                last_tts_date = current_date
                
            fetch_calls()
            
            print(f"Waiting {MINUTES_BETWEEN_RUNS} minutes before next fetch...")
            time.sleep(MINUTES_BETWEEN_RUNS * 60)
    except KeyboardInterrupt:
        print("\nExiting...")
