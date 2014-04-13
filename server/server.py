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
        print 'Number of files: ' + str(row[0])
        print 'Average file size: ' + '%.2f' % row[1]
        print 'Maximum file size: ' + str(row[2])
        print 'Minimum file size: ' + str(row[3])
    else:
        print "Error: no files stored."
        return

def print_file_info(rows):
    print 'File data: '
    for row in rows:
        print 'Filename: ' + str(row[0]) + ', size: ' + str(row[1])

def change_password(user, password):
    """Changes a user's password."""
    cursor.execute("UPDATE account SET password = %s WHERE user_id = %s", (encrypt(password),user))
    print "Updated password for " + user

def get_history():
    """Displays information about the history of connections involving synchronization."""
    cursor.execute("SELECT user_id, time, action FROM log ORDER BY time")
    for row in cursor.fetchall():
        user = row[0]
        action = row[2]
        time = row[1]
        print 'User ' + user + ' committed action ' + action + ' at time ' + str(time)
#
# def remove_user(user):
#     """Removes the user identified by the passed parameter and removes files associated to the user."""
#     cursor.execute("DELETE FROM tablewithusers WHERE user_id = user")
#     remove_all_files(user)

# def remove_user_files(user):
#     """Removes all files associated to user"""
#     cursor.execute("DELETE FROM tablewithfiles WHERE user_id = user")

def prompt():
    """Prompts the user for a command."""
    return raw_input('\nEnter:\n'
    + '"View Users" to see a list of OneDir users\n'
    + '"View File Data" to see information about the synced files\n'
    + '"Change Password" to change a user\'s password\n'
    + '"View History" to view the history of connections\n'
    + 'or "Quit" to exit the program\n').lower()

def main():
    """Receives and executes commands from the user."""
    while True:
        user_input = prompt()
        if user_input == 'view users':
            get_user_data()
        elif user_input == 'view file data':
            user = raw_input('Enter a user ID (or press enter to view data for all files): ')
            if user == '\n':
                get_file_data()
            else:
                get_file_data(user)
        elif user_input == 'change password':
            user = raw_input('Enter a user ID: ')
            password = raw_input('Enter a password: ')
            change_password(user, password)
        elif user_input == 'view history':
            get_history()
        elif user_input == 'quit':
            sys.exit()
        else:
            print 'Command "' + user_input + '" not found.'

if __name__ == "__main__":
    main()

# Close the connection to the database.
db.close()