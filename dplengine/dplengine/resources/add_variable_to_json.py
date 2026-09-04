# filename: add_variable_to_json.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: Replaces the variables provided in the yml/dpl config file (variables are followed by $ sign) with
# either through user input or the value preset in the properties.ini (properties.ini can be global or job specific)

import datetime as dt
import os
import re
import logging

from common.process_tracking import ProcessTracking
from common.process_tracking import ini_file_path
from models.read_ini_file import IniFiles
from common.profiling import profiling

from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)


class EditDetailedJson:

    VARS_FRM_SYSARG = None
    PROPS_FILE_PATH = ini_file_path

    def __init__(self):
        pass

    # getting a user input from the console
    @staticmethod
    @profiling
    def get_usr_input(string):
        """
        getting an user input for the string/variable given in dpl config/yml file
        :param string: name of the variable in string format
        :return: returns the value from user input or from properties.ini file
        """
        frmt_variable = string.strip("\\$")
        value = None

        print("run time variable", frmt_variable)
        logging.info(f"run time variable: {frmt_variable}")
        if re.match('^dpldate$', frmt_variable, re.IGNORECASE):
            value = dt.datetime.now().date().strftime("%d-%m-%Y")
            return str(value)
        elif re.match('^dplprevdate$', frmt_variable, re.IGNORECASE):
            value = dt.datetime.now().date() - dt.timedelta(days=1)
            value = value.strftime("%d-%m-%Y")
            return str(value)
        elif re.match('^dplnextdate$', frmt_variable, re.IGNORECASE):
            value = dt.datetime.now().date() + dt.timedelta(days=1)
            value = value.strftime("%d-%m-%Y")
            return str(value)
        elif re.match('^dpldate\((.*)\)$', frmt_variable, re.IGNORECASE):
            date_format = re.search('^dpldate\((.*)\)$', frmt_variable)
            date_format = date_format.group(1)
            try:
                value = dt.datetime.now().date() + dt.timedelta(days=int(date_format))
                return str(value)
            except Exception as e:
                value = dt.datetime.now().date().strftime(date_format)
                return str(value)
        elif re.match('^dpltime$', frmt_variable, re.IGNORECASE):
            value = dt.datetime.now().time().strftime("%H:%M:%S")
            return str(value)
        elif re.match('^dpltimestamp$', frmt_variable, re.IGNORECASE):
            value = dt.datetime.now().time().strftime("%d-%m-%Y %H:%M:%S")
            return str(value)
        else:
            if EditDetailedJson.check_in_props(string) == True:
                while True:
                    decision = input(f"Value already exists: {frmt_variable} = "
                                     f"{IniFiles.get_prop_file_value('RUNTIME', frmt_variable, os.path.join(EditDetailedJson.PROPS_FILE_PATH, 'properties.ini'))}"
                                     f"\nWould you like to replace (y/n)?:")
                    if decision == 'Y' or decision == 'y' or decision == 'n' or decision == 'N':
                        break
                    else:
                        print("Invalid decision, please say Y for 'YES' or N for 'NO'")
                        continue
                if decision is 'Y' or decision is 'y':
                    value = input(f"Enter the value for {frmt_variable}:")
                    value = EditDetailedJson.autopick_date(value)
                elif decision is 'N' or decision is 'n':
                    value = IniFiles.get_prop_file_value('RUNTIME', frmt_variable, os.path.join(EditDetailedJson.PROPS_FILE_PATH, 'properties.ini'))
                    value = EditDetailedJson.autopick_date(value)

            elif EditDetailedJson.check_in_props(string) == False:
                value = input(f"Variable does not exist in batch file,\n "
                              f"Enter the value for {re.sub('[^A-Za-z0-9_]+', '', string).lower()} as run time variable:")
                value = EditDetailedJson.autopick_date(value)
            else:
                return value

            print("run time variable value given is", value)
            logging.info(f"run time variable value given is: {value}")
            return value

    # removing duplicates from a list
    @staticmethod
    @profiling
    def rm_dup(my_list):
        """
        removing duplicates from a list
        :param my_list: list or an array
        :return: returns the list or an array without duplicates
        """
        my_list = list(dict.fromkeys(my_list))
        return my_list

    # assigning values to user defined variables
    @staticmethod
    @profiling
    def usr_val_to_dtjson(detailed_json):
        """
        replace the string/variable in dpl config/yml file with a value
        :param detailed_json:
        :return: detailed_json
        """
        json_string = str(detailed_json)
        matching_list = re.findall(r'(\$\w+)+(\(.*\))*', json_string, re.IGNORECASE)
        final_match = []
        for tuple in matching_list:
            mylist = list(tuple)
            final_match.append(mylist[0] + mylist[1])
        final_match = EditDetailedJson.rm_dup(final_match)
        sysarg_vars_dict = EditDetailedJson.VARS_FRM_SYSARG
        print("in class",sysarg_vars_dict)
        print(final_match)
        if len(final_match) != 0:
            for match in final_match:
                match = '\\' + str(match)
                if '(' and ')' in match:
                    json_match = match.replace("(", "\(").replace(")", "\)")
                    if sysarg_vars_dict is None or match.strip("\\$") not in sysarg_vars_dict.keys():
                        json_string = re.sub(fr'({json_match})', EditDetailedJson.get_usr_input(match), json_string)
                    elif match.strip("\\$") in sysarg_vars_dict.keys():
                        json_string = re.sub(fr'({json_match})', sysarg_vars_dict[str(match.strip("\\$"))], json_string)
                else:
                    if sysarg_vars_dict is None or match.strip("\\$") not in sysarg_vars_dict.keys():
                        json_string = re.sub(fr'{match}\b', EditDetailedJson.get_usr_input(match), json_string)
                    elif match.strip("\\$") in sysarg_vars_dict.keys():
                        json_string = re.sub(fr'{match}\b', sysarg_vars_dict[str(match.strip("\\$"))], json_string)
            result_detailed_json = eval(json_string)
            return result_detailed_json
        else:
            return detailed_json

    # checking if the variable exists in properties.ini
    @staticmethod
    @profiling
    def check_in_props(variable):
        """
        checks weather if the variable is present in properties.ini file or not.
        :param variable: name of the variable in string format
        :return: returns bool True or False
        """
        try:
            variable = variable.strip("\\$")
            if EditDetailedJson.PROPS_FILE_PATH == None:
                runtime_vars = ProcessTracking.capture_process('RUNTIME')
                if runtime_vars is not False:
                    if variable in runtime_vars.keys():
                        return True
            elif EditDetailedJson.PROPS_FILE_PATH != None:
                properties = IniFiles.read(str(os.path.join(EditDetailedJson.PROPS_FILE_PATH, 'properties.ini')))
                properties_json ={}
                try:
                    for key in properties['RUNTIME']:
                        properties_json[key] = properties['RUNTIME'][key]
                except Exception:
                    return False
                if properties_json is not False:
                    if variable in properties_json.keys():
                        return True
                    else:
                        return False
            else:
                return False
        except Exception as error:
            return False

    # validating input string
    @staticmethod
    @profiling
    def validate_input(input_value):
        if re.fullmatch(r'[A-Z-a-z0-9_ ]*', input_value) == None:
            return False
        else:
            return input_value

    @staticmethod
    @profiling
    def autopick_date(string):
        """
        checks weather if the variable is present in properties.ini file or not.
        :param variable: name of the variable in string format
        :return: returns bool True or False
        """
        date_difference = 0
        if re.match('^current_day-', str(string), re.IGNORECASE) \
                or re.match('^current_date-', str(string), re.IGNORECASE):
            split_string = re.sub(" ", "", string).split("-")
            if len(split_string) == 2:
                date_difference = int(split_string[1])
            result_date = dt.datetime.now().date() - dt.timedelta(days=date_difference)
            result_date = result_date.strftime("%d-%m-%Y")
            return result_date

        elif re.match('^current_date', str(string), re.IGNORECASE) \
                or re.match('^current_month', str(string), re.IGNORECASE) \
                or re.match('^current_year', str(string), re.IGNORECASE) \
                or re.match('^current_day', str(string), re.IGNORECASE):
            result_date = dt.datetime.now().date() - dt.timedelta(days=date_difference)
            result_date = result_date.strftime("%d-%m-%Y")
            return result_date

        elif re.match('^current_date\+', str(string), re.IGNORECASE) \
                or re.match('^current_date\+', str(string), re.IGNORECASE):
            split_string = re.sub(" ", "", string).split("+")
            if len(split_string) == 2:
                date_difference = int(split_string[1])
            result_date = dt.datetime.now().date() + dt.timedelta(days=date_difference)
            result_date = result_date.strftime("%d-%m-%Y")
            return result_date

        elif re.match('^current_month-', str(string), re.IGNORECASE):
            split_string = re.sub(" ", "", string).split("-")
            if len(split_string) == 2:
                date_difference = int(split_string[1])
                date_difference = date_difference * 365 / 12
            result_date = dt.datetime.now().date() - dt.timedelta(date_difference)
            result_date = result_date.strftime("%d-%m-%Y")
            return result_date

        elif re.match('^current_month\+', str(string), re.IGNORECASE):
            split_string = re.sub(" ", "", string).split("+")
            if len(split_string) == 2:
                date_difference = int(split_string[1])
                date_difference = date_difference * 365 / 12
            result_date = dt.datetime.now().date() + dt.timedelta(date_difference)
            result_date = result_date.strftime("%d-%m-%Y")
            return result_date

        elif re.match('^current_year-', str(string), re.IGNORECASE):
            split_string = re.sub(" ", "", string).split("-")
            if len(split_string) == 2:
                date_difference = int(split_string[1])
                date_difference = date_difference * 365
            result_date = dt.datetime.now().date() - dt.timedelta(days=date_difference)
            result_date = result_date.strftime("%d-%m-%Y")
            return result_date

        elif re.match('^current_year\+', str(string), re.IGNORECASE):
            split_string = re.sub(" ", "", string).split("+")
            if len(split_string) == 2:
                date_difference = int(split_string[1])
                date_difference = date_difference * 365
            result_date = dt.datetime.now().date() + dt.timedelta(days=date_difference)
            result_date = result_date.strftime("%d-%m-%Y")
            return result_date

        else:
            return string

    @staticmethod
    @profiling
    def sys_arg_vars_to_dtjson(my_list):
        """
        gets a list of variables from system argument and returns as a dictionary
        :param my_list: list of variables
        :return: dictonary with variable name and its value as key value pair
        """
        final_dict = {}
        if my_list != None:
            for i in my_list:
                split_variable = i.split('=')
                #print("split_variable:",split_variable)
                final_dict[str(split_variable[0].strip("'").strip('"'))] = split_variable[1].strip("'").strip('"').replace("#", ",")
            #print("final_dict",final_dict)    
            EditDetailedJson.VARS_FRM_SYSARG = final_dict
            return final_dict
        elif my_list == None:
            return None

    @staticmethod
    @profiling
    def alt_props_file_path(alt_props_file_path):
        """
        alter the properties.ini path when provided in dpl config/yml file
        :param alt_props_file_path: alternative properties.ini file path
        :return: None
        """
        EditDetailedJson.PROPS_FILE_PATH = alt_props_file_path
        return None
