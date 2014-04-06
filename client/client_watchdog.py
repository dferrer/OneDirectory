import bcrypt, MySQLdb, pysftp, sys, time
from os.path import expanduser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from _mysql_exceptions import IntegrityError, OperationalError

# Use global variables to maintain a connection to the database.
with open('password.txt') as f:
    db = MySQLdb.connect(host="dbm2.itc.virginia.edu", user="dlf3x", passwd=f.read(), db="cs3240onedir")
db.autocommit(True)
cursor = db.cursor()

def connect():
    """Connects to the server using a local password file."""
    with open('server.txt') as f:
        data = f.read().splitlines()
        return pysftp.Connection(host=data[0], username=data[1], password=data[2])

def download(server, remote_path, local_path):
    """Downloads a file from the server."""
    server.get(remote_path, local_path)

def upload(server, local_path, remote_path):
    """Uploads a file to the server."""
    server.put(local_path, remote_path)

def is_valid(user, password):
    """Checks if an entered password matches a user's password in the database."""
    encoded = password.encode("utf-8")
    hashed = get_password(user)
    try:
        if bcrypt.hashpw(encoded, hashed) == hashed:
            return True
        else:
            print 'Error: incorrect password for user {0}'.format(user)
            return False
    except TypeError:
        return False

def get_password(user):
    """Queries the database for a user's password."""
    global cursor
    cursor.execute("SELECT password FROM account WHERE user_id = %s", (user,))
    try:
        return cursor.fetchone()[0]
    except TypeError:
        print "Error: user {0} not found in database.".format(user)

def adjust_path(path, user):
    """Modifies a local path to reflect the corresponding path on the server."""
    home = expanduser('~')
    new_path = '/home/dlf3x/CS3240/{0}'.format(user)
    return path.replace(home,new_path,1)

class Handler(FileSystemEventHandler):
    """Handler inherits from FileSystemEventHandler and overrides key event methods."""
    def __init__(self, user, server):
        self._user = user
        self._server = server
        self._just_created = False

    def on_modified(self, event):
        if not self._just_created and not event.is_directory:
            local_path = event.src_path
            remote_path = adjust_path(local_path, self._user)
            index = local_path.find('onedir')
            upload(self._server, local_path, remote_path)
            print 'Updated file {0} on server.'.format(local_path[index:])
        self._just_created = False

    def on_moved(self, event):
        print "Moved " + event.src_path
        print "Server path is " + adjust_path(event.src_path, self._user)
        self._just_created = False

    def on_created(self, event):
        self._just_created = True
        if not event.is_directory:
            local_path = event.src_path
            remote_path = adjust_path(local_path, self._user)
            index = local_path.find('onedir')
            upload(self._server, local_path, remote_path)
            print 'Uploaded file {0} to server.'.format(local_path[index:])

    def on_deleted(self, event):
        print 'Deleted ' + event.src_path
        print "Server path is " + adjust_path(event.src_path, self._user)
        self._just_created = False

if __name__ == '__main__':
    # Prompt user for user ID and password before syncing.
    while True:
        user = raw_input('Please enter your user ID: ')
        password = raw_input('Please enter your password: ')
        if is_valid(user, password):
            break

    # Set values for paths to onedir folder on client and server machines.
    home = expanduser('~')
    local_path = '{0}/onedir/'.format(home)
    server_path = '/home/dlf3x/CS3240/{0}/onedir/'.format(user)

    # Begin the SFTP session with the server.
    server = connect()

    # Instantiate observer and file system handler.
    observer = Observer()
    event_handler = Handler(user, server)

    # Schedule the observer and set it to run in the background.
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

# Close the connection to the database.
db.close()