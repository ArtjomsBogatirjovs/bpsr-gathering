import logging
import tkinter as tk

from .ui import App


def main():
    logging.basicConfig(
        level=logging.DEBUG,  # или INFO, если надо меньше
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
