# filename: connections.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: using the data base credentials in dpl config/yml file generates a cursor object and a connection object

import logging
from datetime import datetime
import traceback

import cassandra
import cx_Oracle
import psycopg2
import pymssql
import teradatasql
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from google.oauth2 import service_account
from google.cloud import bigquery

from common.profiling import profiling
from common.process_tracking import ProcessTracking
from common.regex_operations import dataframe_columns_mapping
from common.cipher import AESCipher
from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

class DataBaseConnections:

    def __init__(self):
        pass

    @staticmethod
    @profiling
    def connect(dbtype=None, hostname=None, username=None,
                password=None, dbname=None, port=None):
        """
        Creates the connection to the required database
        :param dbtype:
        :param hostname:
        :param username:
        :param password:
        :param dbname:
        :param port:
        :return:
        """
        try:
            if password[0:2] == '~~':
                encryp_obj = AESCipher()
                password = password.replace('~~', '')
                password = "b'" + password + "'"
                password = encryp_obj.decrypt(password)
            
            if dbtype.lower() in 'postgressql':
                connection = psycopg2.connect(host=hostname, user=username,
                                              password=password,
                                              database=dbname,
                                              port=port)
                cursor = connection.cursor()
                return cursor, connection, dbtype

            elif dbtype.lower() in 'oracle':
                connection = cx_Oracle.connect(f'{username}/{password}@'
                                               f'{hostname}:{port}/{dbname}',
                                               encoding="UTF-8")
                print("conn",connection)
                cursor = connection.cursor()
                cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = "
                               "'DD-MM-RR'")
                cursor.execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT ="
                               " 'DD-MM-RR HH.MI.SSXFF AM'")
                return cursor, connection, dbtype

            elif dbtype.lower() == 'mssql':
                connection = pymssql.connect(server=hostname, user=username,
                                             password=password,
                                             database=dbname,
                                             port=port)
                cursor = connection.cursor()
                return cursor, connection, dbtype

            elif dbtype.lower() == 'teradata':
                connection = teradatasql.connect(host=hostname, user=username,
                                                 password=password,
                                                 database=dbname,
                                                 dbs_port=port)
                cursor = connection.cursor()
                return cursor, connection, dbtype

            elif dbtype.lower() == 'cassandra':
                credentials = PlainTextAuthProvider(username=username,
                                                    password=password)

                connection = Cluster([hostname], port,
                                     auth_provider=credentials,
                                     protocol_version=3, connect_timeout=50,
                                     control_connection_timeout=10.0)
                cursor = connection.connect(dbname)
                return cursor, connection, dbtype

            # TODO:: changes added by nagarjuna for google big query
            elif dbtype.lower() == 'googlebigquery':
                if hostname == '':
                    key_path = user
                else:
                    key_path = hostname+username
            # key_path = properties.get('gbq_json')
                credentials = service_account.Credentials.from_service_account_file(key_path,)

                connection = bigquery.Client(credentials=credentials, project=credentials.project_id)
                cursor = connection
                return cursor, connection, dbtype


        except Exception as e:
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=e,
                                            trace_back=traceback.format_exc(),
                                            subject='Exception-Critical')
            raise Exception(e)

    @staticmethod
    @profiling
    def close_connection(connection):
        """
        Closes the connection of the connected database
        :param connection:
        :return:
        """
        if connection:
            if type(connection) != cassandra.cluster.Cluster:
                try:
                    print("Closing connection.............................................")
                    logging.debug("Closing connection.............................................")
                    connection.close()
                except Exception as e:
                    print("Connection already closed")
            else:
                print("Closing connection.............................................")
                logging.debug("Closing connection.............................................")
                connection.shutdown()


class ResultSetDetails:

    @staticmethod
    @profiling
    def get_col_name_from_connection(connection):
        """

        :param connection:
        :return:
        """
        if 'Session' not in str(type(connection)):
            columns_names = [desc[0] for desc in connection.description]
            return columns_names
        else:
            return []


class Columns:

    @staticmethod
    @profiling
    def column_names(dbtype, table_name):
        """

        :param dbtype:
        :param table_name:
        :return:
        """

        if dbtype.lower() == 'postgressql':
            query = "select column_name,data_type from information_schema" \
                    ".columns where table_name = lower('" + table_name + "')"
            return query

        elif dbtype.lower() == 'oracle':
            owner_table = table_name.split(".", 1)
            owner = owner_table[0].upper()
            table = owner_table[1].upper()

            query = f"select COLUMN_NAME, DATA_TYPE  from all_tab_columns  where owner = '{owner}' and TABLE_NAME = '{table}'"

            return query
        elif dbtype.lower() == 'mssql':
            owner_table = table_name.split(".", 1)
            owner = owner_table[0].upper()
            table = owner_table[1].upper()
            query = "select column_name,data_type from information_schema" \
                    ".columns where table_name = lower('" + table + "')"
            return query

    @staticmethod
    @profiling
    def column_constraints(dbtype, table_name, column_name):
        """

        :param dbtype:
        :param table_name:
        :param column_name:
        :return:
        """
        if dbtype.lower() == 'postgres':
            query = "select TC.constraint_type from INFORMATION_SCHEMA.KEY_COLUMN_USAGE KCU \
                    INNER JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS TC ON " \
                    "KCU.constraint_name = TC.constraint_name where KCU." \
                    "table_name =  lower('" + table_name + "') and " \
                                                           "KCU.column_name =  lower('" + column_name + "')"
            return query

        elif dbtype.lower() == 'oracle':
            query = "empty query"
            return query

    @staticmethod
    @profiling
    def check_if_columns_exists(table_name, column_names, cursor, dbtype):
        """
        Checks whether all columns in dataframe exists in table
        :param table_name:
        :param column_names:
        :param cursor:
        :param dbtype:
        :return:
        """
        #print("in if",column_names,dbtype)
        cursor.execute(Columns.column_names(dbtype, table_name))
        query_result = cursor.fetchall()
        print("query_result :", query_result)

        table_column_names = list(map(lambda x: x[0].upper(), query_result))
        # print("table_column_names :", table_column_names)

        result = all(elem.upper() in table_column_names for elem in column_names)
        #print("col result", result)
        if result:
            return True
        # print("result :", result)
        #print("***********",table_column_names)
        return table_column_names

    @staticmethod
    @profiling
    def creating_columns(table_name, dataframe, connection, cursor, dbtype, create_column, table_column_names):
        """
        Creates the columns that are not existing in table
        :param table_name:
        :param dataframe:
        :param connection:
        :param cursor:
        :param dbtype:
        :param create_column:
        :param table_column_names:
        :return:
        """
        df_column_names = dataframe.columns.values.tolist()
        try:
            # cols_to_be_created = list(set(df_column_names) - set(table_column_names))
            # To get column names that are to be created irrespective of case
            cols_to_be_created = list(set(col_name.upper() for col_name in df_column_names) - set(
                col_name.upper() for col_name in table_column_names))
            # print("cols_to_be_created", cols_to_be_created)
            # print('table_column_names', table_column_names)
            # print('column_names', df_column_names)
            cols_to_be_created = set(cols_to_be_created) & set(col_name.upper() for col_name in df_column_names)
            cols_to_be_created = dataframe_columns_mapping(dataframe, list(cols_to_be_created))
            if create_column:
                db_key_words = ['ACCESS', 'ADD', 'ALL', 'ALTER', 'AND', 'AS', 'ASC', 'AUDIT', 'BETWEEN', 'BY', 'CHAR',
                                'CHECK', 'CLUSTER', 'COLUMN',
                                'COLUMN_VALUE', 'COMMENT', 'COMPRESS', 'CONNECT', 'CREATE', 'CURRENT', 'DATE',
                                'DECIMAL',
                                'DEFAULT', 'DELETE', 'DESC',
                                'DISTINCT', 'DROP', 'ELSE', 'EXCLUSIVE', 'EXISTS', 'FILE', 'FLOAT', 'FOR', 'FROM',
                                'GRANT',
                                'GROUP', 'HAVING', 'IDENTIFIED',
                                'IMMEDIATE', 'IN', 'INCREMENT', 'INDEX', 'INITIAL', 'INSERT', 'INTEGER', 'INTERSECT',
                                'INTO', 'IS', 'LEVEL', 'LIKE', 'LOCK',
                                'LONG', 'MAXEXTENTS', 'MINUS', 'MLSLABEL', 'MODE', 'MODIFY', 'NESTED_TABLE_ID',
                                'NOAUDIT',
                                'NOCOMPRESS', 'NOT', 'NOWAIT',
                                'NULL', 'NUMBER', 'OF', 'OFFLINE', 'ON', 'ONLINE', 'OPTION', 'OR', 'ORDER', 'PCTFREE',
                                'PRIOR', 'PUBLIC', 'RAW', 'RENAME',
                                'RESOURCE', 'REVOKE', 'ROW', 'ROWID', 'ROWNUM', 'ROWS', 'SELECT', 'SESSION', 'SET',
                                'SHARE', 'SIZE', 'SMALLINT', 'START',
                                'SUCCESSFUL', 'SYNONYM', 'SYSDATE', 'TABLE', 'THEN', 'TO', 'TRIGGER', 'UID', 'UNION',
                                'UNIQUE', 'UPDATE', 'USER', 'VALIDATE',
                                'VALUES', 'VARCHAR', 'VARCHAR2', 'VIEW', 'WHENEVER', 'WHERE', 'WITH']
                for col in cols_to_be_created:
                    if col.upper() not in db_key_words:
                        datatype = dataframe[col].dtype
                        # print(col, datatype)
                        if 'float' in str(datatype):
                            data_type = 'float(10)'
                        elif 'int' in str(datatype):
                            data_type = 'int'
                        elif 'object' in str(datatype):
                            data_type = 'varchar(250)'
                        elif 'datetime64[ns]' in str(datatype):
                            data_type = 'date'
                        else:
                            data_type = 'varchar(250)'

                        if dbtype.lower() == 'oracle':
                            table_name = table_name
                            query = 'alter table ' + table_name + ' add (' + col.upper() + ' ' + data_type + ')'
                        else:
                            # owner_table = table_name.split(".", 1)
                            # owner = owner_table[0].upper()
                            # table_name  = owner_table[1]
                            table_name = table_name
                            # print("col before con:", col)
                            # print("table_name :", table_name, "data_type :", data_type)
                            query = 'ALTER TABLE ' + table_name + ' ADD ' + col + ' ' + data_type + ';'
                        # query = 'alter table ' + table_name + ' add (' + col + ' ' + data_type + ')'

                        logging.info("Appending a column to table using query: " + str(query) + '\n')

                        print(query)
                        try:
                            cursor.execute(query)
                        except Exception as e:
                            if 'column being added already exists in table' in str(e):
                                logging.warning("Appending already exists column to table")
                                pass
                            else:
                                logging.error("Error occured while adding a new column to table")
                                raise Exception(e)
                        # ProcessTracking.capture_process(f"RC-0-Appending a column to table using query {str(query)}")
                        # ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                        #                                 f"[pyprocessstep:{'none'}]"
                        #                                 f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                        #                                 f"[dploperation:{'none'}][pyoperation:{str(query)}]"
                        #                                 f"[pyobject:{'none'}]"
                        #                                 f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                        #                                 f"[dpldataset:{'none'}]"
                        #                                 f"[timestamp:{datetime.now()}]")
                        connection.commit()
                    else:
                        exception_issue = f"{col} is a keyword, it cannot be a column name"
                        logging.error(exception_issue)
                        # ProcessTracking.capture_process(f"RC-1-column exception {str(col)}")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                                        f"[dploperation:{'none'}][pyoperation:{str(col)}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                                        trace_back=traceback.format_exc(),
                                                        subject='Exception- DB_Keyword as column name')
                        raise Exception(exception_issue)
            else:
                exception_issue = f"Columns doesn't exists and not created......................\n" \
                                  f"Columns that are to be created are:.............\n" \
                                  f"{cols_to_be_created}"
                # print(exception_issue)
                logging.critical(exception_issue)
                # ProcessTracking.capture_process(f"RC-1-column does not exist {create_column}")
                # ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                #                                 f"[pyprocessstep:{'none'}]"
                #                                 f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                #                                 f"[dploperation:{'none'}][pyoperation:{create_column}]"
                #                                 f"[pyobject:{'none'}]"
                #                                 f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                #                                 f"[dpldataset:{'none'}]"
                #                                 f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                #                                 trace_back=traceback.format_exc(), subject='Exception-critical')
                print("Data not saved")
                DataBaseConnections.close_connection(connection)
                raise Exception(exception_issue)
        except Exception as e:
            print("Error while creating col:", e)
            exception_issue = f"Error while creating col: \n\tError: {e}\n\tType of error: {type(e)}"
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                            f"[dploperation:{'none'}][pyoperation:{create_column}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            DataBaseConnections.close_connection(connection)
            raise Exception(exception_issue)


class Tables:

    @staticmethod
    @profiling
    def query_to_list_tables(dbtype, database):
        """

        :param dbtype:
        :param database:
        :return:
        """
        dbtype = dbtype.lower()
        if dbtype.lower() == 'postgres':
            query = """SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'public'"""
            return query

        elif dbtype.lower() == 'oracle':
            query = """SELECT table_name FROM user_tables"""
            return query
        elif dbtype.lower() == 'cassandra':
            query = """SELECT table_name  FROM system_schema.tables"""
            return query

        elif dbtype.lower() == 'mssql':
            query = """SELECT table_name from information_schema.tables"""
            return query

        elif dbtype.lower() == 'teradata':
            query = "select Tablename  from DBC.Tables where tablekind='T'" \
                    " and databasename='" + database + "'"

            return query

    @staticmethod
    @profiling
    def check_table_exists(table_name, dbtype):
        """

        :param table_name:
        :param dbtype:
        :return:
        """
        if dbtype.lower() == 'oracle':
            owner_table = table_name.split(".", 1)
            owner = owner_table[0].upper()
            table = owner_table[1].upper()
            query = f"select * from all_tables where owner = '{owner}' and table_name = '{table}'"
            return query
        elif dbtype.lower() == 'mssql':
            owner_table = table_name.split(".", 1)
            owner = owner_table[0].upper()
            table = owner_table[1].upper()
            query = "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%s' COLLATE SQL_Latin1_General_CP1_CI_AS" % (
                    '%' + table + '%')
            return query
        elif dbtype.lower() == 'postgressql':
            query = "SELECT * FROM information_schema.tables WHERE table_name= '%s'" % table_name
            return query

    @staticmethod
    @profiling
    def check_if_table_exists(table_name, cursor, dbtype):
        """

        :param table_name:
        :param cursor:
        :param dbtype:
        :return:
        """
        query = Tables.check_table_exists(table_name, dbtype)
        cursor.execute(query)
        # print("query :", query)
        query_result = cursor.fetchall()
        # print("qr:", query_result)
        # print(bool(query_result))
        print("query result table",query_result)
        if query_result:
            print(table_name + " exists")
            return True
        print(table_name + "does not exists")
        return False

    @staticmethod
    @profiling
    def creating_table(table_name, dataframe, connection, cursor, dbtype, create_table):
        """
        Creates table if doesnot exists
        :param table_name:
        :param dataframe:
        :param connection:
        :param cursor:
        :param dbtype:
        :param create_table:
        :return:
        """

        try:
            if create_table:
                print("Creating table")
                column_names = dataframe.columns.values.tolist()
                # datatypes = dataframe.dtypes.tolist()
                db_key_words = ['ACCESS', 'ADD', 'ALL', 'ALTER', 'AND', 'AS', 'ASC', 'AUDIT', 'BETWEEN', 'BY', 'CHAR',
                                'CHECK', 'CLUSTER', 'COLUMN',
                                'COLUMN_VALUE', 'COMMENT', 'COMPRESS', 'CONNECT', 'CREATE', 'CURRENT', 'DATE', 'DECIMAL',
                                'DEFAULT', 'DELETE', 'DESC',
                                'DISTINCT', 'DROP', 'ELSE', 'EXCLUSIVE', 'EXISTS', 'FILE', 'FLOAT', 'FOR', 'FROM', 'GRANT',
                                'GROUP', 'HAVING', 'IDENTIFIED',
                                'IMMEDIATE', 'IN', 'INCREMENT', 'INDEX', 'INITIAL', 'INSERT', 'INTEGER', 'INTERSECT',
                                'INTO', 'IS', 'LEVEL', 'LIKE', 'LOCK',
                                'LONG', 'MAXEXTENTS', 'MINUS', 'MLSLABEL', 'MODE', 'MODIFY', 'NESTED_TABLE_ID', 'NOAUDIT',
                                'NOCOMPRESS', 'NOT', 'NOWAIT',
                                'NULL', 'NUMBER', 'OF', 'OFFLINE', 'ON', 'ONLINE', 'OPTION', 'OR', 'ORDER', 'PCTFREE',
                                'PRIOR', 'PUBLIC', 'RAW', 'RENAME',
                                'RESOURCE', 'REVOKE', 'ROW', 'ROWID', 'ROWNUM', 'ROWS', 'SELECT', 'SESSION', 'SET',
                                'SHARE', 'SIZE', 'SMALLINT', 'START',
                                'SUCCESSFUL', 'SYNONYM', 'SYSDATE', 'TABLE', 'THEN', 'TO', 'TRIGGER', 'UID', 'UNION',
                                'UNIQUE', 'UPDATE', 'USER', 'VALIDATE',
                                'VALUES', 'VARCHAR', 'VARCHAR2', 'VIEW', 'WHENEVER', 'WHERE', 'WITH']
                col_list = []
                for col in column_names:
                    # print('col: ', col)
                    try:
                        datatype = dataframe[col].dtype
                        # print('col: ', col)
                    except AttributeError as e:
                        print(e)
                        print(dataframe[col])
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                                        f"[dploperation:{'none'}][pyoperation:{str(col)}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=e,
                                                        trace_back=traceback.format_exc(),
                                                        subject='Exception- DB_Keyword as column name')
                        raise Exception(e)
                    if col.upper() not in db_key_words:
                        # print(col, datatype)
                        if 'float' in str(datatype):
                            data_type = 'float(10)'
                        elif 'int' in str(datatype):
                            data_type = 'int'
                        elif 'object' in str(datatype):
                            data_type = 'varchar(250)'
                        elif 'datetime64[ns]' in str(datatype):
                            data_type = 'date'
                        else:
                            data_type = 'varchar(250)'

                        # col_list.append('"' + col + '" ' + data_type)
                        if dbtype.lower() == 'postgressql':
                            col_list.append(f"{col}  {data_type}")
                        else:
                            col_list.append('"' + col.upper() + '" ' + data_type)
                    else:
                        exception_issue = f"{col} is a keyword, it cannot be a column name"
                        logging.error(exception_issue)
                        # ProcessTracking.capture_process(f"RC-1-column exception {str(col)}")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                                        f"[dploperation:{'none'}][pyoperation:{str(col)}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                                        trace_back=traceback.format_exc(),
                                                        subject='Exception- Critical')
                        raise Exception(exception_issue)

                # print("cl", col_list)
                col_list = ', '.join(col_list)
                if dbtype != 'postgressql':
                    owner_table = table_name.split(".", 1)
                    owner = owner_table[0].upper()
                    table = owner_table[1].upper()
                else:
                    table = table_name.upper()

                if dbtype.lower() == 'oracle':
                    create_query = 'create table "' + owner + '"."' + table + '" (' + col_list + ')'
                elif dbtype.lower() == 'postgressql':
                    create_query = f"create table {table} ({col_list})"
                    # create_query = 'create table "' + table + '" (' + col_list + ')'
                else:
                    create_query = 'create table "' + table + '" (' + col_list + ')'
                logging.info("Creating a table using query: " + str(create_query) + '\n')
                # ProcessTracking.capture_process(f"RC-0-table creation{table_name}-query {create_query}")
                # ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                #                                 f"[pyprocessstep:{'none'}]"
                #                                 f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                #                                 f"[dploperation:{'none'}][pyoperation:{table_name}]"
                #                                 f"[pyobject:{create_query}]"
                #                                 f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                #                                 f"[dpldataset:{'none'}]"
                #                                 f"[timestamp:{datetime.now()}]")
                print("----------------------------------------------------------------------")
                print(create_query)
                cursor.execute(create_query)
                connection.commit()
                return True
            else:
                exception_issue = f"Table {table_name} doesn't exits and not Created"
                logging.critical(exception_issue)
                ProcessTracking.capture_process(f"RC-0-table creation{create_table}")
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                f"[dploperation:{'none'}][pyoperation:{create_table}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                                trace_back=traceback.format_exc(),
                                                subject='Exception- Table does not exist')
                print("Data not saved")
                raise Exception (exception_issue)
                exit(1)
        except Exception as exception_issue:
            logging.error(exception_issue)
            ProcessTracking.capture_process(f"RC-0-table creation{create_table}")
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{create_table}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(),
                                            subject='Exception- Critical')
            DataBaseConnections.close_connection(connection)
            raise Exception(exception_issue)


class GenerateQueries:
    def __init__(self):
        pass

    @staticmethod
    def update_query(dbtype, df_columns, conditional_columns, table_name, upsert_condition=''):
        """
        Generates update query and returns the update query along
         with order of the columns to be in dataframe
        :param dbtype:
        :param df_columns:
        :param conditional_columns:
        :param table_name:
        :param upsert_condition:
        :return:
        """
        logging.info("Generating update query.............")
        columns_to_update = list(set(df_columns) - set(conditional_columns))
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
        if upsert_condition == '':
            where_col_string = where_col_string[:-4]
        else:
            where_col_string += upsert_condition
        df_columns_order = columns_to_update + conditional_columns
        update_query = f"update {table_name} set {set_col_string} where {where_col_string}"
        # print(update_query)
        logging.info(update_query)
        return update_query, df_columns_order


def get_run_id(dpl_file_name):
    """
    Returns run_id from dpl_job_run_id
    :param dpl_file_name:
    :return:
    """
    cursor, connection, dbtype = DataBaseConnections. \
        connect(get_property('validation_db_name'), get_property('validation_db_host'),
                get_property('validation_db_user'), get_property('validation_db_password'),
                get_property('validation_db_service_name'), get_property('validation_db_port'))
    new_id = cursor.var(cx_Oracle.NUMBER)

    insert_query = 'insert into xxdpl.dpl_job_run_ids (dpl_file_name) values(:1) returning run_id into :2'
    values = [dpl_file_name, new_id]
    cursor.execute(insert_query, values)
    run_id = new_id.getvalue()
    run_id = int(run_id[0])
    connection.commit()
    DataBaseConnections.close_connection(connection=connection)
    return run_id
