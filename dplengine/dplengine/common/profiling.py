# filename: profiling.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: searches for properties.ini file to check memory profiling status. On true the memory profile log will
# be save to a given directory. The directory path is provided in dpl_engine.properties.

import os

from memory_profiler import profile

from common.file_name_generation import generate_file_name
from common.process_tracking import ProcessTracking
from models.read_props_file import get_property

# getting memory profiling file name and file path
mf_file_name, mf_file_path = generate_file_name(get_property('profiling_file_path'), 'memory_profiling_file', 'log')

# print("memory profiling file name", mf_file_name, "\nprofiling file path", mf_file_path)

try:
    job_properties = ProcessTracking.capture_process('INIT')
    if job_properties:
        memory_profiling = str(job_properties['memory_profiling'])
    else:
        memory_profiling = False
except Exception as error:
    memory_profiling = False


def profiling(function):
    def profile_fn(function_name):
        """
        generates saves the memory profiling log to a file
        :param function_name: name of the function
        :return: decorator function
        """
        if memory_profiling == 'True':
            mem_log = open(str(os.path.join(mf_file_path, mf_file_name)), 'a+')
            function_name = profile(stream=mem_log)(function_name)
            return function_name
        else:
            return function
    return profile_fn(function)
