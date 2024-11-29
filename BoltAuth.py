# BoltAuth.py is a tool created by Bolt to be used by everybody.
# This tool is also created to help Bolt Users to exctract their bearer token faster, when having multiple accounts.
# If any issues comes up, feel free to open a ticket on discord or message Bolt.


# This tool is using public API for extracting the Bearer Token.




import subprocess
import sys

# List of required libraries
required_libraries = ['requests', 're', 'os', 'threading', 'queue']

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

def extract_values(page_source):
    sfttag = re.search(r'sFTTag:\'<input type="hidden" name="PPFT" id="i0327" value="(.+?)"/>', page_source)
    url_post = re.search(r'urlPost:\'(.+?)\'', page_source)

    if not sfttag or not url_post:
        raise ValueError("Could not extract required values.")
    
    return sfttag.group(1), url_post.group(1)

def microsoft_login(email, password):
    print(f"[Authentication] Attempting to authenticate {email}")
    initial_url = "https://login.live.com/oauth20_authorize.srf?client_id=000000004C12AE6F&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
    session = requests.Session()
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
        print(f"[Failed] Could not authenticate {email} due to invalid credentials")
        return None
    
    raw_login_data = login_request.url.split("#")[1]
    login_data = dict(item.split("=") for item in raw_login_data.split("&"))
    access_token = requests.utils.unquote(login_data["access_token"])

    return access_token

def xbox_live_authenticate(access_token):
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

    response = requests.post(url, json=body, headers=headers)
    
    if response.status_code == 200:
        token = response.json()["Token"]
        user_hash = response.json()["DisplayClaims"]["xui"][0]["uhs"]
        return token, user_hash  
    else:
        print(f"[Failed] Could not authenticate due to Xbox live authentication error.")
        return None, None

def get_xsts_token(xbox_token):
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

    response = requests.post(url, json=body, headers=headers)
    
    if response.status_code == 200:
        xsts_token = response.json()["Token"]
        return xsts_token
    else:
        print(f"[Failed] Could not get XSTS token.")
        return None

def get_minecraft_bearer_token(user_hash, xsts_token):
    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
    headers = {
        'Content-Type': 'application/json'
    }

    body = {
        "identityToken": f"XBL3.0 x={user_hash};{xsts_token}",
        "ensureLegacyEnabled": True
    }

    response = requests.post(url, json=body, headers=headers)
    
    if response.status_code == 200:
        bearer_token = response.json()["access_token"]
        return bearer_token
    else:
        print(f"[Failed] Could not authenticate for Minecraft services.")
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




def process_account_in_thread(email, password, result_queue):
    access_token = microsoft_login(email, password)
    if access_token:
        xbox_token, user_hash = xbox_live_authenticate(access_token)
        if xbox_token:
            xsts_token = get_xsts_token(xbox_token)
            if xsts_token:
                minecraft_token = get_minecraft_bearer_token(user_hash, xsts_token)
                if minecraft_token:
                    print(f"[Success] Successfully retrieved bearer for {email}")
                    result_queue.put(f"{email.strip()}:{minecraft_token.strip()}")
                else:
                    print(f"[Failed] Could not retrieve Minecraft token for {email}.")
            else:
                print(f"[Failed] Could not retrieve XSTS token for {email}.")
        else:
            print(f"[Failed] Could not authenticate {email} due to Xbox Live authentication error.")
    else:
        print(f"[Failed] Could not authenticate {email} due to invalid credentials.")
    



def process_accounts_sequentially(filename):
    accounts = load_accounts(filename)
    successful_count = 0
    result_queue = queue.Queue()

    for email, password in accounts:
        process_account_in_thread(email, password, result_queue)
        
        # Sleep for 20 ish secounds. dont know if this is ok, i only tested with 30 accounts.
        print(f"[Info] Sleeping for 5 seconds before processing the next account...")
        time.sleep(5)

    tokens = []
    while not result_queue.empty():
        tokens.append(result_queue.get())

    successful_count = len(tokens)
    return successful_count, tokens

# Save valid accounts and their Bearer tokens to a file
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
    filename = accounts_file_path  
    successful_count, tokens = process_accounts_sequentially(filename)

    if successful_count > 0:
        print(f"Successfully processed {successful_count} account(s).")
        
        # Save the tokens to valid_accounts.txt
        save_valid_accounts(tokens, filename='valid_accounts.txt')
    else:
        print("No successful logins.")
    
    exit = input("Press enter to exit... ")

if __name__ == "__main__":
    main()
