# filename: verbose_to_log.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: capture and saving the verbose to a log file.

import sys


class Logger(object):
    def __init__(self, verbose_path):
        self.terminal = sys.stdout
        self.verbose_path = verbose_path

    def write(self, message):
        """
        writing the verbose log to a file
        :param message: 
        """""
        with open(self.verbose_path, "a", encoding='utf-8') as self.log:
            self.log.write(message)
        self.terminal.write(message)

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass
