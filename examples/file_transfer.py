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
	# Example path and server information.
	onedir = expanduser('~') + '/onedir/'
	host = '0.0.0.0'
	username = 'dylan'
	with open('password.db') as f:
		password = f.read().strip()

	# Example file transfer.
	server = connect(host, username, password)
	server.chdir(onedir)
	download(server, server.getcwd() + '/hello_world.hs', onedir + '/transferred_file.hs')
	upload(server, onedir + '/transferred_file.hs', server.getcwd() + '/another_file.hs')
	server.close()
