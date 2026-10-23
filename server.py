import os
import sys
import json
import re
import urllib.request
import urllib.error
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'accounts.json')
HTML_PATH = os.path.join(BASE_DIR, 'index.html')

def load_accounts():
    if not os.path.exists(JSON_PATH):
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
        print(f"Token error for {email}: {e}", flush=True)
        return None

def fetch_messages(token):
    url = 'https://api.mail.tm/messages'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get('hydra:member', [])
    except Exception as e:
        print(f"Error fetching messages: {e}", flush=True)
        return []

def fetch_message_detail(msg_id, token):
    url = f'https://api.mail.tm/messages/{msg_id}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error fetching message detail: {e}", flush=True)
        return None

def extract_otp(text):
    if not text:
        return None
    # 1. Match code after common keywords
    m = re.search(r'(?:code|otp|verification|رمز|كود|is|هو)[:\s]*([0-9]{4,8})', text, re.IGNORECASE)
    if m:
        return m.group(1)
    # 2. Match 4 to 8 digit numbers surrounded by boundaries
    numbers = re.findall(r'\b[0-9]{4,8}\b', text)
    if numbers:
        return numbers[0]
    return None

class RequestHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path in ('/', '/index.html'):
            if os.path.exists(HTML_PATH):
                with open(HTML_PATH, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")
            return

        if path == '/api/accounts':
            accounts = load_accounts()
            public_accounts = [{
                'no': a['no'],
                'email': a['email'],
                'username': a['username'],
                'password': a['password']
            } for a in accounts]
            body = json.dumps(public_accounts, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        if path == '/api/otp':
            target = params.get('target', [None])[0]
            if not target:
                resp_data = {'success': False, 'error': 'Target parameter missing'}
            else:
                accounts = load_accounts()
                target_acc = None
                for a in accounts:
                    if str(a['no']) == str(target) or a['username'].lower() == str(target).lower() or a['email'].lower() == str(target).lower():
                        target_acc = a
                        break

                if not target_acc:
                    resp_data = {'success': False, 'error': f"Account '{target}' not found"}
                else:
                    token = get_token(target_acc)
                    if not token:
                        resp_data = {'success': False, 'error': 'Failed to authenticate account'}
                    else:
                        msgs = fetch_messages(token)
                        if not msgs:
                            resp_data = {'success': True, 'latest_otp': None, 'messages_count': 0}
                        else:
                            latest = msgs[0]
                            detail = fetch_message_detail(latest['id'], token)
                            full_text = detail.get('text', '') if detail else latest.get('intro', '')
                            otp_code = extract_otp(full_text)
                            resp_data = {
                                'success': True,
                                'latest_otp': otp_code,
                                'from': latest.get('from', {}).get('address', 'Unknown'),
                                'subject': latest.get('subject', 'No Subject'),
                                'date': latest.get('createdAt', ''),
                                'intro': latest.get('intro', ''),
                                'body': full_text
                            }

            body = json.dumps(resp_data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404, "Endpoint not found")

def run_server(port=5000):
    server_address = ('127.0.0.1', port)
    try:
        httpd = HTTPServer(server_address, RequestHandler)
    except OSError:
        port = 5050
        server_address = ('127.0.0.1', port)
        httpd = HTTPServer(server_address, RequestHandler)

    url = f"http://127.0.0.1:{port}"
    print(f"\n=======================================================", flush=True)
    print(f"[*] Gemgala OTP Dashboard is running at: {url}", flush=True)
    print(f"[*] Open this link in your browser to view and fetch OTP codes!", flush=True)
    print(f"=======================================================\n", flush=True)
    
    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == '__main__':
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
