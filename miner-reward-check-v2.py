import requests
import time
from bs4 import BeautifulSoup
import os
import subprocess

TARGET_BLOCK = 36871000
LOG_FILE = "rewards_log.txt"
RPC_URL = "https://rpc.energyweb.org"
CHECK_INTERVAL = 5  # seconds, assuming ~5s block time

def get_latest_block():
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    }
    response = requests.post(RPC_URL, json=payload)
    response.raise_for_status()
    hex_num = response.json()["result"]
    return int(hex_num, 16)

def has_miner_reward(block_num):
    url = f"https://explorer.energyweb.org/block/{block_num}"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the dt element containing "Miner Reward"
    for dt in soup.find_all('dt'):
        if dt.text.strip() == "Miner Reward":
            dd = dt.find_next_sibling('dd')
            if dd:
                reward_text = dd.text.strip()
                # Extract the numerical value, e.g., "0.1111927824 EWT" -> 0.1111927824
                try:
                    value = float(reward_text.split()[0])
                    return value > 0
                except:
                    return False
    # If field not found, assume no reward
    return False

# Load last checked block from log file if exists
last_checked = TARGET_BLOCK - 1
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()
        if lines:
            last_line = lines[-1].strip()
            try:
                last_checked = int(last_line.split()[0])
            except:
                pass

print(f"Starting watch from block {last_checked + 1}")

while True:
    try:
        latest = get_latest_block()
        with open(LOG_FILE, 'a') as f:
            if latest < TARGET_BLOCK:
                message = f"Current block {latest}, there are still miner rewards, waiting for {TARGET_BLOCK}... "
                print(message)
                f.write(message + "\n")
            else:
                if latest > last_checked:
                    for block_num in range(last_checked + 1, latest + 1):
                        has_reward = has_miner_reward(block_num)
                        yes_no = "yes" if has_reward else "no"
                        message = f"{block_num} are there still miner rewards: {yes_no}"
                        if block_num >= TARGET_BLOCK and has_reward:
                            message += " there should not be rewards anymore - smth seems wrong"
                        print(message)
                        f.write(message + "\n")
                    last_checked = latest
                else:
                    message = f"Latest block {latest}, no new blocks since last check."
                    print(message)
                    f.write(message + "\n")
        
        # Commit and push to GitHub after each iteration
        try:
            subprocess.run(['git', 'add', LOG_FILE], check=True)
            subprocess.run(['git', 'commit', '-m', f'Update log up to block {latest}'], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            print("Committed and pushed to GitHub.")
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in str(e.output):
                print("No changes to commit.")
            else:
                print(f"Git error: {e}")
        
        time.sleep(CHECK_INTERVAL)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(CHECK_INTERVAL)