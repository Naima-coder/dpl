# filename: data_operations.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: using detailed json reads a source data set into a data frame, performs validations and other operations
# on the data frame which are mentioned in the dpl config/yml file

import logging
import traceback
from datetime import datetime

import pandas as pd

from common.process_tracking import ProcessTracking
from common.profiling import profiling
from common.regex_operations import dataframe_columns_mapping
from common.regex_operations import run_time_parameters
from models import get_dataset_details
from models import process_datasets
from resources.data_checking import DataCheck
from models.read_props_file import get_property

log_name = get_property('log_name')
logging = logging.getLogger(log_name)

@profiling
def get_dataframe(json_detailed, logging=logging, req_dfs=None):
    """
    Performs all the operations present in the given json_detailed
    and saves the required op_seq
    Saves any input dataset to the target if requries
    :param json_detailed:
    :param logging:
    :param req_dfs: None or required op_seq_names list
    :return: Returns the final op_seq dataframe when req_dfs is None
             else returns the list of required dataframes
    """

    print("-----------------------------------------------------------------------------------------")

    global variable_names_list
    global variable_values_list

    variable_names_list = []
    variable_values_list = []
    null_count = []
    operation_seq_data_frames = []
    op_seq_id_list = []
    op_seq_names_list = []

    # input data section
    input_dss = json_detailed['input']['DataSources']

    # output data section
    output_dss = json_detailed['output']['DataTargets']

    # data process section
    processing = json_detailed['data']['Processing']

    # operations section
    if any('Operations' in key for key in processing):
        operations = processing['Operations']
    else:
        operations = []
    # Checking in whether any dataset is to be saved
    print("Checking in whether any dataset is to be saved")
    logging.debug("Checking in whether any dataset is to be saved\n")

    for entry in input_dss:
        for _ in input_dss[entry]:
            # print(datasource)
            """
            List of datasets relevant to data source(Database or FileSystem)
            """
            # print(datasource['datasets'])
            datasets_list = _['datasets']
            for dataset_details in datasets_list:
                if dataset_details['op_output']:
                    print("Saving dataset: " + str(dataset_details['dataset']) + " to target")
                    logging.debug("Saving dataset: " + str(dataset_details['dataset']) + " to target")
                    try:
                        dataset_df = get_dataset_details.dataset_details(
                            input_dss, dataset_details['dataset'], logging,
                            variable_names=variable_names_list, variable_values=variable_values_list)
                    except Exception as e:
                        logging.error(f"Error occured while reading dataset {dataset_details['dataset']}")
                        print("Error occured while reading dataset :", e)
                        exit(1)

                    try:
                        if dataset_df.empty:
                            empty_df = "Dataset: '" + str(dataset_df) + "' is empty"
                            logging.warning(f"{empty_df}")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                                            f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]",excepetion=empty_df,
                                                            trace_back=traceback.format_exc(), subject='Exception-critical')
                            print("\nException:------------------")
                            raise BaseException("Dataset: '" + str(dataset_df) + "' is empty")

                        try:
                            get_dataset_details.dataset_details(
                                output_dss, dataset_details['dataset'], logging,
                                flag='save', dataframe=dataset_df)
                        except Exception as e:
                            logging.error(f"Error occured while saving dataset {dataset_details['dataset']}")
                            print("Error occured while saving dataset :", e)
                            exit(1)
                    except Exception as e:
                        print(e)
                        print(f"Dataset: '" + str(dataset_details['dataset']) + "' is empty")
                        exit(1)

    print("-----------------------------------------------------------------------------------------")

    # When Operations are given
    if any('Operations' in key for key in processing):
        operations = processing['Operations']

        for operation in operations:
            if req_dfs is None:
                perform_operation = True
            else:
                if operation['op_seq_name'] in req_dfs:
                    perform_operation = True
                else:
                    perform_operation = False

            if perform_operation:
                print("Op_Seq_No: " + str(operation['op_seq']) + "\n")
                df = []
                logging.info("Performing op_seq: " + str(operation['op_seq']))
                logging.info("Operation_details: " + str(operation))
                logging.info("Reading datasets as dataframes in given data operation")

                # Reading datasets into data-frames using pandas in given operation
                # print("operation data sets", operation['datasets'])
                if type(operation['datasets']) != list:
                    try:
                        if ',' in operation['datasets']:
                            operation['datasets'] = operation['datasets'].split(",")
                        else:
                            operation['datasets'] = [operation['datasets']]
                    except TypeError as te:
                        logging.error("TypeError raised while reading datasets to list" + str(te))
                        operation['datasets'] = [operation['datasets']]

                operation_dataset_names = '[ '
                for dataset in operation['datasets']:
                    if type(dataset) in [int, float] and operation['op_type'] != 'delete'\
                            and operation['op_type'] != 'execute_query':  # added on 12/03/2020 to execute queries
                        # Appends dataframe of the particular operational sequence
                        try:
                            operation_dataset_names += 'op_seq:' + str(dataset) + ', '
                            position = op_seq_id_list.index(dataset)
                            df.append(operation_seq_data_frames[position])
                        except Exception as e:
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                                            f"[dploperation:{str(operation['op_seq'])}][pyoperation:{str(operation['op_type'])}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]")
                            print('op_seq_id_list...................', op_seq_id_list)
                            # print('position.........................', position)
                            # print("len of operation_seq_data_frames ", len(operation_seq_data_frames))
                            raise Exception("Invalid operational sequence format")

                    elif operation['op_type'] != 'delete' and operation['op_type'] != \
                            'execute_query':  # added on 12/03/2020 to execute queries
                        operation_dataset_names += dataset + ', '
                        print("opeartion data set names", operation_dataset_names)
                        print(f"dataset: {dataset}, op_seq_names_list: {op_seq_names_list}")
                        if dataset in op_seq_names_list:
                            # Appends dataframe of the particular op_seq_name
                            position = op_seq_names_list.index(dataset)
                            df.append(operation_seq_data_frames[position])
                        else:
                            # Appends dataframe of the particular dataset
                            dataset_df = (get_dataset_details.dataset_details(
                                input_dss, dataset, logging, opseq=operation['op_seq'],
                                variable_names=variable_names_list, variable_values=variable_values_list))
                            try:
                                if not dataset_df.empty:
                                    df.append(dataset_df)
                                else:
                                    empty_df = f"Dataset: '{dataset}' is empty"
                                    logging.warning(f"{empty_df}")
                                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                                    f"[pyprocessstep:{'none'}]"
                                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                                                    f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                                                    f"[pyobject:{'none'}]"
                                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                                    f"[dpldataset:{'none'}]"
                                                                    f"[timestamp:{datetime.now()}]",
                                                                    excepetion=empty_df,
                                                                    trace_back=traceback.format_exc(),
                                                                    subject='Exception --> Empty Dataset')
                                    if not operation['empty_datasets']:
                                        print("\nException:------------------")
                                        raise BaseException(empty_df)
                                    else:
                                        df.append(dataset_df)

                            except Exception as e:
                                print(e)
                                raise Exception(e)
                                # print(e)
                                # print(f"Dataset: '" + str(dataset) + "' is empty")
                                # exit(1)

                operation_dataset_names = operation_dataset_names[:-2]
                operation_dataset_names += ' ]'

                # Applying data_operations for given datasets
                if operation['op_type'] in ['union', 'concat']:
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{operation['op_seq']}][pyoperation:{str(operation['op_type'])}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{operation_dataset_names}]"
                                                    f"[timestamp:{datetime.now()}]")
                    logging.info("Performing union operation on datasets: " + operation_dataset_names)
                    # Concat's given set of datasets
                    intm_dataframe = process_datasets.concat_data_frames(df)
                    op_seq_id_list.append(operation['op_seq'])
                    op_seq_names_list.append(operation['op_seq_name'])
                    operation_seq_data_frames.append(intm_dataframe)

                elif operation['op_type'] == 'join':
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{operation['op_seq']}][pyoperation:{str(operation['op_type'])}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{operation_dataset_names}]"
                                                    f"[timestamp:{datetime.now()}]")
                    logging.info("Performing join operation on datasets: " + operation_dataset_names)
                    # Merges the given set of datasets
                    cond = {}
                    try:
                        cond['on'] = operation['op_cond']
                    except KeyError:
                        cond['on'] = None
                    try:
                        cond['how'] = operation['op_subtype']
                    except KeyError:
                        cond['how'] = None
                    # print(len(df))
                    DataCheck.validate_dtypes(df, cond['on'], 'join')
                    intm_dataframe = process_datasets.merge_data_frames(df, cond)
                    op_seq_id_list.append(operation['op_seq'])
                    op_seq_names_list.append(operation['op_seq_name'])
                    operation_seq_data_frames.append(intm_dataframe)

                # To compare dataframes
                # Added on 10/09/2020 to perform compare operation when requested from UI
                elif operation['op_type'] == 'compare':
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{operation['op_seq']}][pyoperation:{str(operation['op_type'])}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{operation_dataset_names}]"
                                                    f"[timestamp:{datetime.now()}]")
                    logging.info("Performing compare operation on datasets: " + operation_dataset_names)
                    cond = operation['op_cond']
                    intm_dataframe = process_datasets.compare_data_frames(df, cond)
                    op_seq_id_list.append(operation['op_seq'])
                    op_seq_names_list.append(operation['op_seq_name'])
                    operation_seq_data_frames.append(intm_dataframe)

                # Transformations are performed
                elif operation['op_type'] == 'transformations':
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{operation['op_seq']}][pyoperation:{str(operation['op_type'])}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{operation_dataset_names}]"
                                                    f"[timestamp:{datetime.now()}]")
                    logging.info("Performing transformations on dataset: " + operation_dataset_names)
                    transformations = operation['Transformations']
                    for dataset_df in df:
                        intm_dataframe = transformations_functions(transformed_df=dataset_df,
                                                                   transformations=transformations)
                    op_seq_id_list.append(operation['op_seq'])
                    op_seq_names_list.append(operation['op_seq_name'])
                    operation_seq_data_frames.append(intm_dataframe)

                # Filling null values
                elif operation['op_type'] == 'fill_null':
                    logging.info("Filling null values of dataset: " + operation_dataset_names + ' to given value.')
                    if type(operation['op_col']) != list:
                        try:
                            if ',' in operation['op_col']:
                                operation['op_col'] = operation['op_col'].split(",")
                            else:
                                operation['op_col'] = [operation['op_col']]
                        except TypeError as te:
                            logging.warning("TypeError raised" + str(te))
                            operation['op_col'] = [operation['op_col']]
                    for dataset_df in df:
                        if len(operation['op_col']) != 0 and type(operation['op_col'][0]) == list:
                            if len(operation['op_col']) != len(operation['op_value']):
                                logging.error("no of columns and their respective values arrays have different lengths")
                                raise Exception(
                                    "no of columns and their respective values arrays have different lengths")
                            elif len(operation['op_col']) == len(operation['op_value']):
                                for col_list, col_value in zip(operation['op_col'], operation['op_value']):
                                    for col in col_list:
                                        dataset_df[str(col)].fillna(col_value, inplace=True)
                        else:
                            for col in operation['op_col']:
                                dataset_df[str(col)].fillna(operation['op_value'], inplace=True)
                    intm_dataframe = dataset_df
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{operation['op_seq']}][pyoperation:{str(operation['op_type'])}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{operation_dataset_names}]"
                                                    f"[timestamp:{datetime.now()}]")
                    op_seq_id_list.append(operation['op_seq'])
                    op_seq_names_list.append(operation['op_seq_name'])
                    operation_seq_data_frames.append(intm_dataframe)

                # Executing given commands on dataframe
                elif operation['op_type'] == 'command':
                    logging.info(f"Performing given commands on: {operation_dataset_names} ")
                    # Multi-line commands
                    if operation['op_subtype'] == 'multi_line_command':
                        op_ds_names = operation_dataset_names.strip('][').split(', ')
                        op_ds_names = [ds_name.strip() for ds_name in op_ds_names]
                        df_dict = {}
                        # Generating a key_value pain of dataframes
                        for ds in range(len(op_ds_names)):
                            df_dict[op_ds_names[ds]] = df[ds]
                        print(df_dict)
                        print(operation['op_cond'])

                        # Getting runtime variable values
                        operation['op_cond'] = run_time_parameters(operation['op_cond'],
                                                                   varaiable_names=variable_names_list,
                                                                   variable_values=variable_values_list)
                        logging.info(f"Operations conditions given: {operation['op_cond']}")

                        # Executing multiple commands
                        intm_dataframe = process_datasets.commands_execute(dataframes=df_dict,
                                                                           command=operation['op_cond'],
                                                                           command_type=operation['op_subtype'],
                                                                           dfs_required=operation['op_output'])
                        i = 0
                        for dfs in intm_dataframe:
                            # Appending dataframes to operation_seq_data_frames
                            if 'pandas.core.frame.DataFrame' in str(type(intm_dataframe[dfs])):
                                op_seq_id_list.append(operation['op_seq'])
                                op_seq_names_list.append(operation['op_output'][i])
                                operation_seq_data_frames.append(intm_dataframe[dfs])
                            i += 1
                    else:
                        for dataset_df in df:
                            # Getting runtime variable values
                            operation['op_cond'] = run_time_parameters(operation['op_cond'],
                                                                       varaiable_names=variable_names_list,
                                                                       variable_values=variable_values_list)
                            logging.info(f"Operations conditions given: {operation['op_cond']}")

                            # Executing command
                            intm_dataframe = process_datasets.commands_execute(dataframes=dataset_df,
                                                                               command=operation['op_cond'],
                                                                               command_type=operation['op_subtype'])
                            print(type(intm_dataframe))
                            # Appending dataframes to operation_seq_data_frames
                            if 'pandas.core.frame.DataFrame' in str(type(intm_dataframe)):
                                op_seq_id_list.append(operation['op_seq'])
                                op_seq_names_list.append(operation['op_seq_name'])
                                operation_seq_data_frames.append(intm_dataframe)
                elif operation['op_type'] == 'read':
                    for dataset_df in df:
                        intm_dataframe = dataset_df
                        op_seq_id_list.append(operation['op_seq'])
                        op_seq_names_list.append(operation['op_seq_name'])
                        operation_seq_data_frames.append(dataset_df)

                elif operation['op_type'] == 'delete':
                    try:
                        try:
                            operation_cond = operation["op_cond"]
                        except Exception as e:
                            operation_cond = None
                        # Added on 10/09/2020 to generate a backup file based on user input
                        get_dataset_details.dataset_details(input_dss, operation['datasets'], logging, flag='delete',
                                                            op_cond=operation_cond,
                                                            backup_data=operation["backup_before_truncate"])
                        # Saving the intm_dataframe with op_seq details
                        # Added to avoid reading of input section when req_df is only op_type delete
                        intm_dataframe = pd.DataFrame(operation)
                        op_seq_id_list.append(operation['op_seq'])
                        op_seq_names_list.append(operation['op_seq_name'])
                        operation_seq_data_frames.append(intm_dataframe)
                    except Exception as e:
                        print("Exception while reading delete data set details", e)
                        logging.error(f'Exception while reading delete data set details {e}')

                    else:
                        intm_dataframe = pd.DataFrame(operation)
                        op_seq_id_list.append(operation['op_seq'])
                        op_seq_names_list.append(operation['op_seq_name'])
                        operation_seq_data_frames.append(intm_dataframe)

                elif operation['op_type'] == 'execute_query':
                    try:
                        try:
                            operation_cond = operation["op_cond"]
                        except Exception as e:
                            operation_cond = None
                        get_dataset_details.dataset_details(input_dss, operation['datasets'], logging,
                                                            flag='execute_query',
                                                            op_cond=operation_cond,
                                                            variable_names=variable_names_list,
                                                            variable_values=variable_values_list)
                        # Saving the intm_dataframe with op_seq details
                        # Added to avoid reading of input section when req_df is only op_type delete
                        intm_dataframe = pd.DataFrame(operation)
                        op_seq_id_list.append(operation['op_seq'])
                        op_seq_names_list.append(operation['op_seq_name'])
                        operation_seq_data_frames.append(intm_dataframe)
                    except Exception as e:
                        logging.error(f'Exception while executing given query: \n\t{e}')

                print("-----------------------------------------------------------------------------------------")
                print("op_seq: " + str(operation['op_seq']))
                print(intm_dataframe)
                print("-----------------------------------------------------------------------------------------")

                if operation['purge_datasets']:
                    logging.info(f"Purging op_seq dataframes: {operation['purge_datasets']}")
                    for purge_df in operation['purge_datasets']:
                        # print(purge_df)
                        if purge_df != operation['op_seq'] or purge_df != operation['op_seq_name']:
                            try:
                                position = op_seq_names_list.index(purge_df)
                            except ValueError as ve1:
                                try:
                                    position = op_seq_id_list.index(purge_df)
                                except ValueError as ve2:
                                    position = -99
                            # print(position)
                            if position != -99:
                                logging.info(f"Purging op_seq df: {purge_df}")
                                purging_df = operation_seq_data_frames[position][0:0]
                                operation_seq_data_frames.pop(position)
                                op_seq_id_list.pop(position)
                                op_seq_names_list.pop(position)
                            else:
                                logging.warning(f"op_seq df: {purge_df} is not available to purge")
                            current_op_df_purge = False
                        else:
                            current_op_df_purge = True
                else:
                    current_op_df_purge = False

                # Checking whether operation seq is to be saved
                if any('op_output' in key for key in operation):
                    if operation['op_output'] == True:
                        print("operation df to be saved")
                        logging.debug("Saving op_seq: " + str(operation['op_seq']))
                        output_df = intm_dataframe.copy()
                        get_dataset_details.dataset_details(
                            output_dss, operation['op_seq_name'], logging, flag='save', dataframe=output_df,
                            opseq=operation['op_seq'])
                        output_df = output_df[0:0]

                    elif type(operation['op_output']) == list:
                        i = 0
                        if type(intm_dataframe) == dict:
                            for value in intm_dataframe:
                                # print("i", i)
                                # print(operation['op_output'][i])
                                # print(value)
                                if 'pandas.core.frame.DataFrame' not in str(type(intm_dataframe[value])):
                                    # op_seq_id_list.append(operation['op_seq'])
                                    variable_names_list.append(operation['op_output'][i])
                                    variable_values_list.append(intm_dataframe[value])
                                    print(variable_names_list, variable_values_list)

                                i += 1
                        else:
                            for output_name in operation['op_output']:
                                if 'pandas.core.frame.DataFrame' not in str(type(intm_dataframe)):
                                    variable_names_list.append(output_name)
                                    variable_values_list.append(intm_dataframe)
                                    print(variable_names_list, variable_values_list)
                    else:
                        variable_names_list.append(operation['op_output'])
                        variable_values_list.append(intm_dataframe)
                        print(variable_names_list, variable_values_list)

                logging.debug("Op_Seq_No: " + str(
                    operation[
                        'op_seq']) + ' completed\n---------------------------------------------------------------')
                print("Op_Seq_No: " + str(
                    operation[
                        'op_seq']) + ' completed\n---------------------------------------------------------------')
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{operation['op_seq']}][pyoperation:{str(operation['op_type'])}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]\n")
                if current_op_df_purge:
                    op_seq_id_list.pop(-1)
                    op_seq_names_list.pop(-1)
                    operation_seq_data_frames.pop(-1)
        if operation_seq_data_frames:
            # print(operation_seq_data_frames)
            operation_df = operation_seq_data_frames[-1]

    # When no operations are given
    if not operation_seq_data_frames and not operations:
        df = []
        for entry in input_dss:
            for datasource in input_dss[entry]:
                """
                List of datasets relevant to data
                 source(Database or FileSystem)
                """
                datasets_list = datasource['datasets']
                for dataset_details in datasets_list:
                    df.append(get_dataset_details.dataset_details(
                        input_dss, dataset_details['dataset'], logging,
                        variable_names=variable_names_list, variable_values=variable_values_list))

        if len(df) > 1:
            # Concats the given dataframes
            operation_df = process_datasets.concat_data_frames(df)
        else:
            # When only one dataset is given
            operation_df = df[0]
    if not operation_seq_data_frames and operations:
        operation_df = pd.DataFrame()
    print("-----------------------------------------------------------------------------------------")
    print('final operational dataframe...........')
    print(operation_df)
    print("-----------------------------------------------------------------------------------------")

    """
    Checking for data transformation in data section
    """
    operation_df = transformations_functions(operation_df, processing)

    """
    Checking for data transformation in output section
    """
    transformations = json_detailed['output']['Transformations']
    # print(transforamtions)

    if transformations != {}:
        logging.debug("Performing transformations given in output section: ")
        operation_df = transformations_functions(transformed_df=operation_df, transformations=transformations)

    final_dataframe = operation_df
    print("final dataframe after processing")
    print(final_dataframe)
    print("-----------------------------------------------------------------------------------------")
    if not null_count:
        pass
    else:
        print("NULL Check results: ")
        for count in null_count:
            print(f'\t {count}\n')

    if req_dfs is None:
        return final_dataframe
    else:
        req_dataframes = []

        for df in req_dfs:
            position = op_seq_names_list.index(df)
            req_dataframes.append(operation_seq_data_frames[position])
        return req_dataframes


@profiling
def transformations_functions(transformed_df, transformations, opseq=None):
    """

    :param transformed_df:
    :param transformations:
    :param opseq:
    :return:
    """
    try:
        if any('DerivedColumns' in key for key in transformations):
            # Appends new columns with given formula
            derivedcolumns = \
                transformations['DerivedColumns']
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                            f"[pyobject:{derivedcolumns}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]")
            # Looping over column to be derived from derived columns
            if derivedcolumns:
                for derived_col in derivedcolumns:
                    print(derived_col)
                    # print(operation_df)
                    # derived_col['formula'] = run_time_parameters(derived_col['formula'],
                    #                                              varaiable_names=variable_names_list,
                    #                                              variable_values=variable_values_list)
                    # to take run time variables for formulas
                    formulas = []
                    if derived_col['formula_type'] != 'api':
                        for formula in derived_col['formula']:
                            formula = run_time_parameters(formula, varaiable_names=variable_names_list,
                                                          variable_values=variable_values_list)
                            print(formula, variable_names_list,variable_values_list)
                            formulas.append(formula)

                        derived_col['formula'] = formulas
                    else:
                        derived_col['formula'] = run_time_parameters(derived_col['formula'],
                                                                     varaiable_names=variable_names_list,
                                                                     variable_values=variable_values_list)
                    transformed_df = process_datasets.derived_columns(
                        transformed_df, derived_col)

        # Applying Filters
        if any('Filters' in key for key in transformations):
            if transformations['Filters']:
                for _ in transformations['Filters']:
                    filters = _['fil_list']
                    filters = run_time_parameters(filters, varaiable_names=variable_names_list,
                                                  variable_values=variable_values_list)
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                                    f"[pyobject:{filters}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{'none'}]"
                                                    f"[timestamp:{datetime.now()}]")
                    if filters:
                        filter_columns = DataCheck.filter_cols_to_list(transformed_df, filters)
                        DataCheck.validate_dtypes(transformed_df, filter_columns, 'filter')
                        transformed_df = process_datasets.filter_data_frame(transformed_df, filters)

        # Selecting columns
        if any('FinalColumns' in key for key in transformations):
            if transformations['FinalColumns']:
                for _ in transformations['FinalColumns']:
                    req_columns = _['col_list']

                if req_columns:
                    req_columns = dataframe_columns_mapping(transformed_df, req_columns)
                    transformed_df = transformed_df[req_columns]
                    logging.debug(f"Selecting {req_columns} from data frame")

        # Renaming columns
        if any('RenamedColumns' in key for key in transformations):
            renamed_col = transformations['RenamedColumns']
            transformed_df = process_datasets.rename_columns(
                transformed_df, renamed_col)

        return transformed_df
    except Exception as e:
        logging.error("Exception in transformations block" + str(e))
        raise e
    pass
