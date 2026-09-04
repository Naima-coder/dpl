# from hashlib import sha256
import base64
import logging
import random
import json

from Crypto import Random
from Crypto.Cipher import AES
import cx_Oracle
from models.read_props_file import get_property

BS = 16
pad = lambda s: bytes(s + (BS - len(s) % BS) * chr(BS - len(s) % BS), 'utf-8')
unpad = lambda s: s[0:-ord(s[-1:])]

log_name = get_property('log_name')
logging = logging.getLogger(log_name)

class AESCipher:

    # generating cipher key
    key = '1234abcd1234abcd'
    key = bytes(key, 'utf-8')

    @staticmethod
    def encrypt(raw):
        try:
            raw = pad(raw)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(AESCipher.key, AES.MODE_CBC, iv)
        except Exception as e:
            logging.error(f"Unable to encrypt: {e}")
        else:
            return str(base64.b64encode(iv + cipher.encrypt(raw)))

    @staticmethod
    def decrypt(enc):
        try:
            enc = base64.b64decode(eval(enc))
            iv = enc[:16]
            cipher = AES.new(AESCipher.key, AES.MODE_CBC, iv)
        except Exception as e:
            logging.error(f"Unable to decrypt: {e}")
        else:
            return unpad(cipher.decrypt(enc[16:])).decode('utf8')

