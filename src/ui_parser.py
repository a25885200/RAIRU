from util import *
import tkinter as tk
import xml.etree.ElementTree as et

class TkUIParser:
    """
    XML-based UI parser for Tkinter applications.
    Creates Tkinter UI elements from XML definitions.
    """
    def __init__(self, app_instance):
        """
        Initialize the parser with the application instance.
        
        Args:
            app_instance: The application instance that will handle events
        """
        self.app = app_instance
        self.widget_map = {}
        self.var_map = {}

    
    def parse_file(self, filename):
        """
        Parse an XML file and create the UI.
        
        Args:
            filename: Path to the XML file
            
        Returns:
            The root window
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"UI XML file not found: {filename}")
        
        try:
            tree = et.parse(filename)
            root = tree.getroot()
            
            # Process app-level attributes
            app_element = root.find("application")
            if app_element is not None:
                self._process_application(app_element)
            
            # Process UI elements
            ui_element = root.find("ui")
            if ui_element is not None:
                self._process_ui_elements(ui_element)
            
            return self.app.root
                
        except Exception as e:
            print(f"Error parsing XML file {filename}: {str(e)}")
            traceback.print_exc()
            raise
    
    def _process_application(self, app_element):
        """Process application-level settings"""
        title = app_element.get("title", "Application")
        geometry = app_element.get("geometry", "800x600")
        min_width = app_element.get("min-width")
        min_height = app_element.get("min-height")
        
        # Set application properties
        self.app.root.title(title)
        self.app.root.geometry(geometry)
        
        if min_width and min_height:
            self.app.root.minsize(int(min_width), int(min_height))
    
    def _process_ui_elements(self, parent_element, parent_widget=None):
        """
        Recursively process UI elements and create widgets.
        
        Args:
            parent_element: The parent XML element
            parent_widget: The parent Tkinter widget
        """
        if parent_widget is None:
            parent_widget = self.app.root
        
        for element in parent_element:
            widget_type = element.tag.lower()
            widget_id = element.get("id")
            
            if widget_type == "var":
                self._create_variable(element)
                continue
                
            widget = self._create_widget(widget_type, element, parent_widget)
            
            if widget_id:
                self.widget_map[widget_id] = widget
                
                # Add as attribute to app instance for direct access if needed
                if not hasattr(self.app, widget_id):
                    setattr(self.app, widget_id, widget)
            
            # Process child elements recursively
            self._process_ui_elements(element, widget)
    
    def _create_variable(self, element):
        """Create a Tkinter variable"""
        var_id = element.get("id")
        var_type = element.get("type", "string").lower()
        initial_value = element.get("value", "")
        
        if var_type == "string":
            var = tk.StringVar(value=initial_value)
        elif var_type == "int":
            var = tk.IntVar(value=int(initial_value) if initial_value else 0)
        elif var_type == "double" or var_type == "float":
            var = tk.DoubleVar(value=float(initial_value) if initial_value else 0.0)
        elif var_type == "boolean" or var_type == "bool":
            var = tk.BooleanVar(value=initial_value.lower() in ("true", "1", "yes"))
        else:
            var = tk.StringVar(value=initial_value)
        
        if var_id:
            self.var_map[var_id] = var
            
            # Add as attribute to app instance
            if not hasattr(self.app, var_id):
                setattr(self.app, var_id, var)
    
    def _create_widget(self, widget_type, element, parent):
        """Create a Tkinter widget based on its type"""
        widget = None
        attributes = self._get_widget_attributes(element)
        
        # Create widget based on type
        if widget_type == "frame":
            widget = self._create_frame(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "labelframe":
            widget = self._create_labelframe(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "label":
            widget = self._create_label(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "button":
            widget = self._create_button(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "entry":
            widget = self._create_entry(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "combobox":
            widget = self._create_combobox(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "checkbutton":
            widget = self._create_checkbutton(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "radiobutton":
            widget = self._create_radiobutton(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "scale":
            widget = self._create_scale(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "listbox":
            widget = self._create_listbox(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "scrolledtext":
            widget = self._create_scrolledtext(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "canvas":
            widget = self._create_canvas(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "separator":
            widget = self._create_separator(parent, self.filter_attributes(widget_type, attributes))
        elif widget_type == "scrollbar":
            widget = self._create_scrollbar(parent, self.filter_attributes(widget_type, attributes))
        else:
            print(f"Unknown widget type: {widget_type}")
            return None
        
        # Apply layout
        self._apply_layout(widget, element)
        
        # Apply event bindings
        self._apply_bindings(widget, element)
        
        return widget
    
    
    def _get_widget_attributes(self, element):
        """Extract widget attributes from XML element"""
        attributes = {}
        for key, value in element.attrib.items():
            # Convert variable references to actual variables
            if key == "textvariable" or key == "variable":
                if value in self.var_map:
                    attributes[key] = self.var_map[value]
                else:
                    print(f"Warning: Variable {value} not found")
            elif key == "command":
                # Handle command callbacks
                if hasattr(self.app, value):
                    attributes[key] = getattr(self.app, value)
                else:
                    print(f"Warning: Command {value} not found in app instance")
            else:
                attributes[key] = value
        
        return attributes
    
    def _apply_layout(self, widget, element):
        """Apply layout manager settings to the widget"""
        layout = element.get("layout", "pack")
        
        if layout == "pack":
            pack_options = {}
            
            for key in ["side", "fill", "expand", "padx", "pady", "ipadx", "ipady", "anchor"]:
                if key in element.attrib:
                    value = element.get(key)
                    
                    # Convert string values to proper types
                    if key == "expand":
                        value = value.lower() in ("true", "1", "yes")
                    elif key in ["padx", "pady", "ipadx", "ipady"]:
                        if "," in value:
                            # Handle tuple values like padx="10,20"
                            parts = value.split(",")
                            value = (int(parts[0]), int(parts[1]))
                        else:
                            value = int(value)
                    
                    pack_options[key] = value
            
            widget.pack(**pack_options)
            
        elif layout == "grid":
            grid_options = {}
            
            for key in ["row", "column", "rowspan", "columnspan", "padx", "pady", 
                       "ipadx", "ipady", "sticky"]:
                if key in element.attrib:
                    value = element.get(key)
                    
                    # Convert string values to proper types
                    if key in ["row", "column", "rowspan", "columnspan"]:
                        value = int(value)
                    elif key in ["padx", "pady", "ipadx", "ipady"]:
                        if "," in value:
                            # Handle tuple values like padx="10,20"
                            parts = value.split(",")
                            value = (int(parts[0]), int(parts[1]))
                        else:
                            value = int(value)
                    
                    grid_options[key] = value
            
            widget.grid(**grid_options)
            
        elif layout == "place":
            place_options = {}
            
            for key in ["x", "y", "relx", "rely", "width", "height", 
                       "relwidth", "relheight", "anchor"]:
                if key in element.attrib:
                    value = element.get(key)
                    
                    # Convert string values to proper types
                    if key in ["x", "y", "width", "height"]:
                        value = int(value)
                    elif key in ["relx", "rely", "relwidth", "relheight"]:
                        value = float(value)
                    
                    place_options[key] = value
            
            widget.place(**place_options)
    
    def _apply_bindings(self, widget, element):
        """Apply event bindings to the widget"""
        for binding in element.findall("bind"):
            event = binding.get("event")
            handler = binding.get("handler")
            
            if event and handler and hasattr(self.app, handler):
                widget.bind(event, getattr(self.app, handler))
            elif event and handler:
                print(f"Warning: Event handler {handler} not found in app instance")
    
    def _create_frame(self, parent, attributes):
        """Create a Frame widget"""
        # Extract special attributes
        width = attributes.pop("width", None)
        height = attributes.pop("height", None)
        # Define the keys you want to keep
        allowed_keys = ['padding', 'width', 'height', 'style', 'cursor','background']
        # Filter the attributes
        filtered_attributes = {k: v for k, v in attributes.items() if k in allowed_keys}

        frame = ttk.Frame(parent, **attributes)
        
        if width or height:
            if width:
                frame.config(width=int(width))
            if height:
                frame.config(height=int(height))
            frame.pack_propagate(False)
        
        return frame
    
    def _create_labelframe(self, parent, attributes):
        """Create a LabelFrame widget"""
        # Extract special attributes
        text = attributes.pop("text", "")
        width = attributes.pop("width", None)
        height = attributes.pop("height", None)
        
        frame = ttk.LabelFrame(parent, text=text, **attributes)
        
        if width or height:
            if width:
                frame.config(width=int(width))
            if height:
                frame.config(height=int(height))
            frame.pack_propagate(False)
        
        return frame
    
    def _create_label(self, parent, attributes):
        """Create a Label widget"""
        text = attributes.pop("text", "")
        return ttk.Label(parent, text=text, **attributes)
    
    def _create_button(self, parent, attributes):
        """Create a Button widget"""
        text = attributes.pop("text", "")
        return ttk.Button(parent, text=text, **attributes)
    
    def _create_entry(self, parent, attributes):
        """Create an Entry widget"""
        return ttk.Entry(parent, **attributes)
    
    def _create_combobox(self, parent, attributes):
        """Create a Combobox widget"""
        # Handle values list
        values_str = attributes.pop("values", "")
        values = [v.strip() for v in values_str.split(",")] if values_str else []
        
        combo = ttk.Combobox(parent, values=values, **attributes)
        return combo
    
    def _create_checkbutton(self, parent, attributes):
        """Create a Checkbutton widget"""
        text = attributes.pop("text", "")
        return ttk.Checkbutton(parent, text=text, **attributes)
    
    def _create_radiobutton(self, parent, attributes):
        """Create a Radiobutton widget"""
        text = attributes.pop("text", "")
        value = attributes.pop("value", "")
        
        return ttk.Radiobutton(parent, text=text, value=value, **attributes)
    
    def _create_scale(self, parent, attributes):
        """Create a Scale widget"""
        # Extract numeric attributes
        from_val = float(attributes.pop("from", 0))
        to_val = float(attributes.pop("to", 100))
        orient_val = attributes.pop("orient", "horizontal")
        
        return ttk.Scale(parent, from_=from_val, to=to_val, orient=orient_val, **attributes)
    
    def _create_listbox(self, parent, attributes):
        """Create a Listbox widget"""
        height = int(attributes.pop("height", 10))
        listbox = tk.Listbox(parent, height=height, **attributes)
        
        # Add scrollbar if specified
        if attributes.get("scrollbar", "false").lower() in ("true", "1", "yes"):
            scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=listbox.yview)
            listbox.config(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
        return listbox
    
    def _create_scrolledtext(self, parent, attributes):
        """Create a ScrolledText widget"""
        wrap = attributes.pop("wrap", "word")
        height = int(attributes.pop("height", 10))
        
        text_widget = scrolledtext.ScrolledText(
            parent, wrap=wrap, height=height, **attributes
        )
        
        return text_widget
    
    def _create_canvas(self, parent, attributes):
        """Create a Canvas widget"""
        # Extract special attributes
        width = int(attributes.pop("width", 400))
        height = int(attributes.pop("height", 300))
        bg = attributes.pop("bg", "white")
        
        canvas = tk.Canvas(parent, width=width, height=height, bg=bg, **attributes)
        
        # Add scrollbars if specified
        if attributes.get("scrollbar", "false").lower() in ("true", "1", "yes"):
            h_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=canvas.xview)
            v_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
            
            canvas.config(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
            
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return canvas
    
    def _create_separator(self, parent, attributes):
        """Create a Separator widget"""
        orient_val = attributes.pop("orient", "horizontal")
        return ttk.Separator(parent, orient=orient_val, **attributes)
    
    def _create_scrollbar(self, parent, attributes):
        """Create a Scrollbar widget"""
        # Create the Scrollbar with the filtered attributes
        scrollbar = ttk.Scrollbar(parent, **attributes)
        return scrollbar
    
    def get_widget(self, widget_id):
        """Get a widget by its ID"""
        return self.widget_map.get(widget_id)
    
    def get_variable(self, var_id):
        """Get a variable by its ID"""
        return self.var_map.get(var_id)
    
    def filter_attributes(self, widget_type, attributes):
        allowed_keys = {
            "frame": ['padding', 'width', 'height', 'style'],
            "labelframe": ['text', 'labelanchor', 'padding', 'style', 'width', 'height'],
            "label": ['text', 'image', 'compound', 'padding', 'style', 'anchor', 'width', 'height'],
            "button": ['text', 'command', 'image', 'compound', 'padding', 'style', 'width', 'height'],
            "entry": ['textvariable', 'show', 'width', 'justify', 'style', 'validate', 'validatecommand'],
            "combobox": ['values', 'textvariable', 'state', 'width', 'height', 'style'],
            "checkbutton": ['text', 'variable', 'command', 'padding', 'style', 'onvalue', 'offvalue'],
            "radiobutton": ['text', 'variable', 'value', 'command', 'padding', 'style'],
            "scale": ['from_', 'to', 'orient', 'variable', 'length', 'tickinterval', 'resolution', 'style'],
            "listbox": ['listvariable', 'height', 'width', 'selectmode', 'selectbackground', 'font','scrollbar'],
            "scrolledtext": ['wrap', 'width', 'height', 'font', 'bg', 'fg'],
            "canvas": ['width', 'height', 'bg', 'borderwidth', 'highlightthickness', 'scrollregion','scrollbar'],
            "separator": ['orient', 'style']
            #"scrollbar": ['command', 'orient', 'length', 'width', 'style']
        }
        # Filter the attributes based on the widget type
        return {k: v for k, v in attributes.items() if k in allowed_keys.get(widget_type, [])}
    