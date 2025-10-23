import logging
import tkinter as tk

from autogather.ui.ui import App


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
