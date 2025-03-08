import socket
import threading
import pyautogui
import numpy as np
import cv2
import base64
import json
import os
from cryptography.fernet import Fernet
from time import sleep

class RemoteServer:
    def __init__(self, host='0.0.0.0', port=5000, password='secure_password'):
        self.host = host
        self.port = port
        self.password = password
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Generate encryption key from password
        key = base64.urlsafe_b64encode(password.ljust(32)[:32].encode())
        self.cipher = Fernet(key)
        
        # Screen dimensions
        self.screen_width, self.screen_height = pyautogui.size()
        
        self.clients = []
        self.running = True
    
    def start(self):
        """Start the server and listen for connections"""
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"Server started on {self.host}:{self.port}")
        
        # Start accepting clients
        accept_thread = threading.Thread(target=self.accept_clients)
        accept_thread.daemon = True
        accept_thread.start()
        
        try:
            while self.running:
                sleep(1)
        except KeyboardInterrupt:
            self.shutdown()
    
    def accept_clients(self):
        """Accept connection requests from clients"""
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                print(f"Connection from {addr}")
                
                # Start a new thread to handle the client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                print(f"Error accepting client: {e}")
    
    def handle_client(self, client_socket, addr):
        """Handle communication with a connected client"""
        try:
            # Authentication
            if not self.authenticate_client(client_socket):
                print(f"Authentication failed for {addr}")
                client_socket.close()
                return
            
            print(f"Client {addr} authenticated successfully")
            self.clients.append(client_socket)
            
            # Main communication loop
            while self.running:
                # Receive encrypted command
                encrypted_data = client_socket.recv(4096)
                if not encrypted_data:
                    break
                
                # Decrypt command
                data = self.cipher.decrypt(encrypted_data).decode()
                cmd = json.loads(data)
                
                # Process command
                if cmd['action'] == 'screen':
                    self.send_screen(client_socket)
                elif cmd['action'] == 'mouse':
                    self.handle_mouse(cmd)
                elif cmd['action'] == 'keyboard':
                    self.handle_keyboard(cmd)
                elif cmd['action'] == 'file_download':
                    self.send_file(client_socket, cmd['path'])
                elif cmd['action'] == 'file_upload':
                    self.receive_file(client_socket, cmd['path'], cmd['size'])
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
            print(f"Connection closed for {addr}")
    
    def authenticate_client(self, client_socket):
        """Verify client password"""
        try:
            # Receive encrypted authentication request
            auth_data = client_socket.recv(1024)
            decrypted = self.cipher.decrypt(auth_data).decode()
            auth = json.loads(decrypted)
            
            # Verify password
            if auth.get('password') == self.password:
                response = {'status': 'success'}
                encrypted = self.cipher.encrypt(json.dumps(response).encode())
                client_socket.send(encrypted)
                return True
            else:
                response = {'status': 'failed', 'reason': 'Invalid password'}
                encrypted = self.cipher.encrypt(json.dumps(response).encode())
                client_socket.send(encrypted)
                return False
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def send_screen(self, client_socket):
        """Capture and send screen to client"""
        # Capture screen
        screenshot = pyautogui.screenshot()
        screenshot = np.array(screenshot)
        
        # Compress image
        _, buffer = cv2.imencode('.jpg', screenshot, [cv2.IMWRITE_JPEG_QUALITY, 40])
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
    
    def handle_mouse(self, cmd):
        """Process mouse commands"""
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
    
    def handle_keyboard(self, cmd):
        """Process keyboard commands"""
        if cmd['type'] == 'key':
            pyautogui.press(cmd['key'])
        elif cmd['type'] == 'hotkey':
            pyautogui.hotkey(*cmd['keys'])
        elif cmd['type'] == 'write':
            pyautogui.write(cmd['text'])
    
    def send_file(self, client_socket, path):
        """Send file to client"""
        try:
            with open(path, 'rb') as file:
                file_data = file.read()
            
            # Send file size
            size = len(file_data)
            size_data = {'size': size}
            encrypted = self.cipher.encrypt(json.dumps(size_data).encode())
            client_socket.send(encrypted)
            
            # Send file data (in chunks)
            chunk_size = 4096
            for i in range(0, len(file_data), chunk_size):
                chunk = file_data[i:i+chunk_size]
                encrypted_chunk = self.cipher.encrypt(chunk)
                client_socket.send(encrypted_chunk)
        except Exception as e:
            print(f"Error sending file: {e}")
    
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
        except Exception as e:
            print(f"Error receiving file: {e}")
            response = {'status': 'error', 'message': str(e)}
            encrypted = self.cipher.encrypt(json.dumps(response).encode())
            client_socket.send(encrypted)
    
    def shutdown(self):
        """Stop the server"""
        self.running = False
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.socket.close()
        print("Server shutdown")

if __name__ == "__main__":
    server = RemoteServer()
    server.start()