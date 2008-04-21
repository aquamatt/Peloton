# $Id: crypto.py 90 2008-03-23 23:43:25Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Provides cryptographic services """
import random
import base64
import cPickle as pickle
from peloton.exceptions import PelotonError
from Crypto.PublicKey import RSA
from Crypto.Util.randpool import RandomPool

# default character set on which to draw to make cookies
tokenspace = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_Pub_Alg_ = RSA
randpool = RandomPool()
def makeCookie(tokenlength, tokenspace=tokenspace):
    """ Create a cookie tokenlength characters long made from 
characters randomly chosen from the provided tokenspace (for which
a suitable default is provided.)
"""
    tchars = len(tokenspace)
    cookie = "".join([tokenspace[random.randrange(0,tchars)] 
                      for i in xrange(tokenlength)])
    return cookie

def newKey(lenbits=512):
    """ Return a new key pair lenbits long. """
    randpool.stir()
    key = _Pub_Alg_.generate(lenbits, randpool.get_bytes)
    return key

def importKey(keyStr):
    """ Takes keyStr and returns a key. """
    return pickle.loads(keyStr)

def exportKey(key):
    """ Returns serialization of this key. """
    return pickle.dumps(key)

def encrypt(data, key):
    """ Takes data, pickles to string and encrypts into ASCII for
safe transmission over unknown wire protocols. 

Beware: the encryption is strong but the computation is slow!
"""
    pt = pickle.dumps(data)
    blocksize = key.size()/8
    ct = []
    while pt:
        if len(pt) <= blocksize:
            chunk = pt
            pt=''
        else:
            chunk=pt[:blocksize]
            pt=pt[blocksize:]
        ct.append(key.encrypt(chunk,'')[0])

    return "".join(ct)

def decrypt(ciphertext, key):
    """ Takes ciphertext made by encrypt, decrypts and de-pickles. """
    blocksize = key.size()/8 + 1
    pt = []
    while ciphertext:
        if len(ciphertext) <= blocksize:
            chunk = ciphertext
            ciphertext=''
        else:
            chunk = ciphertext[:blocksize]
            ciphertext = ciphertext[blocksize:]
        pt.append(key.decrypt(chunk))
    pt = ''.join(pt)
    try:
        v = pickle.loads(pt)
        return v
    except:
        raise PelotonError("Invalid ciphertext given to 'decode'")
    
def makeKeyAndCookieFile(keyfile = None, keylength=512, tokenlength=50):
    """ Creates a Peloton key and cookie file and writes to keyfile if
specified. Returns the contents as a string. """
    cookie = makeCookie(tokenlength)
    key = newKey(keylength)
    contents = (cookie, key)
    asciiForm = base64.encodestring(pickle.dumps(contents))
    if keyfile:
        f = open(keyfile,'wt')
        f.writelines(asciiForm)
        f.close()
    return asciiForm

def loadKeyAndCookieFile(keyfile):
    """ Loads a key and cookie file returning a tuple of (cookie, key). """
    f = open(keyfile, 'rt')
    asciiForm = f.readlines()
    pkle = base64.decodestring("".join(asciiForm))
    return pickle.loads(pkle)