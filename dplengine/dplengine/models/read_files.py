# filename: read_files.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: reads various types of files into data frame

import os
import csv
import xlrd

from common.profiling import profiling

import logging
from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

@profiling
def get_file_type(rename_cols_data, file_path, file_name, return_type=None):
    """
    
    :param rename_cols_data: 
    :param file_path: 
    :param file_name: 
    :param return_type: 
    :return: 
    """""

    if os.path.exists(file_path):
        file_type = file_name.split('.')
        # print('ft', file_type)
        # print('csv' in file_type)
        if any('col_headers' in key for key in rename_cols_data[0]):
            col_headers = rename_cols_data[0]['col_headers']
        else:
            col_headers = ''

        if any('col_separator' in key for key in rename_cols_data[0]):
            delimiter = rename_cols_data[0]['col_separator']
            if delimiter is not None:
                if delimiter == 'tab':
                    delimiter_type = '\t'
                elif delimiter == 'comma':
                    delimiter_type = ','
                elif delimiter == 'space':
                    delimiter_type = ' '
                elif delimiter == 'pipe':
                    delimiter_type = '|'
                else:
                    delimiter_type = delimiter
            else:
                delimiter_type = delimiter

        else:
            delimiter_type = None

        # print(any(type_ in file_type for type_ in ['csv', 'txt']))
        # exit(1)

        if any(type_ in file_type for type_ in ['csv', 'txt']):
            # print(file_path, col_headers, delimiter_type)
            rename_col = read_csv_file(file_path, col_headers, delimiter_type, return_type)
            return rename_col

        elif 'xlsx' in file_type:
            rename_col = read_excel_file(file_path, col_headers, delimiter_type, return_type)
            return rename_col

    else:
        raise Exception("No such file found in given path: "+str(file_path))


def read_csv_file(file_path, headers, separator, return_type):
    """
    :param file_path:
    :return:
    """
    # print(os.path.exists(file_path))
    if os.path.exists(file_path):
        # print("file exists")
        # exit(1)
        rename_columns = []
        col_list = []
        with open(file_path, encoding="utf-8-sig", newline='') as csv_file:

            if separator is not None:
                delimiter_type = separator
            else:
                delimiter_type = ','
            csv_reader = csv.reader(csv_file, delimiter=delimiter_type)
            line_count = 0
            if headers != '':
                next(csv_reader)
            try:
                if return_type != 'final_columns':
                    for row in csv_reader:
                        if len(row) == 2:
                            rename_columns.append(f'{row[0]}:{row[1]}')
                        if len(row) == 3:
                            rename_columns.append(f'{row[0]}:{row[1]}:{row[2]}')
                    return rename_columns
                else:
                    for row in csv_reader:
                        if row:
                            col_list.append(f'{row[0]}')

                    return col_list
            except IndexError as ie:
                raise Exception("Please check delimiter type")
    else:
        print("No such file found at given path")
        exit(1)


def read_excel_file(file_path, headers, separator, return_type):
    """
    usage: reading excel for to get list of columns
    :param file_path:
    :param headers:
    :param separator:
    :param return_type:
    :return:
    """

    if os.path.exists(file_path):
        rename_columns = []
        final_columns = []
        wb = xlrd.open_workbook(file_path)
        sheet = wb.sheet_by_index(0)

        # For row 0 and column 0
        # sheet.cell_value(0, 0)

        if headers != '':
            range_start_num = 1
        else:
            range_start_num = 0
        for i in range(range_start_num, sheet.nrows):
            row = sheet.row_values(i)
            if return_type != 'final_columns':
                if len(row) == 2:
                    rename_columns.append(f'{row[0]}:{row[1]}')
                if len(row) == 3:
                    rename_columns.append(f'{row[0]}:{row[1]}:{row[2]}')
            else:
                if row:
                    rename_columns.append(f'{row[0]}')
                # return rename_columns
        return rename_columns
