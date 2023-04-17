from ui.main_window import App
from threading import Thread
from utils.mary_debug import run_long_task, q


if __name__ == '__main__':
    app = App()
    thr = Thread(target=run_long_task, daemon=True)
    thr.start()
    app.mainloop()
    q.put(None) # clear task wait list
