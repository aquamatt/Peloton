# $Id: crypto.py 90 2008-03-23 23:43:25Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Provides cryptographic services """
import random
import ezPyCrypto
import cPickle as pickle
from peloton.exceptions import PelotonError
from yawPyCrypto import AsciiKey

# default character set on which to draw to make cookies
tokenspace = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def makeCookie(tokenlength, tokenspace=tokenspace):
    """ Create a cookie tokenlength characters long made from 
characters randomly chosen from the provided tokenspace (for which
a suitable default is provided.)
"""
    tchars = len(tokenspace)
    cookie = "".join([tokenspace[random.randrange(0,tchars)] 
                      for i in xrange(tokenlength)])
    return cookie

def newKey(lenbits, textEncoded=False):
    """ Return a new key pair lenbits long encoded as text if
textEncoded is set True. """
    key = ezPyCrypto.key(lenbits)
    if textEncoded:
        return key.exportKeyPrivate()
    else:
        return key

def importKey(keyStr):
    """ Takes keyStr, an ascii encoded key, and returns a key. """
    key =  ezPyCrypto.key()
    key.importKey(keyStr)


def encrypt(data, key):
    """ Takes data, pickles to string and encrypts into ASCII for
safe transmission over unknown wire protocols. 

Beware: the encryption is strong but the computation is slow!
"""
    cipherText = key.encStringToAscii(pickle.dumps(data))
    return cipherText

def decrypt(ciphertext, key):
    """ Takes ciphertext made by encrypt, decrypts and de-pickles. """
    plainText = key.decStringFromAscii(ciphertext)
    try:
        v = pickle.loads(plainText)
        return v
    except:
        raise PelotonError("Invalid ciphertext given to 'decode'")