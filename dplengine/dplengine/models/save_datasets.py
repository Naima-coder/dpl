# filename: save_datasets.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: saving the resultant data frames to a data base table or a file

import logging
import os
from datetime import datetime

import cx_Oracle
import numpy as np
import pandas as pd
import traceback

from common.file_name_generation import generate_file_name
from common.process_tracking import ProcessTracking
from common.profiling import profiling
from common.regex_operations import dataframe_columns_mapping
from models import process_datasets
from models import upsert_on_condition
from models.connections import Columns, Tables, GenerateQueries,DataBaseConnections as DBConn
from models.job_properties import JobProperties
from models.read_datasets import ReadDataset
from models.read_props_file import get_property
from resources.data_checking import DataCheck

log_name = get_property('log_name')
logging = logging.getLogger(log_name)

@profiling
def rename_drop_col(dataframe):
    """
    :param dataframe:
    :return:
    """
    try:
        col_name = dataframe.filter(regex='_s', axis=1).head().columns.values.tolist()
        rename_col_list = {}
        for col in col_name:
            rename_col_list[col] = col[:-2]
        dataframe = dataframe.rename(columns=rename_col_list)
        target_col_list = dataframe.filter(regex='_t', axis=1).head().columns.values.tolist()
        dataframe = dataframe.drop(target_col_list, axis=1)
        dataframe = dataframe.drop(['_merge'], axis=1)
    except Exception as e:
        exception_issue = f"Renaming source columns and removing target column while " \
                          f"aligning source with target  failed with following error......\n" \
                          f"Error: {e}\n Type of error: {type(e)}"
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'rename_drop_col'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
    else:
        return dataframe


def convert_nan_to_none(dataframe, datatypes, column_names_list):
    """
    Converts NAN/NAT to None and converts the datatype to target table datatype
    :param dataframe:
    :param datatypes:
    :param column_names_list:
    :return:
    """
    try:
        # Filling null values with -9999 value in total
        logging.debug("Filling 'Nan' values with -9999 value in total dataframe")
        start_time = datetime.now()
        try:
            dataframe.fillna(value=-9999, inplace=True)
        except Exception as e:
            exception_issue = f"Filling 'NAN/NAT' values with '-9999' failed with following error......\n" \
                              f"Error: {e}\n Type of error: {type(e)}"
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{'Filling Nan values with -9999 value in total dataframe'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
        # start_time = datetime.now()
        end_time = datetime.now()
        logging.debug(
            "time taken to convert nan to -9999 " + str((end_time - start_time).total_seconds()) + "sec")

        # Converting df_dataype_to_db_datatype
        conversion_start_time = datetime.now()
        dataframe = convert_datatype_df_to_db(datatypes=datatypes, dataframe=dataframe,
                                              column_names_list=column_names_list)
        conversion_end_time = datetime.now()
        logging.info(f"Time taken to convert df_dataype_to_db_datatype:"
                     f" {conversion_end_time - conversion_start_time} ")
        print(f"Time taken to convert df_dataype_to_db_datatype:"
              f" {conversion_end_time - conversion_start_time} ")

        if dataframe is None:
            exception_issue = f"Error in conversion of dataframes datatypes to target datatype....."
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{'Filling Nan values with -9999 value in total dataframe'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            print(exception_issue, '\n', traceback.format_exc(), '\n')
            raise Exception(exception_issue)
        print('spliting not null and null values...................................')

        split_start_time = datetime.now()
        values_to_replaced = {'-9999', -9999, -9999.0, '1969-12-31', '-9999.0', pd.to_datetime('1969-12-31'),
                              pd.to_datetime('1970-01-01'), np.NAN, np.NaN, np.nan, pd.NaT,
                              pd.to_datetime('1969-12-31 23:59:59.999990001'), '1-01-01 00:00:00'}
        null_df = dataframe[(dataframe.isin(values_to_replaced)).any(axis=1)]
        # Converting dataframe into key_value records
        null_df_values = null_df.to_dict("records")
        print('\n\tlen of null_df_values: ', len(null_df_values))
        # not_null_df = dataframe[~(dataframe.isin(values_to_replaced)).any(axis=1)]
        # Clearing dataframe to free up memory
        del null_df

        # Added on 06/10/2020 at reduce time consumption while splitting
        # null and not null records
        if len(null_df_values) == 0:
            logging.info("Considering complete dataframe as not null df as null df values length is zero")
            not_null_df = dataframe
        elif len(null_df_values) != dataframe.shape[0]:
            logging.info("Splitting dataframe to get not null df")
            not_null_df = dataframe[~(dataframe.isin(values_to_replaced)).any(axis=1)]
        else:
            logging.info("Setting not_null_df as empty df ")
            not_null_df = pd.DataFrame(columns=dataframe.columns)

        # Converting dataframe into key_value records
        not_null_df_values = not_null_df.to_dict("records")
        print('\tlen of not_null_df_values: ', len(not_null_df_values))

        # Clearing dataframe to free up memory
        del not_null_df

        # null_df_values = [tuple(x) for x in null_df.values]
        # # Converting dataframe into key_value records
        # null_df_values = null_df.to_dict("records")
        # print('\n\tlen of null_df_values: ', len(null_df_values))
        #
        # # not_null_df_values = [tuple(x) for x in not_null_df.values]
        # not_null_df_values = not_null_df.to_dict("records")
        # print('\tlen of not_null_df_values: ', len(not_null_df_values))
        split_end_time = datetime.now()
        logging.info(f"Time taken to split null and not null values: "
                     f"{split_end_time - split_start_time}")
        print(f"Time taken to split null and not null values: "
              f"{split_end_time - split_start_time}")

        logging.debug("Converting '-9999' values to null values ")
        print("Converting '-9999' values to null values ")

        # for value in null_df_values:
        #      print(value)
        #      for val in value:
        #          print(val, type(val))
        #      break
        start_time = datetime.now()
        reps = {'nan': None, '-9999': None, '-9999.0': None, '1969-12-31': None, 'Nan': None, 'NaT': None, 'nat': None,
                -9999: None, -9999.0: None, (datetime.strptime('1969-12-31', '%Y-%m-%d')).date(): None,
                datetime.strptime('1969-12-31 00:00:00', '%Y-%m-%d %H:%M:%S'): None,
                pd.to_datetime('1969-12-31 23:59:59.999990001'): None,
                pd.to_datetime('1969-12-31'): None, pd.to_datetime('1970-01-01'): None,
                datetime.strptime('1970-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'): None,
                datetime.strptime('0001-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'): None,
                pd.NaT: None, np.NaN: None, np.NAN: None, np.nan: None}

        # null_df_values = [[reps.get(x, x) for x in a] for a in null_df_values]
        null_df_values = [{x: reps.get(a[x], a[x]) for x in a} for a in null_df_values]

        values = []
        print('len of null_df_values: ', len(null_df_values), '\nlen of not_null_df_values: ', len(not_null_df_values))
        logging.info(
            f'len of null_df_values: {len(null_df_values)}\nlen of not_null_df_values: {len(not_null_df_values)}')
        values.extend(null_df_values)
        null_df_values.clear()
        values.extend(not_null_df_values)
        not_null_df_values.clear()

        # inserting_df = pd.DataFrame(values, columns=column_names)
        end_time = datetime.now()
        logging.debug("Time taken to convert -9999 to none : " + str((end_time - start_time).total_seconds()) + "sec")
        print("Time taken to convert -9999 to none : " + str((end_time - start_time).total_seconds()) + "sec")
    except Exception as e:
        exception_issue = f"Conversion of 'NAN/NAT' to 'None' failed with following error......\n" \
                          f"Error: {e}\n Type of error: {type(e)}"
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'Converting NAT/NAN to None in total dataframe'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        raise Exception(exception_issue)
    else:
        return values


@profiling
def truncate_table_data(cursor, connection, table_name, dataframe, del_query=None):
    """
    Truncates the data from given table
    :param cursor:
    :param connection:
    :param table_name:
    :param dataframe:
    :param del_query:
    :return:
    """

    print("table name for truncation", table_name)
    trg_file_path = None
    try:
        # Creating a backup file of table data
        trg_file_name, trg_file_path = generate_file_name(directory_name=get_property('backup_file_path'),
                                                          file_type='dt_bkp', file_extension='csv')
        # trg_file_name = trg_file_name.replace('.txt', '.csv')
        logging.info(f"Saving truncating table data to a csv file: {trg_file_name}")
        dataframe.to_csv(os.path.join(trg_file_path, trg_file_name), index=None)
        del dataframe
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                        f"[dploperation:{'none'}][pyoperation:{trg_file_path}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]")

        # Deleting data from target table
        logging.info(f"Deleting data from table {table_name}")
        if del_query is not None:
            logging.info("Deleting query: " + str(del_query) + '\n')
            cursor.execute(del_query)
            connection.commit()
            print(f"no of records deleted :{cursor.rowcount}")
        else:
            delete_query = "delete from " + str(table_name)
            logging.info("Deleting query: " + str(delete_query) + '\n')
            cursor.execute(delete_query)
            connection.commit()
            print(f"no of records deleted :{cursor.rowcount}")
    except Exception as e:
        exception_issue = f"Error occurred while truncating the table \n" \
                          f"Error: {e}\nType of error: {type(e)}"
        logging.error(exception_issue)
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{trg_file_path}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        print("Exception : ", str(e))
        DBConn.close_connection(connection=connection)
        raise Exception(exception_issue)


@profiling
def incremental_column_value_generation(insert_key, table_name, cursor, connection, dataframe, dbtype=None,
                                        create_column=None, max_insert_key=None):
    """
    Increments values in given column
    :param insert_key:
    :param table_name:
    :param cursor:
    :param connection:
    :param dataframe:
    :param dbtype:
    :param create_column:
    :param max_insert_key:
    :return:
    """
    if insert_key in dataframe.columns:
        pass
    else:
        query = None
        try:
            if dbtype.lower() == 'postgressql':
                query = 'alter table ' + table_name + ' add column ' + insert_key + ' int'
            else:
                query = 'alter table ' + table_name + ' add (' + insert_key + ' int)'
            logging.info("Appending a surrogate column to table using query: " + str(query) + '\n')
            print(query)
            cursor.execute(query)
            connection.commit()
        except Exception as e:
            if 'column being added already exists in table' in str(e):
                logging.warning("Appending already exists column to table")
                pass
            else:
                exception_issue = f"Adding column: {insert_key} to table: {table_name} failed with error" \
                                  f"\nError: {e}\nType of Error: {type(e)}"
                logging.error(exception_issue)
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'conditional join'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                f"[dploperation:{'none'}][pyoperation:{query}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                                trace_back=traceback.format_exc(), subject='Exception-critical')
                raise Exception(e)

        dataframe[insert_key] = None
    print("auto increment key generation")
    column_to_be_increased = insert_key

    try:
        # Getting maximum value present in that column
        if max_insert_key:
            max_value_of_column = max_insert_key
        else:
            max_value_of_column = int(dataframe[column_to_be_increased].max()) + 1
        print("max vlaue of the column", max_value_of_column)

        # Getting incrementing last value by adding count of null in that column with max_value of that column
        range_end_value = dataframe[insert_key].isnull().sum() + max_value_of_column
        print("range end value", range_end_value)

        # Generating a list with column values in given range
        column_values = [item for item in range(max_value_of_column, range_end_value)]

        # Getting sub_dataframe from dataframe where surrogate key column values are null
        surrogate_key_null_df = dataframe[dataframe[insert_key].isnull()]
        print("surrogate_key_null_df", surrogate_key_null_df)

        # Changing values of surrogate key column with list values
        surrogate_key_null_df[insert_key] = column_values
        # print("Updated surrogate_df:.................................................")
        # print(surrogate_key_null_df)

        # Deleting sub_dataframe from dataframe where surrogate key column values are null
        dataframe_without_null_in_skey = dataframe.dropna(subset=[insert_key])
        # print(
        #     "Dataframe after deletion of null values:..........................................................")
        # print(dataframe)

        # Concating surrogate_key_null_df with dataframe_without_null_in_skey
        dataframe = pd.concat([dataframe_without_null_in_skey, surrogate_key_null_df])

        print(
            "Dataframe after concatenation:..........................................................")
        print(dataframe)
        return dataframe

    except ValueError as ve:
        if str(ve) == 'cannot convert float NaN to integer':
            logging.warning("Column values are completely null \n" + str(ve))
            max_value_of_column = 1
            column_values = [item for item in range(max_value_of_column, dataframe.shape[0] + 1)]
            dataframe[insert_key] = column_values
            print(dataframe)
            return dataframe
        else:
            exception_issue = f"Failed to add an incremental column to dataframe with error\n" \
                              f"Error: {ve}\nType of error: {type(ve)}"
            logging.error(exception_issue)
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{ve}][pyoperation:{'none'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            DBConn.close_connection(connection=connection)
            raise ValueError(ve)
    except Exception as e:
        exception_issue = f"Failed to add an incremental column to dataframe with error\n" \
                          f"Error: {e}\nType of error: {type(e)}"
        logging.error(exception_issue)
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        DBConn.close_connection(connection=connection)
        raise Exception(exception_issue)


@profiling
def sync_with_source(source_df, target_df, conditional_columns, table_name, datatypes, columns, connection, cursor,
                     dbtype):
    """
    Syncs given source dataset with target dataset
    :param source_df:
    :param target_df:
    :param conditional_columns:
    :param table_name:
    :param datatypes:
    :param columns:
    :param connection:
    :param cursor:
    :param dbtype:
    :return:
    """
    try:

        """
        Change on 08/26/2020
        Commented the old code to avoid datatype mismatch errors that occurred while joining both 
        source and target dataframes 
        In new one replaced joining(merge) logic with concat(union) and drop_duplicates
        
        Removed old code on 10/08/2020
        """

        print("Getting records to be inserted...................")
        logging.info("Getting records to be inserted...................")
        insert_df = pd.concat([source_df, target_df, target_df], sort=False).drop_duplicates(subset=conditional_columns,
                                                                                             keep=False)
        delete_df = pd.concat([source_df, source_df, target_df], sort=False).drop_duplicates(subset=conditional_columns,
                                                                                             keep=False)
        update_df = pd.concat([source_df, target_df, insert_df, delete_df], sort=False).drop_duplicates(keep=False)
        if not insert_df.empty:
            print(f'\n{insert_df}')
            logging.info("Inserting record into db.....................................................")
            insert_into_db(dataframe=insert_df, datatypes=datatypes, table_name=table_name,
                           columns=columns, connection=connection, cursor=cursor, dbtype=dbtype)
        else:
            print("No new records found to insert...............................\n")

        print("Getting records to be deleted...................")
        logging.info("Getting records to be deleted...................")
        # Preparing delete query
        i = 1
        where_col_string = ''
        for col in conditional_columns:
            where_col_string += f'{col} = :{col} and '
            i += 1
        where_col_string = where_col_string[:-4]
        delete_df = delete_df[conditional_columns]
        delete_query = f'delete from {table_name} where {where_col_string}'

        if not delete_df.empty:
            print(f'\n{delete_df}')
            print(delete_query, '\n')
            logging.info("Deleting query: " + str(delete_query) + '\n')
            values = convert_nan_to_none(dataframe=delete_df, datatypes=datatypes,
                                         column_names_list=conditional_columns)
            logging.info("Deleting records.......................\n")
            
            # Added on 09072020 to insert timestamp column along with nano seconds
            logging.info("Setting input sizes to insert timestamp column along with nano seconds")
            date_columns = [col for col in delete_df.columns if delete_df[col].dtype == 'datetime64[ns]']
            convert_list = {}
            for column in date_columns:
                convert_list[column] = cx_Oracle.TIMESTAMP
            cursor.setinputsizes(**convert_list)
            # Ended on 09072020 to insert timestamp column along with nano seconds

            row_count = JobProperties.save_db_chunk(delete_query, values, connection, cursor)
            print("values count", len(values), "data frame index count", len(delete_df.index), "shape",
                  delete_df.shape[0], "row count", row_count)
            # Added on 11/12/2020 to avoid checkDBCommit if given in yml
            if not db_count_check:
                DataCheck.checkDBCommit(len(values), row_count)
            # cursor.executemany(delete_query, values)
            # connection.commit()
        else:
            print("No records found to be deleted...............\n")

        print("Getting records to be updated...................")
        logging.info("Getting records to be updated...................")
        update_df = update_df.drop_duplicates(subset=conditional_columns, keep='first')
        # Preparing update query
        df_columns = update_df.columns.values.tolist()
        update_query, df_column_order = GenerateQueries. \
            update_query(dbtype=dbtype, df_columns=df_columns, conditional_columns=conditional_columns,
                         table_name=table_name)
        update_df = update_df[df_column_order]
        logging.info("Updating query: " + str(update_query) + '\n')

        if not update_df.empty:
            print(update_query)
            print(f'\n{update_df}')
            logging.info("Updating records...................................................")
            print("Updating records...................................................")
            values = convert_nan_to_none(dataframe=update_df, datatypes=datatypes, column_names_list=df_column_order)
            start_time = datetime.now()

            # Added on 09072020 to insert timestamp column along with nano seconds
            logging.info("Setting input sizes to insert timestamp column along with nano seconds")
            date_columns = [col for col in update_df.columns if update_df[col].dtype == 'datetime64[ns]']
            convert_list = {}
            for column in date_columns:
                convert_list[column] = cx_Oracle.TIMESTAMP
            cursor.setinputsizes(**convert_list)
            # Ended on 09072020 to insert timestamp column along with nano seconds

            row_count = JobProperties.save_db_chunk(update_query, values, connection, cursor)
            print("values count", len(values), "data frame index count", len(update_df.index), "shape",
                  update_df.shape[0],
                  "row count", row_count)

            # Added on 11/12/2020 to avoid checkDBCommit if given in yml
            if not db_count_check:
                DataCheck.checkDBCommit(len(values), row_count)

            # cursor.executemany(update_query, values)
            # connection.commit()
            end_time = datetime.now()
            difference = end_time - start_time
            logging.debug(f"Time taken for updating target table {table_name}: {difference} ")
            logging.info(f"{row_count} records updated successfully")
        else:
            print("No records found to update..................................\n")
    except Exception as e:
        exception_issue = f"Syncing source with target failed due to following error\n" \
                          f"Error: {e}\nType of error: {type(e)}"
        logging.error(exception_issue)
        print(exception_issue)
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'save_to_database--->align_with_source'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        DBConn.close_connection(connection=connection)
        raise Exception(exception_issue)


@profiling
def update_with_source(source_df, target_df, conditional_columns, updating_columns, table_name, datatypes, columns,
                       connection, cursor):
    """
    Updates the target table with update in source
    :param source_df:
    :param target_df:
    :param conditional_columns:
    :param updating_columns:
    :param table_name:
    :param datatypes:
    :param columns:
    :param connection:
    :param cursor:
    :return:
    """

    # ----------------------------------UPDATE DATA--------------------------------------------------

    dataframes = []
    # source_df = convert_datatype_df_to_db(datatypes=datatypes, dataframe=source_df, column_names_list=source_df.columns.values.tolist()) 
    df_a = target_df.merge(source_df, on=conditional_columns, how='outer',
                           suffixes=['_a', ''])
    col_name = df_a.filter(regex='_a', axis=1).head().columns.values.tolist()
    # print("col_names after upsert_cond merge: ", df_a.columns.values.tolist())
    for col in col_name:
        df_a[col[:-2]] = df_a[col[:-2]].fillna(df_a[col])
    for col in col_name:
        del df_a[col]
    # df_a = df_a[column_names]
    dataframes.append(df_a)

    df = pd.DataFrame()
    # if not (dataframes[0].empty or dataframes[1].empty):
    if len(dataframes) != 1:
        if not dataframes[1].empty:
            df = pd.concat(dataframes)
            print("upsert conditional df")
        else:
            df = dataframes[0]
    else:
        df = dataframes[0]

    update_df = df
    # Preparing update query
    df_columns = update_df.columns.values.tolist()
    # columns_to_update = list(set(df_columns) - set(conditional_columns))
    columns_to_update = updating_columns
    i = 1
    set_col_string = ''
    for col in columns_to_update:
        set_col_string += f'{col} = :{col}, '
        i += 1
    set_col_string = set_col_string[:-2]

    where_col_string = ''
    for col in conditional_columns:
        where_col_string += f'{col} = :{col} and '
        i += 1
    where_col_string = where_col_string[:-4]
    df_columns_order = columns_to_update + conditional_columns
    update_df = update_df[df_columns_order]
    update_query = f"update {table_name} set {set_col_string} where {where_col_string}"
    print(update_query)
    logging.info("Updating query: " + str(update_query) + '\n')
    values = convert_nan_to_none(dataframe=update_df, datatypes=datatypes, column_names_list=df_columns_order)

    print('---------------------------\nUPSERT_DF\n', update_df, '\n---------------------------\n')
    try:
        start_time = datetime.now()

        # Added on 09072020 to insert timestamp column along with nano seconds
        logging.info("Setting input sizes to insert timestamp column along with nano seconds")
        date_columns = [col for col in update_df.columns if update_df[col].dtype == 'datetime64[ns]']
        convert_list = {}
        for column in date_columns:
            convert_list[column] = cx_Oracle.TIMESTAMP
        cursor.setinputsizes(**convert_list)
        # Ended on 09072020 to insert timestamp column along with nano seconds

        row_count = JobProperties.save_db_chunk(update_query, values, connection, cursor)
        print("values count", len(values), "data frame index count", len(update_df.index), "shape", update_df.shape[0],
              "row count", row_count)
        # Added on 11/12/2020 to avoid checkDBCommit if given in yml
        if not db_count_check:
            DataCheck.checkDBCommit(len(values), row_count)

        end_time = datetime.now()
        difference = end_time - start_time
        logging.debug(f"Time taken for updating target table {table_name}: {difference} sec")
        logging.info(f"{row_count} records updated successfully")
    except Exception as error:
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'update to database'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')


@profiling
def convert_datatype_df_to_db(datatypes, column_names_list, dataframe):
    """
    Convert dataframe columns datatypes to the target_table datatypes
    :param datatypes:
    :param column_names_list:
    :param dataframe:
    :return:
    """
    # Converting datatype of columns in dataframe into datatype in table
    try:
        logging.debug("Converting datatype of columns in dataframe into datatype in table")
        print("Converting datatype of columns in dataframe into datatype in table...............")

        for col in datatypes:
            column = col[0]
            data_type = col[1]
            # Added on 08/10/2020 to avoid case-sensitive mismatch
            column = dataframe_columns_mapping(dataframe, column)
            if column in column_names_list:
                if 'VARCHAR' in data_type:
                    dataframe[column] = dataframe[column].astype('str')
                elif 'TIMESTAMP' in data_type or 'DATE' in data_type:
                    logging.info(f"Converting '{column}' to date/timestamp datatype...............\n"
                                 f"Column: {column} information before typecast......................\n"
                                 f"{dataframe[column].describe()}\n{column}: {dataframe[column].dtype}\n"
                                 f"No.of nulls in {column} column: {dataframe[column].isnull().sum()}")
                    try:
                        logging.info(
                            f"Replacing value '0001-01-01 00:00:00/0001-01-01' to default pandas datetime "
                            f"value('1969-12-31') to avoid 'Out of bounds nanosecond timestamp'\n")
                        # f"Replacing value '9999-12-31 00:00:00/9999-12-31' to default value '2120-12-31'"
                        # f" to avoid 'Out of bounds nanosecond timestamp'")
                        dataframe[column] = dataframe[column].replace(to_replace='0001-01-01 00:00:00',
                                                                      value='1969-12-31')
                        dataframe[column] = dataframe[column].replace(to_replace='0001-01-01',
                                                                      value='1969-12-31')
                        # dataframe[column] = dataframe[column].replace(to_replace='9999-12-31 00:00:00',
                        #                                               value='2120-12-31')
                        # print(dataframe[column])
                        # dataframe[column] = dataframe[column].replace(to_replace='9999-12-31',
                        #                                               value='2120-12-31')
                        dataframe[column] = pd.to_datetime(dataframe[column])
                        logging.info(f"Column: {column} information after typecast......................\n"
                                     f"{dataframe[column].describe()}\n{column}: {dataframe[column].dtype}\n"
                                     f"No.of nulls in {column} column: {dataframe[column].isnull().sum()}")
                    except Exception as e:
                        # print(f"error......\n{e}")
                        exception_issue = f"Datatype of column '{column}' in dataframe: {dataframe[column].dtype}\n" \
                                          f"Column: {column} information ......................\n" \
                                          f"{dataframe[column].describe()}\n" \
                                          f"No.of nulls in {column} column: {dataframe[column].isnull().sum()}\n" \
                                          f"Converting column {column} to datetime failed with following error:\n" \
                                          f"Error: {e}\nType of error: {type(e)}"
                        logging.error(exception_issue)
                        if str(e) == 'mixed datetimes and integers in passed array':
                            logging.warning(f"Exception while converting column {column} into datetime..........\n{e}")
                            logging.warning(
                                "Replacing value '-9999' value to default pandas datetime value('1969-12-31')"
                                f" to avoid 'mixed datetimes and integers in passed array'")
                            dataframe[column] = dataframe[column].replace(to_replace=-9999, value='1969-12-31')
                            try:
                                logging.info("Typecasting after 'mixed datetimes and integers in passed array' error")
                                dataframe[column] = pd.to_datetime(dataframe[column])
                            except Exception as e2:
                                exception_issue2 = f"Datatype of column '{column}' in dataframe: {dataframe[column].dtype}\n" \
                                                   f"Column: {column} information ......................\n" \
                                                   f"{dataframe[column].describe()}\n" \
                                                   f"No.of nulls in {column} column: {dataframe[column].isnull().sum()}\n" \
                                                   f"Converting column {column} to datetime failed with following error:\n" \
                                                   f"Error: {e2}\nType of error: {type(e2)}"
                                if str(e2) != 'Reindexing only valid with uniquely valued Index objects':
                                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                                    f"[pyprocessstep:{'none'}]"
                                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                                    f"[dploperation:{'none'}][pyoperation:{f'Exception while typecasting {column} to datetime...:n{e2}'}]"
                                                                    f"[pyobject:{'none'}]"
                                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                                    f"[dpldataset:{'none'}]"
                                                                    f"[timestamp:{datetime.now()}]",
                                                                    excepetion=exception_issue2,
                                                                    trace_back=traceback.format_exc(),
                                                                    subject='Exception-info')
                                logging.error(exception_issue2)

                                if str(e2) == 'Reindexing only valid with uniquely valued Index objects':
                                    logging.critical(exception_issue2)
                                else:
                                    logging.error(f"Exception while typecasting {column} to datetime...: \n"
                                                  f"Error: {e2}\nType of error: {type(e2)}")
                                    raise Exception(f"Exception while typecasting {column} to datetime...: \n"
                                                    f"Error: {e2}\nType of error: {type(e2)})")

                        elif str(e) == 'Reindexing only valid with uniquely valued Index objects':
                            # col_df = dataframe[column]
                            # print(column, dataframe[column].dtype)
                            logging.critical(f"Datatype of column '{column}' in dataframe: {dataframe[column].dtype}\n"
                                             f"Column: {column} information ......................\n"
                                             f"{dataframe[column].describe()}\n"
                                             f"No.of nulls in {column} column: {dataframe[column].isnull().sum()}\n"
                                             f"Converting column {column} to datetime failed with following error:\n"
                                             f"Error: {e}\nType of error: {type(e)}")
                        else:
                            # print(f"in else block..............\nError: {e}")
                            # print("raising an exception.....................................\n")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                            f"[dploperation:{'none'}][pyoperation:{f'Exception while typecasting {column} to datetime...:n{e}'}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]",
                                                            excepetion=e,
                                                            trace_back=traceback.format_exc(),
                                                            subject='Exception-info')
                            logging.error(f"Exception while typecasting {column} to datetime...: \n{e}")
                            raise Exception(f"Exception while typecasting {column} to datetime...: \n{e}")
                        # logging.warning(f"Exception while converting column {column} to datetime\n {e} ")
                elif 'NUMBER' in data_type:
                    dataframe[column] = dataframe[column].astype('float64')
                elif 'FLOAT' in data_type:
                    dataframe[column] = dataframe[column].astype('float64')

        return dataframe

    except Exception as error:
        logging.error(f"Exception while converting datatypes......:\n{error}")
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'save to database'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        raise Exception(f"Exception while converting datatypes......:\n{error}")


@profiling
##Todo#  trigger_script added by Naima vr for triggering script   functionality.
def insert_into_db(columns, dataframe, datatypes, table_name, connection, cursor, dbtype,trigger_script):
    """
    Inserts dataframe values into db
    :param columns:
    :param dataframe:
    :param datatypes:
    :param table_name:
    :param connection:
    :param cursor:
    :return:
    """
    values_len_list = []
    # Getting columns names from dataframe
    if columns == '':
        column_names = dataframe.columns.values
    else:
        column_names = columns
        dataframe = dataframe[columns]
    column_names_list = column_names

    # Converting NaN/NaT to None values
    values = convert_nan_to_none(dataframe, datatypes, column_names_list)

    for col in column_names:
        if dbtype.lower() == 'oracle':
            values_len_list.append(f':{col}')
        else:
            values_len_list.append(f'%s')

    # Converts list to string
    values_len_list = ', '.join(values_len_list)
    # print(values_len_list)

    # Converts list to string
    column_names = ', '.join(column_names)

    if dbtype.lower() == 'oracle':
        table_name = table_name
    elif dbtype.lower() == 'postgressql':
        table_name = table_name
    else:
        owner_table = table_name.split(".", 1)
        owner = owner_table[0].upper()
        table_name = owner_table[1].upper()
    insert_query = f'insert into {table_name}  ({column_names})' \
                   f' values ({values_len_list})'
    print(insert_query)
    print(len(values))

    # i = 0
    # for value in values:
    #     print(value)
    #     for val in value:
    #         print(val, type(val))


    logging.info("Inserting query: " + str(insert_query) + '\n')
    start_time = datetime.now()
    row_count = None
    try:
        # Added on 09072020 to insert timestamp column along with nano seconds
        logging.info("Setting input sizes to insert timestamp column along with nano seconds")
        date_columns = [col for col in dataframe.columns if dataframe[col].dtype == 'datetime64[ns]']
        convert_list = {}
        if dbtype.lower() == 'oracle':
           for column in date_columns:
              convert_list[column] = cx_Oracle.TIMESTAMP
           cursor.setinputsizes(**convert_list)
        # Ended on 09072020 to insert timestamp column along with nano seconds

        row_count = JobProperties.save_db_chunk(insert_query, values, connection, cursor,dbtype)
        ## Added by Naima VR for calling the trigger_scheduler function
        if trigger_script !=None:
            JobProperties.trigger_scheduler(trigger_script)
    except Exception as error:
        print("error",error)
        logging.error(error)
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'insert into db'}][pyoperation:{insert_query}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                        trace_back=traceback.format_exc(), subject='Exception-info')
        DBConn.close_connection(connection=connection)
        raise error
    print("values count", len(values), "data frame index count", len(dataframe.index), "shape", dataframe.shape[0],
          "row count", row_count)
    # Added on 11/12/2020 to avoid checkDBCommit if given in yml
    if not db_count_check:
        DataCheck.checkDBCommit(len(values), row_count)

    logging.info(f"Inserted {len(values)} into {table_name}")
    end_time = datetime.now()
    logging.info("INSERTION DURATION: " + str(end_time - start_time))
    # ProcessTracking.capture_process(f"RC-0-insert query to table-query{insert_query}")
    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                    f"[pyprocessstep:{'none'}]"
                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                    f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                    f"[pyobject:{insert_query}]"
                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                    f"[dpldataset:{'none'}]"
                                    f"[timestamp:{datetime.now()}]")
    connection.commit()

    print("saved to db")
    print("-----------------------------------------------------------------------------------------")


class SaveDataFrame:

    @staticmethod
    @profiling

 ##TODO# comp3_col,insert_string,date_format,data_structure,trigger_script are  Added by Naima VR
 ##TODO# record_length added by Guru Arun
    def save_to_file(path, dataframe, filters, columns, delimiter, file_type,headers,insert_string,date_format,data_structure,trigger_script,record_length,comp3_col=[],logging=logging, dataset=None):
        """
        Saves dataframe in csv format in desired path
        :param path:
        :param dataframe:
        :param filters:
        :param columns:
        :param logging:
        :param dataset:
        :param comp3_col
        :param insert_string
        :return:
        """
        if filters != '':
            dataframe = process_datasets.filter_data_frame(data_frame=dataframe, filters=filters)
        if columns != '':
            dataframe = dataframe[columns]
       ##TODO #Added by Naima VR for maintaining space adjustment to keep same length as in copy book
        if data_structure != None:
           if not os.path.dirname(data_structure):
                    try:
                        root=os.path.split(path)[0]
                        data_structure= os.path.join(root,data_structure)
                        print("data_structure file path : ",data_structure)
                    except Exception as e:
                        print("An Error occoured while looking for data_structure file: ",e)
           else:
               data_structure=data_structure      
           dataframe=process_datasets.align_copybook_to_dataframe(data_structure,dataframe)

       
        logging.info("Saving to given file: " + str(path) + "\n")
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                        f"[dploperation:{'none'}][pyoperation:{path}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{dataset}]"
                                        f"[timestamp:{datetime.now()}]")
        print("Saving to file: " + str(path))
        print("-----------------------------------------------------------------------------------------")

        # return dataframe.to_csv(path, index=None)
        logging.debug(f"Writing {dataframe.shape[0]} into {path}")
        try:
            # Added on 12/09/2020 to save to a parquet file
            file_name, file_ext = os.path.splitext(path)
            # print("file_ext", file_ext)
            if file_ext != '.parquet':
                ##Todo #Added by Naima vr for trigger_script,insert_string,headers ,date_format
                result = JobProperties.save_file_chunk(path, dataframe, delimiter, file_type,headers,insert_string,date_format,trigger_script,record_length=record_length,comp3_col=comp3_col                                                       )
            else:
                logging.info("Writing to parquet file")
                result = dataframe.to_parquet(path, use_deprecated_int96_timestamps=True)
            # Ended on 12/09/2020 to save to a parquet file
        except Exception as error:
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{'none'}][pyoperation:{path}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{dataset}]"
                                            f"[timestamp:{datetime.now()}][Exception:{error}]")

        else:
            return result

    @staticmethod
    @profiling
##New parameter trigger_script added By Naima VR
    def save_to_db(table_name, columns, filters, create_table, create_column, cursor, connection, dataframe, dbtype,
                   insert_type, insert_cond, insert_key, truncate_before_load,trigger_script,target_filter=None,
                   excludecolumns=None, save_conditions=None, logging=logging):
        """
        Saves dataframe to required table in given database
        :param table_name:
        :param columns:
        :param filters:
        :param create_table:
        :param create_column:
        :param cursor:
        :param connection:
        :param dataframe:
        :param dbtype:
        :param insert_type:
        :param insert_cond:
        :param insert_key:
        :param truncate_before_load:
        :param trigger_script
        :param target_filter:
        :param excludecolumns:
        :param save_conditions:
        :param logging:
        :return:
        """

        global db_count_check
        print("save_conditions", save_conditions)
        db_count_check = save_conditions['commit_count_mismatch']
        logging.info("Saving to table: " + str(table_name))
        if filters != '':
            dataframe = process_datasets.filter_data_frame(data_frame=dataframe, filters=filters)

        values_len_list = []
        # Includes necessary column from dataframe
        try:
            if columns != '':
                dataframe = dataframe[columns]
        except Exception as e:
            exception_issue = f"Exception occurred while selecting given columns in data_target section" \
                              f"\nError: {e}\nType of error: {type(e)}"
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'insert into db'}][pyoperation:{'selecting columns'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-info')
            raise Exception(exception_issue)

        # Excludes unnecessary column from dataframe
        if excludecolumns != [] and excludecolumns is not None:
            dataframe = process_datasets.exclude_column(dataframe, excludecolumns)
        column_names = dataframe.columns.values.tolist()
        print(f'column_names in dataframe that is being saved........\n{column_names}')

        table_status = Tables.check_if_table_exists(table_name, cursor, dbtype)
        print("table status",table_status)
        if table_status == False:
            # print("in table does not exist :", table_name, table_status)
            create_table_status = Tables.creating_table(table_name, dataframe, connection, cursor, dbtype, create_table)
            print("create_table_status",create_table_status)


        columns_status = Columns.check_if_columns_exists(table_name, column_names, cursor, dbtype)
        print('columns_status :', columns_status)
        if columns_status != True:
            # print("in columns status in creation :", columns_status)
            Columns.creating_columns(table_name, dataframe, connection, cursor, dbtype, create_column,
                                     table_column_names=columns_status)

        try:
            # cursor = connection.cursor()
            logging.info("Getting column datatypes from table")

            cursor.execute(Columns.column_names(dbtype, table_name))
            datatypes = cursor.fetchall()

            if truncate_before_load:
                print("Truncation....................")
                # Added on 10/09/2020 to generate a backup file based on user input
                if save_conditions['backup_before_truncate']:
                    # Reading data from target table
                    sql_query = 'select * from ' + str(table_name)
                    print(sql_query)
                    target_table_df = ReadDataset.read_sql_data(sql_query, connection, cursor, dbtype, excludecolumns=[])
                else:
                    target_table_df = pd.DataFrame()
                no_of_records = target_table_df.shape[0]
                print(no_of_records)
                # Deleting data from table
                print("Truncating table data before insertion")
                truncate_table_data(cursor, connection, table_name, target_table_df)
                print(f"Deleted {cursor.rowcount} records from {table_name}")

            print("insert_type",insert_type)
            if insert_type == 'insert_with_key':
                try:
                    query = 'SELECT MAX(' + insert_key + ') FROM ' + table_name
                    cursor.execute(query)
                    max_col_value = cursor.fetchone()
                    max_insert_key = max_col_value[0] + 1
                    print(max_insert_key)
                except Exception as e:
                    print(e)
                    max_insert_key = 1

                dataframe = incremental_column_value_generation(insert_key, table_name, cursor, connection, dataframe,
                                                                dbtype, create_column, max_insert_key)

                if not dataframe.empty:
                    insert_into_db(dataframe=dataframe, datatypes=datatypes, table_name=table_name,
                                   columns=columns, connection=connection, cursor=cursor, dbtype=dbtype,trigger_script=trigger_script)

            elif insert_type == 'upsert' or insert_type == 'upsert_with_key':
                logging.debug("upsert_function")
                print("upsert_function-------------------")

                # Reading data from target table
                start_time = datetime.now()
                if target_filter:
                    sql_query = 'select * from ' + str(table_name) + ' where ' + target_filter
                else:
                    sql_query = 'select * from ' + str(table_name)
                print(sql_query)
                target_table_df = ReadDataset.read_sql_data(sql_query, connection, cursor, dbtype)
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{insert_type}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                                f"[pyobject:{sql_query}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{dbtype}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")
                end_time = datetime.now()
                logging.debug(
                    "time taken to target table dataset as dataframe" + str(
                        (end_time - start_time).total_seconds()) + "sec")

                # print("condition")
                start_time = datetime.now()

                if insert_type == 'upsert_with_key':
                    insert_key = insert_key
                elif insert_type == 'upsert':
                    insert_key = None

                try:
                    dataframe = upsert_on_condition.upsert_fun(dataframe, target_table_df, insert_cond, datatypes,
                                                               table_name, connection, cursor, dbtype, insert_key)
                except Exception as e:
                    exception_issue = f"Exception occurred while upserting source data to target\n" \
                                      f"Error: {e}\nType of error: {type(e)}"
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                    f"[dploperation:{'insert into db'}][pyoperation:{'upsert_on_condition'}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{'none'}]"
                                                    f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                                    trace_back=traceback.format_exc(), subject='Exception-Critical')
                    DBConn.close_connection(connection=connection)
                    raise Exception(exception_issue)
                # dataframe = upsert_on_condition.upsert_fun(dataframe, target_table_df, insert_cond)
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{insert_type}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")
                end_time = datetime.now()
                print("Upsert fn duration:" + str((end_time - start_time).total_seconds()) + "sec")
                logging.debug("Upsert fn duration:" + str((end_time - start_time).total_seconds()) + "sec")

                # Incrementing a column value
                if insert_type == 'upsert_with_key' and dataframe is not None:
                    start_time = datetime.now()
                    dataframe = incremental_column_value_generation(insert_key, table_name, cursor, connection,
                                                                    dataframe, dbtype, create_column)

                    end_time = datetime.now()
                    difference = end_time - start_time
                    logging.debug("Time taken for surrogating key: " + str(difference.total_seconds()) + " sec")
                    print("------------------------------------------------------------------------------------------")
                    print("Dataframe after upsert_surrogate")
                    print(dataframe)
                    print("------------------------------------------------------------------------------------------")
                    # exit()

                    truncate_table_data(cursor, connection, table_name, target_table_df)
                    if not dataframe.empty:
                        insert_into_db(dataframe=dataframe, datatypes=datatypes, table_name=table_name,
                                       columns=columns, connection=connection, cursor=cursor, dbtype=dbtype,trigger_script=trigger_script)

            elif insert_type == 'align_with_source':
                # Reading data from target table
                start_time = datetime.now()
                sql_query = 'select * from ' + str(table_name)
                print(sql_query)
                target_df = ReadDataset.read_sql_data(sql_query, connection, cursor, dbtype)
                print(target_df)
                conditional_columns = insert_cond[0]['upsert_keys']
                sync_with_source(source_df=dataframe, target_df=target_df, cursor=cursor,
                                 connection=connection, datatypes=datatypes, columns=columns,
                                 conditional_columns=conditional_columns, table_name=table_name,
                                 dbtype=dbtype)

            elif insert_type == 'update_with_source':
                start_time = datetime.now()
                sql_query = 'select * from ' + str(table_name)
                print(sql_query)
                target_df = ReadDataset.read_sql_data(sql_query, connection, cursor, dbtype)
                print(target_df)
                conditional_columns = insert_cond[0]['upsert_keys']
                updating_columns = insert_cond[0]['upsert_columns']
                update_with_source(source_df=dataframe, target_df=target_df, cursor=cursor,
                                   updating_columns=updating_columns, connection=connection,
                                   datatypes=datatypes, columns=columns, table_name=table_name,
                                   conditional_columns=conditional_columns)

            elif insert_type == 'update_target':
                try:
                    df_columns = dataframe.columns.values.tolist()
                    conditional_columns = insert_cond[0]['upsert_keys']
                    upsert_cond = insert_cond[0]['upsert_cond']
                    print("generating update query.................")
                    logging.info("generating update query.......................")
                    update_query, df_column_order = GenerateQueries. \
                        update_query(dbtype=dbtype, df_columns=df_columns, conditional_columns=conditional_columns,
                                     table_name=table_name, upsert_condition=upsert_cond)
                    logging.info(f"Update query.............\n{update_query}")
                    dataframe = dataframe[df_column_order]
                    values = convert_nan_to_none(dataframe, datatypes, df_column_order)
                    logging.info(f"Updating records to {table_name}")
                    print(f"Update query...............\n{update_query}")
                    print("Updating records.................................")
                    row_count = None
                    try:
                        start_time = datetime.now()
                        # Added on 09072020 to insert timestamp column along with nano seconds
                        logging.info("Setting input sizes to insert timestamp column along with nano seconds")
                        date_columns = [col for col in dataframe.columns if dataframe[col].dtype == 'datetime64[ns]']
                        convert_list = {}
                        for column in date_columns:
                            convert_list[column] = cx_Oracle.TIMESTAMP
                        cursor.setinputsizes(**convert_list)
                        # Ended on 09072020 to insert timestamp column along with nano seconds

                        row_count = JobProperties.save_db_chunk(update_query, values, connection, cursor)
                        print("values count", len(values), "data frame index count", len(dataframe.index), "shape",
                              dataframe.shape[0],
                              "row count", row_count)

                        # Added on 11/12/2020 to avoid checkDBCommit if given in yml
                        if not db_count_check:
                            DataCheck.checkDBCommit(len(values), row_count)

                        # cursor.executemany(update_query, values)
                        # connection.commit()
                        print(f"{row_count} records updated successfully")
                        end_time = datetime.now()
                        difference = end_time - start_time
                        logging.debug(f"Time taken for updating target table {table_name}: {difference} sec")
                        logging.info(f"{row_count} records updated successfully")
                    except Exception as error:
                        print("error",error)
                        exception_issue = f"Failed to {insert_type} data to target table: {table_name} due to following error" \
                                          f"\nError: {error}\nType of error: {type(error)}"
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                        f"[dploperation:{'insert into db'}][pyoperation:{update_query}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                                        trace_back=traceback.format_exc(), subject='Exception-Critical')
                        DBConn.close_connection(connection=connection)
                        raise Exception(exception_issue)

                except Exception as error:
                    print(error)
                    logging.error(f"Error occurred while updating to target ...............\n{error}")
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                    f"[dploperation:{'insert into db'}][pyoperation:{'updating target table'}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{'none'}]"
                                                    f"[timestamp:{datetime.now()}]", excepetion=error,
                                                    trace_back=traceback.format_exc(), subject='Exception-info')
                    DBConn.close_connection(connection=connection)
                    raise error

            else:
                if not dataframe.empty:
                    # To perform NAN to None operation in batches if provided in properties file
                    chunk_size = ProcessTracking.get_prop_value('df_save_chunk_size', 'default_df_save_chunk_size')
                    logging.info(f"Chunk size given in properties file: {chunk_size}")
                    if chunk_size is not None and chunk_size != 'None':
                        chunk_size = int(chunk_size)
                        if dataframe.shape[0] > chunk_size:
                            while not dataframe.empty:
                                chunk_df = dataframe[0:chunk_size]
                                logging.info("Performing NAN to None conversion in chunks")
                                if not chunk_df.empty:
                                    insert_into_db(dataframe=chunk_df, datatypes=datatypes, table_name=table_name,
                                                   columns=columns, connection=connection, cursor=cursor, dbtype=dbtype,trigger_script=trigger_script)
                                logging.info("Removing chunk df from memory")
                                dataframe = dataframe.iloc[chunk_size:, ]  # dataframe[i:i + chunk_size]

                        else:
                            logging.info("Chunk size is less than dataframe size, saving complete dataframe in a "
                                         "single chunk")
                            insert_into_db(dataframe=dataframe, datatypes=datatypes, table_name=table_name,
                                           columns=columns, connection=connection, cursor=cursor, dbtype=dbtype,trigger_script=trigger_script)
                    else:
                        logging.info("Chunk size is set to None saving complete dataframe in a single chunk")
                        insert_into_db(dataframe=dataframe, datatypes=datatypes, table_name=table_name,
                                       columns=columns, connection=connection, cursor=cursor, dbtype=dbtype,trigger_script=trigger_script)
        except Exception as e:
            print("Exception", e)
            logging.error(e)
            logging.error(dataframe.columns)
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{'insert into db'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=e,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            # pickling dataframe on exception
            # DataCheck.pickleDF(dataframe)
            # logging.info("data frame has been pickled during error " + str(e))
            try:
                cursor.close()
                DBConn.close_connection(connection=connection)
            finally:
                pass
            raise e
            # connection.rollback()
            # connection.close()
            # raise
        # finally:
        #     connection.rollback()
