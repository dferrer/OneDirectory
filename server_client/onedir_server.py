import pysftp, paramiko
import time
from os.path import expanduser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Connect to the server.
def connect(host, username, password):
	return pysftp.Connection(host=host, username=username, password=password)

# Download a file from the server.
def download(server, remote_path, local_path):
	server.get(remote_path, local_path)

# Upload a file to the server.
def upload(server, local_path, remote_path):
	server.put(local_path, remote_path)

# Define a class that inherits from FileSystemEventHandler
# and overrides key event methods.
class Handler(FileSystemEventHandler):
    def on_modified(self, event):
        upload(server, event.src_path, server_path + str(event.src_path)[str(event.src_path).rfind("/")+1:len(str(event.src_path))])
    def on_moved(self, event):
        print "Moved " + event.src_path
    def on_created(self, event):
        upload(server, event.src_path, server_path + str(event.src_path)[str(event.src_path).rfind("/")+1:len(str(event.src_path))])
    def on_deleted(self, event):
	sftp_para.remove(server_path + str(event.src_path)[str(event.src_path).rfind("/")+1:len(str(event.src_path))])

if __name__ == "__main__":
	# Information needed to connect to remote server.
	host = '128.143.67.201' # labunix01.cs.virginia.edu/
	username = 'dlf3x'
	password = 'NVFmHjoe'

	# Paths to ~/onedir on local machine and server.
	local_path = expanduser('~') + '/onedir/'
	server_path = '/home/dlf3x/onedir/'

	# Connect to the server via SSH.
	server = connect(host, username, password)

	# Change the server's current working directory to ~/onedir
	server.chdir(server_path)

	# Instantiate observer and file system handler.
	# Find path to OneDirectory folder.
	event_handler = Handler()
	observer = Observer()

	#Testing Paramiko ####
	transport = paramiko.Transport((host,22))
	transport.connect(username = username,password = password)
	sftp_para = paramiko.SFTPClient.from_transport(transport)

	######################

	# Schedule the observers and set it to run in the background.
	observer.schedule(event_handler, path=local_path, recursive=True)
	observer.daemon = True
	observer.start()

	# Monitor the file system until the user manually halts the process.
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		observer.stop()
	observer.join()

	# Close the connection to the server.
	server.close()