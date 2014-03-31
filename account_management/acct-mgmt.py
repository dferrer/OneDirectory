__author__ = 'nb5kn'

import sys, bcrypt

def changePass(currPass, password):
    """If user successfully validates current pass, updates password to newPass"""
    if is_valid(currPass):


def is_valid(password):
    """If passed password is valid, returns True"""
    encoded = password.encode("utf8")
    hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
    if bcrypt.hashpw(encoded, hashed) == hashed:
        return True
    else:
        return False