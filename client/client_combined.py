import bcrypt, json, MySQLdb, os, pysftp, sys, time, threading
from os.path import expanduser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from _mysql_exceptions import IntegrityError, OperationalError
from twisted.internet import protocol, reactor

# Use global variables to maintain a connection to the database.
with open('password.txt') as f:
    db = MySQLdb.connect(host="dbm2.itc.virginia.edu", user="dlf3x", passwd=f.read().strip(), db="cs3240onedir")
db.autocommit(True)
cursor = db.cursor()

# Use global variables to specify server address and port number
HOST = '128.143.67.201'
PORT = 2121

# Use global variables for Watchdog
observer = Observer()

# Server database methods
def encrypt(password):
    """Returns a secure hash of a string."""
    return bcrypt.hashpw(password, bcrypt.gensalt())

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

def create_account(user, password, auto_sync=True):
    """Adds a user's account information to the database and creates an account on the server."""
    try:
        cursor.execute("INSERT INTO account VALUES (%s, %s, %s)", (user, encrypt(password), auto_sync))
        print "Added user " + user + " to the database."
        return True
    except IntegrityError:
        print "Error: user " + user + " already exists."
        return False

def get_password(user):
    """Queries the database for a user's password."""
    cursor.execute("SELECT password FROM account WHERE user_id = %s", (user,))
    try:
        return cursor.fetchone()[0]
    except TypeError:
        print "Error: user " + user + " not found in database."

def update_password(user, current_pass, new_pass):
    """Updates a user's password upon validation of old password."""
    try:
        if is_valid(user, current_pass):
            cursor.execute("UPDATE account SET password = %s WHERE user_id = %s", (encrypt(new_pass),user))
            print "Updated password for " + user
            return True
        else:
            print "Error: entered password does not match actual password for user " + user
            return False
    except TypeError:
        return False

def prompt():
    """Prompts the user for a command."""
    return raw_input('\nEnter:\n'
    + '"Create Account" to create an account\n'
    + '"Change Password" to modify your password\n'
    + 'or "Quit" to exit the program\n').lower()

class ClientProtocol(protocol.Protocol):
    def send_data(self):
        """Receives a command and handles it locally or sends it to the server."""
        cmd = prompt()
        if cmd == 'create account':
            self.handle_create_account()
        elif cmd == 'change password':
            self.handle_update_password()
	elif cmd == 'login':
	    self.handle_login()
	elif cmd == 'logout':
	    self.handle_logout()
        elif cmd == 'quit':
            os._exit()
        else:
            print 'Command "{0}" not found.'.format(cmd)

    def handle_create_account(self):
        """Helper function for create_account."""
        user = raw_input('Enter a user ID: ')
        password = raw_input('Enter a password: ')
        if create_account(user, password):
            data = json.dumps({
                'cmd' : 'create account', 
                'user' : user, 
                'password' : password
            })
            print 'Sending ' + str(data)
            self.transport.write(str(data))
        else:
            self.send_data()

    def handle_update_password(self):
        """Helper function for update_password."""
        user = raw_input('Enter a user ID: ')
        current_pass = raw_input('Enter current password: ')
        new_pass = raw_input('Enter new password: ')
        if update_password(user, current_pass, new_pass):
            data = json.dumps({
                'cmd' : 'update password', 
                'user' : user, 
                'old_pass' : current_pass, 
                'new_pass' : new_pass
            })
            self.transport.write(data)
        else:
            self.send_data()
  
    def handle_login(self): 
        # Prompt user for user ID and password before syncing.
        user = raw_input('Please enter your user ID: ')
        password = raw_input('Please enter your password: ')
        global observer
        if not is_valid(user, password):
            print "Invalid Login."
            self.send_data()
        elif observer != None and observer.isAlive():
            print "Already Logged In."	
            self.send_data()
        else:
            # Set values for paths to onedir folder on client and server machines.
            home = expanduser('~')
            local_path = '{0}/onedir/'.format(home)
            server_path = '/home/dlf3x/CS3240/{0}/onedir/'.format(user)
            # Begin the SFTP session with the server.
            server = connect()
            # Instantiate file system handler.
            event_handler = Handler(user, server)
            # Schedule the observer and set it to run in the background.
            observer = Observer()
            observer.schedule(event_handler, path=local_path, recursive=True)
            observer.daemon = True
            observer.start()
            data = json.dumps({
                    'cmd' : 'login', 
                    'user' : user, 
                    'local_path' : local_path, 
                    'server_path' : server_path
                    })
            self.transport.write(data)
            
            
    def handle_logout(self):
        global observer
        if observer != None and not observer.isAlive():
            print "Not Logged In."
            self.send_data()
        else:
            observer.stop()
            observer.join()
            self.send_data()
            
    def connectionMade(self):
        """Executes when client connects to server."""
        self.send_data()
        
    def dataReceived(self, data):
        """Executes when data is received from the server."""
        if str(data) != 'flag':
            print "Received: " + str(data)
        self.send_data()

class ClientFactory(protocol.ClientFactory):
    def buildProtocol(self, addr):
        return ClientProtocol()

    def startedConnecting(self, connector):
        print 'Connected to ' + HOST + ':' + str(PORT)

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection: ' + str(reason)
        reactor.stop()
        sys.exit(1)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed:' + str (reason)
        reactor.stop()
        sys.exit(1)

# Watchdog methods
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

def delete(server, remote_path):
    """Deletes a file in the server."""
    server.remove(remote_path)

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
	else:
	    #Finish
	    local_path = event.src_path
	    index = local_path.find('onedir')
	    print 'Uploaded directory {0} to server.'.format(local_path[index:])

    def on_deleted(self, event):
	#Finish
        print 'Deleted ' + event.src_path
        print "Server path is " + adjust_path(event.src_path, self._user)
        self._just_created = False

if __name__ == "__main__":
    factory = ClientFactory()
    factory.protocol = ClientProtocol()
    reactor.connectTCP(HOST, PORT, factory)
    reactor.run()

# Close the connection to the database.
db.close()
