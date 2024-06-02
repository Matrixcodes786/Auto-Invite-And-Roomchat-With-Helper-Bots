import requests
import json
import time
import os
import random
import sqlite3

api = "https://www.clubhouseapi.com/api/"
path = os.getenv('Appdata')
filename = os.path.join(path, 'Clubdeck', 'profile.json')

isExisting = os.path.exists(filename)

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

if isExisting:
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
        token = data.get('token')
        botname = data['user']['name']
        print(f"Welcome 🫧{botname}🫧is Syncing...")
        print(f"Please Wait Connecting To Clubhouse Server...")
else:
    print("Please Login Properly On Clubdeck.")

cursor.execute('''
    CREATE TABLE IF NOT EXISTS invited_speakers (
        user_id INTEGER PRIMARY KEY
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS sent_messages (
        name TEXT PRIMARY KEY
    )
''')

invited_speakers = set()
sent_messages = set()

def extract_user_id_and_channel_id(token):
    action = "get_feed_v3"
    url = api + action

    headers = {
        'CH-Languages': 'en-US',
        'CH-Locale': 'en_US',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
        'CH-AppBuild': '588',
        'CH-AppVersion': '1.0.10',
        'CH-UserID': '667493545',
        'User-Agent': 'clubhouse/588 (iPhone; iOS 15; Scale/2.00)',
        'Connection': 'close',
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': 'Token ' + token
    }

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if 'items' in data and len(data['items']) > 1 and 'channel' in data['items'][1]:
            channel_id = data['items'][1]['channel']['channel']
        else:
            raise ValueError("Invalid response format. Unable to extract channel ID.")

        action = "get_channel"
        url = api + action

        data = {
            "channel": channel_id
        }

        response = requests.post(url, headers=headers, json=data)
        #print(response.json())
        response.raise_for_status()
        users = response.json().get('users', [])

        user_ids = [user['user_id'] for user in users]

        return user_ids, channel_id, users
    except requests.exceptions.RequestException as e:
        print("Error 400 Please Join A Channel For Start This Script...")

    return [], None, []

time.sleep(1)

def invite_uninvited_speakers():
    user_ids, channel_id, users = extract_user_id_and_channel_id(token)
    uninvited_users = [user for user in users if not user['is_invited_as_speaker']]

    for user in uninvited_users:
        invite_speaker(token, channel_id, user['user_id'])
        send_channel_message(token, user['name'])

def invite_speaker(token, channel_id, user_id):

    url = "https://www.clubhouseapi.com/api/invite_speaker"

    headers = {
        'CH-Languages': 'en-US',
        'CH-Locale': 'en_US',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
        'CH-AppBuild': '588',
        'CH-AppVersion': '1.0.10',
        'CH-UserID': '667493545',
        'User-Agent': 'clubhouse/588 (iPhone; iOS 15; Scale/2.00)',
        'Connection': 'close',
        'Content-Type': 'application/json; charset=utf-8',
        "Authorization": f"Token {token}"
    }

    payload = {
        "channel": channel_id,
        "user_id": user_id
    }

    # Convert payload to JSON format
    json_payload = json.dumps(payload)
    print("\033[92m" + json_payload + "\033[0m")

    try:
        # Send a POST request to invite the speaker
        response = requests.post(url, headers=headers, data=json_payload)
        response.raise_for_status()
        #print("Response Code:", response.status_code)

        # Add the invited speaker to the set
        invited_speakers.add(user_id)
        cursor.execute('INSERT OR REPLACE INTO invited_speakers (user_id) VALUES (?)', (user_id,))
        conn.commit()
    except requests.exceptions.RequestException as e:
        print("Error:", e)

def send_channel_message(token, name):
    url = api + "send_channel_message"

    headers = {
        "CH-Languages": "en-US",
        "CH-Locale": "en_US",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "CH-AppBuild": "2446",
        "CH-AppVersion": "23.09.01",
        "CH-UserID": "736014831",
        "User-Agent": "clubhouse/2446 (iPhone; iOS 16.6; Scale/3.00)",
        "Connection": "close",
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": "Token " + token
    }

    with open("emoji1.txt", "r", encoding="utf-8") as file1, open("emoji2.txt", "r", encoding="utf-8") as file2:
        emojis1 = file1.read().splitlines()
        emojis2 = file2.read().splitlines()

    # Check if a message has already been sent for the user
    if name in sent_messages:
        return

    emoji1 = random.choice(emojis1)
    emoji2 = random.choice(emojis2)

    message = f"{emoji1} {name} {emoji2}"
    print(message)
    data = {
        "channel": channel_id,
        "message": message
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print('Channel Message Status:', response.text)
    else:
        if response.status_code == 429:
            print('Invite Failed due to too Many Users, Pausing Application For 5 Seconds')
            time.sleep(5)

    sent_messages.add(name)

    cursor.execute('INSERT OR IGNORE INTO sent_messages (name) VALUES (?)', (name,))
    conn.commit()

    time.sleep(1)

def delete_database():
    if os.path.exists('data.db'):
        os.remove('data.db')
        print("Deleted data.db")

while True:
    user_ids, channel_id, users = extract_user_id_and_channel_id(token)
    if channel_id is not None:
        invite_uninvited_speakers()
        for user in users:
            send_channel_message(token, user['name'])
    else:
        print("Waiting For Connection To Channel...")

    if time.time() % 1200 == 0:
        delete_database()

    time.sleep(1)
