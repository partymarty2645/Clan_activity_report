import requests
import logging

def check_missing():
    users = ['cervixthumpr', 'sulkypeen']
    print(f"Checking {len(users)} missing users...")
    
    for u in users:
        url = f"https://api.wiseoldman.net/v2/players/{u}"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                print(f"✅ {u} FOUND. Reviving...")
                requests.post(url) # Update
            elif resp.status_code == 404:
                print(f"❌ {u} NOT FOUND (Dead).")
            else:
                print(f"⚠️ {u}: {resp.status_code}")
        except Exception as e:
            print(f"Error {u}: {e}")

if __name__ == "__main__":
    check_missing()
