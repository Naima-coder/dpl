# filename: regex_operations.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: performs various kinds of python regex operation or for comparision of strings.

import os
import re
from datetime import datetime, timedelta

from models.read_ini_file import IniFiles


def query_date_conversions(query):
    """
    Converts and returns the various date_formats in query into 'DD-MM-YYYY' format
    :param query:
    :return:
    """
    date_formats = [r'\d{4}-\d{1,2}-\d{1,2}[ |\'|"]',  # 2019-11-01
                    r'\d{2}-\d{1,2}-\d{1,2}[ |\'|"]',  # 19-11-01
                    r'\d{4}/\d{1,2}/\d{1,2}[ |\'|"]',  # 2019/11/01
                    r'\d{2}/\d{1,2}/\d{1,2}[ |\'|"]',  # 19/11/01
                    r"[\d]{4}-[adfjmnosADFJMNOS]\w*-[\d]{1,2}[ |'|\"]",  # 2019-nov-01
                    r"[\d]{2}-[adfjmnosADFJMNOS]\w*-[\d]{1,2}[ |'|\"]",  # 19-nov-01
                    r"[\d]{4}/[adfjmnosADFJMNOS]\w*/[\d]{1,2}[ |'|\"]",  # 2019/nov/01
                    r"[\d]{2}/[adfjmnosADFJMNOS]\w*/[\d]{1,2}[ |'|\"]",  # 19/nov/01
                    r"[\d]{4} [adfjmnosADFJMNOS]\w* [\d]{1,2}[ |'|\"]",  # 2019 nov 01
                    r"[\d]{2} [adfjmnosADFJMNOS]\w* [\d]{1,2}[ |'|\"]",  # 19 nov 01
                    r"[\d]{2}[adfjmnosADFJMNOS]\w*[\d]{1,2}[ |'|\"]",  # 19nov01
                    r"[\d]{1,2}-[adfjmnosADFJMNOS]\w*[ |'|\"]",  # 01-NOV
                    r"[\d]{1,2}/[adfjmnosADFJMNOS]\w*[ |'|\"]",  # 01/NOV
                    r"[\d]{1,2} [adfjmnosADFJMNOS]\w*[ |'|\"]",  # 01 NOV
                    r"[\d]{1,2}[adfjmnosADFJMNOS]\w*[ |'|\"]",  # 01Nov
                    r"[adfjmnosADFJMNOS]\w*-[\d]{1,2}[ |'|\"]",  # NOV-01
                    r"[adfjmnosADFJMNOS]\w*/[\d]{1,2}[ |'|\"]",  # NOV/01
                    r"[adfjmnosADFJMNOS]\w* [\d]{1,2}[ |'|\"]",  # NOV 01
                    r"[adfjmnosADFJMNOS]\w*[\d]{1,2}[ |'|\"]"  # Nov01
                    ]

    py_formats = ['%Y-%m-%d',
                  '%y-%m-%d',
                  '%Y/%m/%d',
                  '%y/%m/%d',
                  '%Y-%b-%d',
                  '%y-%b-%d',
                  '%Y/%b/%d',
                  '%y/%b/%d',
                  '%Y %b %d',
                  '%Y%b%d',
                  '%y %b %d',
                  '%d-%b',
                  '%d/%b',
                  '%d %b',
                  '%d%b',
                  '%b-%d',
                  '%b/%d',
                  '%b %d',
                  '%b%d'
                  ]

    # Getting current year
    current_year = datetime.now().year

    match_list = []
    map_list = []

    # Getting all dates from query
    for date_format, py_format in zip(date_formats, py_formats):
        # print(date_format, py_format)
        matches_in_query = re.findall(date_format, query)
        for match in matches_in_query:
            print("match", match)
            new_match = datetime.strptime(match[:-1], py_format).date()
            if py_format in ['%d-%b', '%d/%b', '%d %b', '%d%b', '%b-%d', '%b/%d', '%b %d', '%b%d']:
                new_match = new_match.strftime(f'%d-%m-{current_year}')
            else:
                new_match = new_match.strftime('%d-%m-%Y')
            match_list.append(match[:-1])
            map_list.append(new_match)

    # Replacing the dates in query in 'DD-MM-YYYY' format
    for match_value, map_value in zip(match_list, map_list):
        # print("Match Value: ", match_value)
        # print("Map_Value: ", map_value)
        query = query.replace(match_value, map_value)
        # print(query)
        # print('\n')

    return query


def dataframe_columns_mapping(data_frame, string):
    """
    Replaces the column_names in given string with column names in dataframe
    :param data_frame:
    :param string (can be a list or string):
    :return: a string list or single string
    """
    if type(string) == list and type(data_frame) != list:
        result_string_list = []
        for sub_string in string:
            result_string_list.append(df_columns_to_upper_case(data_frame, sub_string))
        return result_string_list

    elif type(string) == str and type(data_frame) != list:
        result_string = df_columns_to_upper_case(data_frame, string)
        return result_string

    elif type(string) == list and type(data_frame) == list:
        result_string_list = []
        for df in data_frame:
            for sub_string in string:
                result_string_list.append(df_columns_to_upper_case(df, sub_string))
        return result_string_list

    elif type(string) == str and type(data_frame) == list:
        result_string = string
        for df in data_frame:
            result_string = df_columns_to_upper_case(df, result_string)
        return result_string
    else:
        return string


def df_columns_to_upper_case(data_frame, string):
    """
        Replaces the column_names in given string with column names in dataframe
        :param data_frame:
        :param string:
        :return: a single string
        """
    try:
        for col in data_frame.columns.tolist():
            # print("column: ", col)
            matching_list = re.findall(fr'\b{col}\b', string, re.IGNORECASE)
            if len(matching_list) != 0:
                for match in matching_list:
                    string = re.sub(fr'\b{match}\b', col, string)
        return string
    except Exception as error:
       return string


def parameter_values(string):
    """

    :param string:
    :return:
    """
    while '$' in string:
        # print("sql_query: ", string)
        # if sql_query[-1] != '':
        #     sql_query += ''
        # key_name_ini_file = re.search('parameter.(.+?) ', sql_query, re.IGNORECASE)
        key_name_ini_file = string.split('$')[1]
        # print('key_name_ini_file with parameter split: ', key_name_ini_file)
        key_name_ini_file = key_name_ini_file.split(' ')[0]
        # print('key_name_ini_file with split: ', key_name_ini_file)
        # print("key_name_ini_file: ", key_name_ini_file)
        if os.path.exists(str(os.path.join(os.getcwd(), 'properties.ini'))):
            properties = IniFiles.read_ini_file(str(os.path.join(os.getcwd(), 'properties.ini')))
            try:
                key_value = properties['RUNTIME'][key_name_ini_file]
                # print("key_value: ", key_value)
                if key_name_ini_file == 'DATE_RANGE':
                    if ',' in key_value or ', ' in key_value:
                        key_value = key_value.replace(',', ', ')
                        # print(key_value)
                        date_value1 = key_value.split(', ')[0]
                        if date_value1[0] == '[':
                            date_value1 = date_value1[1:]
                        date_value2 = key_value.split(', ')[1]
                        if date_value2[-1] == ']':
                            date_value2 = date_value2[:-1]
                        key_value = f"'{date_value1}' and '{date_value2}'"
                        # print("key_value after replacement: ", key_value)
                        string = string.replace(f'${key_name_ini_file}', f'{key_value}')
                    else:
                        string = string.replace(f'${key_name_ini_file}', f"'{key_value}'")
                else:
                    string = string.replace(f'${key_name_ini_file}', f"'{key_value}'")
                # print("sql_query after replace: ", string, '\n')
            except KeyError as ke:
                if 'DATE_RANGE' in str(ke):
                    key_value = str(datetime.now().date())
                    string = string.replace(f'${key_name_ini_file}', f"'{key_value}'")
                else:
                    print(f" No such key {ke} in 'properties.ini' file")
                    exit(1)
        else:
            print(f"Properties file doesnot exist in path: {os.getcwd()}")
            exit(1)
    # print(string)
    return string


def get_date_from_string(string):
    """

    :param string:
    :return:
    """
    # print(string)
    date_formats = [r'\d{4}-\d{1,2}-\d{1,2}[ |\'|"]',  # 2019-11-01
                    r'\d{2}-\d{1,2}-\d{1,2}[ |\'|"]',  # 19-11-01
                    r'\d{4}/\d{1,2}/\d{1,2}[ |\'|"]',  # 2019/11/01
                    r'\d{2}/\d{1,2}/\d{1,2}[ |\'|"]',  # 19/11/01
                    r'\d{1,2}-\d{1,2}-\d{4}[ |\'|"]',  # 01-11-2019
                    r'\d{1,2}-\d{1,2}-\d{2}[ |\'|"]',  # 01-11-19
                    r'\d{1,2}/\d{1,2}/\d{4}[ |\'|"]',  # 01/11/2019
                    r'\d{1,2}/\d{1,2}/\d{2}[ |\'|"]'  # 01/11/19
                    ]

    py_formats = ['%Y-%m-%d',
                  '%y-%m-%d',
                  '%Y/%m/%d',
                  '%y/%m/%d',
                  '%d-%m-%Y',
                  '%d-%m-%y',
                  '%d/%m/%Y',
                  '%d/%m/%Y'
                  ]

    # Getting current year
    current_year = datetime.now().year

    match_list = []
    map_list = []

    for date_format, py_format in zip(date_formats, py_formats):
        # print(date_format, py_format)
        matches_in_query = re.findall(date_format, string)
        # print(matches_in_query)
        for match in matches_in_query:
            # print("match", match)
            new_match = datetime.strptime(match[:-1], py_format).date()
            if py_format in ['%d-%b', '%d/%b', '%d %b', '%d%b', '%b-%d', '%b/%d', '%b %d', '%b%d']:
                new_match = new_match.strftime(f'%d-%m-{current_year}')
            else:
                new_match = new_match.strftime('%d-%m-%Y')
            match_list.append(datetime.strptime(match[:-1], py_format).date())
            map_list.append(new_match)

    # print(match_list, map_list)
    today = datetime.now().date()
    run_time_date = None
    day_start_date = None
    day_end_date = None
    week_start_date = (today - timedelta(days=today.weekday() + 1))
    week_end_date = week_start_date + timedelta(days=6)
    if len(match_list) == 2:
        if match_list[0] == match_list[1]:
            run_time_date = match_list[0]
            day_start_date = match_list[0]
            day_end_date = match_list[0]
            week_start_date = None
            week_end_date = None
        else:
            if match_list[0] > match_list[1]:
                run_time_date = None
                day_start_date = None
                day_end_date = None
                week_start_date = match_list[1]
                week_end_date = match_list[0]
            else:
                run_time_date = None
                day_start_date = None
                day_end_date = None
                week_start_date = match_list[0]
                week_end_date = match_list[1]
    if len(match_list) == 1:
        run_time_date = match_list[0]
        day_start_date = match_list[0]
        day_end_date = match_list[0]
        week_start_date = None
        week_end_date = None

    return [run_time_date, day_start_date, day_end_date, week_start_date, week_end_date]


def run_time_parameters(string, varaiable_names, variable_values):
    """

    :param string:
    :param varaiable_names:
    :param variable_values:
    :return:
    """
    print(varaiable_names)
    # while '$' in string:
    #     key_name_ini_file = string.split('$')[1]
    #     # print('key_name_ini_file with parameter split: ', key_name_ini_file)
    #     key_name_ini_file = key_name_ini_file.split(' ')[0]
    #     # print(key_name_ini_file)
    #     if f'${key_name_ini_file}' in varaiable_names:
    #         position = varaiable_names.index(f'${key_name_ini_file}')
    #         string = string.replace(f'${key_name_ini_file}', str(variable_values[position]))
    for var_name in varaiable_names:
        if var_name in string:
            position = varaiable_names.index(f'{var_name}')
            # print(type(variable_values[position]))
            string = string.replace(var_name, str(variable_values[position]))

    return string

