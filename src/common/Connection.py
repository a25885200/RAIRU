import socket
import json
import base64
from cryptography.fernet import Fernet
from datetime import datetime
import os

class Connection:
    def __init__(self, host, port, password, client_id=None):
        self.host = self.fix_host(host)
        self.port = port
        self.password = password
        self.connect_type = None
        self.client_id = client_id
        self.socket = None
        self.cipher = None
        self.connected = False

    def fix_host(self, host):
        if host.lower() == "localhost":
            return "127.0.0.1"
            

    def connect(self):
        """Connect to the remote server"""
        try:
            self.host = self.fix_host(self.host)
            # Generate encryption key from password
            key = base64.urlsafe_b64encode(self.password.ljust(32)[:32].encode())
            self.cipher = Fernet(key)
            
            # Create socket and connect
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 5 second timeout for connection
            # print (self.host)
            # print (self.port)
            self.socket.connect((self.host, self.port))
            
            # Authenticate
            if not self.authenticate():
                self.disconnect()
                raise Exception("Authentication failed")
            
            self.socket.settimeout(None)  # Remove timeout after successful connection
            self.connected = True
            return True
        
        except Exception as e:
            self.disconnect()
            raise e

    def disconnect(self):
        """Disconnect from the server"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False

    def authenticate(self):
        """Authenticate with the server"""
        try:
            auth_data = {'password': self.password}
            encrypted = self.cipher.encrypt(json.dumps(auth_data).encode())
            self.socket.send(encrypted)
            
            # Receive response
            response_data = self.socket.recv(1024)
            decrypted = self.cipher.decrypt(response_data).decode()
            response = json.loads(decrypted)
            
            return response.get('status') == 'success'
        
        except Exception:
            return False

    def update_manager_connection_status(self, config_path):
        """Update the connection status in the manager if client_id is set"""
        if not self.client_id:
            return
            
        try:
            # Check if clients_data.config exists
            if not os.path.exists(config_path):
                return
                
            # Load client data
            with open(config_path, 'r') as f:
                data = json.load(f)
                
            # Update last_connected for this client
            if self.client_id in data:
                data[self.client_id]["last_connected"] = datetime.now().isoformat()
                
                # Save updated data
                with open(config_path, 'w') as f:
                    json.dump(data, f, indent=4)
                    
        except Exception as e:
            print(f"Error updating client connection status: {e}")
