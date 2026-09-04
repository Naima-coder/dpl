# filename: data_checking.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: performs various checks/validations on the a single or multiple data frames

import datetime
import hashlib
import os
import time
import logging

from common.process_tracking import ProcessTracking
from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

try:
    job_properties = ProcessTracking.capture_process('INIT')
except Exception as e:
    job_properties = {}
try:
    run_time_props = ProcessTracking.capture_process('RUNTIME')
except Exception as e:
    run_time_props = {}


# checking data quality
class DataCheck:

    def __init__(self):
        pass

    @staticmethod
    def joinKeyValidation(data_frames, columns):
        """
        validates the key columns for joining two data frames
        :param data_frames:
        :param columns:
        :return:
        """
        try:
            ignore_right_duplicates = None
            if job_properties != {}:
                try:
                    ignore_right_duplicates = job_properties['ignore_right_duplicates']
                    logging.info("Ignore right duplicates property", job_properties['ignore_right_duplicates'])
                except Exception as error:
                    ignore_right_duplicates = False
            if type(columns) == str:
                if ',' in columns:
                    columns = columns.split(",")
                else:
                    columns = columns.split()
            if type(data_frames) == list and len(data_frames) == 2 and columns is not None and type(columns) == list:
                left_df = data_frames[0]
                right_df = data_frames[1]
                left_columns = []
                right_columns = []
                if not left_df.empty and not right_df.empty and type(columns) == list:
                    for col in columns:
                        if type(col) == dict:
                            if type(col["left_on"]) == list and type(col["right_on"]) == list:
                               left_columns = col["left_on"]
                               right_columns = col["right_on"]
                            elif type(col["right_on"]) == str and type(col["left_on"]) == str:
                               left_columns.append(col["left_on"])
                               right_columns.append(col["right_on"])
                            else:
                               raise Exception ("invalid column format")
                        elif type(col) == str:
                            left_columns.append(col)
                            right_columns.append(col)
                        else:
                            raise Exception ("invalid column format")
                    if len(left_columns) > 0 and len(right_columns) > 0 and len(left_columns) == len(right_columns):
                        if left_df.duplicated(subset=left_columns).sum() > 0:
                            print("..........Warning: duplicated records detected in left dataframe..........")
                            print("..... duplicated data ......")
                            print(left_df[left_df[left_columns].duplicated()])
                            logging.debug(f"duplicated records detected in left dataframe for the "
                                          f"key columns {left_columns}")
                            pass
                        if left_df[left_columns].isnull().any(axis=1).sum() > 0:
                            print(f"..........Warning: null values detected in left  columns {left_columns}..........")
                            print("........ null value datafame .....")
                            print(left_df[left_df[left_columns].isnull().any(axis=1)])
                            print("..... exiting job.....")
                            logging.debug(f"null records detected in left dataframe for the "
                                          f"key columns {left_columns}, exiting the job")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.datetime.now()}]"
                                                            f"[pyprocessstep:{'join'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                            f"[timestamp:{datetime.datetime.now()}]",
                                                            excepetion="Null records on key columns for join",
                                                            trace_back=None, subject='Exception --> Null Values in Key Columns')

                            raise Exception("Null records on key columns for join")
                            # time.sleep(3)
                            # exit(1)
                        if right_df.duplicated(subset=right_columns).sum() > 0:
                             print(f"..........Warning: duplicated records detected in right dataframe ..........")
                             print("..... duplicated data ......")
                             print(right_df[right_df[right_columns].duplicated()])
                             logging.debug(f"duplicate records detected in right dataframe for the "
                                           f"key columns {right_columns}, but are ignored")
                             if ignore_right_duplicates == False or ignore_right_duplicates == 'False':
                                print("...... Removing duplicate records.....")
                                right_df = right_df.drop_duplicates(subset=right_columns, keep='first')
                                print(right_df)
                                logging.debug(f"duplicate records detected in right dataframe for the "
                                              f"key columns {right_columns}, and removed duplicates")
                             else:
                                 pass
                             pass

                        if right_df[right_columns].isnull().any(axis=1).sum() > 0:
                            print(f"..........Warning: null values detected in right columns {right_columns}..........")
                            print("........ null value datafame .....")
                            print(right_df[right_df[right_columns].isnull().any(axis=1)])
                            print("..... exiting job.....")
                            logging.debug(f"null records detected in right dataframe for the "
                                          f"key columns {right_columns}")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.datetime.now()}]"
                                                            f"[pyprocessstep:{'join'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                            f"[timestamp:{datetime.datetime.now()}]",
                                                            excepetion="Null records on key columns for join",
                                                            trace_back=None, subject='Exception --> Null Values in Key Columns')
                            raise Exception("Null records on key columns for join")
                            # time.sleep(3)
                            # exit(1)
                        else:
                            print("in else part")
                            data_frames = [left_df, right_df]
                            return data_frames
                    else:
                       raise Exception("left and right columns count doest not match")
                else:
                   raise Exception("invalid input dataframes and column")
            else:
               raise Exception("invalid input dataframes and column")
        except Exception as error:
            print("error2",error)
            if str(error) == 'Null records on key columns for join':
            # print("exeption occured", error)
                raise Exception(error)
            else:
                return data_frames


    @staticmethod
    def generate_urid(data_frame, key_columns):
        """
        generate unique ID based on the key column values of a data frame
        :param data_frame:
        :param key_columns:
        :return: data frame
        """
        my_string = ''
        for col in key_columns:
            my_string += str(col)
        data_frame = data_frame.eval(f"URID = {my_string}")
        data_frame["URID"] = data_frame["URID"].apply(lambda col_val: hashlib.sha512(str(col_val).encode()).hexdigest())
        return data_frame

    @staticmethod
    def pickleDF(dataframe):
        """
        pickling the data frame
        :param dataframe:
        :return: data frame on exception and True on success
        """
        filename = str(datetime.datetime.now())
        try:
            pickling_path = str(job_properties['pickling_path'])
        except Exception:
            return dataframe
        pickling_path = os.path.join(pickling_path, filename, '.ftr')
        dataframe.to_pickle(pickling_path)
        if os.path.isfile(pickling_path):
            return True
        else:
            raise Exception("pickling failed")

    @staticmethod
    def checkDBCommit(df_row_count, row_count):
        """
        validates if the data has been committed to the table
        :param df_row_count:
        :param row_count:
        :return: False when the row count is less than count of index in table
        """
        print(f"data frame row count : {df_row_count}" '\n' f"sql row count: {row_count}")
        logging.info(f"data frame row count : {df_row_count}" '\n' f"sql row count: {row_count}")
        error = f"data frame row count : {df_row_count}" '\n' f"sql row count: {row_count}"
        if int(df_row_count) < int(row_count):
            # DataCheck.pickleDF(dataframe)
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{'rename_drop_col'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.datetime.now()}]", excepetion="insert/update failed",
                                            trace_back=error, subject='Exception-critical')
            raise Exception("insert/update failed")

        else:
            print(f"insert/update successful with {row_count} records")

        return False


    @staticmethod
    def keyColumnsCheck(data_frame):
        """
        checking columns have duplicates in a data frame based on key columns provided in properties.ini
        :param data_frame:
        :return: data frame
        """
        try:
            key_columns = []
            key_cols = run_time_props['KEY_COLUMNS']
            key_cols = key_cols.split(",")
            for col in key_cols:
                col.replace(" ", "")
                col.strip()
                key_columns.append(col)
            if any(data_frame.duplicated(subset=str(col)).sum() > 0 for col in key_columns) or \
                    any(data_frame[col].isnull().sum() > 0 for col in key_columns):
                raise Exception("detected duplicate/null in key columns")
            return data_frame
        except Exception:
            return data_frame


    @staticmethod
    def getDuplicateRcords(data_frame, columns_list = None):
        """
        get duplicate records in a data frame
        :param data_frame:
        :param columns_list:
        :return: data frame
        """
        if columns_list == None:
            result = data_frame[data_frame.duplicated()]
            return result
        elif len(columns_list) > 0:
            if type(columns_list) != list:
                raise Exception ("invalid columns")
            result = data_frame[data_frame.duplicated(columns_list)]
            return result


    @staticmethod
    def drop_dup_cols(data_frame):
        """
        removing duplicate columns in a data frame
        :param data_frame:
        :return: data frame
        """
        data_frame.columns = data_frame.columns.str.upper()
        data_frame = data_frame.loc[:, ~data_frame.columns.duplicated()]
        return data_frame


    @staticmethod
    def drop_dup_rows(data_frame):
        """
        removing duplicate rows
        :param data_frame:
        :return: data_Frame
        """
        data_frame = data_frame.drop_duplicates(keep='first')
        return data_frame


    @staticmethod
    def validate_dtypes(data_frames, column_names, operation_type):
        """
        :param data_frame:
        :param column_name:
        :param operation_type:
        :return:
        """
        try:
            print("------------------- performing data type validations on join --------------------------")
            if operation_type == 'join':
                if type(data_frames) == list and len(data_frames) == 2 and column_names is not None and type(column_names) == list:
                    left_df = data_frames[0]
                    right_df = data_frames[1]
                    left_key_columns = []
                    right_key_columns = []
                    if not left_df.empty and not right_df.empty and type(column_names) == list:
                        for col in column_names:
                            if type(col) == dict:
                                if type(col["left_on"]) == list and type(col["right_on"]) == list:
                                   left_key_columns = col["left_on"]
                                   right_key_columns = col["right_on"]
                                elif type(col["right_on"]) == str and type(col["left_on"]) == str:
                                   left_key_columns.append(col["left_on"])
                                   right_key_columns.append(col["right_on"])
                                else:
                                   raise Exception("invalid column format")

                    object_type_columns_in_left_df = left_df.select_dtypes('object').columns.to_list()
                    object_type_columns_in_left_df = list(set(left_key_columns) & set(object_type_columns_in_left_df))
                    logging.info(f"no object type columns in left df {len(object_type_columns_in_left_df)}")
                    object_type_columns_in_right_df = right_df.select_dtypes('object').columns.to_list()
                    object_type_columns_in_right_df = list(set(right_key_columns) & set(object_type_columns_in_right_df))
                    logging.info(f"no object type columns in right df {len(object_type_columns_in_left_df)}")
                    actual_record_count_left_data_frame = len(left_df.index)
                    actual_record_count_right_data_frame = len(right_df.index)

                    if len(object_type_columns_in_left_df) > 0:
                        multi_data_type_records_count = None
                        multi_data_type_records = None
                        for column in object_type_columns_in_left_df:
                            date_type_records_count, date_type_records = DataCheck.get_date_type_record_details(left_df, column)
                            float_type_records_count, float_type_records = DataCheck.get_float_type_record_details(left_df, column)
                            integer_type_record_count, integer_type_records = DataCheck.get_integer_type_record_details(left_df, column)
                            varchar_type_records_count, varchar_type_records = DataCheck.get_varchar_type_record_details(left_df, column)

                            multi_data_type_records_count = [date_type_records_count, float_type_records_count, integer_type_record_count, varchar_type_records_count]
                            multi_data_type_records = [date_type_records, float_type_records, integer_type_records, varchar_type_records]

                        if max(multi_data_type_records_count) != actual_record_count_left_data_frame:
                            error_causing_records_index = multi_data_type_records_count.index(min(multi_data_type_records_count))
                            print("------------------------ left data frame with mis match data types --------------------------------")
                            print(multi_data_type_records[error_causing_records_index])

                    if len(object_type_columns_in_right_df) > 0:
                        multi_data_type_records_count = None
                        multi_data_type_records = None
                        for column in object_type_columns_in_right_df:
                            date_type_records_count, date_type_records = DataCheck.get_date_type_record_details(right_df, column)
                            float_type_records_count, float_type_records = DataCheck.get_float_type_record_details(right_df, column)
                            integer_type_record_count, integer_type_records = DataCheck.get_integer_type_record_details(right_df, column)
                            varchar_type_records_count, varchar_type_records = DataCheck.get_varchar_type_record_details(right_df, column)

                            multi_data_type_records_count = [date_type_records_count, float_type_records_count, integer_type_record_count, varchar_type_records_count]
                            multi_data_type_records = [date_type_records, float_type_records, integer_type_records, varchar_type_records]

                        if max(multi_data_type_records_count) != actual_record_count_right_data_frame:
                            error_causing_records_index = multi_data_type_records_count.index(min(multi_data_type_records_count))
                            print("------------------------ right data frame with mis match data types --------------------------------")
                            print(multi_data_type_records[error_causing_records_index])
                    print("-------------------------------------------------------------------------------------------")
                else:
                    pass

            elif operation_type == 'filter' and type(data_frames) != list:
                print("------------------- performing data type validations on filters --------------------------")
                object_type_columns_in_df = data_frames.select_dtypes('object').columns.to_list()
                object_type_columns_in_df = list(set(column_names) & set(object_type_columns_in_df))
                logging.info(f"no object type columns in df {len(object_type_columns_in_df)}")
                actual_record_count_in_data_frame = len(data_frames.index)

                if len(object_type_columns_in_df) > 0:
                    multi_data_type_records_count = None
                    multi_data_type_records = None
                    for column in object_type_columns_in_df:
                        date_type_records_count, date_type_records = DataCheck.get_date_type_record_details(data_frames,
                                                                                                            column)
                        float_type_records_count, float_type_records = DataCheck.get_float_type_record_details(data_frames,
                                                                                                               column)
                        integer_type_record_count, integer_type_records = DataCheck.get_integer_type_record_details(
                            data_frames, column)
                        varchar_type_records_count, varchar_type_records = DataCheck.get_varchar_type_record_details(
                            data_frames, column)

                        multi_data_type_records_count = [date_type_records_count, float_type_records_count,
                                                         integer_type_record_count, varchar_type_records_count]
                        multi_data_type_records = [date_type_records, float_type_records, integer_type_records,
                                                   varchar_type_records]

                    if max(multi_data_type_records_count) != actual_record_count_in_data_frame:
                        error_causing_records_index = multi_data_type_records_count.index(
                            min(multi_data_type_records_count))
                        print("------------------------ data frame with mis match data types --------------------------------")
                        print(multi_data_type_records[error_causing_records_index])
                print("-----------------------------------------------------------------------------------------------")

            elif operation_type == 'conditional_join' and type(data_frames) == list:
                print("------------------- performing data type validations on conditional join --------------------------")
                left_df = data_frames[0]
                right_df = data_frames[1]
                left_key_columns = DataCheck.filter_cols_to_list(data_frames[0], column_names)
                right_key_columns = DataCheck.filter_cols_to_list(data_frames[1], column_names)

                object_type_columns_in_left_df = left_df.select_dtypes('object').columns.to_list()
                object_type_columns_in_left_df = list(set(left_key_columns) & set(object_type_columns_in_left_df))
                object_type_columns_in_right_df = right_df.select_dtypes('object').columns.to_list()
                object_type_columns_in_right_df = list(set(right_key_columns) & set(object_type_columns_in_right_df))
                logging.info(f"no object type columns in left df {len(object_type_columns_in_left_df)}")
                logging.info(f"no object type columns in right df {len(object_type_columns_in_right_df)}")
                actual_record_count_left_data_frame = len(left_df.index)
                actual_record_count_right_data_frame = len(right_df.index)

                if len(object_type_columns_in_left_df) > 0:
                    multi_data_type_records_count = None
                    multi_data_type_records = None
                    for column in object_type_columns_in_left_df:
                        date_type_records_count, date_type_records = DataCheck.get_date_type_record_details(left_df,
                                                                                                            column)
                        float_type_records_count, float_type_records = DataCheck.get_float_type_record_details(left_df,
                                                                                                               column)
                        integer_type_record_count, integer_type_records = DataCheck.get_integer_type_record_details(
                            left_df, column)
                        varchar_type_records_count, varchar_type_records = DataCheck.get_varchar_type_record_details(
                            left_df, column)

                        multi_data_type_records_count = [date_type_records_count, float_type_records_count,
                                                         integer_type_record_count, varchar_type_records_count]
                        multi_data_type_records = [date_type_records, float_type_records, integer_type_records,
                                                   varchar_type_records]

                    if max(multi_data_type_records_count) != actual_record_count_left_data_frame:
                        error_causing_records_index = multi_data_type_records_count.index(
                            min(multi_data_type_records_count))
                        print("------------------------ left data frame with mis match data types --------------------------------")
                        print(multi_data_type_records[error_causing_records_index])

                if len(object_type_columns_in_right_df) > 0:
                    multi_data_type_records_count = None
                    multi_data_type_records = None
                    for column in object_type_columns_in_right_df:
                        date_type_records_count, date_type_records = DataCheck.get_date_type_record_details(right_df,
                                                                                                            column)
                        float_type_records_count, float_type_records = DataCheck.get_float_type_record_details(right_df,
                                                                                                               column)
                        integer_type_record_count, integer_type_records = DataCheck.get_integer_type_record_details(
                            right_df, column)
                        varchar_type_records_count, varchar_type_records = DataCheck.get_varchar_type_record_details(
                            right_df, column)

                        multi_data_type_records_count = [date_type_records_count, float_type_records_count,
                                                         integer_type_record_count, varchar_type_records_count]
                        multi_data_type_records = [date_type_records, float_type_records, integer_type_records,
                                                   varchar_type_records]

                    if max(multi_data_type_records_count) != actual_record_count_right_data_frame:
                        error_causing_records_index = multi_data_type_records_count.index(
                            min(multi_data_type_records_count))
                        print("------------------------ right data frame with mis match data types --------------------------------")
                        print(multi_data_type_records[error_causing_records_index])

                print("-------------------------------------------------------------------- --------------------------")

                pass
            else:
                pass
            pass
        except Exception as error:
            print(
                "----------------------------------------------------------------------------------------------------")
            pass

    @staticmethod
    def get_varchar_type_record_details(data_frame, column_name):
        """
        :param data_frame:
        :param column_name:
        :return: actual record count, filtered record count and filtered data frame
        """

        record_count = data_frame[column_name][data_frame[column_name].str.match(r'(A-Za-z)') == True].count()
        index_list = data_frame[column_name][data_frame[column_name].str.match(r'(A-Za-z)') == True].index.to_list()
        df_with_varchar_values = data_frame.iloc[index_list]

        try:
            df_with_varchar_values[column_name].astype('string')
        except Exception as error:
            print("------------------ error causing data frame ------------------")
            print(df_with_varchar_values[column_name])
            print("---------------------------------------------------------------")

        return record_count, df_with_varchar_values

    @staticmethod
    def get_integer_type_record_details(data_frame, column_name):
        """
        :param data_frame:
        :param column_name:
        :return: actual record count, filtered record count and filtered data frame
        """

        record_count = data_frame[column_name][data_frame[column_name].str.match(r'\d+\.\d+') == False].count()
        index_list = data_frame[column_name][data_frame[column_name].str.match(r'\d+\.\d+') == False].index.to_list()
        df_with_varchar_values = data_frame.iloc[index_list]

        try:
            df_with_varchar_values[column_name].astype('int')
        except Exception as error:
            print("------------------ data type mismatch observed on key columns ------------------")
            print(df_with_varchar_values[column_name])
            print("---------------------------------------------------------------")

        return record_count, df_with_varchar_values

    @staticmethod
    def get_float_type_record_details(data_frame, column_name):
        """
        :param data_frame:
        :param column_name:
        :return: actual record count, filtered record count and filtered data frame
        """

        record_count = data_frame[column_name][data_frame[column_name].str.match(r'\d+\.\d+') == True].count()
        index_list = data_frame[column_name][data_frame[column_name].str.match(r'\d+\.\d+') == True].index.to_list()
        df_with_varchar_values = data_frame.iloc[index_list]

        try:
            df_with_varchar_values[column_name].astype('float')
        except Exception as error:
            print("------------------ error causing data frame ------------------")
            print(df_with_varchar_values[column_name])
            print("---------------------------------------------------------------")

        return record_count, df_with_varchar_values

    @staticmethod
    def get_date_type_record_details(data_frame, column_name):
        """
        :param data_frame:
        :param column_name:
        :return: actual record count, filtered record count and filtered data frame
        """

        record_count = data_frame[column_name][data_frame[column_name].str.match(r'^([1-9] |1[0-9]| 2[0-9]|3[0-1])(.|-)([1-9] |1[0-2])(.|-|)[1-2][0-9][0-9][0-9]$') == True].count()
        index_list = data_frame[column_name][data_frame[column_name].str.match(r'^([1-9] |1[0-9]| 2[0-9]|3[0-1])(.|-)([1-9] |1[0-2])(.|-|)[1-2][0-9][0-9][0-9]$') == True].index.to_list()
        df_with_varchar_values = data_frame.iloc[index_list]

        try:
            df_with_varchar_values[column_name].astype('datetime64[ns]')
        except Exception as error:
            print("------------------ error causing data frame ------------------")
            print(df_with_varchar_values[column_name])
            print("---------------------------------------------------------------")

        return record_count, df_with_varchar_values

    @staticmethod
    def filter_cols_to_list(data_frame, filter_string):
        df_cols = data_frame.columns.to_list()
        final_cols_list = []
        for col in df_cols:
            if col.upper() in filter_string.upper():
                final_cols_list.append(col.upper)
        return final_cols_list









