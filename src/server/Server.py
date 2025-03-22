
from common.util import *

import numpy as np
import tkinter as tk
from time import sleep
import common.LoggingHD as lg
import Globals as gb

# Import the UI parser
from common.ui_parser import TkUIParser

class RemoteControlServer:
    def __init__(self, tk):
        lg.logger.info("initiating Server")
        """Initialize the Remote Control Server application"""
        self.host = '0.0.0.0'  # Listen on all available interfaces
        self.port = 5000
        self.password = 'secure_password'
        self.socket = None
        self.running = False
        self.clients = []
        
        # Generate key from password (will be updated when server starts)
        key = base64.urlsafe_b64encode(self.password.ljust(32)[:32].encode())
        self.cipher = Fernet(key)
        
        # Screen dimensions (will be updated when server starts)
        self.screen_width, self.screen_height = 0, 0
        
        # Quality settings
        self.image_quality = 30  # JPEG compression (0-100)
        self.update_rate = 0.5  # seconds between screen updates
        
        # Create the root Tkinter window
        self.tk = tk
        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create UI from XML definition
        self.setup_gui()
    
    def setup_gui(self):
        """Set up the GUI from XML definition"""
        try:
            # Create UI parser and parse the XML file
            xml_ui = gb.get_server_ui_xml_path()
            lg.logger.debug(f"xml_ui: {xml_ui}") 
            parser = TkUIParser(self)
            parser.parse_file(xml_ui)
            
            # Update IP addresses
            self.update_ip_addresses()
            
            # Add initial log message
            self.log("Server application started")
            
        except Exception as e:
            print(f"Error setting up GUI: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load UI: {str(e)}")
    
    def update_ip_addresses(self):
        """Update the IP address dropdown with available addresses"""
        ip_addresses = self.get_local_ips()
        if ip_addresses:
            self.ip_var.set(ip_addresses[0])
            self.ip_combo['values'] = ip_addresses
        else:
            self.ip_var.set("No network connection")
    
    def get_local_ips(self):
        """Get all local IP addresses"""
        try:
            # Create a socket to connect to an external server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Doesn't actually send traffic
            primary_ip = s.getsockname()[0]
            s.close()
            
            # Also get all available IPs
            ips = []
            for if_name in socket.if_nameindex():
                try:
                    ip = socket.gethostbyname(socket.gethostname())
                    if ip not in ips and not ip.startswith("127."):
                        ips.append(ip)
                except:
                    pass
            
            if primary_ip not in ips:
                ips.insert(0, primary_ip)
                
            return ips
        except:
            # Fallback method
            hostname = socket.gethostname()
            try:
                return [socket.gethostbyname(hostname)]
            except:
                return ["127.0.0.1"]
    
    def toggle_password_visibility(self, event=None):
        """Toggle password visibility in the UI"""
        if self.show_password_var.get():
            self.pass_entry.config(show="")
        else:
            self.pass_entry.config(show="•")
    
    def toggle_server(self):
        """Start or stop the server"""
        if not self.running:
            # Start the server
            self.start_server()
        else:
            # Stop the server
            self.stop_server()
    
    def start_server(self):
        """Start the server"""
        try:
            # Update config from UI
            self.port = self.port_var.get()
            new_password = self.password_var.get()
            
            # Update encryption key if password changed
            if new_password != self.password:
                self.password = new_password
                key = base64.urlsafe_b64encode(self.password.ljust(32)[:32].encode())
                self.cipher = Fernet(key)
            
            # Update quality settings
            self.image_quality = self.quality_var.get()
            self.update_rate = self.rate_var.get()
            
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind and start listening
            selected_ip = self.ip_var.get()
            self.socket.bind((self.host, self.port))  # Bind to all interfaces
            self.socket.listen(5)
            
            # Start the server thread
            self.running = True
            self.server_thread = threading.Thread(target=self.run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Start screen preview thread
            self.preview_thread = threading.Thread(target=self.update_preview)
            self.preview_thread.daemon = True
            self.preview_thread.start()
            
            # Update UI
            self.status_var.set("Running")
            self.status_indicator.config(foreground="green")
            self.start_btn.config(text="Stop Server")
            
            # Log
            self.log(f"Server started on {selected_ip}:{self.port}")
            self.log(f"Use the following information on the client:")
            self.log(f"  - IP Address: {selected_ip}")
            self.log(f"  - Port: {self.port}")
            self.log(f"  - Password: {self.password}")
            
            # Get screen dimensions
            self.screen_width, self.screen_height = pyautogui.size()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {str(e)}")
            self.running = False
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        
        # Close all client connections
        for client in self.clients:
            try:
                client['socket'].close()
            except:
                pass
        
        self.clients = []
        
        # Close server socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Update UI
        self.status_var.set("Stopped")
        self.status_indicator.config(foreground="red")
        self.start_btn.config(text="Start Server")
        self.client_listbox.delete(0, self.tk.END)
        
        # Log
        self.log("Server stopped")
    
    def run_server(self):
        """Main server thread that accepts connections"""
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                
                # Start a new thread to handle the client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    self.log(f"Error accepting connection: {str(e)}")
            
            sleep(0.1)  # Small delay to prevent CPU hogging
    
    def handle_client(self, client_socket, addr):
        """Handle a client connection"""
        client_info = {
            'socket': client_socket,
            'address': addr,
            'authenticated': False,
            'last_activity': datetime.now()
        }
        
        try:
            # Authentication
            if not self.authenticate_client(client_socket, addr):
                self.log(f"Failed authentication attempt from {addr[0]}:{addr[1]}")
                client_socket.close()
                return
            
            client_info['authenticated'] = True
            self.clients.append(client_info)
            
            # Update client list in UI
            self.update_client_list()
            
            self.log(f"Client connected: {addr[0]}:{addr[1]}")
            
            # Main communication loop
            while self.running and client_socket:
                try:
                    # Receive encrypted command
                    encrypted_data = client_socket.recv(4096)
                    if not encrypted_data:
                        break
                    
                    # Decrypt command
                    data = self.cipher.decrypt(encrypted_data).decode()
                    cmd = json.loads(data)
                    
                    # Update activity timestamp
                    client_info['last_activity'] = datetime.now()
                    
                    # Process command
                    if cmd['action'] == 'screen':
                        self.send_screen(client_socket)
                    elif cmd['action'] == 'mouse':
                        self.handle_mouse(cmd)
                        self.log(f"Mouse action: {cmd['type']} from {addr[0]}:{addr[1]}")
                    elif cmd['action'] == 'keyboard':
                        self.handle_keyboard(cmd)
                        self.log(f"Keyboard action: {cmd['type']} from {addr[0]}:{addr[1]}")
                    elif cmd['action'] == 'file_download':
                        self.send_file(client_socket, cmd['path'])
                        self.log(f"File download request: {cmd['path']} from {addr[0]}:{addr[1]}")
                    elif cmd['action'] == 'file_upload':
                        self.receive_file(client_socket, cmd['path'], cmd['size'])
                        self.log(f"File upload: {cmd['path']} ({cmd['size']} bytes) from {addr[0]}:{addr[1]}")
                
                except Exception as e:
                    self.log(f"Error handling client {addr[0]}:{addr[1]}: {str(e)}")
                    break
        
        except Exception as e:
            self.log(f"Client error {addr[0]}:{addr[1]}: {str(e)}")
        
        finally:
            # Remove client from list
            if client_info in self.clients:
                self.clients.remove(client_info)
            
            # Close socket
            try:
                client_socket.close()
            except:
                pass
            
            # Update client list in UI
            self.update_client_list()
            
            self.log(f"Client disconnected: {addr[0]}:{addr[1]}")
    
    def authenticate_client(self, client_socket, addr):
        """Authenticate a client connection"""
        try:
            # Receive authentication request
            auth_data = client_socket.recv(1024)
            
            # Decrypt the authentication data
            try:
                decrypted = self.cipher.decrypt(auth_data).decode()
                auth = json.loads(decrypted)
                
                # Check the password
                if auth.get('password') == self.password:
                    # Send success response
                    response = {'status': 'success'}
                    encrypted = self.cipher.encrypt(json.dumps(response).encode())
                    client_socket.send(encrypted)
                    return True
                else:
                    # Send failure response
                    response = {'status': 'failed', 'reason': 'Invalid password'}
                    encrypted = self.cipher.encrypt(json.dumps(response).encode())
                    client_socket.send(encrypted)
                    return False
            
            except Exception as e:
                # Decryption failed - send error response
                response = {'status': 'failed', 'reason': 'Authentication error'}
                try:
                    # Try to create a new cipher with the received data as if it were a password
                    # This helps when client uses a different password
                    temp_key = base64.urlsafe_b64encode(auth_data[:32].ljust(32, b'='))
                    temp_cipher = Fernet(temp_key)
                    encrypted = temp_cipher.encrypt(json.dumps(response).encode())
                    client_socket.send(encrypted)
                except:
                    # If that fails too, just send raw error
                    client_socket.send(json.dumps(response).encode())
                return False
        
        except Exception as e:
            self.log(f"Authentication error with {addr[0]}:{addr[1]}: {str(e)}")
            return False
    
    def send_screen(self, client_socket):
        """Capture and send screen to client"""
        try:
            # Capture screen
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            
            # Convert to JPEG with compression
            _, buffer = cv2.imencode('.jpg', screenshot_np, [cv2.IMWRITE_JPEG_QUALITY, self.image_quality])
            jpg_as_text = base64.b64encode(buffer).decode()
            
            # Send screen data
            screen_data = {
                'width': self.screen_width,
                'height': self.screen_height,
                'image': jpg_as_text
            }
            
            encrypted = self.cipher.encrypt(json.dumps(screen_data).encode())
            
            # Send size first, then data
            size = len(encrypted)
            client_socket.send(size.to_bytes(4, byteorder='big'))
            client_socket.send(encrypted)
        
        except Exception as e:
            self.log(f"Error sending screen: {str(e)}")
            raise
    
    def handle_mouse(self, cmd):
        """Process mouse commands"""
        try:
            if cmd['type'] == 'move':
                pyautogui.moveTo(cmd['x'], cmd['y'])
            elif cmd['type'] == 'click':
                pyautogui.click(cmd['x'], cmd['y'], button=cmd['button'])
            elif cmd['type'] == 'double_click':
                pyautogui.doubleClick(cmd['x'], cmd['y'], button=cmd['button'])
            elif cmd['type'] == 'drag':
                pyautogui.dragTo(cmd['x'], cmd['y'], button=cmd['button'])
            elif cmd['type'] == 'scroll':
                pyautogui.scroll(cmd['amount'])
        except Exception as e:
            self.log(f"Error executing mouse command: {str(e)}")
    
    def handle_keyboard(self, cmd):
        """Process keyboard commands"""
        try:
            if cmd['type'] == 'key':
                pyautogui.press(cmd['key'])
            elif cmd['type'] == 'hotkey':
                pyautogui.hotkey(*cmd['keys'])
            elif cmd['type'] == 'write':
                pyautogui.write(cmd['text'])
        except Exception as e:
            self.log(f"Error executing keyboard command: {str(e)}")
    
    def send_file(self, client_socket, path):
        """Send file to client"""
        try:
            # Check if file exists
            if not os.path.isfile(path):
                error_data = {'error': 'File not found'}
                encrypted = self.cipher.encrypt(json.dumps(error_data).encode())
                client_socket.send(encrypted)
                return
            
            # Read file data
            with open(path, 'rb') as file:
                file_data = file.read()
            
            # Send file size
            size_data = {'size': len(file_data)}
            encrypted = self.cipher.encrypt(json.dumps(size_data).encode())
            client_socket.send(encrypted)
            
            # Send file data in chunks
            chunk_size = 4096
            for i in range(0, len(file_data), chunk_size):
                chunk = file_data[i:i+chunk_size]
                encrypted_chunk = self.cipher.encrypt(chunk)
                client_socket.send(encrypted_chunk)
            
            self.log(f"File sent: {path} ({len(file_data)} bytes)")
        
        except Exception as e:
            self.log(f"Error sending file {path}: {str(e)}")
            # Try to send error message
            try:
                error_data = {'error': str(e)}
                encrypted = self.cipher.encrypt(json.dumps(error_data).encode())
                client_socket.send(encrypted)
            except:
                pass
    
    def receive_file(self, client_socket, path, size):
        """Receive file from client"""
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            # Receive file data
            with open(path, 'wb') as file:
                received = 0
                while received < size:
                    encrypted_chunk = client_socket.recv(4096)
                    if not encrypted_chunk:
                        break
                    
                    chunk = self.cipher.decrypt(encrypted_chunk)
                    file.write(chunk)
                    received += len(chunk)
            
            # Send confirmation
            response = {'status': 'success'}
            encrypted = self.cipher.encrypt(json.dumps(response).encode())
            client_socket.send(encrypted)
            
            self.log(f"File received: {path} ({received} bytes)")
        
        except Exception as e:
            self.log(f"Error receiving file {path}: {str(e)}")
            # Try to send error message
            try:
                response = {'status': 'error', 'message': str(e)}
                encrypted = self.cipher.encrypt(json.dumps(response).encode())
                client_socket.send(encrypted)
            except:
                pass
    
    def update_client_list(self):
        """Update the client list in the UI"""
        # This needs to be run on the main thread
        self.root.after(0, self._update_client_list)
    
    def _update_client_list(self):
        """Internal method to update client listbox (runs on main thread)"""
        self.client_listbox.delete(0, self.tk.END)
        for client in self.clients:
            if client['authenticated']:
                addr = client['address']
                self.client_listbox.insert(self.tk.END, f"{addr[0]}:{addr[1]}")
    
    def disconnect_client(self):
        """Disconnect the selected client"""
        selection = self.client_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index >= len(self.clients):
            return
        
        client = self.clients[index]
        try:
            client['socket'].close()
        except:
            pass
        
        # The client will be removed from the list in the handle_client method
        self.log(f"Disconnected client: {client['address'][0]}:{client['address'][1]}")
    
    def update_preview(self):
        """Update the screen preview periodically"""
        while self.running:
            try:
                # Capture screen
                screenshot = pyautogui.screenshot()
                
                # Resize for preview
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                if canvas_width > 10 and canvas_height > 10:  # Ensure canvas is visible
                    # Calculate aspect ratio
                    screen_ratio = self.screen_width / self.screen_height if self.screen_width and self.screen_height else screenshot.width / screenshot.height
                    canvas_ratio = canvas_width / canvas_height
                    
                    if screen_ratio > canvas_ratio:
                        # Fit to width
                        new_width = canvas_width
                        new_height = int(canvas_width / screen_ratio)
                    else:
                        # Fit to height
                        new_height = canvas_height
                        new_width = int(canvas_height * screen_ratio)
                    
                    # Resize image
                    screenshot = screenshot.resize((new_width, new_height), PIL.Image.LANCZOS)
                    
                    # Convert to PhotoImage and update canvas
                    self.update_preview_image(screenshot)
            
            except Exception as e:
                print(f"Preview error: {e}")
            
            sleep(1)  # Update preview once per second
    
    def update_preview_image(self, image):
        """Update the preview image in the UI (runs on main thread)"""
        try:
            photo = PIL.ImageTk.PhotoImage(image)
            
            # This needs to be run on the main thread
            self.root.after(0, lambda: self._update_canvas(photo))
        except Exception as e:
            print(f"Error updating preview: {e}")
    
    def _update_canvas(self, photo):
        """Internal method to update canvas (runs on main thread)"""
        try:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                self.preview_canvas.winfo_width() // 2,
                self.preview_canvas.winfo_height() // 2,
                anchor=self.tk.CENTER,
                image=photo
            )
            self.preview_canvas.image = photo  # Keep a reference
        except Exception as e:
            print(f"Canvas update error: {e}")
    
    def log(self, message):
        """Add a message to the log"""
        # This needs to be run on the main thread
        self.root.after(0, lambda: self._log(message))
    
    def _log(self, message):
        """Internal method to update log (runs on main thread)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        self.log_text.config(state=self.tk.NORMAL)
        self.log_text.insert(self.tk.END, log_message + "\n")
        self.log_text.see(self.tk.END)
        self.log_text.config(state=self.tk.DISABLED)
    
    def on_close(self):
        """Handle window close event"""
        if self.running:
            if messagebox.askyesno("Confirm Exit", "Server is still running. Stop it and exit?"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()        
    
    def run(self):
        """Run the server application"""
        self.root.mainloop()



if __name__ == "__main__":
    lg.logger.debug("Parse Server arguments")
    server = RemoteControlServer(tk)
    lg.logger.debug("calling RemoteControlServer.run()")
    server.run()