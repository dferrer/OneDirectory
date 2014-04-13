import bcrypt, MySQLdb, sys
from _mysql_exceptions import IntegrityError, OperationalError

# Use global variables to maintain a connection to the database.
with open('password.txt') as f:
    db = MySQLdb.connect(host="dbm2.itc.virginia.edu", user="dlf3x", passwd=f.read().strip(), db="cs3240onedir")
db.autocommit(True)
cursor = db.cursor()

def encrypt(password):
    """Returns a secure hash of a string."""
    return bcrypt.hashpw(password, bcrypt.gensalt())

def get_user_data():
    """Returns information about the users in the database."""
    cursor.execute("SELECT user_id FROM account")
    result = cursor.fetchall()
    if len(result) == 0:
        print "Error: no users are registered."
    else:
        print "Users:"
        for user in result:
            print user[0]

def get_file_data(user=None):
    if not user:
        cursor.execute("SELECT COUNT(path), AVG(size), MAX(size), MIN(size) FROM file NATURAL JOIN log")
        print_file_stats(cursor.fetchone())
        cursor.execute("SELECT path, size FROM file NATURAL JOIN log")
        print_file_info(cursor.fetchall())
    else:
        cursor.execute("SELECT COUNT(path), AVG(size), MAX(size), MIN(size) FROM file NATURAL JOIN log WHERE user_id = %s", (user,))
        print_file_stats(cursor.fetchone())
        cursor.execute("SELECT path, size FROM file NATURAL JOIN log WHERE user_id = %s", (user,))
        print_file_info(cursor.fetchall())

def print_file_stats(row):
    if row[0] != 0:
        print 'Number of files: {0}'.format(row[0])
        print 'Average file size: {0:.2f}'.format(row[1])
        print 'Maximum file size: {0}'.format(row[2])
        print 'Minimum file size: {0}'.format(row[3])
    else:
        print "Error: no files stored."

def print_file_info(rows):
    print 'File data: '
    for row in rows:
        print 'Filename: {0}, size: {1}'.format(row[0], row[1])

def change_password(user, password):
    """Changes a user's password."""
    cursor.execute("UPDATE account SET password = %s WHERE user_id = %s", (encrypt(password),user))
    print "Updated password for {0}".format(user)

def get_history():
    """Displays information about the history of connections involving synchronization."""
    cursor.execute("SELECT user_id, time, action FROM log ORDER BY time")
    for row in cursor.fetchall():
        user = row[0]
        action = row[2]
        time = row[1]
        print 'User {0} committed action {1} at time {2}'.format(user, action, time)

def remove_user(user):
    """Removes the user identified by the passed parameter and removes files associated with the user."""
    cursor.execute("DELETE FROM account WHERE user_id = %s", (user,))
    print 'Deleted account for user {0}'.format(user)    

def remove_user_files(user):
    """Removes all files associated with a user"""
    cursor.execute("DELETE FROM file WHERE user_id = %s", (user,))
    print 'Removed all files for user {0}'.format(user)

def get_file_data_aux():
    """Helper function for get_file_data()"""
    user = raw_input('Enter a user ID (or press enter to view data for all files): ')
    if user == '\n':
        get_file_data()
    else:
        get_file_data(user)

def remove_user_aux():
    """Helper function for remove_user()"""
    user = raw_input('Enter a user ID: ')
    remove_user(user)

def remove_user_files_aux():
    """Helper function for remove_user_files()"""
    user = raw_input('Enter a user ID: ')
    remove_user_files(user)

def change_password_aux():
    """Helper function for change_password()"""
    user = raw_input('Enter a user ID: ')
    password = raw_input('Enter a password: ')
    change_password(user, password)

def prompt():
    """Prompts the user for a command."""
    return raw_input('\nEnter:\n'
    + '"View Users" to see a list of OneDir users\n'
    + '"View File Data" to see information about the synced files\n'
    + '"Delete Account" to delete a user\s account\n'
    + '"Delete Files" to remove a user\s files\n'
    + '"Change Password" to change a user\'s password\n'
    + '"View History" to view the history of connections\n'
    + 'or "Quit" to exit the program\n').lower()

def main():
    """Receives and executes commands from the user."""
    commands = {
        'view users' : get_user_data,
        'view file data' : get_file_data_aux,
        'delete account' : remove_user_aux,
        'delete files' : remove_user_files_aux,
        'change password' : change_password_aux,
        'view history' : get_history,
        'quit' : sys.exit,
    }
    while True:
        cmd = prompt()
        commands.get(cmd, lambda: sys.stdout.write('Command "' + cmd + '" not found.'))()

if __name__ == "__main__":
    main()

# Close the connection to the database.
db.close()