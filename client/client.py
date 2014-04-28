import bcrypt, json, MySQLdb, os, sys
from _mysql_exceptions import IntegrityError, OperationalError
from twisted.internet import protocol, reactor
from getpass import getpass

with open('hidden.txt') as f:
    data = f.read().splitlines()
    HOST = data[0]
    PORT = int(data[1])
    USERNAME = data[2]
    PASSWORD = data[3]
    DBHOST = data[4]
    DBNAME = data[5]

db = MySQLdb.connect(host=DBHOST, user=USERNAME, passwd=PASSWORD, db=DBNAME)
db.autocommit(True)
cursor = db.cursor()

def encrypt(password):
    return bcrypt.hashpw(password, bcrypt.gensalt())

def is_valid(user, password):
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
    try:
        cursor.execute("INSERT INTO account VALUES (%s, %s, %s)", (user, encrypt(password), auto_sync))
        print "Added user {0} to the database.".format(user)
        return True
    except IntegrityError:
        print "Error: user {0} already exists.".format(user)
        return False

def get_password(user):
    cursor.execute("SELECT password FROM account WHERE user_id = %s", (user,))
    try:
        return cursor.fetchone()[0]
    except TypeError:
        print "Error: user {0} not found in database.".format(user)

def update_password(user, current_pass, new_pass):
    try:
        if is_valid(user, current_pass):
            cursor.execute("UPDATE account SET password = %s WHERE user_id = %s", (encrypt(new_pass),user))
            print "Updated password for {0}".format(user)
            return True
        else:
            print "Error: entered password does not match actual password for user {0}".format(user)
            return False
    except TypeError:
        return False

def toggle_autosync(user, password):
    try:
        if is_valid(user, password):
            cursor.execute("SELECT auto_sync FROM account WHERE user_id = %s", (user,))
            sync = cursor.fetchone()[0]
            if sync == 0:
                print "Turning on autosync."
                cursor.execute("UPDATE account SET auto_sync = 1 WHERE user_id = %s", (user,))                
                local_path = "".join([os.path.expanduser('~'),"/onedir/"])
                home = expanduser('~')
                server_path = "{0}@{1}:{2}/CS3240/{3}/onedir/".format(USERNAME, HOST, home, user)
                cmd1 = "rsync -azu {1} {2}".format(user,server_path,local_path)
                cmd2 = "rsync -azu {1} {2}".format(user,local_path,server_path)
                os.system(cmd1)
                os.system(cmd2)
                print "Sync done"
                return True
            elif sync == 1:
                print "Turning off autosync."
                cursor.execute("UPDATE account SET auto_sync = 0 WHERE user_id = %s", (user,))
                return True
            else:
                return False
    except IntegrityError:
            return False

def prompt():
    return raw_input('\nEnter:\n'
    + '"Create Account" to create an account\n'
    + '"Change Password" to modify your password\n'
    + '"Toggle Autosync" to start/stop automatically synchronizing files\n'
    + 'or "Quit" to exit the program\n').lower()

class ClientProtocol(protocol.Protocol):
    def send_data(self):
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
            user = raw_input('Enter a user ID: ').strip().lower()
            password = getpass('Enter password: ').strip().lower()
            toggle_autosync(user, password)
            reactor.callInThread(self.send_data)
        elif cmd == 'quit':
            os._exit(1)
        else:
            print 'Command "{0}" not found.'.format(cmd)
            reactor.callInThread(self.send_data())

    def connectionMade(self):
        print 'Connected to {0}:{1}'.format(HOST, PORT)
        self.send_data()

class ClientFactory(protocol.ClientFactory):
    def __init__(self):
        self._protocol = ClientProtocol()

    def buildProtocol(self, addr):
        return self._protocol

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection: {0}'.format(reason)
        reactor.stop()
        sys.exit(1)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed:{0}'.format(reason)
        reactor.stop()
        sys.exit(1)

if __name__ == "__main__":
    factory = ClientFactory()
    reactor.connectTCP(HOST, PORT, factory)
    reactor.run()

db.close()
