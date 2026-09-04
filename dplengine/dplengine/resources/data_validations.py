# filename: data_validations.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: performs various null checks/validations on a data frame

from datetime import datetime
import logging
from common.process_tracking import ProcessTracking
from common.profiling import profiling
from common.regex_operations import get_date_from_string
from models import process_datasets, get_dataset_details
from models.connections import DataBaseConnections as DBConn
from models.read_props_file import get_property
from models.save_datasets import SaveDataFrame

from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

@profiling
def validate_data(json_detailed, run_id, logging):
    """

    :param json_detailed:
    :param run_id:
    :param logging:
    :return:
    """
    print("-----------------------------------------------------------------------------------------")
    print("VALIDATIONS")
    input_dss = json_detailed['input']['DataSources']
    data_processing = json_detailed['data']['Processing']
    validation_report = json_detailed['output']['Validations']
    if any('Validations' in key for key in data_processing):
        validations = data_processing['Validations']

        for validation in validations:
            print("-----------------------------------------------------------------------------------------")
            print("Val_Seq_No: "+str(validation['val_seq'])+"\n")
            logging.info("reading dataset on which validation is to be performed")
            df, table_name, query = get_dataset_details.dataset_details(
                input_dss, validation['dataset'], logging, validation=True)

            if validation['val_type'] == 'null_check':
                null_count = []
                dates = get_date_from_string(query)
                if validation['val_col'] != 'All':
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{validation['val_type']}]"
                                                    f"[pyoperation:{validation['val_col']}]"
                                                    f"[pyobject:{validation['val_seq']}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{table_name}]"
                                                    f"[timestamp:{datetime.now()}]")
                    null_count.append(process_datasets.nullcount(
                        data_frames=df, datasets=table_name, column=validation['val_col'], date_values=dates, run_id=run_id, query=query, logging=logging))
                else:
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{validation['val_type']}]"
                                                    f"[pyobject:{validation['val_seq']}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{table_name}]"
                                                    f"[timestamp:{datetime.now()}]")
                    null_count.append(process_datasets.nullcount(
                        data_frames=df, datasets=table_name, date_values=dates, run_id=run_id, query=query, logging=logging))
                print("\nVal_Seq_No: "+str(validation['val_seq'])+' completed\n---------------------------------------------------------------')
                logging.info("validation results: " + str(null_count))
                logging.debug("Saving validation results")

                null_count = process_datasets.concat_data_frames(data_frames=null_count,
                                                                 logging=logging)
                cursor, connection, dbtype = DBConn. \
                    connect(get_property('validation_db_name'), get_property('validation_db_host'),
                            get_property('validation_db_user'), get_property('validation_db_password'),
                            get_property('validation_db_service_name'), get_property('validation_db_port'))
                logging.info("validation results: " + str(null_count))
                logging.debug("Saving validation results")
                SaveDataFrame.save_to_db(dataframe=null_count,
                                         create_table=True,
                                         create_column=True,
                                         connection=connection,
                                         cursor=cursor,
                                         dbtype=dbtype,
                                         logging=logging,
                                         insert_cond='NA',
                                         insert_type='insert',
                                         insert_key='NA',
                                         truncate_before_load=False,
                                         table_name=get_property('validation_db_table_name'),
                                         filters='',
                                         columns='')

                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{validation['val_type']}]"
                                                f"[pyoperation:{validation['val_col']}]"
                                                f"[pyobject:{validation['val_seq']}]"
                                                f"[pyconnection:{connection}][dpldbtype:{dbtype}]"
                                                f"[dpldataset:{table_name}]"
                                                f"[timestamp:{datetime.now()}]")
                DBConn. \
                    close_connection(connection)
                for entry in validation_report:
                    for datatarget in validation_report[entry]:
                        datasets = datatarget['datasets']

                        # If validation reports are to be saved to particular table
                        for dataset in datasets:
                            if validation['val_output']:
                                if dataset['val_output'] == validation['val_seq_name']:
                                    if entry == 'DataBase':
                                        try:
                                            """
                                            Connects to the database and
                                            returns the dataframe of the specified dataset
                                            """
                                            cursor, connection, dbtype = DBConn. \
                                                connect(dbtype=dataset['dataset_format'],
                                                        hostname=datatarget['host'],
                                                        username=datatarget['username'],
                                                        password=datatarget['password'],
                                                        dbname=datatarget['alias'],
                                                        port=datatarget['port'])

                                            # print(connection, cursor)
                                            SaveDataFrame.save_to_db(dataframe=null_count,
                                                                     create_table=dataset['create_table'],
                                                                     create_column=dataset['create_column'],
                                                                     connection=connection,
                                                                     cursor=cursor,
                                                                     dbtype=dbtype,
                                                                     logging=logging,
                                                                     insert_cond='NA',
                                                                     insert_type='insert',
                                                                     insert_key='NA',
                                                                     truncate_before_load=False,
                                                                     table_name=dataset['table_name'],
                                                                     filters='',
                                                                     columns='')
                                            ProcessTracking.capture_process(
                                                f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{validation['val_type']}]"
                                                f"[pyoperation:{validation['val_col']}]"
                                                f"[pyobject:{validation['val_seq']}]"
                                                f"[pyconnection:{connection}][dpldbtype:{dbtype}]"
                                                f"[dpldataset:{table_name}]"
                                                f"[timestamp:{datetime.now()}]")

                                            DBConn. \
                                                close_connection(connection)
                                            print(
                                                "--------------------------------------------------------------------------------")
                                        except Exception as e:
                                            raise e

                            else:
                                if entry == 'FileSystem':
                                    logging.info("Saving to given filesystem")

                                    path = datatarget['path'] + dataset['dataset']
                                    print('path', path)
                                    print('null_count', null_count)

                                if entry == 'DataBase':
                                    try:
                                        """
                                        Connects to the database and
                                        returns the dataframe of the specified dataset
                                        """
                                        cursor, connection, dbtype = DBConn. \
                                            connect(dbtype=dataset['dataset_format'],
                                                    hostname=datatarget['host'],
                                                    username=datatarget['username'],
                                                    password=datatarget['password'],
                                                    dbname=datatarget['alias'],
                                                    port=datatarget['port'])

                                        SaveDataFrame.save_to_db(dataframe=null_count,
                                                                 create_table=dataset['create_table'],
                                                                 create_column=dataset['create_column'],
                                                                 connection=connection,
                                                                 cursor=cursor,
                                                                 dbtype=dbtype,
                                                                 logging=logging,
                                                                 insert_cond='NA',
                                                                 insert_type='insert',
                                                                 insert_key='NA',
                                                                 truncate_before_load=False,
                                                                 table_name=dataset['table_name'],
                                                                 filters='',
                                                                 columns='')

                                        ProcessTracking.capture_process(
                                            f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{validation['val_type']}]"
                                            f"[pyoperation:{validation['val_col']}]"
                                            f"[pyobject:{validation['val_seq']}]"
                                            f"[pyconnection:{connection}][dpldbtype:{dbtype}]"
                                            f"[dpldataset:{table_name}]"
                                            f"[timestamp:{datetime.now()}]")

                                        DBConn. \
                                            close_connection(connection)
                                        print(
                                            "--------------------------------------------------------------------------------")
                                    except Exception as e:
                                        raise e

        print("Validations completed")
        print("-----------------------------------------------------------------------------------------")
