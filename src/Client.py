import socket
import threading
import base64
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import PIL.Image, PIL.ImageTk
import cv2
import numpy as np
import os
import argparse
from io import BytesIO
from cryptography.fernet import Fernet
from datetime import datetime
import time

# Import the UI parser
from ui_parser import TkUIParser
xml_ui = os.path.join(r'.','assets','forms','client_ui.xml' )
class RemoteControlClient:
    def __init__(self, host='localhost', port=5000, password='secure_password', client_id=None):
        """Initialize the Remote Control Client application"""
        self.host = host
        self.port = port
        self.password = password
        self.client_id = client_id  # Used for updating connection status
        self.socket = None
        self.connected = False
        self.cipher = None
        
        # Screen update settings
        self.screen_running = False
        self.screen_thread = None
        self.update_interval = 0.1  # seconds
        
        # Remote screen dimensions
        self.remote_width = 0
        self.remote_height = 0
        
        # Mouse state
        self.mouse_dragging = False
        
        # Create the root Tkinter window
        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create UI from XML definition
        self.setup_gui()
        
        # Auto-connect if parameters were provided
        if host != 'localhost' or port != 5000 or password != 'secure_password':
            self.root.after(500, self.auto_connect)
    
    def setup_gui(self):
        """Set up the GUI from XML definition"""
        try:
            # Create UI parser and parse the XML file
            parser = TkUIParser(self)
            parser.parse_file(xml_ui)
            
            # Add scrollbars to canvas
            self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
            self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
            
            self.canvas.config(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
            
            # Bind mouse events to canvas
            self.canvas.bind("<Button-1>", self.on_mouse_click)
            self.canvas.bind("<Double-Button-1>", self.on_mouse_double_click)
            self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            self.canvas.bind("<Motion>", self.on_mouse_move)
            
            # Bind keyboard events to root window
            self.root.bind("<Key>", self.on_key_press)
            
            # Set up variable traces
            self.host_var.trace_add("write", lambda *args: self.update_connect_button())
            self.port_var.trace_add("write", lambda *args: self.update_connect_button())
            self.password_var.trace_add("write", lambda *args: self.update_connect_button())
            
            # Set initial values from parameters
            self.host_var.set(self.host)
            self.port_var.set(self.port)
            self.password_var.set(self.password)
            
            # Add initial log message
            self.log("Client application started")
            
        except Exception as e:
            print(f"Error setting up GUI: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load UI: {str(e)}")

    def auto_connect(self):
        """Automatically connect using provided parameters"""
        self.connect()
    
    def toggle_password_visibility(self, event=None):
        """Toggle password visibility in the UI"""
        if self.show_password_var.get():
            self.pass_entry.config(show="")
        else:
            self.pass_entry.config(show="•")
    
    def update_connect_button(self):
        """Enable/disable connect button based on input fields"""
        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get())
            valid_port = 1 <= port <= 65535
        except:
            valid_port = False
        
        password = self.password_var.get().strip()
        
        if host and valid_port and password:
            self.connect_btn.config(state=tk.NORMAL)
        else:
            self.connect_btn.config(state=tk.DISABLED)
    
    def connect(self):
        """Connect to the remote server"""
        if self.connected:
            self.disconnect()
            return
        
        try:
            # Get connection details from UI
            self.host = self.host_var.get().strip()
            self.port = int(self.port_var.get())
            self.password = self.password_var.get().strip()
            
            # Update status
            self.status_var.set("Connecting...")
            self.root.update()
            
            # Generate encryption key from password
            key = base64.urlsafe_b64encode(self.password.ljust(32)[:32].encode())
            self.cipher = Fernet(key)
            
            # Create socket and connect
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 5 second timeout for connection
            self.socket.connect((self.host, self.port))
            
            # Authenticate
            if self.authenticate():
                self.socket.settimeout(None)  # Remove timeout after successful connection
                self.connected = True
                self.status_var.set("Connected")
                
                # Update button states
                self.connect_btn.config(text="Disconnect")
                self.enable_controls(True)
                
                # Start screen updates
                self.screen_running = True
                self.screen_thread = threading.Thread(target=self.update_screen)
                self.screen_thread.daemon = True
                self.screen_thread.start()
                
                self.log(f"Connected to {self.host}:{self.port}")
                
                # Update connection status in manager if client_id is provided
                self.update_manager_connection_status()
                
            else:
                self.status_var.set("Authentication Failed")
                if self.socket:
                    self.socket.close()
                    self.socket = None
                self.log(f"Authentication failed for {self.host}:{self.port}")
        
        except socket.timeout:
            messagebox.showerror("Connection Error", f"Connection to {self.host}:{self.port} timed out")
            self.status_var.set("Connection Timeout")
            if self.socket:
                self.socket.close()
                self.socket = None
            self.log(f"Connection timeout: {self.host}:{self.port}")
        
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", f"Connection to {self.host}:{self.port} refused")
            self.status_var.set("Connection Refused")
            if self.socket:
                self.socket.close()
                self.socket = None
            self.log(f"Connection refused: {self.host}:{self.port}")
        
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.status_var.set("Connection Error")
            if self.socket:
                self.socket.close()
                self.socket = None
            self.log(f"Connection error: {str(e)}")
    
    def update_manager_connection_status(self):
        """Update the connection status in the manager if client_id is set"""
        if not self.client_id:
            return
            
        try:
            # Check if clients_data.config exists
            if not os.path.exists("clients_data.config"):
                return
                
            # Load client data
            with open("clients_data.config", 'r') as f:
                data = json.load(f)
                
            # Update last_connected for this client
            if self.client_id in data:
                data[self.client_id]["last_connected"] = datetime.now().isoformat()
                
                # Save updated data
                with open("clients_data.config", 'w') as f:
                    json.dump(data, f, indent=4)
                    
                print(f"Updated connection status for client {self.client_id}")
                
        except Exception as e:
            print(f"Error updating client connection status: {e}")
    
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
        
        except Exception as e:
            self.log(f"Authentication error: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        self.screen_running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.connected = False
        self.status_var.set("Disconnected")
        
        # Update button states
        self.connect_btn.config(text="Connect")
        self.enable_controls(False)
        
        # Clear the canvas
        self.canvas.delete("all")
        self.screen_size_label.config(text="Remote Screen: Not connected")
        
        self.log("Disconnected from server")
    
    def enable_controls(self, enabled):
        """Enable or disable controls based on connection state"""
        state = tk.NORMAL if enabled else tk.DISABLED
        
        # Mouse and keyboard controls
        self.mouse_track_check.config(state=state)
        self.keyboard_input_check.config(state=state)
        
        # Text input
        self.text_input.config(state=state)
        self.send_text_btn.config(state=state)
        
        # File transfer
        self.upload_btn.config(state=state)
        self.download_btn.config(state=state)
    
    def update_screen(self):
        """Request and display screen updates from server"""
        while self.screen_running and self.connected:
            try:
                start_time = time.time()
                
                # Request screen update
                cmd = {'action': 'screen'}
                encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
                self.socket.send(encrypted)
                
                # Receive data size
                size_bytes = self.socket.recv(4)
                if not size_bytes:
                    break
                
                size = int.from_bytes(size_bytes, byteorder='big')
                
                # Receive screen data
                data = b''
                while len(data) < size:
                    chunk = self.socket.recv(min(size - len(data), 8192))
                    if not chunk:
                        break
                    data += chunk
                
                if not data:
                    break
                
                # Decrypt and parse screen data
                decrypted = self.cipher.decrypt(data).decode()
                screen_data = json.loads(decrypted)
                
                # Update remote screen dimensions
                self.remote_width = screen_data['width']
                self.remote_height = screen_data['height']
                
                # Update screen size label in UI
                self.root.after(0, lambda: self.screen_size_label.config(
                    text=f"Remote Screen: {self.remote_width}x{self.remote_height}"
                ))
                
                # Decode image
                image_data = base64.b64decode(screen_data['image'])
                image_array = np.frombuffer(image_data, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_img = PIL.Image.fromarray(image)
                
                # Display the image
                self.display_image(pil_img)
                
                # Calculate time to process and adjust delay
                process_time = time.time() - start_time
                delay = max(0.05, self.update_interval - process_time)
                time.sleep(delay)
            
            except Exception as e:
                if self.screen_running:  # Only log if we're still running
                    self.log(f"Screen update error: {str(e)}")
                break
        
        if self.connected:
            # If we broke out of the loop but are still connected, something went wrong
            self.root.after(0, self.disconnect)
    
    def display_image(self, image):
        """Display an image on the canvas"""
        try:
            # Convert PIL image to PhotoImage for Tkinter
            tk_img = PIL.ImageTk.PhotoImage(image)
            
            # Update on main thread
            self.root.after(0, lambda: self._update_canvas(tk_img, image.width, image.height))
        
        except Exception as e:
            self.log(f"Display error: {str(e)}")
    
    def _update_canvas(self, tk_img, width, height):
        """Update the canvas with a new image (runs on main thread)"""
        try:
            # Clear canvas
            self.canvas.delete("all")
            
            # Create image on canvas
            self.canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
            self.canvas.image = tk_img  # Keep reference to prevent garbage collection
            
            # Update canvas scrollregion
            self.canvas.config(scrollregion=(0, 0, width, height))
            
            # Show scrollbars if needed
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if width > canvas_width:
                self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            else:
                self.h_scrollbar.pack_forget()
            
            if height > canvas_height:
                self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                self.v_scrollbar.pack_forget()
        
        except Exception as e:
            print(f"Canvas update error: {e}")
    
    def map_coordinates(self, x, y):
        """Map canvas coordinates to remote screen coordinates"""
        # Get canvas view
        view_x = self.canvas.canvasx(x)
        view_y = self.canvas.canvasy(y)
        
        # Return raw coordinates - no scaling needed since we're not scaling the image
        return int(view_x), int(view_y)
    
    def on_mouse_move(self, event):
        """Handle mouse movement event"""
        if not self.connected or not self.mouse_tracking_var.get():
            return
        
        x, y = self.map_coordinates(event.x, event.y)
        
        # Update status bar
        self.cursor_pos_label.config(text=f"Position: {x}, {y}")
        
        if self.mouse_dragging:
            cmd = {
                'action': 'mouse',
                'type': 'drag',
                'x': x,
                'y': y,
                'button': 'left'
            }
        else:
            cmd = {
                'action': 'mouse',
                'type': 'move',
                'x': x,
                'y': y
            }
        
        try:
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
        except:
            pass
    
    def on_mouse_click(self, event):
        """Handle mouse click event"""
        if not self.connected or not self.mouse_tracking_var.get():
            return
        
        x, y = self.map_coordinates(event.x, event.y)
        
        cmd = {
            'action': 'mouse',
            'type': 'click',
            'x': x,
            'y': y,
            'button': 'left'
        }
        
        try:
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
            self.log(f"Mouse click at {x},{y}")
        except Exception as e:
            self.log(f"Error sending mouse click: {str(e)}")
    
    def on_mouse_double_click(self, event):
        """Handle mouse double click event"""
        if not self.connected or not self.mouse_tracking_var.get():
            return
        
        x, y = self.map_coordinates(event.x, event.y)
        
        cmd = {
            'action': 'mouse',
            'type': 'double_click',
            'x': x,
            'y': y,
            'button': 'left'
        }
        
        try:
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
            self.log(f"Mouse double-click at {x},{y}")
        except Exception as e:
            self.log(f"Error sending mouse double-click: {str(e)}")
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event"""
        if not self.connected or not self.mouse_tracking_var.get():
            return
        
        self.mouse_dragging = True
        x, y = self.map_coordinates(event.x, event.y)
        
        cmd = {
            'action': 'mouse',
            'type': 'drag',
            'x': x,
            'y': y,
            'button': 'left'
        }
        
        try:
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
        except:
            pass
    
    def on_mouse_release(self, event):
        """Handle mouse release event"""
        self.mouse_dragging = False
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel event"""
        if not self.connected or not self.mouse_tracking_var.get():
            return
        
        # In Windows, event.delta is used
        # Delta is positive when scrolling up, negative when scrolling down
        amount = event.delta // 120  # Normalize to steps
        
        cmd = {
            'action': 'mouse',
            'type': 'scroll',
            'amount': amount
        }
        
        try:
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
            self.log(f"Mouse scroll: {amount}")
        except Exception as e:
            self.log(f"Error sending mouse scroll: {str(e)}")
    
    def on_key_press(self, event):
        """Handle key press event"""
        if not self.connected or not self.keyboard_input_var.get():
            return
        
        # Avoid capturing special keys meant for the UI
        if event.widget != self.root and event.widget != self.canvas:
            return
        
        # Get the key name
        key = event.keysym
        
        # Special handling for modifier keys
        if key in ('Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R'):
            return
        
        # Check if any modifiers are pressed
        modifiers = []
        if event.state & 0x4:  # Control
            modifiers.append('ctrl')
        if event.state & 0x8:  # Alt
            modifiers.append('alt')
        if event.state & 0x1:  # Shift
            modifiers.append('shift')
        
        if modifiers:
            # Send hotkey command
            cmd = {
                'action': 'keyboard',
                'type': 'hotkey',
                'keys': modifiers + [key.lower()]
            }
            self.log(f"Keyboard hotkey: {'+'.join(modifiers + [key.lower()])}")
        else:
            # Send single key command
            cmd = {
                'action': 'keyboard',
                'type': 'key',
                'key': key.lower()
            }
            self.log(f"Keyboard key: {key.lower()}")
        
        try:
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
        except Exception as e:
            self.log(f"Error sending keyboard input: {str(e)}")
    
    def send_text(self):
        """Send text from the text input field"""
        if not self.connected:
            return
        
        text = self.text_input.get()
        if not text:
            return
        
        cmd = {
            'action': 'keyboard',
            'type': 'write',
            'text': text
        }
        
        try:
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
            self.log(f"Sent text: {text}")
            
            # Clear the input field
            self.text_input.delete(0, tk.END)
        except Exception as e:
            self.log(f"Error sending text: {str(e)}")
    
    def upload_file(self):
        """Upload a file to the remote computer"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        
        # Open file dialog
        file_path = filedialog.askopenfilename(title="Select File to Upload")
        if not file_path:
            return
        
        # Ask for remote path
        remote_path = simpledialog.askstring(
            "Remote Path", 
            "Enter destination path on remote computer:",
            initialvalue=os.path.basename(file_path)
        )
        if not remote_path:
            return
        
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Send file upload command
            cmd = {
                'action': 'file_upload',
                'path': remote_path,
                'size': file_size
            }
            
            self.log(f"Uploading {file_path} to {remote_path} ({file_size} bytes)")
            
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
            
            # Read and send file data
            with open(file_path, 'rb') as file:
                chunk_size = 4096
                bytes_sent = 0
                
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    
                    encrypted_chunk = self.cipher.encrypt(chunk)
                    self.socket.send(encrypted_chunk)
                    
                    bytes_sent += len(chunk)
                    
                    # Update progress in log
                    if file_size > 1000000 and bytes_sent % 1000000 < chunk_size:
                        self.log(f"Upload progress: {bytes_sent/file_size*100:.1f}% ({bytes_sent} bytes)")
            
            # Receive confirmation
            response_data = self.socket.recv(1024)
            decrypted = self.cipher.decrypt(response_data).decode()
            response = json.loads(decrypted)
            
            if response.get('status') == 'success':
                messagebox.showinfo("Success", "File uploaded successfully")
                self.log("File upload completed successfully")
            else:
                messagebox.showerror("Error", response.get('message', 'Unknown error'))
                self.log(f"File upload error: {response.get('message', 'Unknown error')}")
        
        except Exception as e:
            messagebox.showerror("Upload Error", str(e))
            self.log(f"Upload error: {str(e)}")
    
    def download_file(self):
        """Download a file from the remote computer"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        
        # Ask for remote path
        remote_path = simpledialog.askstring("Remote Path", "Enter remote file path to download:")
        if not remote_path:
            return
        
        # Ask for local save path
        local_path = filedialog.asksaveasfilename(
            title="Save file locally as",
            initialfile=os.path.basename(remote_path)
        )
        if not local_path:
            return
        
        try:
            # Send file download command
            cmd = {
                'action': 'file_download',
                'path': remote_path
            }
            
            self.log(f"Requesting download of {remote_path}")
            
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
            
            # Receive file size
            size_data = self.socket.recv(1024)
            decrypted = self.cipher.decrypt(size_data).decode()
            size_info = json.loads(decrypted)
            
            if 'error' in size_info:
                messagebox.showerror("Error", size_info['error'])
                self.log(f"Download error: {size_info['error']}")
                return
            
            file_size = size_info['size']
            self.log(f"Downloading {remote_path} to {local_path} ({file_size} bytes)")
            
            # Receive file data
            with open(local_path, 'wb') as file:
                received = 0
                while received < file_size:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    
                    decrypted_chunk = self.cipher.decrypt(chunk)
                    file.write(decrypted_chunk)
                    received += len(decrypted_chunk)
                    
                    # Update progress in log
                    if file_size > 1000000 and received % 1000000 < 4096:
                        self.log(f"Download progress: {received/file_size*100:.1f}% ({received} bytes)")
            
            messagebox.showinfo("Success", "File downloaded successfully")
            self.log("File download completed successfully")
        
        except Exception as e:
            messagebox.showerror("Download Error", str(e))
            self.log(f"Download error: {str(e)}")
    
    def log(self, message):
        """Add a message to the log"""
        # This needs to be run on the main thread
        self.root.after(0, lambda: self._log(message))
    
    def _log(self, message):
        """Internal method to update log (runs on main thread)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def on_close(self):
        """Handle window close event"""
        if self.connected:
            if messagebox.askyesno("Confirm Exit", "You are still connected. Disconnect and exit?"):
                self.disconnect()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Run the client application"""
        self.root.mainloop()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Remote Control Client')
    parser.add_argument('--host', type=str, default='localhost', help='Host to connect to')
    parser.add_argument('--port', type=int, default=5000, help='Port to connect to')
    parser.add_argument('--password', type=str, default='secure_password', help='Password for authentication')
    parser.add_argument('--client-id', type=str, help='Client ID for updating connection status')
    
    args = parser.parse_args()
    
    client = RemoteControlClient(
        host=args.host,
        port=args.port,
        password=args.password,
        client_id=args.client_id
    )
    client.run()