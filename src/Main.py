import tkinter as tk
from tkinter import messagebox

class MainUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RAIRU Main UI")
        self.root.geometry("400x300")

        # Create a label
        self.label = tk.Label(root, text="Welcome to RAIRU!", font=("Arial", 16))
        self.label.pack(pady=20)

        # Create a button
        self.button = tk.Button(root, text="Click Me", command=self.on_button_click)
        self.button.pack(pady=10)

    def on_button_click(self):
        messagebox.showinfo("Info", "Button clicked!")

if __name__ == "__main__":
    root = tk.Tk()
    app = MainUI(root)
    root.mainloop()