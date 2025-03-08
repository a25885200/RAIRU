import os
import json

__xml_key = "wupH_xMcVbS_j2SvAXguZGbGRY6tF__PsvEqcNyNpkE="
__max_client = 3
__public_current_client_file = os.path.join(os.getenv('LOCALAPPDATA'), "RAIRU", "public_current_client.json")
__localappdata_path = os.getenv('LOCALAPPDATA') + "\\RAIRU"
__client_data_config_path = os.getenv('LOCALAPPDATA') + "\\RAIRU\\clients_data.config"

def get_xml_key():
    return __xml_key

def get_max_client():
    return __max_client

def add_public_current_client():
    current_value = get_public_current_client()
    current_value += 1
    if current_value > __max_client:
        current_value = __max_client
    set_public_current_client(current_value)

def sub_public_current_client():
    current_value = get_public_current_client()
    current_value -= 1
    if current_value < 0:
        current_value = 0
    set_public_current_client(current_value)

def set_public_current_client(value):
    data = {"public_current_client": value}
    with open(__public_current_client_file, 'w') as f:
        json.dump(data, f)

def get_public_current_client():
    if not os.path.exists(__public_current_client_file):
        return 0
    with open(__public_current_client_file, 'r') as f:
        data = json.load(f)
    return data.get("public_current_client", 0)

def get_client_data_config_path():
    check_dir()
    return __client_data_config_path

def check_dir():
    if not os.path.exists(__localappdata_path):
        os.makedirs(__localappdata_path)
