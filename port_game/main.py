import tkinter as tk
from .PortGame import PortGame

if __name__ == "__main__":
    root = tk.Tk()
    game = PortGame(root)
    root.mainloop()
