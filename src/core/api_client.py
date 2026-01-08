import platform
import hashlib
import requests
import keyring
import json

def get_machine_id():
    """
    Generates a stable, anonymous machine ID.
    """
    system_info = {
        'system': platform.system(),
        'node_name': platform.node(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
    }
    # Convert dictionary to a sorted JSON string to ensure consistent hashing
    info_string = json.dumps(system_info, sort_keys=True)
    return hashlib.sha256(info_string.encode('utf-8')).hexdigest()

class APIClient:
    def __init__(self, supabase_url, supabase_anon_key):
        self.supabase_url = supabase_url
        self.supabase_anon_key = supabase_anon_key
        self.headers = {
            "apikey": self.supabase_anon_key,
            "Content-Type": "application/json"
        }

    def _make_request(self, endpoint, data):
        """Helper to make POST requests to Supabase Edge Functions."""
        url = f"{self.supabase_url}/functions/v1/{endpoint}"
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} - {response.text}")
            return {"status": "error", "message": f"HTTP Error: {http_err}, Response: {response.text}"}
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
            return {"status": "error", "message": f"Connection Error: {conn_err}"}
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
            return {"status": "error", "message": f"Timeout Error: {timeout_err}"}
        except requests.exceptions.RequestException as req_err:
            print(f"An unexpected error occurred: {req_err}")
            return {"status": "error", "message": f"Request Error: {req_err}"}

    def verify_license(self, license_key, machine_id):
        """
        Verifies a license key against the Supabase Edge Function.
        """
        data = {"license_key": license_key, "machine_id": machine_id}
        return self._make_request("verify-license", data)

    def activate_license(self, license_key, machine_id):
        """
        Activates a license key against the Supabase Edge Function.
        """
        data = {"license_key": license_key, "machine_id": machine_id}
        return self._make_request("activate-license", data)

def save_license_key(key):
    """
    Securely saves the license key using the OS credential manager.
    """
    try:
        keyring.set_password("earthworm_app", "license_key", key)
        return True
    except Exception as e:
        print(f"Error saving license key: {e}")
        return False

def get_saved_license_key():
    """
    Retrieves the securely saved license key from the OS credential manager.
    """
    try:
        return keyring.get_password("earthworm_app", "license_key")
    except Exception as e:
        print(f"Error retrieving license key: {e}")
        return None
