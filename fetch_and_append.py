import requests
import pandas as pd
import os

API_URL = "http://54.234.201.60:5000/chat/getFormData"
CSV_PATH = "data/database_data.csv"



def fetch_data_from_api():
    try:
        print(f"[INFO] Fetching data from API: {API_URL}")
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "formData" in data:
                print(f"[✓] Successfully fetched {len(data['formData'])} records")
                return data["formData"]
            else:
                print("[!] Warning: 'formData' key not found in response")
                return []
        else:
            raise Exception(f"API error: {response.status_code}")
    except requests.exceptions.Timeout:
        print("[!] API request timed out (10 seconds). Using existing data if available.")
        return []
    except requests.exceptions.ConnectionError:
        print("[!] Could not connect to API. Using existing data if available.")
        return []
    except Exception as e:
        print(f"[!] Error fetching data: {e}")
        return []

def update_csv():
    new_data = fetch_data_from_api()
    
    if not new_data:
        print("[!] No new data fetched from API")
        if os.path.exists(CSV_PATH):
            print(f"[INFO] Using existing CSV file: {CSV_PATH}")
            return
        else:
            print("[!] No existing CSV file found and no API data available")
            return
    
    new_df = pd.DataFrame(new_data)

    if os.path.exists(CSV_PATH):
        old_df = pd.read_csv(CSV_PATH)
        combined_df = pd.concat([old_df, new_df]).drop_duplicates().reset_index(drop=True)
        print(f"[INFO] Combined data: {len(old_df)} existing + {len(new_df)} new = {len(combined_df)} total records")
    else:
        combined_df = new_df
        print(f"[INFO] Creating new CSV with {len(combined_df)} records")

    # Ensure the data directory exists
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    
    combined_df.to_csv(CSV_PATH, index=False)
    print("[✓] CSV updated.")

if __name__ == "__main__":
    update_csv()
