import bcrypt, json, MySQLdb, os, sys, time
from _mysql_exceptions import IntegrityError, OperationalError
from twisted.internet import protocol, reactor, defer
from getpass import getpass

# Use global variables to maintain a connection to the database.
with open('password.txt') as f:
    db = MySQLdb.connect(host="dbm2.itc.virginia.edu", user="dlf3x", passwd=f.read().strip(), db="cs3240onedir")
db.autocommit(True)
cursor = db.cursor()

# Use global variables to specify server address and port number
HOST = '128.143.67.201'
PORT = 2222

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

def toggle_autosync(user):
    """Turns autosync on or off for the user."""
    cursor.execute("SELECT auto_sync FROM account WHERE user_id = %s", (user,))
    if cursor.fetchone()[0] == 0:
	    cursor.execture("UPDATE account SET auto_sync = 1 WHERE user_id = %s", (user,))
        print "Turning on autosync."
	    return True
    elif cursor.fetchone()[0] == 1:
	    cursor.execture("UPDATE account SET auto_sync = 0 WHERE user_id = %s", (user,))
        print "Turning off autosync."
	    return True
    else:
	    return False

def prompt():
    """Prompts the user for a command."""
    return raw_input('\nEnter:\n'
    + '"Create Account" to create an account\n'
    + '"Change Password" to modify your password\n'
    + '"Toggle Autosync" to start/stop automatically synchronizing files\n'
    + 'or "Quit" to exit the program\n').lower()

class ClientProtocol(protocol.Protocol):
    def send_data(self):
        """Receives a command from stdin and handles it locally or sends it to the server."""
        cmd = prompt()
        if cmd == 'create account':
            user = raw_input('Enter a user ID: ')
            password = getpass('Enter a password: ')
            if create_account(user, password):
                data = json.dumps({
                    'cmd' : 'create account', 
                    'user' : user, 
                    })
                self.transport.write(data)
            reactor.callInThread(self.send_data)
        elif cmd == 'change password':
            user = raw_input('Enter a user ID: ')
            current_pass = getpass('Enter current password: ')
            new_pass = getpass('Enter new password: ')
            update_password(user, current_pass, new_pass)
            reactor.callInThread(self.send_data) 
        elif cmd == 'toggle autosync':
            user = raw_input('Enter a user ID: ')
            toggle_autosync(user)
        elif cmd == 'quit':
            os._exit()
        else:
            print 'Command "{0}" not found.'.format(cmd)
            reactor.callInThread(self.send_data())

    def connectionMade(self):
        """Executes when client connects to server."""
        print 'Connected to ' + HOST + ':' + str(PORT)
        self.send_data()

class ClientFactory(protocol.ClientFactory):
    def __init__(self):
        self._protocol = ClientProtocol()

    def buildProtocol(self, addr):
        return self._protocol

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection: ' + str(reason)
        reactor.stop()
        sys.exit(1)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed:' + str (reason)
        reactor.stop()
        sys.exit(1)

if __name__ == "__main__":
    factory = ClientFactory()
    reactor.connectTCP(HOST, PORT, factory)
    reactor.run()

# Close the connection to the database.
db.close()
