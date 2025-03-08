import os

__xml_key = "wupH_xMcVbS_j2SvAXguZGbGRY6tF__PsvEqcNyNpkE="
__max_client = 5
Public_current_client = 0 
__localappdata_path = os.getenv('LOCALAPPDATA') + "\\RAIRU"
__client_data_config_path = os.getenv('LOCALAPPDATA') + "\\RAIRU\\clients_data.config"

def get_xml_key():
    return __xml_key

def get_max_client():
    return __max_client

def set_Public_current_client(Public_current_client):
    Public_current_client = Public_current_client

def get_Public_current_client():
    return Public_current_client

def get_client_data_config_path():
    check_dir()
    return __client_data_config_path

def check_dir():
    if not os.path.exists(__localappdata_path):
        os.makedirs(__localappdata_path)
    