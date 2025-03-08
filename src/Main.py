
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import os
import lib.Server as sc
import lib.Client as cc

class MainUI:
    form = tk.Tk()

    def __init__(self, xml_file):
        root = self.load_ui_from_xml(xml_file)
        if root == 0 : return None

        title = root.find('title').text
        button_text = root.find('button/text').text

        # Get resolution if needed
        width = int(root.find('resolution/width').text)
        height = int(root.find('resolution/height').text)

        self.form.title(title)
        self.form.geometry("400x300")  # Default geometry
        self.form.geometry(f"{width}x{height}")  # Set geometry from XML

        # Create a label
        label = tk.Label(self.form, text="Welcome to RAIRU!", font=("Arial", 16))
        label.pack(pady=20)

        # Create a button to show resolution
        res_button = tk.Button(self.form, text="Get Resolution", command=self.show_resolution)
        res_button.pack(pady=10)

        # Create a button based on XML data
        button = tk.Button(self.form, text=button_text, command=self.on_button_click)
        button.pack(pady=10)    

        

    def on_button_click(self):
        appClient = cc.RemoteClient()
        appClient.save_to_xml()
        appClient.run()



    def show_resolution(self):
        width = self.form.winfo_screenwidth()
        height = self.form.winfo_screenheight()
        messagebox.showinfo("Screen Resolution", f"Current Resolution: {width}x{height}")

    def load_ui_from_xml(self, xml_file):
        #xml_file = 'J://Remote Control Software//Master//dev_rairu//RAIRU//assets//forms//form_Main.xml'
        print(xml_file)
        if not os.path.exists(xml_file):
            print(f"File not found: {xml_file}")
            return 0,0,0,0
        else:
            print(f"File found: {xml_file}")
            # Proceed to parse the XML
            tree = ET.parse(xml_file)
        root = tree.getroot()

        return root


if __name__ == "__main__":

    xml_file = os.path.join(r'.','assets','forms','form_Main.xml' )
    #print(xml_file)
    #xml_file = os.path.abspath(xml_file)
    #print(os.path.isdir(xml_file))

    app = MainUI(xml_file)
    server = sc.RemoteServer()

    if app == None : 
        exit
    app.form.mainloop()
