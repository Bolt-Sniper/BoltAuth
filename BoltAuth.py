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

import datetime

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def log(message, color=Fore.CYAN):
    timestamp = get_timestamp()
    print(f"{Style.DIM}[{timestamp}]{Style.RESET_ALL} {color}{message}{Style.RESET_ALL}\n")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_header():
    clear_screen()
    print(BOLTAUTH_ASCII)
    print(f"{Fore.CYAN}BoltAuth - A tool to retrieve your bearer tokens from your minecraft account.{Style.RESET_ALL}")
    print("\n")  # Add some spacing

def create_session():
    return requests.Session()

def extract_values(page_source):
    sfttag = re.search(r'sFTTag:\'<input type="hidden" name="PPFT" id="i0327" value="(.+?)"/>', page_source)
    url_post = re.search(r'urlPost:\'(.+?)\'', page_source)

    if not sfttag or not url_post:
        raise ValueError("Could not extract required values.")
    
    return sfttag.group(1), url_post.group(1)

def microsoft_login(email, password):
    try:
        session = create_session()
        log(f"\nAttempting login for: {email}")
        
        initial_url = "https://login.live.com/oauth20_authorize.srf?client_id=000000004C12AE6F&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
        response = session.get(initial_url)
        
        sfttag_value, url_post_value = extract_values(response.text)
        
        login_data = {
            'login': email,
            'loginfmt': email,
            'passwd': password,
            'PPFT': sfttag_value
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        login_request = session.post(url_post_value, data=login_data, headers=headers)
        
        if "accessToken" in login_request.url or login_request.url == url_post_value:
            log(f"Login failed for: {email}", Fore.RED)
            return None
        
        raw_login_data = login_request.url.split("#")[1]
        login_data = dict(item.split("=") for item in raw_login_data.split("&"))
        access_token = requests.utils.unquote(login_data["access_token"])
        
        return access_token
            
    except Exception as e:
        log(f"Error during login: {str(e)}", Fore.RED)
        return None

def xbox_live_authenticate(access_token):
    try:
        session = create_session()
        
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
        
        response = session.post('https://user.auth.xboxlive.com/user/authenticate', 
                              json=body, headers=headers)
        
        if response.status_code == 200:
            token = response.json()["Token"]
            user_hash = response.json()["DisplayClaims"]["xui"][0]["uhs"]
            return token, user_hash
        else:
            log(f"Failed to authenticate with Xbox Live. Status: {response.status_code}", Fore.RED)
            return None, None
            
    except Exception as e:
        log(f"Error during Xbox authentication: {str(e)}", Fore.RED)
        return None, None

def get_xsts_token(xbox_token):
    try:
        session = create_session()
        
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
        
        response = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', 
                              json=body, headers=headers)
        
        if response.status_code == 200:
            xsts_token = response.json()["Token"]
            log("Successfully obtained XSTS token")
            return xsts_token
        elif response.status_code == 401:
            log("XSTS token retrieval failed with 401 status", Fore.RED)
            return "401"
        else:
            log(f"Failed to obtain XSTS token. Status: {response.status_code}", Fore.RED)
            return None
            
    except Exception as e:
        log(f"Error during XSTS token retrieval: {str(e)}", Fore.RED)
        return None

def get_minecraft_bearer_token(user_hash, xsts_token):
    try:
        session = create_session()
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        body = {
            "identityToken": f"XBL3.0 x={user_hash};{xsts_token}",
            "ensureLegacyEnabled": True
        }
        
        response = session.post('https://api.minecraftservices.com/authentication/login_with_xbox', 
                              json=body, headers=headers)
        
        if response.status_code == 200:
            bearer_token = response.json()["access_token"]
            return bearer_token
        else:
            log(f"Failed to obtain Minecraft bearer token. Status: {response.status_code}", Fore.RED)
            return None
            
    except Exception as e:
        log(f"Error during bearer token retrieval: {str(e)}", Fore.RED)
        return None

def load_accounts(filename='ACCOUNTS.txt'):
    try:
        with open(filename, 'r') as f:
            accounts = []
            for line in f:
                if ':' in line:
                    email, password = line.strip().split(':', 1)
                    accounts.append((email, password))
        return accounts
    except Exception as e:
        log(f"Error loading accounts: {str(e)}", Fore.RED)
        return []

def save_failed_account(email, password, filename='NON_WORKINGACCOUNTS.txt'):
    try:
        with open(filename, 'a') as f:
            f.write(f"{email}:{password}\n")
    except Exception as e:
        log(f"Error saving failed account: {str(e)}", Fore.RED)

def save_bearer_token(email, token, filename='TOKENS.txt'):
    try:
        with open(filename, 'a') as f:
            f.write(f"{email}:{token}\n")
    except Exception as e:
        log(f"Error saving bearer token: {str(e)}", Fore.RED)

class StatusCounter:
    def __init__(self):
        self.success = 0
        self.failed = 0
        self.lock = threading.Lock()
        
    def update(self, status):
        with self.lock:
            if status == "SUCCESS":
                self.success += 1
            else:
                self.failed += 1

class ProcessingManager:
    def __init__(self):
        self.processed_count = 0
        self.lock = threading.Lock()
        self.batch_size = 1
        self.sleep_time = 20

    def should_sleep(self):
        with self.lock:
            self.processed_count += 1
            if self.processed_count % self.batch_size == 0:
                log(f"Processed {self.batch_size} account. Sleeping for {self.sleep_time} seconds...", Fore.YELLOW)
                time.sleep(self.sleep_time)
                return True
        return False

def process_account(email, password, status_counter):
    log(f"\nProcessing account: {email}")
    
    # Try to get access token
    access_token = microsoft_login(email, password)
    if not access_token:
        with open('[FAILED]Accounts.txt', 'a') as f:
            f.write(f"{email}:{password}\n")
        status_counter.update("FAILED")
        return False
        
    # Try to get Xbox token
    xbox_token, user_hash = xbox_live_authenticate(access_token)
    if not xbox_token:
        if "401" in str(xbox_token):
            with open('[SUSPENDED]Accounts.txt', 'a') as f:
                f.write(f"{email}:{password}\n")
        else:
            with open('[FAILED]Accounts.txt', 'a') as f:
                f.write(f"{email}:{password}\n")
        status_counter.update("FAILED")
        return False
        
    # Try to get XSTS token
    xsts_token = get_xsts_token(xbox_token)
    if xsts_token == "401":
        with open('[SUSPENDED]Accounts.txt', 'a') as f:
            f.write(f"{email}:{password}\n")
        status_counter.update("FAILED")
        return False
    elif not xsts_token:
        with open('[FAILED]Accounts.txt', 'a') as f:
            f.write(f"{email}:{password}\n")
        status_counter.update("FAILED")
        return False
        
    # Try to get bearer token
    bearer_token = get_minecraft_bearer_token(user_hash, xsts_token)
    if not bearer_token:
        with open('[FAILED]Accounts.txt', 'a') as f:
            f.write(f"{email}:{password}\n")
        status_counter.update("FAILED")
        return False
        
    # Save successful bearer token
    save_bearer_token(email, bearer_token)
    with open('[SUCCESS]Accounts.txt', 'a') as f:
        f.write(f"{email}:{password}\n")
    log(f"\nSuccessfully processed: {email}", Fore.GREEN)
    status_counter.update("SUCCESS")
    return True

def worker(account_queue, status_counter, processing_manager):
    while True:
        try:
            email, password = account_queue.get_nowait()
        except queue.Empty:
            break
            
        process_account(email, password, status_counter)
        processing_manager.should_sleep()
        account_queue.task_done()

def main():
    display_header()
    
    # Create required files if they don't exist
    for file in ['ACCOUNTS.txt', 'TOKENS.txt', 'NON_WORKINGACCOUNTS.txt']:
        if not os.path.exists(file):
            open(file, 'a').close()
    
    accounts = load_accounts()
    if not accounts:
        log("No accounts found in ACCOUNTS.txt", Fore.RED)
        return
        
    log(f"Loaded {len(accounts)} accounts")
    
    # Initialize counters and managers
    status_counter = StatusCounter()
    processing_manager = ProcessingManager()
    
    # Create account queue
    account_queue = queue.Queue()
    for account in accounts:
        account_queue.put(account)
    
    # Create and start worker threads
    threads = []
    for _ in range(1):  # Single worker for better control
        thread = threading.Thread(target=worker, args=(account_queue, status_counter, processing_manager))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Wait for all accounts to be processed
    account_queue.join()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    log(f"\nProcessing complete. Successful: {status_counter.success}, Failed: {status_counter.failed}", Fore.GREEN)

if __name__ == "__main__":
    main()
