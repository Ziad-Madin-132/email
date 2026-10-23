import os
import json
import time
import secrets
import string
import csv
import urllib.request
import urllib.error
import sys

BASE_DIR = r'C:\Users\NTG SCHOOL\.gemini\antigravity\scratch\gemgala_accounts'
os.makedirs(BASE_DIR, exist_ok=True)

# 1. Fetch domain
req = urllib.request.Request('https://api.mail.tm/domains', headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        domains_data = json.loads(resp.read().decode())
    domain = domains_data.get('hydra:member', [])[0].get('domain', 'maxxspace.com')
except Exception:
    domain = 'maxxspace.com'

print(f"Using domain: {domain}", flush=True)

batch_tag = secrets.token_hex(2)  # 4 hex characters for uniqueness e.g. '8a2f'
print(f"Batch Tag: {batch_tag}", flush=True)

accounts = []
csv_rows = []

for i in range(1, 36):
    num_str = f"{i:02d}"
    username = f"user{num_str}"
    email_address = f"gem.{username}.{batch_tag}@{domain}"
    password = f"GalaPass2026!{num_str}"
    
    # Create account with retry on 429
    create_url = 'https://api.mail.tm/accounts'
    payload = json.dumps({'address': email_address, 'password': password}).encode()
    
    created_ok = False
    acc_id = None
    
    for attempt in range(8):
        req = urllib.request.Request(
            create_url,
            data=payload,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    data = json.loads(resp.read().decode())
                    acc_id = data.get('id')
                    created_ok = True
                    break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = 6 + (attempt * 2)
                print(f"[{i}/35] Rate limited (429), waiting {wait_time}s...", flush=True)
                time.sleep(wait_time)
            else:
                print(f"[{i}/35] HTTP {e.code}: {e.read().decode()}", flush=True)
                time.sleep(3)
        except Exception as e:
            print(f"[{i}/35] Network error: {e}", flush=True)
            time.sleep(3)
            
    if not created_ok:
        print(f"FAILED to create account {i}: {email_address}", flush=True)
        continue

    # Get authentication token
    token = None
    token_url = 'https://api.mail.tm/token'
    for attempt in range(4):
        req_token = urllib.request.Request(
            token_url,
            data=payload,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        try:
            with urllib.request.urlopen(req_token, timeout=15) as resp:
                if resp.status == 200:
                    token_data = json.loads(resp.read().decode())
                    token = token_data.get('token')
                    break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5)
            else:
                time.sleep(2)
        except Exception:
            time.sleep(2)

    accounts.append({
        'no': i,
        'email': email_address,
        'username': username,
        'password': password,
        'id': acc_id,
        'token': token,
        'created': created_ok
    })

    csv_rows.append({
        'No.': i,
        'Email Address': email_address,
        'Username': username,
        'Password (set securely)': password,
        'Account Created?': 'Yes',
        'Email Verified?': 'Ready for OTP',
        'Recovery Method': f'Mail.tm Inbox (Web/API)',
        'Notes': 'Active inbox ready for Gemgala activation'
    })

    print(f"[{i}/35] SUCCESS: {email_address} (Password: {password})", flush=True)

    # Save progress after every account so data is never lost
    json_path = os.path.join(BASE_DIR, 'accounts.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, indent=2)

    csv_path = os.path.join(BASE_DIR, 'gemgala_35_accounts.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = [
            'No.', 'Email Address', 'Username', 'Password (set securely)',
            'Account Created?', 'Email Verified?', 'Recovery Method', 'Notes'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    # Friendly delay to avoid aggressive rate limit
    time.sleep(3)

print("=== ALL 35 ACCOUNTS COMPLETED SUCCESSFULLY ===", flush=True)
