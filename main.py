import os
from web.app import app, init_application

if __name__ == "__main__":
    # Initialize the application fully before starting the server.
    # This avoids exposing endpoints before the model and graph are ready.
    init_application()

    # Read port from environment variable (default to 5000 if not set)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)