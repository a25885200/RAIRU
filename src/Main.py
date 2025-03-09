import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import datetime
import sys
import platform
import psutil  
from ui_parser import TkUIParser
import Globals as gb
import LoggingHD as lg
import multiprocessing

class ClientData:
    """Class to hold client connection data"""
    def __init__(self, nickname="", host="", port=5000, password="", notes="", last_connected=None):
        self.nickname = nickname
        self.host = host
        self.port = port
        self.password = password
        self.notes = notes
        self.last_connected = last_connected  # datetime or None
        
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "nickname": self.nickname,
            "host": self.host,
            "port": self.port,
            "password": self.password,
            "notes": self.notes,
            "last_connected": self.last_connected.isoformat() if self.last_connected else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create ClientData object from dictionary"""
        client = cls(
            nickname=data.get("nickname", ""),
            host=data.get("host", ""),
            port=data.get("port", 5000),
            password=data.get("password", ""),
            notes=data.get("notes", "")
        )
        
        # Parse last_connected if it exists
        last_conn = data.get("last_connected")
        if last_conn:
            try:
                client.last_connected = datetime.datetime.fromisoformat(last_conn)
            except (ValueError, TypeError):
                client.last_connected = None
                
        return client
    
    def display_name(self):
        """Get display name for list"""
        if self.nickname:
            return f"{self.nickname} ({self.host}:{self.port})"
        return f"{self.host}:{self.port}"


class RemoteControlManager:
    def __init__(self):        
        lg.logger.debug("Initializing RemoteControlManager")
        """Initialize the Remote Control Manager application""" 
        multiprocessing.get_start_method("spawn")
        multiprocessing.freeze_support()
        multiprocessing.allow_connection_pickling()
        self.result_piep = multiprocessing.Pipe 
        self.result_queue = multiprocessing.Queue()
        self.config_file = gb.get_client_data_config_path()
        self.clients = {}  # Dictionary of ClientData objects
        self.current_edit_id = None  # ID of client being edited
        self.editing_new = False  # Whether we're editing a new client
        self.client_process = None
        self.server_process = None
        
        # Server process tracking
        self.opened_server = None
        self.opend_client = set()
        
        # Create the root Tkinter window
        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create UI from XML definition
        self.setup_gui()
        
        # Load saved clients
        self.load_clients()
        # Set up the UI with initial state
        self.setup_listbox()
        self.update_client_count()
        self.set_details_state(tk.DISABLED)
        
        # Update server status periodically
        self.check_server_status()
    
    def setup_gui(self):
        """Set up the GUI from XML definition"""
        try:
            # Create UI parser and parse the XML file
            xml_ui = gb.get_main_ui_xml_path()
            lg.logger.debug(f"xml_ui: {xml_ui}")    
            parser = TkUIParser(self)
            parser.parse_file(xml_ui)
            
            # Configure the listbox and scrollbar
            self.clients_listbox.config(yscrollcommand=self.list_scrollbar.set)
            self.list_scrollbar.config(command=self.clients_listbox.yview)
            
            # Bind events
            self.clients_listbox.bind("<<ListboxSelect>>", self.on_client_select)
            self.search_entry.bind("<Return>", lambda e: self.search_clients())
            
            # Set status
            self.status_var.set("Ready")
            self.server_status_var.set("Server: Not Running")
            
            # version label
            self.version_label.config(text=gb.get_application_name() + " : v" + gb.get_application_version())
        
            
        except Exception as e:
            print(f"Error setting up GUI: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load UI: {str(e)}")
    
    def load_clients(self):
        """Load client data from config file"""
        self.clients = {}
        
        if not os.path.exists(self.config_file):
            print(f"Config file not found, will create a new one when clients are saved")
            return
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                
            for client_id, client_data in data.items():
                self.clients[client_id] = ClientData.from_dict(client_data)
                
            print(f"Loaded {len(self.clients)} clients from config")
            
        except Exception as e:
            print(f"Error loading clients: {e}")
            messagebox.showerror("Error", f"Failed to load client data: {str(e)}")
    
    def save_clients(self):
        """Save all clients to config file"""
        try:
            data = {client_id: client.to_dict() for client_id, client in self.clients.items()}
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
                
            print(f"Saved {len(self.clients)} clients to config")
            self.status_var.set(f"Saved {len(self.clients)} clients to config")
            
        except Exception as e:
            print(f"Error saving clients: {e}")
            messagebox.showerror("Error", f"Failed to save client data: {str(e)}")
    
    def setup_listbox(self):
        """Set up the clients listbox with all clients"""
        self.clients_listbox.delete(0, tk.END)
        
        # Sort clients by nickname/host
        sorted_clients = sorted(
            self.clients.items(), 
            key=lambda x: x[1].display_name().lower()
        )
        
        for client_id, client in sorted_clients:
            self.clients_listbox.insert(tk.END, client.display_name())
    
    def update_client_count(self):
        """Update the client count label"""
        count = len(self.clients)
        self.client_count_label.config(text=f"Clients: {count}")
    
    def on_client_select(self, event=None):
        """Handle client selection from the listbox"""
        selection = self.clients_listbox.curselection()
        if not selection:
            return
        
        # Get the client ID from the sorted list position
        sorted_clients = sorted(
            self.clients.items(), 
            key=lambda x: x[1].display_name().lower()
        )
        
        if selection[0] < len(sorted_clients):
            client_id, client = sorted_clients[selection[0]]
            self.selected_client_var.set(client_id)
            self.display_client_details(client)
    
    def display_client_details(self, client):
        """Display the selected client's details in the form"""
        # Set form fields
        self.nickname_entry.delete(0, tk.END)
        self.nickname_entry.insert(0, client.nickname)
        
        self.host_entry.delete(0, tk.END)
        self.host_entry.insert(0, client.host)
        
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, str(client.port))
        
        self.password_entry.delete(0, tk.END)
        self.password_entry.insert(0, client.password)
        
        self.notes_text.config(state=tk.NORMAL)
        self.notes_text.delete(1.0, tk.END)
        self.notes_text.insert(tk.END, client.notes)
        self.notes_text.config(state=tk.DISABLED)
        
        # Set last connected label
        if client.last_connected:
            formatted_date = client.last_connected.strftime("%Y-%m-%d %H:%M:%S")
            self.last_conn_label.config(text=formatted_date)
        else:
            self.last_conn_label.config(text="Never")
    
    def set_details_state(self, state):
        """Enable or disable detail form fields"""
        self.nickname_entry.config(state=state)
        self.host_entry.config(state=state)
        self.port_entry.config(state=state)
        self.password_entry.config(state=state)
        self.notes_text.config(state=state)
        self.save_btn.config(state=state)
        self.cancel_btn.config(state=state)
        self.show_pass_check.config(state=state)
    
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        current = self.password_entry.cget("show")
        self.password_entry.config(show="" if current else "•")
    
    def search_clients(self):
        """Search clients by name or host"""
        search_text = self.search_var.get().lower()
        
        if not search_text:
            # If search is empty, show all clients
            self.setup_listbox()
            return
        
        # Clear the listbox
        self.clients_listbox.delete(0, tk.END)
        
        # Filter and sort clients
        filtered_clients = [
            (client_id, client) for client_id, client in self.clients.items()
            if search_text in client.display_name().lower()
        ]
        
        sorted_clients = sorted(
            filtered_clients, 
            key=lambda x: x[1].display_name().lower()
        )
        
        # Add matching clients to listbox
        for client_id, client in sorted_clients:
            self.clients_listbox.insert(tk.END, client.display_name())
        
        # Update status
        self.status_var.set(f"Found {len(sorted_clients)} matching clients")
    
    def new_client(self):
        """Create a new client"""
        # Enable the form
        self.set_details_state(tk.NORMAL)
        
        # Clear form fields
        self.nickname_entry.delete(0, tk.END)
        self.host_entry.delete(0, tk.END)
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, "5000")
        self.password_entry.delete(0, tk.END)
        self.password_entry.config(show="•")
        self.notes_text.delete(1.0, tk.END)
        self.last_conn_label.config(text="Never")
        
        # Set flags
        self.editing_new = True
        self.current_edit_id = None
        
        # Focus nickname field
        self.nickname_entry.focus_set()
    
    def edit_client(self):
        """Edit the selected client"""
        selection = self.clients_listbox.curselection()
        if not selection:
            messagebox.showinfo("Information", "Please select a client to edit")
            return
        
        # Get the client ID from the sorted list position
        sorted_clients = sorted(
            self.clients.items(), 
            key=lambda x: x[1].display_name().lower()
        )
        
        if selection[0] < len(sorted_clients):
            client_id, client = sorted_clients[selection[0]]
            self.current_edit_id = client_id
            self.editing_new = False
            
            # Display the client details and enable form
            self.display_client_details(client)
            self.set_details_state(tk.NORMAL)
            self.notes_text.config(state=tk.NORMAL)
            
            # Focus nickname field
            self.nickname_entry.focus_set()
    
    def delete_client(self):
        """Delete the selected client"""
        selection = self.clients_listbox.curselection()
        if not selection:
            messagebox.showinfo("Information", "Please select a client to delete")
            return
        
        # Get the client ID from the sorted list position
        sorted_clients = sorted(
            self.clients.items(), 
            key=lambda x: x[1].display_name().lower()
        )
        
        if selection[0] < len(sorted_clients):
            client_id, client = sorted_clients[selection[0]]
            
            # Confirm deletion
            display_name = client.display_name()
            confirm = messagebox.askyesno(
                "Confirm Deletion", 
                f"Are you sure you want to delete client '{display_name}'?"
            )
            
            if confirm:
                # Delete the client
                del self.clients[client_id]
                
                # Update UI
                self.setup_listbox()
                self.update_client_count()
                self.save_clients()
                
                # Clear and disable form
                self.nickname_entry.delete(0, tk.END)
                self.host_entry.delete(0, tk.END)
                self.port_entry.delete(0, tk.END)
                self.password_entry.delete(0, tk.END)
                self.notes_text.config(state=tk.NORMAL)
                self.notes_text.delete(1.0, tk.END)
                self.notes_text.config(state=tk.DISABLED)
                self.last_conn_label.config(text="")
                
                self.status_var.set(f"Deleted client '{display_name}'")
    
    def save_client(self):
        """Save the current client data from the form"""
        # Validate input
        host = self.host_entry.get().strip()
        if not host:
            messagebox.showerror("Error", "Host cannot be empty")
            return
        
        try:
            port = int(self.port_entry.get())
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid port: {str(e)}")
            return
        
        # Create client data object
        nickname = self.nickname_entry.get().strip()
        password = self.password_entry.get()
        notes = self.notes_text.get(1.0, tk.END).strip()
        
        client = ClientData(
            nickname=nickname,
            host=host,
            port=port,
            password=password,
            notes=notes
        )
        
        # If editing existing client, preserve the last_connected timestamp
        if not self.editing_new and self.current_edit_id in self.clients:
            client.last_connected = self.clients[self.current_edit_id].last_connected
        
        # Generate a new ID for new clients
        if self.editing_new:
            # Use timestamp + host:port as a unique ID
            client_id = f"{datetime.datetime.now().timestamp()}-{host}-{port}"
        else:
            client_id = self.current_edit_id
        
        # Save the client
        self.clients[client_id] = client
        
        # Update UI
        self.setup_listbox()
        self.update_client_count()
        self.save_clients()
        
        # Disable form
        self.set_details_state(tk.DISABLED)
        self.notes_text.config(state=tk.DISABLED)
        
        # Reset edit flags
        self.editing_new = False
        self.current_edit_id = None
        
        # Update status
        display_name = client.display_name()
        self.status_var.set(f"Saved client '{display_name}'")
    
    def cancel_edit(self):
        """Cancel the current client edit"""
        # Disable form
        self.set_details_state(tk.DISABLED)
        self.notes_text.config(state=tk.DISABLED)
        
        # If we were editing an existing client, restore its details
        if not self.editing_new and self.current_edit_id in self.clients:
            self.display_client_details(self.clients[self.current_edit_id])
        else:
            # Clear form
            self.nickname_entry.delete(0, tk.END)
            self.host_entry.delete(0, tk.END)
            self.port_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
            self.notes_text.delete(1.0, tk.END)
            self.last_conn_label.config(text="")
        
        # Reset edit flags
        self.editing_new = False
        self.current_edit_id = None
        
        # Update status
        self.status_var.set("Edit cancelled")
    
    def connect_client(self):        
        lg.logger.debug("button connect_client clicked")
        """Connect to the selected client"""
        selection = self.clients_listbox.curselection()
        if not selection:
            messagebox.showinfo("Information", "Please select a client to connect to")
            return
        
        # Get the client ID from the sorted list position
        sorted_clients = sorted(
            self.clients.items(), 
            key=lambda x: x[1].display_name().lower()
        )
        
        if selection[0] < len(sorted_clients):
            client_id, client = sorted_clients[selection[0]]
            
            # Update status
            display_name = client.display_name()
            self.status_var.set(f"Connecting to '{display_name}'...")
            self.root.update()
            
            try:
                """Check number of opened client form"""
                if gb.get_public_current_client() >= gb.get_max_client():
                    messagebox.showinfo("Information", "You can't open more than " + gb.get_max_client() + " clients")
                    return
                
                new_client_form = multiprocessing.Process(target=open_client_form, args=(client,client_id))                
                lg.logger.debug(f"{new_client_form.name} :({new_client_form.pid})")
                new_client_form.start()
                new_client_form.join(3)


                gb.add_public_current_client()
                lg.logger.debug(f"public_current_client: {gb.get_public_current_client()}")

                # Set last connected timestamp
                client.last_connected = datetime.datetime.now()
                self.last_conn_label.config(text=client.last_connected.strftime("%Y-%m-%d %H:%M:%S"))
                
                # Save clients to update last_connected
                self.save_clients()
                
                # Update status
                self.status_var.set(f"Connected to '{display_name}'")
                
            except Exception as e:
                print(f"Error launching client: {e}")
                messagebox.showerror("Error", f"Failed to launch client: {str(e)}")
                self.status_var.set(f"Error connecting to '{display_name}'")


    def update_client_connection_success(self, client_id):
        """Update the last connected time for a client after successful connection"""
        if client_id in self.clients:
            # Update the timestamp
            self.clients[client_id].last_connected = datetime.datetime.now()
            
            # Update UI if this client is selected
            if self.selected_client_var.get() == client_id:
                formatted_date = self.clients[client_id].last_connected.strftime("%Y-%m-%d %H:%M:%S")
                self.last_conn_label.config(text=formatted_date)
            
            # Save clients
            self.save_clients()
    
    def toggle_server(self):
        """Start or stop the server"""
        if self.is_server_running():
            # If server is running, try to focus its window
            self.focus_server_window()
        else:
            # If server is not running, start it
            self.start_server()
    
    def is_server_running(self):
        """Check if the server process is still running"""
        if self.server_process is None:
            return False
            
        try:
            # Check if process is still running
            if isinstance(self.server_process, int):
                # Process ID case
                return psutil.pid_exists(self.server_process)
            else:
                # Subprocess.Popen case
                return self.server_process.poll() is None
        except:
            return False
    
    def start_server(self):        
        lg.logger.debug("button start_server clicked")
        """Start the server application"""
        try:
            # Launch the server in a new process
            self.status_var.set("Starting server...")
            self.root.update()

            new_server_form = multiprocessing.Process(target=open_server_form)            
            lg.logger.debug(f"{new_server_form.name} :({new_server_form.pid})")
            new_server_form.start()
            self.server_process = new_server_form.pid 
            print(self.server_process)
            new_server_form.join(3)

            # Update UI
            self.server_status_var.set("Server: Running")
            self.server_btn.config(text="Focus Server")
            self.status_var.set("Server started successfully")
            
        except Exception as e:
            print(f"Error starting server: {e}")
            messagebox.showerror("Error", f"Failed to start server: {str(e)}")
            self.status_var.set("Failed to start server")
            self.opened_server = None

    def focus_server_window(self):
        """Try to focus the server window if it's running"""
        # This is platform-specific and might not work in all environments
        try:
            if platform.system() == "Windows":
                # On Windows, we can use the win32gui module to find and focus the window
                try:
                    import win32gui
                    import win32con
                    
                    def callback(hwnd, extra):
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if "Remote Control Server" in title:
                                # Found the server window, bring it to front
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                win32gui.SetForegroundWindow(hwnd)
                                return False  # Stop enumeration
                        return True  # Continue enumeration
                    
                    win32gui.EnumWindows(callback, None)
                    
                except ImportError:
                    # win32gui not available, show message to user
                    messagebox.showinfo("Server Running", "The server is already running.")
            else:
                # On other platforms, just show a message
                messagebox.showinfo("Server Running", "The server is already running.")
                
        except Exception as e:
            print(f"Error focusing server window: {e}")
            messagebox.showinfo("Server Running", "The server is already running but couldn't be focused.")
    
    def check_server_status(self):
        """Periodically check if the server is still running and update UI"""
        if self.is_server_running():
            self.server_status_var.set("Server: Running")
            self.server_btn.config(text="Focus Server")
        else:
            self.server_status_var.set("Server: Not Running")
            self.server_btn.config(text="Start Server")
            self.opened_server = None
            
        # Schedule next check after 2 seconds
        self.root.after(2000, self.check_server_status)
    
    def stop_server(self):
        """Stop the server if it's running"""
        if not self.is_server_running():
            return
            
        try:
            # Get the process
            if isinstance(self.server_process, int):
                # We have a process ID
                process = psutil.Process(self.server_process)
                
                # Try to terminate gracefully first
                process.terminate()
                
                # Wait a bit and kill if still running
                try:
                    process.wait(timeout=3)
                except psutil.TimeoutExpired:
                    process.kill()
            else:
                # We have a Popen object
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=3)
                except:
                    self.server_process.kill()
                    
            # Update UI
            self.server_status_var.set("Server: Not Running")
            self.server_btn.config(text="Start Server")
            self.server_process = None
            
        except Exception as e:
            print(f"Error stopping server: {e}")

    def on_close(self):
        """Handle window close event"""
        # Save any unsaved changes
        self.save_clients()
        
        # Stop the server if it's running
        self.stop_server()
        
        self.root.destroy()
    
    def run(self):
        """Run the manager application"""
        self.root.mainloop()

def open_client_form(client,client_id):
    
    # Determine the correct path to Client.py
    if getattr(sys, 'frozen', False):
        # If running as a bundled executable
        base_path = sys._MEIPASS
    else:
        # If running as a script
        base_path = os.path.dirname(__file__)
    
    client_script = os.path.join(base_path, "Client.py")
    lg.logger.debug(f"client_script: {client_script}")
    
    # Function to run the client script
    cmd = [
        sys.executable, client_script,
        "--host", client.host,
        "--port", str(client.port),
        "--password", client.password,
        "--client-id", client_id
    ]
    lg.logger.debug(f"cmd: {cmd}")             
    subprocess.run(cmd)

def open_server_form():
    # Determine the correct path to Server.py
    if getattr(sys, 'frozen', False):
        # If running as a bundled executable
        base_path = sys._MEIPASS
    else:
        # If running as a script
        base_path = os.path.dirname(__file__)
    
    server_script = os.path.join(base_path, "Server.py")
    lg.logger.debug(f"server_script: {server_script}")       
    cmd = [sys.executable, server_script]
    lg.logger.debug(f"cmd: {cmd}")
    subprocess.run(cmd)

if __name__ == "__main__":
    
    multiprocessing.freeze_support()
    lg.logger.debug("Main.main() called")
    manager = RemoteControlManager()    
    lg.logger.debug("calling RemoteControlManager.run()")
    manager.run()