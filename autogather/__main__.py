import logging
import tkinter as tk

from autogather.winutil import enable_dpi_awareness
from .ui import App


def main():
    logging.basicConfig(
        level=logging.DEBUG,  # или INFO, если надо меньше
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    enable_dpi_awareness()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
