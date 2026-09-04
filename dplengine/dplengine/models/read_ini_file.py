# filename: read_ini_files.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: reads .ini files

import configparser

class IniFiles:

    def __init__(self):
        pass

    @staticmethod
    def ini_to_dict(config_parser):
        """
        reading .ini file into a dictionary
        :param config_parser: 
        :return: dictionary
        """""
        my_dict = dict(config_parser._sections)
        for k in my_dict:
            my_dict[k] = dict(config_parser._defaults, **my_dict[k])
            my_dict[k].pop('__name__', None)
        return my_dict



    @staticmethod
    def read(file_path):
        """
        creating a config object to read the .ini file from the given path
        :param config_parser: 
        :return: config object
        """""
        config = configparser.ConfigParser()
        config.read(file_path)
        return config

    @staticmethod
    def update_prop_file(section, variable, value, file_path):
        """
        updating the values in .ini file
        :param section: 
        :param variable: 
        :param value: 
        :param file_path: 
        :return: 
        """""
        try:
            config = configparser.ConfigParser()
            config.read(file_path)
            config.set(f'{section}', f'{variable}', f'{value}')
            with open(file_path, 'w') as inifile:
                config.write(inifile)
        except Exception:
            return False
        return True

    @staticmethod
    def get_prop_file_value(section, variable, file_path):
        """
        getting property values using the variable and section
        :param section: 
        :param variable: 
        :param file_path: 
        :return: value of the variable
        """""
        try:
            config = configparser.ConfigParser()
            config.read(file_path)
            value = config[f'{section}'][f'{variable}']
        except Exception:
            return False
        return value

