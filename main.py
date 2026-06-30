"""
MicMaster Pro — Real-time Microphone Audio Processor
Entry point.
"""

import sys
import os

# Ensure the project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import socket
import sys
import threading
from gui.app import MicMasterApp

def _run_ipc_server(app):
    """Listens for wake-up calls from secondary instances."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', 19420))
    server.listen(1)
    while True:
        try:
            conn, _ = server.accept()
            msg = conn.recv(1024)
            if b"SHOW" in msg:
                # Force app to front
                app.after(0, app.deiconify)
                app.after(50, app.lift)
            elif b"KILL" in msg:
                # Force kill
                app.after(0, app._destroy_completely)
            conn.close()
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description="MicMaster Pro")
    parser.add_argument("--startup", action="store_true", help="Invoked on system startup")
    args = parser.parse_args()

    # -- SINGLE INSTANCE LOCK --
    try:
        # If this succeeds, we are the first instance.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 19420))
        s.close()
    except OSError:
        # App is already running! Send a wake-up packet and exit.
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', 19420))
            client.sendall(b"SHOW")
            client.close()
        except:
            pass
        sys.exit(0)
    # --------------------------

    app = MicMasterApp(is_startup=args.startup)
    
    # Start IPC server daemon thread
    t = threading.Thread(target=_run_ipc_server, args=(app,), daemon=True)
    t.start()
    
    if args.startup:
        app.withdraw()  # Starts completely invisible (daemon)
        
    app.mainloop()

if __name__ == "__main__":
    main()
