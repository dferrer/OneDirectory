import bcrypt, MySQLdb, os, sys
from _mysql_exceptions import IntegrityError, OperationalError
from getpass import getpass
from shutil import rmtree

with open('hidden.txt') as f:
    data = f.read().splitlines()
    USERNAME = data[2]
    PASSWORD = data[3]
    DBHOST = data[4]
    DBNAME = data[5]

db = MySQLdb.connect(host=DBHOST, user=USERNAME, passwd=PASSWORD, db=DBNAME)
db.autocommit(True)
cursor = db.cursor()

def encrypt(password):
    return bcrypt.hashpw(password, bcrypt.gensalt())

def get_user_data():
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
        cursor.execute("SELECT COUNT(path), AVG(size), MAX(size), MIN(size) FROM file")
        print_file_stats(cursor.fetchone())
        cursor.execute("SELECT path, size FROM file")
        print_file_info(cursor.fetchall())
    else:
        cursor.execute("SELECT COUNT(path), AVG(size), MAX(size), MIN(size) FROM file WHERE user_id = %s", (user,))
        print_file_stats(cursor.fetchone())
        cursor.execute("SELECT path, size FROM file WHERE user_id = %s", (user,))
        print_file_info(cursor.fetchall())

def print_file_stats(row):
    if row[0] != 0:
        print 'Number of files: {0}'.format(row[0])
        print 'Average file size: {0:.2f}'.format(row[1])
        print 'Maximum file size: {0}'.format(row[2])
        print 'Minimum file size: {0}'.format(row[3])

def print_file_info(rows):
    print 'File data: '
    for row in rows:
        print 'Filename: {0}, size: {1}'.format(row[0], row[1])

def change_password(user, password):
    cursor.execute("UPDATE account SET password = %s WHERE user_id = %s", (encrypt(password),user))
    print "Updated password for {0}".format(user)

def get_history():
    cursor.execute("SELECT user_id, time, action, path FROM log ORDER BY time")
    for row in cursor.fetchall():
        user = row[0]
        action = row[2]
        filename = row[3]
        time = row[1]
        print '{0} performed action {1} on {3} at {2}'.format(user, action, time, filename)

def remove_user(user):
    cursor.execute("DELETE FROM account WHERE user_id = %s", (user,))
    remove_user_files(user)
    print 'Deleted account for user {0}'.format(user)    

def remove_user_files(user):
    path = '/home/dlf3x/CS3240/{0}'.format(user)
    rmtree(path)
    cursor.execute("DELETE FROM file WHERE user_id = %s", (user,))
    print 'Removed all files for user {0}'.format(user)

def get_file_data_aux():
    user = raw_input('Enter a user ID (or press enter to view data for all files): ')
    if user == '\n':
        get_file_data()
    else:
        get_file_data(user)

def remove_user_aux():
    user = raw_input('Enter a user ID: ')
    remove_user(user)

def remove_user_files_aux():
    user = raw_input('Enter a user ID: ')
    remove_user_files(user)

def change_password_aux():
    user = raw_input('Enter a user ID: ')
    password = getpass('Enter a password: ')
    change_password(user, password)

def prompt():
    return raw_input('\nEnter:\n'
    + '"View Users" to see a list of OneDir users\n'
    + '"View File Data" to see information about the synced files\n'
    + '"Delete Account" to delete a user\'s account\n'
    + '"Delete Files" to remove a user\'s files\n'
    + '"Change Password" to change a user\'s password\n'
    + '"View History" to view the history of connections\n'
    + 'or "Quit" to exit the program\n').lower()

def main():
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

db.close()