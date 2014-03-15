import time
from os.path import expanduser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Define a class that inherits from FileSystemEventHandler
# and overrides key event methods.
class Handler(FileSystemEventHandler):
    def on_modified(self, event):
        print "Modified " + event.src_path
    def on_moved(self, event):
        print "Moved " + event.src_path
    def on_created(self, event):
        print 'Created ' + event.src_path
    def on_deleted(self, event):
        print 'Deleted ' + event.src_path

if __name__ == "__main__":
    # Instantiate observer and file system handler.
    # Find path to OneDirectory folder.
    event_handler = Handler()
    observer = Observer()
    path = expanduser('~') + '/onedir/'

    # Schedule the observer and set it to run in the background.
    observer.schedule(event_handler, path=path, recursive=True)
    observer.daemon = True
    observer.start()

    # Monitor the file system until the user manually halts the process.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
