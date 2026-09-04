# filename: get_dataset_details.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: reads the source data set from table or file into a data frame using the details given in dpl config/yml
# file

import os
from datetime import datetime
import logging

import pandas as pd

from common.process_tracking import ProcessTracking
from common.profiling import profiling
from common.regex_operations import run_time_parameters
from models.connections import DataBaseConnections as DBConn
from models.read_datasets import ReadDataset
from models.save_datasets import SaveDataFrame
from models.save_datasets import truncate_table_data

from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

@profiling
def dataset_details(input_dss, dataset_name, logging=logging, flag=None, dataframe=None, validation=None, opseq=None,
                    variable_names=None, variable_values=None, op_cond=None, backup_data=None):
    """

    :param input_dss:
    :param dataset_name:
    :param logging:
    :param flag:
    :param dataframe:
    :param validation:
    :param opseq:
    :param variable_names:
    :param variable_values:
    :param op_cond:
    :param backup_data:
    :return: reads dataset dataframe when flag is None
             Saves dataframe to desired when flag in 'save'
    """
    # print('---------------------------------------------------------------------------------------------')
    print("dataset_name", dataset_name)
    for entry in input_dss:
        for _ in input_dss[entry]:
            """
            List of datasets relevant to data source(Database or FileSystem)
            """
            datasets_list = _['datasets']
            for dataset_details in datasets_list:
                if entry == 'DataBase':
                    if flag is None:
                        if dataset_details['dataset'] == dataset_name:
                            try:
                                """
                               Connects to the database and
                               returns the dataframe of the specified dataset
                               """
                                start_time = datetime.now()
                                cursor, connection, dbtype = DBConn. \
                                    connect(dbtype=dataset_details['dataset_format'],
                                            hostname=_['host'],
                                            username=_['username'],
                                            password=_['password'],
                                            dbname=_['alias'],
                                            port=_['port'])

                                end_time = datetime.now()
                                difference = end_time - start_time
                                logging.info("Time taken for connecting to database: " + str(
                                    difference.total_seconds()) + " sec")
                                if cursor:
                                    if dataset_details['data_format'] == 'table':
                                        table_name = dataset_details['table_name']
                                        if dataset_details['filters'] != '':
                                            filters = dataset_details['filters']
                                            if '==' in filters:
                                                filters = filters.replace('==', '=')
                                            sql_query = f'select * from {table_name} where {filters}'
                                        else:
                                            sql_query = f'select * from {table_name}'
                                        if dataset_details['column_selection'] == 'Auto':
                                            sql_query = sql_query
                                        else:
                                            if type(dataset_details['columns']) == list:
                                                column_names = ', '.join(dataset_details['columns'])
                                            else:
                                                column_names = dataset_details['columns']
                                            sql_query = sql_query.replace('*', column_names)

                                    elif dataset_details['data_format'] == 'query':
                                        sql_query = dataset_details['query']
                                        table_name = dataset_name
                                    sql_query = run_time_parameters(sql_query, variable_names, variable_values)
                                    print('sql_query', sql_query)
                                    logging.info(
                                        "SQL_QUERY to read data from dataset: " + dataset_name + " is \n" + sql_query + "\n")
                                    non_req_columns = dataset_details['excludecolumns']
                                    source_dataframe = \
                                        ReadDataset.read_sql_data(sql_query,
                                                                  connection,
                                                                  cursor,
                                                                  dbtype,
                                                                  excludecolumns=non_req_columns)
                                    end_time = datetime.now()
                                    difference = end_time - start_time

                                    ProcessTracking.capture_process(f"RC-0-'reading'-'opseq'-{opseq}'read_sql_data-{sql_query}-"
                                                                    f"'connection'-{connection}-'dbtype-{dbtype}-"
                                                                    f"'dataset'-{dataset_name}")

                                    logging.info("Time taken for reading dataset as dataframe: " + str(
                                        difference.total_seconds()) + " sec\n")
                                    DBConn. \
                                        close_connection(connection)

                                    if validation:
                                        
                                        return source_dataframe, table_name, sql_query
                                    else:
                                        return source_dataframe

                            except Exception as e:

                                print(e)
                                raise e

                    elif flag == 'delete':
                        if dataset_details['dataset'] in dataset_name or dataset_details['dataset'] == dataset_name:
                            try:
                                cursor, connection, dbtype = DBConn. \
                                    connect(dbtype=dataset_details['dataset_format'],
                                            hostname=_['host'],
                                            username=_['username'],
                                            password=_['password'],
                                            dbname=_['alias'],
                                            port=_['port'])

                                logging.info("deleting record from table: " + str(dataset_details['dataset']))

                                if op_cond is not None:
                                    delete_query = f"DELETE FROM {dataset_details['table_name']} WHERE {op_cond}"
                                else:
                                    delete_query = f"DELETE FROM {dataset_details['table_name']}"
                                print("delete query for deleting the records", delete_query)

                                # Added on 10/09/2020 to generate a backup file based on user input
                                if backup_data:
                                    if op_cond is not None:
                                        select_query = f"SELECT * FROM {dataset_details['table_name']} WHERE {op_cond}"
                                    else:
                                        select_query = f"SELECT * FROM {dataset_details['table_name']}"

                                    target_table_df = ReadDataset.read_sql_data(select_query, connection, cursor, dbtype, logging=logging,
                                                                               excludecolumns=[])
                                else:
                                    target_table_df = pd.DataFrame()

                                truncate_table_data(cursor, connection, dataset_details["table_name"], target_table_df,
                                                    del_query=delete_query)

                                DBConn.close_connection(connection)
                            except Exception as e:
                                logging.error(f"Exception while deleting the records from table {e}")
                                raise Exception("Exception while deleting the records from table", e)
                    elif flag == 'execute_query':
                        if dataset_details['dataset'] in dataset_name or dataset_details['dataset'] == dataset_name:
                            try:
                                cursor, connection, dbtype = DBConn. \
                                    connect(dbtype=dataset_details['dataset_format'],
                                            hostname=_['host'],
                                            username=_['username'],
                                            password=_['password'],
                                            dbname=_['alias'],
                                            port=_['port'])
                                sql_query = dataset_details['query']
                                table_name = dataset_name
                                sql_query = run_time_parameters(sql_query, variable_names, variable_values)
                                logging.info("executing query: " + str(sql_query))
                                execution_start_time = datetime.now()
                                cursor.execute(sql_query)
                                # print("sql_query....", sql_query)
                                # print(cursor.rowcount)
                                connection.commit()
                                execution_end_time = datetime.now()
                                logging.info(f"Time taken to execute query:......\t{execution_end_time-execution_start_time}")

                            except Exception as e:
                                print(e)
                                logging.error(f"Exception while executing query {e}")
                                raise Exception("Exception while executing query", e)
                    else:
                        if dataset_details['op_output'] == dataset_name or dataset_details['op_output'] == opseq:
                            cursor, connection, dbtype = DBConn. \
                                connect(dbtype=dataset_details['dataset_format'],
                                        hostname=_['host'],
                                        username=_['username'],
                                        password=_['password'],
                                        dbname=_['alias'],
                                        port=_['port'])
                            logging.info("Saving to the table: "+str(dataset_details['dataset']))
                            SaveDataFrame.save_to_db(table_name=dataset_details['dataset'],
                                                     columns=dataset_details['columns'],
                                                     filters=dataset_details['filters'],
                                                     create_table=dataset_details['create_table'],
                                                     create_column=dataset_details['create_column'],
                                                     connection=connection,
                                                     dataframe=dataframe,
                                                     cursor=cursor,
                                                     dbtype=dbtype,
                                                     insert_type=dataset_details['insert_type'],
                                                     insert_cond=dataset_details['insert_cond'],
                                                     insert_key=dataset_details['insert_key'],
                                                     truncate_before_load=dataset_details['truncate_before_load'],
                                                     target_filter=dataset_details['target_filter'],
                                                     excludecolumns=dataset_details['excludecolumns'],
                                                     save_conditions=dataset_details)

                            DBConn. \
                                close_connection(connection)

                            ProcessTracking.capture_process(f"RC-0-saving to db-opseq-{opseq}'"
                                                            f"table-{dataset_details['create_table']}"
                                                            f"'connection'-{connection}-'dbtype-{dbtype}-"
                                                            f"'dataset'-{dataset_details['dataset']}"
                                                            f"insertype-{dataset_details['insert_type']}-"
                                                            f"inset condition-{dataset_details['insert_cond']}-"
                                                            f"auto increment key-{dataset_details['insert_key']}")

                elif entry == 'FileSystem':
                    try:
                        if flag is None:
                            if dataset_details['dataset'] == dataset_name:
                                delimiter = dataset_details['delimiter']
                                header = dataset_details['header']
                                file_paths = []
                                if ',' in dataset_details['file_name']:
                                    print("multiple files are given")
                                    files = dataset_details['file_name'].split(",")
                                    for file in files:
                                        file = file.strip()
                                        file_path = os.path.join(_['path'], file)
                                        file_paths.append(file_path)
                                else:
                                    file_paths.append(os.path.join(_['path'], dataset_details['file_name']))
                                print("given file paths", file_paths)
                                logging.info("Reading given file: "+str(dataset_details['file_name']))

                                """
                                Reads the file and
                                returns the dataframe in the specified path
                                """
                                source_dataframe = ReadDataset.read_file_data(
                                    file_paths, dataset_details, delimiter, header, logging)
                                print(
                                    "-----------------------------------------------------------------------------------------")
                                if validation:
                                    return source_dataframe, dataset_details['file_name']
                                else:
                                    return source_dataframe
                        else:
                            if dataset_details['op_output'] == dataset_name:
                                logging.info("Saving to given file: "+str(dataset_name))

                                path = os.path.join(_['path'], dataset_details['dataset'])
                                # saves final dataframe to the desired path
                                SaveDataFrame.save_to_file(path=path,
                                                           dataframe=dataframe,
                                                           filters=dataset_details['filters'],
                                                           columns=dataset_details['columns'],
                                                           logging=logging)

                                ProcessTracking.capture_process(f"RC-0-opseq-{opseq}-saving to file"
                                                                f"file-{path}")
                    except Exception as e:
                        print(e)
                        raise e

