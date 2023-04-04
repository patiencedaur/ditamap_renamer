from ui.main_window import App
from utils.mary_debug import logger, MaryLogHandler

if __name__ == '__main__':
    app = App()

    log_handler = MaryLogHandler(app)
    logger.addHandler(log_handler)

    app.mainloop()
