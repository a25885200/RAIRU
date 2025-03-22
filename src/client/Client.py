from lib.util import *
import tkinter as tk
import lib.LoggingHD as lg
from lib.Connection import Connection as ClientConnection # Import the correct class
from client.Client_Event_Handler import EventHandler
import Globals as gb
from client.Client_Command import CommandInvoker

class RemoteControlClient:
    def __init__(self, host='localhost', port=5000, password='secure_password', client_id=None, root=None):
        lg.logger.debug("initiating Client")
        """Initialize the Remote Control Client application"""
        self.host = host
        self.port = port
        self.password = password
        self.client_id = client_id  # Used for updating connection status
        self.conn = ClientConnection(self.host, self.port, self.password, self.client_id)  # Use the correct class
        self.socket = None
        self.connected = False
        self.cipher = None

        # Screen update settings
        self.screen_running = False     
        self.screen_thread = None
        self.update_interval = 0.1  # seconds
        self.is_screen_relative = False
        
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
        self.enable_controls(True)

        # Initialize EventHandler
        self.event_handler = EventHandler(self.conn)
        self.command_invoker = CommandInvoker(self.event_handler)
        
        # Auto-connect if parameters were provided
        if host != 'localhost' or port != 5000 or password != 'secure_password':
            self.root.after(500, self.auto_connect)
    
    def setup_gui(self):
        """Set up the GUI from XML definition"""
        try:
            # Create UI parser and parse the XML file
            xml_ui = gb.get_client_ui_xml_path()
            lg.logger.debug(f"xml_ui: {xml_ui}") 
            parser = TkUIParser(self)
            parser.parse_file(xml_ui)
            
            # Add scrollbars to canvas

            self.canvas_v_scrollbar.config(command=self.canvas.yview)
            self.canvas_h_scrollbar.config(command=self.canvas.xview)
            
            # self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
            # self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
            self.canvas.config(xscrollcommand=self.canvas_h_scrollbar.set, yscrollcommand=self.canvas_v_scrollbar.set)
            
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

    ### Other User Control    
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

    def toggle_screen_relative(self):
        self.is_screen_relative = self.is_relative_var.get()
        
    def toggle_password_visibility(self, event=None):
        """Toggle password visibility in the UI"""
        if self.show_password_var.get():
            self.pass_entry.config(show="")
        else:
            self.pass_entry.config(show="•")

    def _display_image(self, image):
        """Display an image on the canvas"""
        try:
            tk_img = PIL.ImageTk.PhotoImage(image)
            # self.canvas.delete("all")
            # self.canvas.create_image(0, 0, anchor="nw", image=tk_img)
            # self.canvas.image = tk_img  # Keep reference to prevent garbage collection
        
            # Update on main thread
            self.root.after(0, lambda: self._update_canvas(tk_img, image.width, image.height))
        except Exception as e:
            print(f"Display error: {str(e)}")

    def _update_canvas(self, tk_img, width, height):
        """Update the canvas with a new image (runs on main thread)"""
        try:
            # Clear canvas
            self.canvas.delete("all")
            
            # Determine image position
            if self.is_screen_relative:
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                x_offset = max((canvas_width - width) // 2, 0)
                y_offset = max((canvas_height - height) // 2, 0)
            else:
                x_offset, y_offset = 0, 0
            
            # Create image on canvas
            self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=tk_img)
            self.canvas.image = tk_img  # Keep reference to prevent garbage collection
            
            # Update canvas scrollregion
            self.canvas.config(scrollregion=(0, 0, width, height))
        
        except Exception as e:
            print(f"Canvas update error: {e}")
    
    def send_command(self):
        """Send a command from the command entry field"""
        command_text = self.command_entry.get().strip()
        if not command_text:
            return
        try:
            # Example: Parse command and arguments (e.g., "mouse_move 100 200")
            parts = command_text.split()
            command_name = parts[0]
            args = parts[1:]
            result_message = self.command_invoker.execute_command(command_name, *args)
            self._log_command(result_message)
        except Exception as e:
            self._log_command(f"Error executing command: {e}")
        finally:
            self.command_entry.delete(0, tk.END)

    def _log_command(self, message):
        """Log a message to the command log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.command_log_text.config(state=tk.NORMAL)
        self.command_log_text.insert(tk.END, log_message + "\n")
        self.command_log_text.see(tk.END)
        self.command_log_text.config(state=tk.DISABLED)
    
    ### Connection
    def auto_connect(self):
        """Automatically connect using provided parameters"""
        self.connect()

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
        try:
            self.conn.host = self.host_var.get().strip()
            self.conn.port = self.port_var.get()
            self.conn.password = self.password_var.get().strip()
            self.conn.client_id = self.client_id 
            
            self.status_var.set("Connecting...")
            #self.root.update()
            self.conn.connect()


            # Authenticate
            self.connected = self.conn.connected
            if self.conn.connected:
                self.status_var.set("Connected")
                self.connect_btn.config(text="Disconnect")
                self.enable_controls(True)

                # Start screen updates
                self.screen_running = True
                self.screen_thread = threading.Thread(target=self.update_screen)
                self.screen_thread.daemon = True
                self.screen_thread.start()
                
                self.log(f"Connected to {self.host}:{self.port}")
                self.conn.update_manager_connection_status(gb.get_client_data_config_path())
            
        except Exception as e:
            self.status_var.set("Connection Error")
            self.log(f"Connection error: {e}")
            tk.messagebox.showerror("Connection Error", e)

    def update_screen(self):
        """Continuously update the screen with data from the server"""
        while self.screen_running and self.connected:
            start_time = time.time()
            screen_data = self.event_handler.receive_screen()
            if not screen_data:
                break
            
            # Update remote screen dimensions
            self.remote_width = screen_data['width']
            self.remote_height = screen_data['height']

            # Update remote screen dimensions
            self.root.after(0, lambda: self.screen_size_label.config(
                text=f"Remote Screen: {screen_data['width']}x{screen_data['height']}"
            ))
            
            # Decode image
            image_data = base64.b64decode(screen_data['image'])
            
            image_tensor = torch.tensor(list(image_data), dtype=torch.uint8).cuda()
            
            # Transfer the tensor back to CPU and convert to numpy array
            image_array = image_tensor.detach().cpu().numpy()
            image_array = np.frombuffer(image_data, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR_RGB)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_img = PIL.Image.fromarray(image)
            
            # Resize image to fit canvas while maintaining aspect ratio
            if self.is_screen_relative:
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                scale = min(canvas_width / self.remote_width, canvas_height / self.remote_height)
                new_width = int(self.remote_width * scale)
                new_height = int(self.remote_height * scale)
                pil_img = pil_img.resize((new_width, new_height), PIL.Image.LANCZOS)
            
            # Display the resized image
            self._display_image(pil_img)
            
            # Calculate time to process and adjust delay
            process_time = time.time() - start_time
            delay = max(0.05, self.update_interval - process_time)
            time.sleep(delay)

    def disconnect(self):
        """Disconnect from the server"""
        self.screen_running = False  # Stop screen updates
        self.connection.disconnect()
        self.connected = False
        self.status_var.set("Disconnected")
        self.connect_btn.config(text="Connect")
        self.enable_controls(False)
        self.canvas.delete("all")
        self.screen_size_label.config(text="Remote Screen: Not connected")
        self.log("Disconnected from server")
    
    def update_manager_connection_status(self):
        """Update the connection status in the manager if client_id is set"""
        if not self.client_id:
            return
            
        try:
            # Check if clients_data.config exists
            if not os.path.exists(gb.get_client_data_config_path()):
                return
                
            # Load client data
            with open(gb.get_client_data_config_path(), 'r') as f:
                data = json.load(f)
                
            # Update last_connected for this client
            if self.client_id in data:
                data[self.client_id]["last_connected"] = datetime.now().isoformat()
                
                # Save updated data
                with open(gb.get_client_data_config_path(), 'w') as f:
                    json.dump(data, f, indent=4)
                    
                print(f"Updated connection status for client {self.client_id}")
                
        except Exception as e:
            print(f"Error updating client connection status: {e}")
    
    ### Mouse Control    
    def map_coordinates(self, x, y):
        """Map canvas coordinates to remote screen coordinates"""
        view_x = self.canvas.canvasx(x)
        view_y = self.canvas.canvasy(y)
        return int(view_x), int(view_y)

    def on_mouse_move(self, event):
        """Delegate mouse move event to EventHandler"""   
        if not self.mouse_tracking_var.get():
            return        
        x, y = self.map_coordinates(event.x, event.y)     
        self.cursor_label.config(text=f"Position: {x}, {y}")
        self.event_handler.on_mouse_move(x, y)
    
    def on_mouse_click(self, event):
        """Delegate mouse click event to EventHandler"""
        if not self.mouse_tracking_var.get():
            return        
        x, y = self.map_coordinates(event.x, event.y)     
        self.event_handler.on_mouse_click(x, y)
    
    def on_mouse_double_click(self, event):
        """Delegate mouse double click event to EventHandler"""
        if not self.mouse_tracking_var.get():
            return
        x, y = self.map_coordinates(event.x, event.y)
        self.event_handler.on_mouse_double_click(x, y)
    
    def on_mouse_drag(self, event):
        """Delegate mouse drag event to EventHandler"""
        if not self.mouse_tracking_var.get():
            return
        
        x, y = self.map_coordinates(event.x, event.y)
        self.event_handler.on_mouse_drag(x,y)
    
    def on_mouse_release(self, event):
        """Delegate mouse release event to EventHandler"""
        self.event_handler.on_mouse_release()
    
    def on_mouse_wheel(self, event):
        """Delegate mouse wheel event to EventHandler"""
        if not self.mouse_tracking_var.get():
            return
        
        amount = event.delta // 120
        self.event_handler.on_mouse_wheel(amount)
    
    ###KeyBoard Control
    def on_key_press(self, event):
        """Delegate key press event to EventHandler"""
        if not self.keyboard_input_var.get():
            return        
        key = event.keysym        
        modifiers = []
        if event.state & 0x4:
            modifiers.append('ctrl')
        if event.state & 0x8:
            modifiers.append('alt')
        if event.state & 0x1:
            modifiers.append('shift')
        self.event_handler.on_key_press(key, modifiers)
    
    def send_text(self):
        """Send text from the text input field"""
        if not self.connected:
            return
        text = self.text_input.get()
        self.event_handler.send_text(text)
        self.text_input.delete(0, tk.END)

    def upload_file(self):
        """Delegate file upload to EventHandler"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        self.event_handler.upload_file()

    def download_file(self):
        """Delegate file download to EventHandler"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        self.event_handler.download_file()

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
        if self.conn.connected:
            if messagebox.askyesno("Confirm Exit", "You are still connected. Disconnect and exit?"):
                gb.sub_public_current_client()
                self.conn.disconnect()
                self.root.destroy()
        else:
            gb.sub_public_current_client()
            self.root.destroy()
    
    def run(self):
        """Run the client application"""
        self.root.mainloop()

if __name__ == "__main__":
    lg.logger.debug("Parse Client arguments")
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

    lg.logger.debug("calling RemoteControlClient.run()")
    client.run()