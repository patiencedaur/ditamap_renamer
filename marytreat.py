from ui.main_window import App
from utils.mary_debug import DebugWindowLogHandler


if __name__ == '__main__':
    app = App()
    log_handler = DebugWindowLogHandler(app.debug_window.text)
    app.mainloop()
