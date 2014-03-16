import pysftp
from os.path import expanduser

# Connect to the server.
def connect(host, username, password):
	return pysftp.Connection(host=host, username=username, password=password)

# Download a file from the server.
def download(server, remote_path, local_path):
	server.get(remote_path, local_path)

# Upload a file to the server.
def upload(server, local_path, remote_path):
	server.put(local_path, remote_path)

if __name__ == "__main__":
	# Information needed to connect to remote server.
	host = '128.143.67.201' # labunix01.cs.virginia.edu/
	username = 'dlf3x'
	password = 'NVFmHjoe'

	# Paths to ~/onedir on local machine and server.
	local_path = expanduser('~') + '/onedir/'
	server_path = '/home/dlf3x/onedir'

	# Connect to the server via SSH.
	server = connect(host, username, password)

	# Change the server's current working directory to ~/onedir
	server.chdir(server_path)

	# Download an example file from the server.
	download(server, server_path + '/example1.txt', local_path + '/example1.txt')

	# Upload an example file to the server.
	upload(server, local_path + '/example2.hs', server_path + '/example2.hs')

	# Close the connection to the server.
	server.close()
