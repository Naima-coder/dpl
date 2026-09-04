# filename: file_name_generation.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: Generates file names and file paths for logs, profiling, process tracking and detailed json files

import datetime
import os
import sys
import logging

from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

current_timestamp = datetime.datetime.now()

#global current_timestamp
# getter method
def get_time():
    return current_timestamp.strftime("%Y-%m-%d_%H-%M-%S_%f")


# setter method
def set_time():
    global current_timestamp
    current_timestamp = datetime.datetime.now()
    print(f"current_timestamp at start: {current_timestamp}")

def generate_file_name(directory_name, file_type, file_extension):
    """
    generates file name and file path
    :param directory_name:
    :param file_type: Ex: log, vlog, profiling, process_tracking etc
    :return: file name and file path
    """
    """
    Made changes on 10/09/2020
    To integrate with UI
    """
    try:
        dpl_file = sys.argv[1]
        dpl_file_name, dpl_file_ext = os.path.splitext(dpl_file)
        # Getting filename if file path is given
        base_file_name = os.path.basename(dpl_file_name)
        date_time = current_timestamp.strftime("%Y-%m-%d_%H-%M-%S_%f")
        file_name = f"{base_file_name}_{file_type}_{str(date_time)}.{file_extension}"
        # print("directory name given", directory_name)
        if not os.path.exists(directory_name):
            raise Exception("given directory does not exists please check .properties file")
        file_path = os.path.join(directory_name)
        file_name = os.path.join(file_path, file_name)
        # print(f"file_name : {file_type} '" + file_name + "' path: " + file_path)

        return file_name, file_path
    except Exception as e:
        # To continue on when sys.argv[1] is passed when call happened through UI
        file_path = get_property('logs_file_path')
        date_time = current_timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"request_from_ui_{file_type}_{str(date_time)}.{file_extension}"
        file_name = os.path.join(file_path, file_name)
        return file_name, file_path