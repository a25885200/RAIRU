import os
import json
import datetime as dt

__xml_key = "wupH_xMcVbS_j2SvAXguZGbGRY6tF__PsvEqcNyNpkE="
__max_client = 3
__localappdata_path = os.getenv('LOCALAPPDATA') + "\\RAIRU"

__public_current_client_file = os.path.join(__localappdata_path, "public_current_client.json")

__client_data_config_name ="clients_data.config"
__client_data_config_path = os.path.join(__localappdata_path, __client_data_config_name)

__logging_txt_name = "logging.log"
__logging_txt_path = os.path.join(__localappdata_path,"logs")

__assets_forms_path = os.path.join(os.path.dirname(__file__),'assets','forms')
__client_ui_xml_path= os.path.join(__assets_forms_path,'client_ui.xml' )
__server_ui_xml_path= os.path.join(__assets_forms_path,'server_ui.xml' )
__main_ui_xml_path= os.path.join(__assets_forms_path,'main_ui.xml' )

__assets_config_path = os.path.join(os.path.dirname(__file__),'assets','configs')
__logging_config_path = os.path.join(__assets_config_path,'logging_config.json' )
def get_xml_key():
    return __xml_key

#common function section
def check_dir(value):
    if not os.path.exists(value):
        os.makedirs(value)

def get_assets_forms_path():
    return __assets_forms_path

def get_assets_config_path():
    return __assets_config_path


# UI xml path
def get_client_ui_xml_path():
    return __client_ui_xml_path

def get_server_ui_xml_path():
    return __server_ui_xml_path

def get_main_ui_xml_path():
    return __main_ui_xml_path


# Current Client servise count
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


# Main Client data list
def get_client_data_config_path():
    check_dir(__localappdata_path)
    return __client_data_config_path


# Logging section
def set__logging_txt_name():
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + __logging_txt_name

def get_logging_txt_path():
    check_dir(__logging_txt_path)    
    return os.path.join(__logging_txt_path, get__logging_txt_name())

def get__logging_txt_name():
    if __logging_txt_name == "logging.log":
        return set__logging_txt_name()
    else: 
        return __logging_txt_name

# Logging config
def get_logging_config_path():
    return __logging_config_path

def get__logging_config():    
    if not os.path.exists(__logging_config_path):
        return 0
    with open(__logging_config_path, 'r') as f:
        data = json.load(f)
    return data.get("logging_config", 0)

def set__logging_config(value):
    data = value
    with open(__logging_config_path, 'w') as f:
        json.dump(data, f)



