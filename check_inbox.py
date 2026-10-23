import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'accounts.json')

def load_accounts():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.", flush=True)
        return []
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_token(account):
    token = account.get('token')
    if token:
        return token
    email = account['email']
    password = account['password']
    url = 'https://api.mail.tm/token'
    payload = json.dumps({'address': email, 'password': password}).encode()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get('token')
    except Exception as e:
        print(f"Failed to get token for {email}: {e}", flush=True)
        return None

def fetch_messages(token):
    url = 'https://api.mail.tm/messages'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get('hydra:member', [])
    except Exception as e:
        return []

def fetch_message_detail(msg_id, token):
    url = f'https://api.mail.tm/messages/{msg_id}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

def check_single(acc):
    email = acc['email']
    token = get_token(acc)
    if not token:
        print(f"Could not get token for {email}", flush=True)
        return
    msgs = fetch_messages(token)
    print(f"\n==========================================", flush=True)
    print(f"[*] Account [{acc['no']}] {acc['username']} ({email})", flush=True)
    if not msgs:
        print("  Status: No messages yet (Inbox is empty).", flush=True)
    else:
        print(f"  Messages: {len(msgs)} received!", flush=True)
        for m in msgs:
            msg_id = m.get('id')
            subject = m.get('subject', 'No Subject')
            sender = m.get('from', {}).get('address', 'Unknown')
            intro = m.get('intro', '')
            detail = fetch_message_detail(msg_id, token)
            text_content = detail.get('text', intro) if detail else intro
            print(f"  - From: {sender}", flush=True)
            print(f"  - Subject: {subject}", flush=True)
            print(f"  - Content / Code: {text_content.strip()}", flush=True)
    print(f"==========================================\n", flush=True)

def check_all_inboxes():
    accounts = load_accounts()
    print(f"Checking inboxes for all {len(accounts)} accounts...", flush=True)
    found_any = False
    for acc in accounts:
        token = get_token(acc)
        if not token:
            continue
        msgs = fetch_messages(token)
        if msgs:
            found_any = True
            check_single(acc)
    if not found_any:
        print("All inboxes are currently empty.", flush=True)

def wait_for_otp(target, timeout=180, poll_interval=3):
    accounts = load_accounts()
    target_acc = None
    for acc in accounts:
        if str(acc['no']) == str(target) or acc['username'].lower() == str(target).lower() or acc['email'].lower() == str(target).lower():
            target_acc = acc
            break
    if not target_acc:
        print(f"Account '{target}' not found.", flush=True)
        return

    print(f"Waiting for OTP on [{target_acc['no']}] {target_acc['username']} ({target_acc['email']})...", flush=True)
    print(f"Trigger the code in Gemgala now! (Timeout: {timeout}s)", flush=True)
    
    token = get_token(target_acc)
    start_time = time.time()
    seen_ids = set()
    
    for m in fetch_messages(token):
        seen_ids.add(m.get('id'))

    while time.time() - start_time < timeout:
        msgs = fetch_messages(token)
        for m in msgs:
            m_id = m.get('id')
            if m_id not in seen_ids:
                print("\n>>> [NEW OTP MESSAGE ARRIVED!] <<<", flush=True)
                subject = m.get('subject', 'No Subject')
                sender = m.get('from', {}).get('address', 'Unknown')
                detail = fetch_message_detail(m_id, token)
                text = detail.get('text', m.get('intro', '')) if detail else m.get('intro', '')
                print(f"From: {sender}", flush=True)
                print(f"Subject: {subject}", flush=True)
                print(f"Content / Code: {text.strip()}\n", flush=True)
                return
        time.sleep(poll_interval)
    print("Timed out waiting for message.", flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Gemgala Mail Inbox Checker")
    parser.add_argument('target', nargs='?', default=None, help="Account number (1-35) or username (e.g. user01)")
    parser.add_argument('--all', action='store_true', help="Check all accounts")
    parser.add_argument('--watch', action='store_true', help="Wait in real-time for incoming OTP on target account")
    args = parser.parse_args()

    if args.watch and args.target:
        wait_for_otp(args.target)
    elif args.target:
        accounts = load_accounts()
        found = False
        for a in accounts:
            if str(a['no']) == str(args.target) or a['username'].lower() == str(args.target).lower():
                check_single(a)
                found = True
                break
        if not found:
            print(f"Account '{args.target}' not found.")
    else:
        check_all_inboxes()
