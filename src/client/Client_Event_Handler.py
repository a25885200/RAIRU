import json
import os
from tkinter import filedialog, simpledialog, messagebox

class EventHandler:
    def __init__(self, connection):
        self.connection = connection
        self.mouse_dragging = False

    def on_mouse_move(self, x, y):
        """Handle mouse movement event"""                
        cmd = {
            'action': 'mouse',
            'type': 'drag' if self.mouse_dragging else 'move',
            'x': x,
            'y': y,
            'button': 'left'
        }
        self._send_command(cmd)

    def on_mouse_click(self, x, y):
        """Handle mouse click event"""
        cmd = {
            'action': 'mouse',
            'type': 'click',
            'x': x,
            'y': y,
            'button': 'left'
        }
        self._send_command(cmd)

    def on_mouse_double_click(self, x, y):
        """Handle mouse double click event"""
        cmd = {
            'action': 'mouse',
            'type': 'double_click',
            'x': x,
            'y': y,
            'button': 'left'
        }
        self._send_command(cmd)

    def on_mouse_drag(self, x, y):
        """Handle mouse drag event"""
        self.mouse_dragging = True
        cmd = {
            'action': 'mouse',
            'type': 'drag',
            'x': x,
            'y': y,
            'button': 'left'
        }
        self._send_command(cmd)

    def on_mouse_release(self):
        """Handle mouse release event"""
        self.mouse_dragging = False

    def on_mouse_wheel(self, amount):
        """Handle mouse wheel event"""
        cmd = {
            'action': 'mouse',
            'type': 'scroll',
            'amount': amount
        }
        self._send_command(cmd)

    def on_key_press(self, key, modifiers):
        """Handle key press event"""
        if key in ('Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R'):
            return
        
        cmd = {
            'action': 'keyboard',
            'type': 'hotkey' if modifiers else 'key',
            'keys': modifiers + [key.lower()] if modifiers else None,
            'key': key.lower() if not modifiers else None
        }
        self._send_command(cmd)

    def send_text(self, text):
        """Send text to the remote server"""
        if not text:
            return
        
        cmd = {
            'action': 'keyboard',
            'type': 'write',
            'text': text
        }
        self._send_command(cmd)

    def upload_file(self):
        """Upload a file to the remote server"""
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
            self._send_command(cmd)
            
            # Read and send file data
            with open(file_path, 'rb') as file:
                chunk_size = 4096
                while chunk := file.read(chunk_size):
                    encrypted_chunk = self.connection.cipher.encrypt(chunk)
                    self.connection.socket.send(encrypted_chunk)
            
            # Receive confirmation
            response_data = self.connection.socket.recv(1024)
            decrypted = self.connection.cipher.decrypt(response_data).decode()
            response = json.loads(decrypted)
            
            if response.get('status') == 'success':
                messagebox.showinfo("Success", "File uploaded successfully")
            else:
                messagebox.showerror("Error", response.get('message', 'Unknown error'))
        
        except Exception as e:
            messagebox.showerror("Upload Error", str(e))

    def download_file(self):
        """Download a file from the remote server"""
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
            self._send_command(cmd)
            
            # Receive file size
            size_data = self.connection.socket.recv(1024)
            decrypted = self.connection.cipher.decrypt(size_data).decode()
            size_info = json.loads(decrypted)
            
            if 'error' in size_info:
                messagebox.showerror("Error", size_info['error'])
                return
            
            file_size = size_info['size']
            
            # Receive file data
            with open(local_path, 'wb') as file:
                received = 0
                while received < file_size:
                    chunk = self.connection.socket.recv(4096)
                    if not chunk:
                        break
                    decrypted_chunk = self.connection.cipher.decrypt(chunk)
                    file.write(decrypted_chunk)
                    received += len(decrypted_chunk)
            
            messagebox.showinfo("Success", "File downloaded successfully")
        
        except Exception as e:
            messagebox.showerror("Download Error", str(e))

    def receive_screen(self):
        """Request and receive screen updates from the server"""
        try:
            # Request screen update
            cmd = {'action': 'screen'}
            self._send_command(cmd)
            
            # Receive data size
            size_bytes = self.connection.socket.recv(4)
            if not size_bytes:
                return None
            
            size = int.from_bytes(size_bytes, byteorder='big')
            
            # Receive screen data
            data = b''
            while len(data) < size:
                chunk = self.connection.socket.recv(min(size - len(data), 8192))
                if not chunk:
                    break
                data += chunk
            
            if not data:
                return None
            
            # Decrypt and parse screen data
            decrypted = self.connection.cipher.decrypt(data).decode()
            screen_data = json.loads(decrypted)
            return screen_data
        
        except Exception as e:
            print(f"Screen receive error: {str(e)}")
            return None

    def _send_command(self, cmd):
        """Send a command to the server"""
        try:
            encrypted = self.connection.cipher.encrypt(json.dumps(cmd).encode())
            self.connection.socket.send(encrypted)
        except Exception as e:
            print(f"Error sending command: {str(e)}")
