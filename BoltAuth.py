# BoltAuth.py is a tool created by Bolt to be used by everybody.
# This tool is also created to help Bolt Users to exctract their bearer token faster, when having multiple accounts.
# If any issues comes up, feel free to open a ticket on discord or message Bolt.


# This tool is using public API for extracting the Bearer Token.




import subprocess
import sys
import os
import time
import threading
import queue
import requests
import re
import json
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# ASCII Art and UI
BOLTAUTH_ASCII = f"""{Fore.CYAN}
██████╗  ██████╗ ██╗  ████████╗ █████╗ ██╗   ██╗████████╗██╗  ██╗
██╔══██╗██╔═══██╗██║  ╚══██╔══╝██╔══██╗██║   ██║╚══██╔══╝██║  ██║
██████╔╝██║   ██║██║     ██║   ███████║██║   ██║   ██║   ███████║
██╔══██╗██║   ██║██║     ██║   ██╔══██║██║   ██║   ██║   ██╔══██║
██████╔╝╚██████╔╝███████╗██║   ██║  ██║╚██████╔╝   ██║   ██║  ██║
╚═════╝  ╚═════╝ ╚══════╝╚═╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝
{Style.RESET_ALL}"""

class StatusCounter:
    def __init__(self):
        self.success = 0
        self.failed = 0
        self.twofa = 0
        self.lock = threading.Lock()
        self.last_update = 0
        self._display_status()  # Show initial status
        
    def update(self, status):
        with self.lock:
            if status == "SUCCESS":
                self.success += 1
            elif status == "2FA":
                self.twofa += 1
            else:
                self.failed += 1
            self._display_status()
    
    def _display_status(self):
        # Only update every 0.1 seconds to prevent screen flicker
        current_time = time.time()
        if current_time - self.last_update < 0.1:
            return
        self.last_update = current_time
        
        # Move cursor up and clear line
        sys.stdout.write('\033[F' if self.success + self.failed + self.twofa > 0 else '')  # Move up only if not first print
        sys.stdout.write('\033[K')  # Clear line
        
        # Print status
        print(f"{Fore.GREEN}[SUCCESS] > {self.success}   {Fore.RED}[FAILED] > {self.failed}   {Fore.YELLOW}[2FA] > {self.twofa}{Style.RESET_ALL}")
        sys.stdout.flush()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_header():
    clear_screen()
    print(BOLTAUTH_ASCII)
    print(f"{Fore.CYAN}BoltAuth - A tool to retrieve your bearer tokens from your minecraft account.{Style.RESET_ALL}")
    print("\n")  # Add some spacing

# List of required libraries
required_libraries = ['requests', 're', 'os', 'threading', 'queue', 'requests[socks]', 'colorama', 'json']

# Function to install missing libraries
def install_missing_libraries(libraries):
    for library in libraries:
        try:
            __import__(library)
        except ImportError:
            print(f"'{library}' module not found. Installing it now...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", library])

# Install missing libraries
install_missing_libraries(required_libraries)

# After this, all required libraries should be available for use
import threading
import queue
import requests
import re
import os
import time
import json

def extract_values(page_source):
    sfttag = re.search(r'sFTTag:\'<input type="hidden" name="PPFT" id="i0327" value="(.+?)"/>', page_source)
    url_post = re.search(r'urlPost:\'(.+?)\'', page_source)

    if not sfttag or not url_post:
        raise ValueError("Could not extract required values.")
    
    return sfttag.group(1), url_post.group(1)

class ProxyManager:
    def __init__(self, config):
        self.proxies = []
        self.current_index = 0
        self.lock = threading.Lock()
        self.config = config
        self.load_proxies()

    def load_proxies(self):
        script_directory = os.path.dirname(os.path.abspath(__file__))
        proxies_file = os.path.join(script_directory, 'proxies.txt')
        
        if not os.path.exists(proxies_file):
            print("Creating proxies.txt file...")
            with open(proxies_file, 'w') as f:
                f.write("# Add your proxies here in format: ip:port\n")
            return

        try:
            with open(proxies_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if self.proxies:
                print(f"Loaded {len(self.proxies)} proxies")
            else:
                print("No proxies found in proxies.txt")
        except Exception as e:
            print(f"Error loading proxies: {e}")

    def get_next_proxy(self):
        if not self.proxies:
            return None
            
        with self.lock:
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            
            # Format proxy based on config
            proxy_type = self.config['proxy']['type'].lower()
            if self.config['proxy']['needsAuth']:
                auth = f"{self.config['proxy']['username']}:{self.config['proxy']['password']}@"
            else:
                auth = ""
                
            return {
                'http': f"{proxy_type}://{auth}{proxy}",
                'https': f"{proxy_type}://{auth}{proxy}"
            }

def create_session(proxy=None):
    session = requests.Session()
    if proxy:
        session.proxies.update(proxy)
    return session

def microsoft_login(email, password, proxy=None):
    initial_url = "https://login.live.com/oauth20_authorize.srf?client_id=000000004C12AE6F&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
    
    session = create_session(proxy)
    try:
        response = session.get(initial_url)
        sfttag_value, url_post_value = extract_values(response.text)

        login_url = url_post_value
        login_data = {
            'login': email,
            'loginfmt': email,
            'passwd': password,
            'PPFT': sfttag_value
        }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        login_request = session.post(login_url, data=login_data, headers=headers)

        if "accessToken" in login_request.url or login_request.url == url_post_value:
            return None
        
        raw_login_data = login_request.url.split("#")[1]
        login_data = dict(item.split("=") for item in raw_login_data.split("&"))
        access_token = requests.utils.unquote(login_data["access_token"])

        return access_token
    except requests.exceptions.RequestException as e:
        return None

def xbox_live_authenticate(access_token, proxy=None):
    url = "https://user.auth.xboxlive.com/user/authenticate"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    body = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": access_token
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }

    try:
        session = create_session(proxy)
        response = session.post(url, json=body, headers=headers)
        
        if response.status_code == 200:
            token = response.json()["Token"]
            user_hash = response.json()["DisplayClaims"]["xui"][0]["uhs"]
            return token, user_hash  
        else:
            return None, None
    except requests.exceptions.RequestException as e:
        return None, None

def get_xsts_token(xbox_token, proxy=None):
    url = "https://xsts.auth.xboxlive.com/xsts/authorize"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    body = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [xbox_token]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }

    try:
        session = create_session(proxy)
        response = session.post(url, json=body, headers=headers)
        
        if response.status_code == 200:
            xsts_token = response.json()["Token"]
            return xsts_token
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None

def get_minecraft_bearer_token(user_hash, xsts_token, proxy=None):
    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
    headers = {
        'Content-Type': 'application/json'
    }

    body = {
        "identityToken": f"XBL3.0 x={user_hash};{xsts_token}",
        "ensureLegacyEnabled": True
    }

    try:
        session = create_session(proxy)
        response = session.post(url, json=body, headers=headers)
        
        if response.status_code == 200:
            bearer_token = response.json()["access_token"]
            return bearer_token
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None

script_directory = os.path.dirname(os.path.abspath(__file__))
accounts_file_path = os.path.join(script_directory, 'accounts.txt')

def load_accounts(filename):
    accounts = []
    script_directory = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_directory, filename)
    
    if not os.path.exists(file_path):
        print(f"File {filename} not found. Creating a new one...")
        with open(file_path, 'w') as file:
            file.write("email:password\n")

        print(f"A new {filename} file has been created. Please add accounts in the format 'email:password'.")
    else:
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    if ':' in line and not line.startswith("#"):
                        email, password = line.strip().split(':', 1)
                        accounts.append((email, password))
        except Exception as e:
            print(f"An error occurred while loading accounts: {e}")
    
    return accounts

def save_locked_accounts(email, password, filename='locked_accounts.txt'):
    try:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_directory, filename)
        
        with open(file_path, 'a') as file:
            file.write(f"{email}:{password}\n")
    except Exception as e:
        print(f"Error saving locked account: {e}")

def update_accounts_file(valid_accounts, filename='accounts.txt'):
    try:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_directory, filename)
        
        with open(file_path, 'w') as file:
            file.write("email:password\n")  # Keep the header
            for email, password in valid_accounts:
                file.write(f"{email}:{password}\n")
        
        print(f"Updated {filename} - Removed invalid accounts")
    except Exception as e:
        print(f"Error updating accounts file: {e}")

def load_config():
    try:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_directory, 'config.json')
        
        if not os.path.exists(config_path):
            print(f"{Fore.RED}[ERROR] config.json not found!{Style.RESET_ALL}")
            return None
            
        with open(config_path, 'r') as f:
            # Filter out lines starting with #
            config_lines = [line for line in f if not line.strip().startswith('"#')]
            config_str = ''.join(config_lines)
            return json.loads(config_str)
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to load config.json: {str(e)}{Style.RESET_ALL}")
        return None

def process_accounts_with_workers(filename, config):
    accounts = load_accounts(filename)
    if not accounts:
        print("No accounts found to process.")
        return [], []

    result_queue = queue.Queue()
    account_queue = queue.Queue()
    valid_accounts = []
    proxy_manager = ProxyManager(config)
    status_counter = StatusCounter()
    
    # Fill account queue
    for account in accounts:
        account_queue.put((account, 0))  # (account, retry_count)
    
    def worker():
        while True:
            try:
                try:
                    (email, password), retries = account_queue.get(timeout=1)
                except queue.Empty:
                    break
                
                proxy = proxy_manager.get_next_proxy() if proxy_manager.proxies else None
                
                access_token = microsoft_login(email, password, proxy)
                if access_token:
                    xbox_token, user_hash = xbox_live_authenticate(access_token, proxy)
                    if xbox_token:
                        xsts_token = get_xsts_token(xbox_token, proxy)
                        if xsts_token:
                            minecraft_token = get_minecraft_bearer_token(user_hash, xsts_token, proxy)
                            if minecraft_token:
                                status_counter.update("SUCCESS")
                                result_queue.put(f"{email.strip()}:{minecraft_token.strip()}")
                                valid_accounts.append((email, password))
                                account_queue.task_done()
                                continue
                
                # Handle retries based on config
                if config['authentication']['allowRetry'] and retries < config['authentication']['retryCount']:
                    account_queue.put(((email, password), retries + 1))
                else:
                    status_counter.update("FAILED")
                    save_locked_accounts(email, password)
                
                account_queue.task_done()
                time.sleep(5)
                
            except Exception as e:
                if 'email' in locals():
                    status_counter.update("FAILED")
                    save_locked_accounts(email, password)
                account_queue.task_done()
    
    # Create and start worker threads based on config
    thread_count = min(config['authentication']['threadCount'], len(accounts))
    threads = []
    for _ in range(thread_count):
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    account_queue.join()
    
    for thread in threads:
        thread.join()
    
    valid_tokens = []
    while not result_queue.empty():
        valid_tokens.append(result_queue.get())
    
    return valid_tokens, valid_accounts

def save_valid_accounts(tokens, filename='valid_accounts.txt'):
    try:
        # Get the absolute path of the script's directory
        script_directory = os.path.dirname(os.path.abspath(__file__))
        
        # Combine the script's directory with the filename to get the full path
        file_path = os.path.join(script_directory, filename)
        
     
        # Open the file and write the tokens
        with open(file_path, 'a') as file:
            for token in tokens:
                file.write(f"{token}\n")  
        print("Tokens saved successfully.")
    except Exception as e:
        print(f"Error saving tokens: {e}")

def main():
    display_header()
    
    # Load configuration
    config = load_config()
    if not config:
        print(f"{Fore.RED}Please ensure config.json is properly configured.{Style.RESET_ALL}")
        input("\nPress enter to exit...")
        return
        
    filename = accounts_file_path
    valid_tokens, valid_accounts = process_accounts_with_workers(filename, config)

    print("\n\nProcess completed!")
    if valid_tokens:
        print(f"\n{Fore.GREEN}Successfully processed {len(valid_tokens)} account(s).{Style.RESET_ALL}")
        save_valid_accounts(valid_tokens, filename='valid_accounts.txt')
        update_accounts_file(valid_accounts)
    
    print("\nPress enter to exit...")
    input()

if __name__ == "__main__":
    main()

