# filename: derive_data_dataframe_columns.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: performs derivations on a particular column of a data frame.

import re

import numpy as np
import pandas as pd


class DeriveDataFrameColumns:

    def __init__(self):
        pass

    def date_formatting(data_frame, column_name, input_format, year_prefix):
        """
        formatting the date from string to date type and in
        :param data_frame:
        :param column_name:
        :param input_format: actual format of the input date
        :param year_prefix: year prefix if any ( ex: 19 for 2019, 20 for 2020)
        :return: data frame with column
        """
        if data_frame.empty:
            raise Exception("data frame empty for derivation")
        else:
            if input_format.startswith('%Y'):
                data_frame[str(column_name)] = np.where(data_frame[str(column_name)].astype(str).apply(len) == 6,
                                                        '20' + data_frame[str(column_name)].str.slice(stop=2)
                                                        + data_frame[str(column_name)].str.slice(start=2, stop=4)
                                                        + data_frame[str(column_name)].str.slice(start=4),
                                                        np.where(
                                                            data_frame[str(column_name)].astype(str).apply(len) == 8,
                                                            data_frame[str(column_name)].str.slice(stop=4) + '-' +
                                                            data_frame[str(column_name)].str.slice(start=4, stop=6)
                                                            + '-' + data_frame[str(column_name)].str.slice(start=6),
                                                            data_frame[str(column_name)]))
                data_frame[str(column_name)] = pd.to_datetime(data_frame[str(column_name)], format=str(input_format),
                                                              errors='coerce')
                return data_frame
            else:
                data_frame[str(column_name)] = np.where(data_frame[str(column_name)].astype(str).apply(len) == 5,
                                                        '0' + data_frame[str(column_name)].str.slice(stop=1) + '-' +
                                                        data_frame[str(column_name)].str.slice(start=1,
                                                                                               stop=3) + '-20' +
                                                        data_frame[str(column_name)].str.slice(start=3),
                                                        np.where(
                                                            data_frame[str(column_name)].astype(str).apply(len) == 6,
                                                            data_frame[str(column_name)].str.slice(stop=2) + '-' +
                                                            data_frame[str(column_name)].str.slice(start=2, stop=4)
                                                            + '-20' + data_frame[str(column_name)].str.slice(start=4),
                                                            np.where(data_frame[str(column_name)].astype(str).apply(
                                                                len) == 7,
                                                                     '0' + data_frame[str(column_name)].str.slice(
                                                                         stop=1)
                                                                     + '-' + data_frame[str(column_name)].str.slice(
                                                                         start=1, stop=3)
                                                                     + '-' + data_frame[str(column_name)].str.slice(
                                                                         start=3),
                                                                     np.where(
                                                                         data_frame[str(column_name)].astype(str).apply(
                                                                             len) == 8,
                                                                         data_frame[str(column_name)].str.slice(stop=2)
                                                                         + '-' + data_frame[str(column_name)].str.slice(
                                                                             start=2, stop=4)
                                                                         + '-' + data_frame[str(column_name)].str.slice(
                                                                             start=4),
                                                                         data_frame[str(column_name)]))))
                data_frame[str(column_name)] = pd.to_datetime(data_frame[str(column_name)], format=str(input_format),
                                                              errors='coerce')
                return data_frame

    def right(self, derived_column, columnName, places, dataFrame):
        """
        striping the string in a column from right to given number of places
        :param derived_column:
        :param columnName:
        :param places: no of places to strip from
        :param dataFrame:
        :return: data frame
        """
        places = int(places)

        # changing column data type to string using astype function
        dataFrame = dataFrame.astype({str(columnName): str})

        # slicing the string to  a substring with give integer value i.e palces
        dataFrame[str(derived_column)] = dataFrame[str(columnName)].str.slice(0, int(places))
        return dataFrame

    def string_to_decimial(self, value):
        """
        converting string value to decimal
        :param value:
        :return: value
        """
        value = int(value)
        return value

    def dataframe_derivation(self, column, strDerivation, dataFrame):
        """
        data frame derivation on a particular column of data frame
        :param column:
        :param strDerivation: type of derivation
        :param dataFrame:
        :return: value
        """
        if strDerivation:
            try:
                string = strDerivation.split('(')
                strFNString = string[0]
                strRight = string[1]
                strRightTrim = strRight.split(')')
                strParameters = strRightTrim[0]
            except Exception as e:
                print(e)
                strParameters = strDerivation
                strFNString = strDerivation
                try:
                    dataFrame[str(column)] = dataFrame.eval(strDerivation)
                    return dataFrame
                except Exception as e:
                    print(e)
                    dataFrame[str(column)] = strDerivation
                    return dataFrame

            print("Checking conditions")
            if strFNString.find('NullToZero') != -1:

                if 'int' in str(dataFrame[str(strParameters)].dtype):
                    dataFrame[str(strParameters)] = dataFrame[str(strParameters)].fillna(0, inplace=False)

                    return dataFrame
                elif 'object' in str(dataFrame[str(strParameters)].dtype):
                    dataFrame[str(strParameters)] = dataFrame[str(strParameters)].astype(str).fillna('0', inplace=False)
                    return dataFrame
                else:
                    return dataFrame

            # converting null to value
            if strFNString.find('NullToValue') != -1:
                split = strRight.split(',')
                strParameters = split[0]
                strValue = split[1]
                strValue = strValue.strip(")")
                if 'int' in str(dataFrame[str(strParameters)].dtype):
                    dataFrame[str(strParameters)] = dataFrame[str(strParameters)].fillna(int(strValue), inplace=False)
                    return dataFrame
                elif 'object' in str(dataFrame[str(strParameters)].dtype):
                    dataFrame[str(strParameters)] = dataFrame[str(strParameters)].fillna(str(strValue), inplace=False)
                    return dataFrame
                else:
                    return dataFrame

            print("performing string to date derivation..........")
            if strFNString.find('If StringToDecimal') != -1:
                split = re.split('If|Then|Else|Format', strDerivation)
                IfCondition = split[1]
                ThenCondition = split[2]
                ThenCondition = ThenCondition.strip("'")
                ElseCondition = split[3]
                IfSplit = IfCondition.split('=')
                IfValue = IfSplit[1]
                IfFn = IfSplit[0]
                columnName = re.search('\((.*)\)', IfFn)
                columnName = columnName.group(1)
                date_format = split[4].strip("(").strip(")").split(",")
                input_format = date_format[0]
                input_format = input_format.split("=")
                input_format = input_format[1]
                year_prefix = date_format[1]
                year_prefix = year_prefix.split("=")
                year_prefix = year_prefix[1]
                dataFrame[str(columnName)] = dataFrame[str(columnName)].astype(str)
                dataFrame[str(columnName)] = dataFrame[str(columnName)].str.strip()
                dataFrame[str(columnName)] = dataFrame[str(columnName)].str.replace(r'[-, /, ., ,]*', "")
                try:
                    dataFrame.loc[(dataFrame[str(columnName)].astype(str) == '0'),
                                  str(columnName)] = np.nan
                except Exception as e:
                    print("string to date conversion error", e)

                try:
                    dataFrame = DeriveDataFrameColumns.date_formatting(dataFrame, columnName, input_format, year_prefix)
                    return dataFrame
                except Exception as e:
                    print("string to date conversion error", e)
                return dataFrame

            elif strFNString.find('Right') != -1:
                split = strParameters.split(',')
                strColumnName = split[0]
                intPlaces = split[1]
                return self.right(column, strColumnName, intPlaces, dataFrame)

            elif strFNString.find('StringToDecimal') != 1:
                if dataFrame[str(column)].dtype == str or dataFrame[str(column)].dtype == object:
                    dataFrame[str(column)] = dataFrame[str(column)].astype(int)
                    return dataFrame
                else:
                    return dataFrame

            else:
                try:
                    dataFrame[str(column)] = dataFrame.eval(strDerivation)
                except Exception as e:
                    print(e)
                    dataFrame[str(column)] = strDerivation
        elif not strDerivation or strDerivation == '':
            return dataFrame
