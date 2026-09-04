import os
import logging
import time
import shutil
from datetime import date, timedelta,datetime
import glob
import fnmatch


def cleanup(number_of_days, path):
    """
    Removes files from the passed in path that are older than or equal
    to the number_of_days
    """
    try:
        time_in_secs = time.time() - (number_of_days * 24 * 60 * 60)
        paths_ = glob.glob(path)
        for path_ in paths_:
            if os.path.isfile(path_):
                stat = os.stat(path_)
                if stat.st_mtime <= time_in_secs:
                    os.remove(path_)
                    # print(path_)
                    logging.info('Removed file :: '+path_)
    except Exception as e:
        logging.error('Error occurred : ' + str(e))

cleanup(14, '/u01/apps/config/config/denorms/chain_ads/core.*')
