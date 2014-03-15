import pysftp
from os.path import expanduser

def connect(host, username, password):
	return pysftp.Connection(host=host, username=username, password=password)

def download(server, remote_path, local_path):
	server.get(remote_path, local_path)

def upload(server, local_path, remote_path):
	server.put(local_path, remote_path)

if __name__ == "__main__":
	host = '0.0.0.0'
	username = 'dylan'
	with open('password.db') as f:
		password = f.read().strip()
	# home = expanduser('~')
	# onedir = home + '/OneDirectory/'
	onedir = '/home/dylan/OneDirectory'

	server = connect(host, username, password)
	server.chdir(onedir)
	download(server, server.getcwd() + '/hello_world.hs', onedir + '/transferred_file.hs')
	upload(server, onedir + '/transferred_file.hs', server.getcwd() + '/another_file.hs')
	server.close()
