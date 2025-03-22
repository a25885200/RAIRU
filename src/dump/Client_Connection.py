import socket
import json
import base64
from cryptography.fernet import Fernet
from tkinter import messagebox
from datetime import datetime
import Globals as gb
from lib.util import *

class ClientConnection:
    def __init__(self, client):
        self.client = client

    def connect(self):
        """Connect to the remote server"""
        if self.client.connected:
            self.disconnect()
            return
        
        try:
            # Get connection details from UI
            self.client.host = self.client.host_var.get().strip()
            self.client.port = int(self.client.port_var.get())
            self.client.password = self.client.password_var.get().strip()
            
            # Update status
            self.client.status_var.set("Connecting...")
            self.client.root.update()
            
            # Generate encryption key from password
            key = base64.urlsafe_b64encode(self.client.password.ljust(32)[:32].encode())
            self.client.cipher = Fernet(key)
            
            # Create socket and connect
            self.client.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.socket.settimeout(5)  # 5 second timeout for connection
            self.client.socket.connect((self.client.host, self.client.port))
            
            # Authenticate
            if self.authenticate():
                self.client.socket.settimeout(None)  # Remove timeout after successful connection
                self.client.connected = True
                self.client.status_var.set("Connected")
                
                # Update button states
                self.client.connect_btn.config(text="Disconnect")
                self.client.enable_controls(True)
                
                # Start screen updates
                self.client.screen_running = True
                self.client.screen_thread = threading.Thread(target=self.client.event_handler.update_screen)
                self.client.screen_thread.daemon = True
                self.client.screen_thread.start()
                
                self.client.log(f"Connected to {self.client.host}:{self.client.port}")
                
                # Update connection status in manager if client_id is provided
                self.update_manager_connection_status()
                
            else:
                self.client.status_var.set("Authentication Failed")
                if self.client.socket:
                    self.client.socket.close()
                    self.client.socket = None
                self.client.log(f"Authentication failed for {self.client.host}:{self.client.port}")
        
        except socket.timeout:
            messagebox.showerror("Connection Error", f"Connection to {self.client.host}:{self.client.port} timed out")
            self.client.status_var.set("Connection Timeout")
            if self.client.socket:
                self.client.socket.close()
                self.client.socket = None
            self.client.log(f"Connection timeout: {self.client.host}:{self.client.port}")
        
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", f"Connection to {self.client.host}:{self.client.port} refused")
            self.client.status_var.set("Connection Refused")
            if self.client.socket:
                self.client.socket.close()
                self.client.socket = None
            self.client.log(f"Connection refused: {self.client.host}:{self.client.port}")
        
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.client.status_var.set("Connection Error")
            if self.client.socket:
                self.client.socket.close()
                self.client.socket = None
            self.client.log(f"Connection error: {str(e)}")

    def disconnect(self):
        """Disconnect from the server"""
        self.client.screen_running = False
        if self.client.socket:
            try:
                self.client.socket.close()
            except:
                pass
            self.client.socket = None
        
        self.client.connected = False
        self.client.status_var.set("Disconnected")
        
        # Update button states
        self.client.connect_btn.config(text="Connect")
        self.client.enable_controls(False)
        
        # Clear the canvas
        self.client.canvas.delete("all")
        self.client.screen_size_label.config(text="Remote Screen: Not connected")
        
        self.client.log("Disconnected from server")

    def authenticate(self):
        """Authenticate with the server"""
        try:
            auth_data = {'password': self.client.password}
            encrypted = self.client.cipher.encrypt(json.dumps(auth_data).encode())
            self.client.socket.send(encrypted)
            
            # Receive response
            response_data = self.client.socket.recv(1024)
            decrypted = self.client.cipher.decrypt(response_data).decode()
            response = json.loads(decrypted)
            
            return response.get('status') == 'success'
        
        except Exception as e:
            self.client.log(f"Authentication error: {str(e)}")
            return False

    def update_manager_connection_status(self):
        """Update the connection status in the manager if client_id is set"""
        if not self.client.client_id:
            return
            
        try:
            # Check if clients_data.config exists
            if not os.path.exists(gb.get_client_data_config_path()):
                return
                
            # Load client data
            with open(gb.get_client_data_config_path(), 'r') as f:
                data = json.load(f)
                
            # Update last_connected for this client
            if self.client.client_id in data:
                data[self.client.client_id]["last_connected"] = datetime.now().isoformat()
                
                # Save updated data
                with open(gb.get_client_data_config_path(), 'w') as f:
                    json.dump(data, f, indent=4)
                    
                print(f"Updated connection status for client {self.client.client_id}")
                
        except Exception as e:
            print(f"Error updating client connection status: {e}")
