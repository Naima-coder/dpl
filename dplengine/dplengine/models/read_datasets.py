# filename: read_datasets.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: reads data sets from a table and file into a data frame


import glob
import os
import traceback
import logging
from datetime import datetime
from io import StringIO
import shutil
import pandas as pd

from common.dsefs_operations import DSEFS
from common.process_tracking import ProcessTracking
from common.profiling import profiling
from models import process_datasets
from models.connections import ResultSetDetails
from models.job_properties import JobProperties
from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)
class ReadDataset:

    @staticmethod
    @profiling
    def read_file_data(path, dataset_req, delimiter, header, logging):
        """
        Reads the given CSV file into dataframe format
        :param path:
        :param dataset_req:
        :param delimiter:
        :param header:
        :param logging:
        :return:
        """

        logging.debug("Reading file into pandas dataframe")
        print(f"dataset_requirements...\n{dataset_req}\n\n")
        try:
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

            if header:
                header_availability = 'infer'
            else:
                header_availability = None
            # if '*' not in path:
            #     path = path
            # elif type(path) == list:
            #     path = path
            # else:
            #     folder_path = path
            #     list_of_files = glob.glob(folder_path)
            #     path = path
            #     for fname in list_of_files:
            #         print('fname', fname)
            #         print('file_name', path)
            #         if fnmatch.fnmatch(fname, path):
            #             print('file with name', fname)
            #             path = fname
            #             break
            #         else:
            #             path = ''

            if '*' not in str(path):
                path = path
            elif '*' in str(path) and type(path) == list:
                for file_path in path:
                    if '*' in file_path:
                        list_of_files = glob.glob(file_path)
                        path.remove(file_path)
                        for i in list_of_files:
                            path.append(i)
                    else:
                        pass
            path = list(set(path))
            #for f_path in path:
            #    if fnmatch.fnmatch(f_path, '*.*'):
            #        pass
            #    else:
            #        pass
            #        path.remove(f_path)
            if path == '':
                # ProcessTracking.capture_process(f"RC-1-file not found in path {path}")
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{path}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")
                try:
                    raise Exception("No such files found in given path")
                except Exception as e:
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                    f"[dploperation:{'none'}][pyoperation:{path}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{'none'}]"
                                                    f"[timestamp:{datetime.now()}]", excepetion=e,
                                                    trace_back=traceback.format_exc(), subject='Exception-critical')

            if any(os.path.exists(file_path) is False for file_path in path):
                data_frames = []
                for file_url in path:
                    if 'http' in file_url:
                        # file_url = DSEFS.get_file_name(file_url)
                        dsefs_file = DSEFS.get_file(file_url)
                        s = str(dsefs_file, 'utf-8')
                        data = StringIO(s)
                        data_frames.append(pd.read_csv(data, sep=delimiter_type, header=header_availability,
                                                       encoding='utf-8'))
                        # print("dsefs_file", df)
                    else:
                        raise Exception("please check the given file paths", path)
                dataframe = pd.concat(data_frames, sort=False)
                dataframe.reset_index(drop=True, inplace=True)

            else:
            # if os.path.exists(path):
                # reading csv file using pandas

                # TODO:: changes added by nagarjuna reddy for delete rows
                if dataset_req['delete_rows'] is not None:
                    dataset_req['delete_rows'] = str(dataset_req['delete_rows'])
                    delete_split = dataset_req['delete_rows'].split(',')
                    range_data = []
                    for r_split in delete_split:
                        if '-' in r_split:
                            for spl in range(int(r_split.split('-')[0]), int(r_split.split('-')[1])):
                                range_data.append(int(spl))
                        else:
                            if r_split.lower() != 'last_row':
                                range_data.append(int(r_split))
                    if range_data == []:
                        skiprows = None
                    else:
                        skiprows = range_data
                else:
                    skiprows = None

                data_frames = []
                for file_path in path:

                    # TODO:: Changes added by Nagarjuna Gade to copy file default location for reading and writing
                    default_path = get_property('default_path')
                    def_filename = os.path.basename(file_path)
                    org_filepath = file_path
                    file_path = os.path.join(default_path,def_filename)
                    shutil.copy(org_filepath, file_path)

                    # TODO:: changes added by nagarjuna for ebcdic to ascii conversion
                    if dataset_req['file_type'].upper() not in ['ASCII','ZIP']:

                        if dataset_req['file_type'].upper() == 'ZEBCDIC':
                            os.rename(file_path, file_path+'_zipebcdic')
                            cmd = 'unzip -p '+file_path+'_zipebcdic > '+file_path
                            os.popen(cmd).read()

                        write_file = file_path + '_asc'
                        with open(file_path, 'rb') as input_file, open(write_file, 'w') as output_file:
                            os.rename(file_path, file_path + '_ebc')
                            line = input_file.read()
                            line = line.decode('cp1140')

                            if dataset_req['record_length'] is None:
                                output_file.write(line)
                            else:
                                chunks = len(line)
                                chunk_size = int(dataset_req['record_length'])
                                split_line = [line[i:i + chunk_size] for i in range(0, chunks, chunk_size)]
                                output_file.write('\n'.join(split_line))

                        os.rename(write_file, file_path)
                    ##TODO# Added by Naima VR for unzip functionality
                    if dataset_req['file_type'].upper() == 'ZIP':
                        os.rename(file_path, file_path + '_zip')
                        cmd = 'unzip -p ' + file_path + '_zip > ' + file_path
                        os.popen(cmd).read()
                    print(f" file path in read datasets : {file_path}")

                    try:
                        # Added on 12/09/2020 to read parquet files
                        if dataset_req['data_format'].lower() != "parquet":
                            if delimiter_type is not None:
                                try:
                                    logging.info("With Delimiter utf8 encoding.........................")
                                    data_frames.append(pd.read_csv(file_path, sep=delimiter_type,header=header_availability,skiprows = skiprows, encoding='utf-8'))
                                except:
                                    logging.info("With Delimiter cp1252 encoding.........................")
                                    data_frames.append(pd.read_csv(file_path, sep=delimiter_type,header=header_availability,skiprows = skiprows, encoding='cp1252'))
                            else:
                                try:
                                    try:
                                        logging.info("Without Delimiter utf8 encoding.........................")
                                        data_frames.append(pd.read_csv(file_path, sep='崇',header=header_availability,skiprows = skiprows, encoding='utf-8'))
                                    except:
                                        logging.info("Without Delimiter utf8 encoding with different seperator.........................")
                                        data_frames.append(pd.read_csv(file_path, sep='@#$%', header=header_availability,skiprows=skiprows, encoding='utf-8'))                               
                                except:
                                    logging.info("Without Delimiter cp1252 encoding.........................")
                                    data_frames.append(pd.read_csv(file_path, sep='崇',header=header_availability,skiprows = skiprows, encoding='cp1252'))
                        else:
                            data_frames.append(pd.read_parquet(path=file_path, engine='pyarrow'))

                        if dataset_req['file_type'].upper() != 'ASCII':
                            os.remove(file_path)
                            os.rename(file_path + '_ebc', file_path)

                        if dataset_req['file_type'].upper() == 'ZEBCDIC':
                            os.rename(file_path+'_zipebcdic',file_path)

                       ##TODO# Added by Naima VR to maintain the original zip file in source path
                        if dataset_req['file_type'].upper() == 'ZIP':
                            os.rename(file_path+'_zip',file_path)

                        # TODO:: Changes added by Nagarjuna Gade to copy file default location for reading and writing
                        os.remove(file_path)

                        # Ended on 12/09/2020 to read parquet files
                    except Exception as error:
                        print("exception while reading the files", error)
                dataframe = pd.concat(data_frames, sort = False)
                dataframe.reset_index(drop=True, inplace=True)
                # dataframe = JobProperties.read_file_chunk(pd, path, delimiter_type, header_availability, data_format=dataset_req['data_format'].lower())

                # TODO:: changes added by nagarjuna reddy for delete rows
                if dataset_req['delete_rows'] is not None:
                    dataset_req['delete_rows'] = str(dataset_req['delete_rows'])
                    if 'last_row' in dataset_req['delete_rows'].lower():
                        Rows = len(dataframe.index)
                        range_split = [int(Rows)-1]
                        dataframe.drop(index=dataframe.index[range_split], axis=0, inplace=True)

                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{path}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")

            # Getting data_structure of given file
            if dataset_req['data_structure'] != '' and not header:
                headers_info_list = pd.read_csv(dataset_req['data_structure'],
                                                header=None).values.tolist()

                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{dataset_req['data_structure']}][pyoperation:{'none'}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")

                # Renaming columns with columns names in data_structure file
                # TODO:: changes added by nagarjuna reddy for reading flat file with fixed columns
                if delimiter_type is None and len(dataframe.columns.tolist()) == 1:
                    columns = headers_info_list[0]
                    datatypes = headers_info_list[1]
                    start_index = headers_info_list[2]
                    end_index = headers_info_list[3]


                    for col, datatype, start, end in zip(columns, datatypes, start_index, end_index):

                        if int(start) == 0:
                            dataframe[col] = dataframe.iloc[:, 0].str[int(start):int(end)]
                        else:
                            dataframe[col] = dataframe.iloc[:, 0].str[int(start)-1:int(end)]

                        dataframe[col] = dataframe[col].str.strip()

                    dataframe.drop(columns=[0], inplace=True)
                else:
                    # Renaming columns with columns names in data_structure file
                    dataframe.columns = headers_info_list[0]
                    column_names = headers_info_list[0]
                    datatypes_in_structure = headers_info_list[1]

                    # Converting datatypes in dataframe to given datatypes in data_structure file
                    for column, data_type in zip(column_names, datatypes_in_structure):
                        if 'VARCHAR' in data_type.upper():
                            dataframe[column] = dataframe[column].astype('object')
                        elif 'TIMESTAMP' in data_type.upper() or 'DATE' in data_type.upper():
                            dataframe[column] = dataframe[column].astype('datetime64[ns]')
                            if 'DATE' in data_type.upper():
                                dataframe[column] = dataframe[column].dt.date
                        elif 'NUMBER' in data_type.upper() or 'INT' in data_type.upper():
                            # dataframe[column] = dataframe[column].astype('int64')
                            dataframe[column] = dataframe[column].apply(pd.to_numeric)

                        elif 'FLOAT' in data_type.upper():
                            dataframe[column] = dataframe[column].astype('float64')
                        else:
                            dataframe[column] = dataframe[column].astype('object')

            if dataset_req['filters'] != '':
                filters = dataset_req['filters']
                filtered_dataframe = process_datasets. \
                    filter_data_frame(dataframe, filters, logging)

                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")

                dataframe = filtered_dataframe

            if dataset_req['column_selection'] == 'Auto':
                dataframe = dataframe
            else:
                required_columns = dataset_req['columns']
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{required_columns}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")
                dataframe = dataframe[required_columns]

            logging.debug("No of records retrieved from file: " + str(dataframe.shape[0]))
        except Exception as e:
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{path}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=e,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
        else:
        
            # TODO:: changes added ny nagarjuna gade to remove non ascci characters
            # for col_name in dataframe.columns.tolist():
            #     dataframe[col_name] = dataframe[col_name].str.encode('ascii', 'ignore').str.decode('ascii')

            # return dataframe
            col_dtypes={}
            for col_name in dataframe.columns.tolist():
                col_dtypes[col_name] = str(dataframe[col_name].dtype)
            dataframe=dataframe.astype(str)
            
            # TODO:: changes added ny nagarjuna gade to remove non ascci characters
            for col_name in dataframe.columns.tolist():
                dataframe[col_name] = dataframe[col_name].str.encode('ascii', 'ignore').str.decode('ascii')
            #Changes added by Naima VR to convert datatypes to previous datatypes

            for col, dtype in col_dtypes.items():
                dataframe[col] = dataframe[col].astype(dtype)
            return dataframe
    # else:
        #     print("No such file found")
        #     raise Exception("No such file found in " + path)

    @staticmethod
    @profiling
    def read_sql_data(sql_query, connection, cursor, dbtype, excludecolumns=None, logging=logging):
        """
         Reads the given query result into dataframe format
        :param sql_query:
        :param connection:
        :param cursor:
        :param dbtype:
        :param excludecolumns:
        :param logging:
        :return:
        """
        try:
            logging.info("Reading the dataset into dataframe format")
            if dbtype.lower() == 'googlebigquery':
                final_dataframe = cursor.query(sql_query).to_dataframe()
                return final_dataframe
            query_result = cursor.execute(sql_query)

            if query_result:
                df = JobProperties.read_db_chunk(pd, sql_query, connection, query_result)
                # df = pd.DataFrame(query_result)
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                                f"[pyobject:{sql_query}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")

            else:

                row = cursor.fetchall()
                df = pd.DataFrame(row)
            print(df)
            # df = pd.DataFrame(query_result)
            rename_columns = ResultSetDetails.get_col_name_from_connection(cursor)
            logging.debug("No of records retrieved from sql_query: " + str(df.shape[0]))
            if not df.empty:
                try:
                    if rename_columns:
                        df.columns = rename_columns
                        dataset_dataframe = df
                    else:
                        dataset_dataframe = df
                    if excludecolumns != [] and excludecolumns != 'NA' and excludecolumns is not None:
                        dataset_dataframe = process_datasets.exclude_column(dataset_dataframe, excludecolumns)
                    print(f"dataset_dataframe..................\n{dataset_dataframe}")
                    return dataset_dataframe
                except Exception as e:
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                                    f"[pyobject:{sql_query}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{'none'}]"
                                                    f"[timestamp:{datetime.now()}]", excepetion=e,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
                    logging.error("Exception while reading dataset: " + str(e))
                    raise e
            else:
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{rename_columns}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")
                dataset_dataframe = pd.DataFrame(columns=rename_columns)
                # print("datasets in read_datasets --------------------------\n")
                # print(dataset_dataframe)
                if excludecolumns != [] and excludecolumns != 'NA' and excludecolumns is not None:
                    dataset_dataframe = process_datasets.exclude_column(dataset_dataframe, excludecolumns)
                return dataset_dataframe

        except Exception as e:
            exception_issue = f"Exception occurred while fetching data from database" \
                              f"\nError: {e}\nType of error: {type(e)}\n" \
                              f"Query used: {sql_query}"
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{sql_query}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            raise Exception(exception_issue)

    @staticmethod
    def read_table_data_batch(sql_query, connection, cursor, dbtype, batchsize, logging):
        """

        :param sql_query:
        :param connection:
        :param cursor:
        :param dbtype:
        :param batchsize:
        :param logging:
        :return:
        """
        # Create empty list
        dfl = []

        # Start Chunking
        print("start Chunking")
        for chunk in pd.read_sql(sql_query, con=connection, chunksize=batchsize):
            # Start Appending Data Chunks from SQL Result set into List
            print("Appending batch data-------")
            print(chunk)
            dfl.append(chunk)
            yield chunk
            # print('sleep_start')
            # time.sleep(10)
            # print('sleep_end')
        # Start appending data from list to dataframe
        df = pd.concat(dfl, ignore_index=True)
        print(df.columns.values.tolist())
