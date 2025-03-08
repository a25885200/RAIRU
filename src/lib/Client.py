import socket
import threading
import base64
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog 
import cv2
import numpy as np
from PIL import Image, ImageTk
import os
from cryptography.fernet import Fernet
from io import BytesIO
import xml.etree.ElementTree as ET

class RemoteClient:
    def __init__(self, host='localhost', port=5000, password='secure_password'):
        self.host = host
        self.port = port
        self.password = password
        self.socket = None
        self.connected = False
        self.xml_file =''
        # Generate encryption key from password
        key = base64.urlsafe_b64encode(password.ljust(32)[:32].encode())
        self.cipher = Fernet(key)
        
        # Set up the GUI
        self.setup_gui(self.xml_file)
    
    def setup_gui(self,xml_file):
        """Create the GUI interface"""
        self.root = tk.Tk()
        self.root.title("Python Remote Control Client")
        self.root.geometry("1200x800")
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connection frame (left side)
        conn_frame = ttk.LabelFrame(main_frame, text="Connection")
        conn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Host input
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.host_var = tk.StringVar(value=self.host)
        ttk.Entry(conn_frame, textvariable=self.host_var, width=20).grid(row=0, column=1, pady=5)
        
        # Port input
        ttk.Label(conn_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.IntVar(value=self.port)
        ttk.Entry(conn_frame, textvariable=self.port_var, width=20).grid(row=1, column=1, pady=5)
        
        # Password input
        ttk.Label(conn_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar(value=self.password)
        ttk.Entry(conn_frame, textvariable=self.password_var, show="*", width=20).grid(row=2, column=1, pady=5)
        
        # Connect button
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.connect_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Disconnected")
        status_label = ttk.Label(conn_frame, textvariable=self.status_var, foreground="red")
        status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # File transfer frame
        file_frame = ttk.LabelFrame(conn_frame, text="File Transfer")
        file_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Upload button
        self.upload_btn = ttk.Button(file_frame, text="Upload File", command=self.upload_file, state=tk.DISABLED)
        self.upload_btn.pack(fill=tk.X, pady=5)
        
        # Download button
        self.download_btn = ttk.Button(file_frame, text="Download File", command=self.download_file, state=tk.DISABLED)
        self.download_btn.pack(fill=tk.X, pady=5)
        
        # Screen display frame (right side)
        screen_frame = ttk.LabelFrame(main_frame, text="Remote Screen")
        screen_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas for screen display
        self.canvas = tk.Canvas(screen_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind mouse events to canvas
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.canvas.bind("<Double-Button-1>", self.on_mouse_double_click)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        
        # Bind keyboard events to root window
        self.root.bind("<Key>", self.on_key_press)
        
        # Set up screen update thread
        self.screen_thread = None
        self.screen_running = False
        
        # Remote screen dimensions
        self.remote_width = 0
        self.remote_height = 0
        
        # Protocol handler for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def save_to_xml(self):
        root = ET.Element("Configuration")

        # Host
        host_element = ET.SubElement(root, "Host")
        host_element.text = self.host_var.get()

        # Port
        port_element = ET.SubElement(root, "Port")
        port_element.text = str(self.port_var.get())

        # Password
        password_element = ET.SubElement(root, "Password")
        password_element.text = self.password_var.get()

        # Write to XML file
        tree = ET.ElementTree(root)
        with open("config.xml", "wb") as fh:
            tree.write(fh)

    def connect(self):
        """Connect to the remote server"""
        try:
            # Get connection details from GUI
            self.host = self.host_var.get()
            self.port = self.port_var.get()
            self.password = self.password_var.get()
            
            # Create socket and connect
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Authenticate
            if self.authenticate():
                self.connected = True
                self.status_var.set("Connected")
                
                # Update button states
                self.connect_btn.configure(text="Disconnect", command=self.disconnect)
                self.upload_btn.configure(state=tk.NORMAL)
                self.download_btn.configure(state=tk.NORMAL)
                
                # Start screen updates
                self.screen_running = True
                self.screen_thread = threading.Thread(target=self.update_screen)
                self.screen_thread.daemon = True
                self.screen_thread.start()
            else:
                messagebox.showerror("Authentication Failed", "Invalid password")
                self.socket.close()
                self.socket = None
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def authenticate(self):
        """Authenticate with the server"""
        auth_data = {'password': self.password}
        encrypted = self.cipher.encrypt(json.dumps(auth_data).encode())
        self.socket.send(encrypted)
        
        # Receive response
        response_data = self.socket.recv(1024)
        decrypted = self.cipher.decrypt(response_data).decode()
        response = json.loads(decrypted)
        
        return response.get('status') == 'success'
    
    def disconnect(self):
        """Disconnect from the server"""
        self.screen_running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        
        self.connected = False
        self.status_var.set("Disconnected")
        
        # Update button states
        self.connect_btn.configure(text="Connect", command=self.connect)
        self.upload_btn.configure(state=tk.DISABLED)
        self.download_btn.configure(state=tk.DISABLED)
    
    def update_screen(self):
        """Request and display screen updates from server"""
        while self.screen_running and self.connected:
            try:
                # Request screen update
                cmd = {'action': 'screen'}
                encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
                self.socket.send(encrypted)
                
                # Receive data size
                size_bytes = self.socket.recv(4)
                size = int.from_bytes(size_bytes, byteorder='big')
                
                # Receive screen data
                data = b''
                while len(data) < size:
                    chunk = self.socket.recv(min(size - len(data), 4096))
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
                
                # Decode image
                image_data = base64.b64decode(screen_data['image'])
                image_array = np.frombuffer(image_data, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Resize image to fit canvas
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    # Calculate aspect ratio
                    img_ratio = self.remote_width / self.remote_height
                    canvas_ratio = canvas_width / canvas_height
                    
                    if img_ratio > canvas_ratio:
                        # Fit to width
                        new_width = canvas_width
                        new_height = int(canvas_width / img_ratio)
                    else:
                        # Fit to height
                        new_height = canvas_height
                        new_width = int(canvas_height * img_ratio)
                    
                    image = cv2.resize(image, (new_width, new_height))
                
                # Convert to PhotoImage and display
                pil_img = Image.fromarray(image)
                tk_img = ImageTk.PhotoImage(pil_img)
                
                # Update canvas
                self.canvas.config(width=tk_img.width(), height=tk_img.height())
                self.canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
                self.canvas.image = tk_img  # Keep reference to prevent garbage collection
            
            except Exception as e:
                print(f"Screen update error: {e}")
                break
        
        if self.connected:
            self.disconnect()
    
    def map_coordinates(self, x, y):
        """Map canvas coordinates to remote screen coordinates"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return x, y
        
        remote_x = int((x / canvas_width) * self.remote_width)
        remote_y = int((y / canvas_height) * self.remote_height)
        
        return remote_x, remote_y
    
    def on_mouse_click(self, event):
        """Handle mouse click event"""
        if not self.connected:
            return
        
        x, y = self.map_coordinates(event.x, event.y)
        cmd = {
            'action': 'mouse',
            'type': 'click',
            'x': x,
            'y': y,
            'button': 'left'
        }
        
        encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
        self.socket.send(encrypted)
    
    def on_mouse_double_click(self, event):
        """Handle mouse double click event"""
        if not self.connected:
            return
        
        x, y = self.map_coordinates(event.x, event.y)
        cmd = {
            'action': 'mouse',
            'type': 'double_click',
            'x': x,
            'y': y,
            'button': 'left'
        }
        
        encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
        self.socket.send(encrypted)
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event"""
        if not self.connected:
            return
        
        x, y = self.map_coordinates(event.x, event.y)
        cmd = {
            'action': 'mouse',
            'type': 'move',
            'x': x,
            'y': y
        }
        
        encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
        self.socket.send(encrypted)
    
    def on_mouse_release(self, event):
        """Handle mouse release event"""
        pass  # We might need this for drag operations
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel event"""
        if not self.connected:
            return
        
        # In Windows, event.delta is used
        amount = event.delta // 120
        
        cmd = {
            'action': 'mouse',
            'type': 'scroll',
            'amount': amount
        }
        
        encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
        self.socket.send(encrypted)
    
    def on_mouse_move(self, event):
        """Handle mouse movement event"""
        if not self.connected:
            return
        
        x, y = self.map_coordinates(event.x, event.y)
        cmd = {
            'action': 'mouse',
            'type': 'move',
            'x': x,
            'y': y
        }
        
        encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
        self.socket.send(encrypted)
    
    def on_key_press(self, event):
        """Handle key press event"""
        if not self.connected:
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
        else:
            # Send single key command
            cmd = {
                'action': 'keyboard',
                'type': 'key',
                'key': key.lower()
            }
        
        encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
        self.socket.send(encrypted)
    
    def upload_file(self):
        """Upload a file to the remote computer"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        
        # Open file dialog
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        
        # Ask for remote path
        remote_path = filedialog.asksaveasfilename(title="Save as on remote computer")
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
            
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
            
            # Read and send file data
            with open(file_path, 'rb') as file:
                chunk_size = 4096
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    
                    encrypted_chunk = self.cipher.encrypt(chunk)
                    self.socket.send(encrypted_chunk)
            
            # Receive confirmation
            response_data = self.socket.recv(1024)
            decrypted = self.cipher.decrypt(response_data).decode()
            response = json.loads(decrypted)
            
            if response.get('status') == 'success':
                messagebox.showinfo("Success", "File uploaded successfully")
            else:
                messagebox.showerror("Error", response.get('message', 'Unknown error'))
        
        except Exception as e:
            messagebox.showerror("Upload Error", str(e))
    
    def download_file(self):
        """Download a file from the remote computer"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        
        # Ask for remote path
        remote_path = simpledialog.askstring("Download File", "Enter remote file path:")
        if not remote_path:
            return
        
        # Ask for local save path
        local_path = filedialog.asksaveasfilename(title="Save file locally as")
        if not local_path:
            return
        
        try:
            # Send file download command
            cmd = {
                'action': 'file_download',
                'path': remote_path
            }
            
            encrypted = self.cipher.encrypt(json.dumps(cmd).encode())
            self.socket.send(encrypted)
            
            # Receive file size
            size_data = self.socket.recv(1024)
            decrypted = self.cipher.decrypt(size_data).decode()
            size_info = json.loads(decrypted)
            
            if 'error' in size_info:
                messagebox.showerror("Error", size_info['error'])
                return
            
            file_size = size_info['size']
            
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
            
            messagebox.showinfo("Success", "File downloaded successfully")
        
        except Exception as e:
            messagebox.showerror("Download Error", str(e))
    
    def run(self):
        """Run the application"""
        self.root.mainloop()
    
    def on_close(self):
        """Handle window close event"""
        if self.connected:
            self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    client = RemoteClient()
    client.run()