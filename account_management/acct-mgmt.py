__author__ = 'nb5kn'

import sys, bcrypt, sqlite3

def changePass(currPass, password):
    """If user successfully validates current pass, updates password to newPass"""
    if is_valid(currPass):
        set_password("user-id", password)
        return True
    return False

def is_valid(password):
    """If passed password is valid, returns True"""
    encoded = password.encode("utf8")
    hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
    if bcrypt.hashpw(encoded, hashed) == hashed:
        return True
    else:
        return False

def get_password(username):
    """For the given username, returns the password from the database"""
    # use sqlite3 to get password

def set_password(username, password):
    """Updates the passed user's password"""
    # encrypt passed parameter
    # should we first validate currPass? for security measures
    # update password using sqlite3 and bcrypt


