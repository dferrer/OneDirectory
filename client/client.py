import bcrypt, MySQLdb, sys, time
from _mysql_exceptions import IntegrityError, OperationalError

# Use global variables to maintain a connection to the database.
with open('password.txt') as f:
    db = MySQLdb.connect(host="dbm2.itc.virginia.edu", user="dlf3x", passwd=f.read(), db="cs3240onedir")
db.autocommit(True)
cursor = db.cursor()

def encrypt(password):
    """Returns a secure hash of a string."""
    return bcrypt.hashpw(password, bcrypt.gensalt())

def is_valid(user, password):
    """Checks if an entered password matches a user's password in the database."""
    encoded = password.encode("utf-8")
    hashed = get_password(user)
    return bcrypt.hashpw(encoded, hashed) == hashed

def create_account(user, password, auto_sync=True):
    """Adds a user's account information to the database."""
    try:
        cursor.execute("INSERT INTO account VALUES (%s, %s, %s)", (user, encrypt(password), auto_sync))
        print "Added user " + user + " to the database."
    except IntegrityError:
        print "Error: user " + user + " already exists."

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
        else:
            print "Error: entered password does not match actual password for user " + user
    except TypeError:
        return

def prompt():
    """Prompts the user for a command."""
    return raw_input('\nEnter:\n'
    + '"Create Account" to create an account\n'
    + '"Change Password" to modify your password\n'
    + 'or "Quit" to exit the program\n').lower()

def main():
    """Receives commands from the user."""
    while True:
        user_input = prompt()
        if user_input == 'create account':
            user = raw_input('Enter a user ID: ')
            password = raw_input('Enter a password: ')
            create_account(user, password)
        elif user_input == 'change password':
            user = raw_input('Enter a user ID: ')
            current_pass = raw_input('Enter current password: ')
            new_pass = raw_input('Enter new password: ')
            update_password(user, current_pass, new_pass)
        elif user_input == 'quit':
            sys.exit()
        else:
            print 'Command "' + user_input + '" not found.'

if __name__ == "__main__":
    main()

# Close the connection to the database.
db.close()