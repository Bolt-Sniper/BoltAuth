# ⚡️ BoltAuth - A tool to retrieve your bearer tokens faster in bulk!
This is a free and open-source minecraft bearer token retriever - It's used to retrieve your tokens faster for multiple accounts.
It now supports proxies such as (SOCKS4, SOCKS5 & HTTPS).
Also added a config.json to mess around with the few settings there is.

# ⚙️ NEW CHANGES
- Added proxy support (SOCKS4, SOCKS5 & HTTPS).
- Added faster authentication with threads.
- Added live update of amount of accounts is success & how many is failed.
- Added "locked_accounts.txt" file to insert the ones that doesn't work.


# ❓ How to use?
1. First you download the BoltAuth.py tool, along with the config.json
2. Run the code, it will install all libraries you are missing.
3. If you haven't already created the 3 files (accounts.txt | proxies.txt | locked_accounts.txt), you should create them.
4. Insert your accounts (email:pass) into accounts.txt and your proxies into the proxies.txt (IP:PORT)
5. Run the program and watch the magic happen.


# ❗️ Information
Make sure you open the config.json and choose your proxy type. If the proxies needs Authentication, make sure to put that in as well and set the "needAuth" to true.
locked_accounts doesnt mean the accounts are locked, but doesnt work or has 2FA. Could also be locked.

# 📄 Config
```{
    "proxy": {
        "enabled": false,
        "type": "SOCKS5", 
        "needsAuth": false,
        "username": "",
        "password": "" 
    },

    "authNoProxy": {
        "authDelay": 20
    },
    
    
    "authentication": {
        "threadCount": 10, 
        "allowRetry": true, 
        "retryCount": 3 
    }
}```

# 🔰 Need help with something?
Join the discord here [Boltsniper Discord](discord.gg/boltsniper)




