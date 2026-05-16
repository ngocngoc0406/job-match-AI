import os
import sys
import threading

from web.app import app, init_application

if __name__ == "__main__":
    # Run initialization in a background thread so the server starts immediately.
    # The `state['is_ready']` flag in app.py guards endpoints until init completes.
    # use_reloader=False prevents Flask from forking a child process that would
    # start with a blank state (is_ready=False), causing the "still initializing" error.
    init_thread = threading.Thread(target=init_application, daemon=True)
    init_thread.start()

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)