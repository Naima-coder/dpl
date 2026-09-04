# filename: detailed_json_generation.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: using dpl config/yml as input a detailed json is generated for dpl engine process

import json
import logging
import os
import re

from common.file_name_generation import generate_file_name
from common.profiling import profiling
from models import read_files
from models import read_yaml_file
from models.read_ini_file import IniFiles
from models.read_props_file import get_property
from resources.add_variable_to_json import EditDetailedJson

log_name = get_property('log_name')
logging = logging.getLogger(log_name)

@profiling
def generate_detailed_json(dpl_config_file, run_type):  # cli
    """
    Generates the detailed json file from given DPL file
    :param dpl_config_file:
    :param run_type:
    :return:Detailed_Json
    """
    try:
        print("EditDetailedJs",EditDetailedJson.VARS_FRM_SYSARG)
        global api_file_path
        data_source_list = []
        data_target_list = []
        data_section = {}
        datatransformations = {}
        batch_properties = []
        job_alert_details = []

        # Reading input file
        input_files = read_yaml_file.read_yuml(dpl_config_file)
        for key in input_files.keys():
            if key not in ["common", "include", "input", "data", "output"]:
                print(f"\n '{key}' is not a valid key\n "
                      f"Valid keywords are: 'common', 'include, input, data, output' ")
                logging.error(f"'Invalid keyword {key}' \n "
                              f"Valid keywords are: 'common', 'include, input, data, output'")
                exit(1)

        # Reading connectors file
        conn_config = read_yaml_file.read_yuml(get_property(input_files['include']['connectors']))

        # Reading properties file
        try:
            EditDetailedJson.alt_props_file_path(get_property(input_files['include']['properties']))
            batch_props_parser = IniFiles.read(get_property(input_files['include']['properties']))
            batch_properties = IniFiles.ini_to_dict(batch_props_parser)
        except KeyError:
            pass

        df_config = {key: val for key, val in input_files.items() if key != 'include'}

        # Rename columns
        if any('column_derivations' in key for key in input_files['include']):
            df_config = column_selection_through_external_file(input_files, df_config)
        else:
            # rename_file_columns = ''
            df_config = df_config
        api_file_path = key_check_fn('apis', input_files['include'], '')

        if api_file_path and api_file_path is not '':
            api_file_path = get_property(api_file_path)

        # Looping on sections(input,data,output) in simple_json(df_config)
        print("before for lopp in detailed json genration")
        for section in df_config:
            print("section", section)
            section_details = df_config[section]

            if section == 'common':
                job_alert_details = input_files['common']['jobalert']

            if section == 'input':
                dataset_names_list = []
                alias = 'datasources'
                if section_details is not None:
                    for key in section_details.keys():
                        if key not in ['datasources']:
                            print(f"\n Invalid keyword '{key}' in input section.\n"
                                  f'Valid key_words are: ["datasources"]')
                            logging.error(f"Invalid keyword '{key}' in input section.\n"
                                          f'Valid key_words are: ["datasources"]')
                            exit(1)

            elif section == 'output':
                alias = 'datatargets'
                if section_details is not None:
                    output_keywords = ["transformations", "datatargets", "validation_report"]
                    for key in section_details.keys():
                        if key not in output_keywords:
                            print(f"\n Invalid keyword '{key}' in output section.\n"
                                  f"Valid key_words are: {output_keywords}")
                            logging.error(f"Invalid keyword '{key}' in output section.\n"
                                          f"Valid key_words are: {output_keywords}")
                            exit(1)
            if 'data' not in section and 'common' not in section:
                fs_dataset_details = []
                db_dataset_details = []
                #Added by Naima VR for adding api connetion details
                api_dataset_details=[]
                try:
                    if any(alias in key for key in section_details):
                        for connector in section_details[alias]:
                            # Getting connector details
                            try:
                                conn_details = conn_config[connector]
                            except KeyError as e:
                                print(
                                    f"\n Error: \n Invalid connector {e} in file {input_files['include']['connectors']}")
                                exit(1)
                            dataset_list = []
                            for dataset_details in section_details[alias][connector]:
                                if section == 'input':
                                    if dataset_details is not None:
                                        input_keywords = ['dataset', 'query', 'data_format', 'op_output', 'columns',
                                                          'filters', 'columns', 'filters', 'batchsize', 'delimiter',
                                                          'headers', 'op_output', 'table_name', 'file_name',
                                                          'data_structure', 'excludecolumns', 'delete_rows','file_type','record_length']
                                        for key in dataset_details.keys():
                                            if key not in input_keywords:
                                                print(f"\n Invalid keyword '{key}' in input section.\n"
                                                      f"Valid key_words are: {input_keywords}")
                                                logging.error(f"Invalid keyword '{key}' in input section.\n"
                                                              f"Valid key_words are: {input_keywords}")
                                                exit(1)
                                    try:
                                        data_format = dataset_details['data_format'].lower()
                                        data_formats = ['query', 'table', 'file', 'flatfile', 'csv', 'excel',
                                                        'parquet']  # Added on 12/09/2020 to read parquet files
                                        if data_format not in data_formats:
                                            print(f"\n Invalid keyword '{data_format}' in dataformat \n "
                                                  f"Valid keywords are {data_formats}")
                                            logging.error(f"Invalid keyword '{data_format}' in dataformat \n "
                                                          f"Valid keywords are {data_formats}")
                                            exit(1)
                                        print("line no 147 detailed json generation", dataset_details )
                                        dataset_name = dataset_details['dataset']
                                        if dataset_name in dataset_names_list:
                                            print(f"\n Dataset Name '{dataset_name}' is already exists.")
                                            exit(1)
                                        dataset_names_list.append(dataset_name)

                                        if (type(dataset_details['dataset'])) != str:
                                            print("Dataset_name cannot be an integer")
                                            logging.error("Dataset_name cannot be an integer")
                                            exit(1)
                                        batch_size = key_check_fn('batchsize', dataset_details, None)
                                        op_output = key_check_fn('op_output', dataset_details, False)

                                        # For both table format and files
                                        if data_format != 'query':
                                            if any('columns' in key for key in dataset_details):
                                                try:
                                                    columns_selected = dataset_details['columns']
                                                    column_selection_type = 'Manual'
                                                except KeyError as ke:
                                                    columns_selected = 'All'
                                                    column_selection_type = 'Auto'
                                                columns_excluded = convert_str_to_list(key_check_fn('excludecolumns',
                                                                                                    dataset_details,
                                                                                                    []))
                                            else:
                                                columns_selected = 'All'                                                
                                                column_selection_type = 'Auto'
                                                columns_excluded = []
                                            filters_applied = key_check_fn('filters', dataset_details, '')
                                            print("in if line no 178 in DJG", dataset_details)
                                            datasets_info = dict(
                                                dataset=dataset_details['dataset'],
                                                dataset_format=conn_details['dataset_format'],
                                                data_format=data_format,
                                                column_selection=column_selection_type,
                                                columns=columns_selected,
                                                excludecolumns=columns_excluded,
                                                filters=filters_applied,
                                                batchsize=batch_size,
                                                delimiter='NA',
                                                header='NA',
                                                op_output=op_output)
                                        # When data_format in query
                                        else:
                                            print("in else",dataset_details )
                                            datasets_info = dict(
                                                dataset=dataset_details['dataset'],
                                                dataset_format=conn_details['dataset_format'],
                                                data_format=data_format,
                                                query=dataset_details['query'],
                                                column_selection='NA',
                                                columns='NA',
                                                excludecolumns='NA',
                                                filters='NA',
                                                batchsize=batch_size,
                                                delimiter='NA',
                                                header='NA',
                                                op_output=op_output)

                                        if conn_details['datatype'] == "filesystem":
                                            print("in if line no 208 in DJG", dataset_details)
                                            delimiter_type = key_check_fn('delimiter', dataset_details, None)
                                            header_avaliability = key_check_fn('headers', dataset_details, True)

                                            datasets_info['delimiter'] = delimiter_type
                                            datasets_info['header'] = header_avaliability
                                            datasets_info['file_name'] = key_check_fn('file_name', dataset_details,
                                                                                      dataset_details['dataset'])


                                            # TODO:: changes added by magarjuna reddy for delete rows
                                            datasets_info['delete_rows'] = key_check_fn('delete_rows', dataset_details, None)

                                            # TODO:: Changes added by nagarjuna reddy for file type
                                            datasets_info['file_type'] = key_check_fn('file_type',dataset_details, 'ASCII')

                                            ## TODO:: Changes added nagarjuna reddy for record length specifies
                                            datasets_info['record_length'] = key_check_fn('record_length',dataset_details,None)

                                            datasets_info['data_structure'] = key_check_fn('data_structure',
                                                                                           dataset_details, '')


                                            # print(input_files['include']['data_structures'])
                                            print(input_files['include'], type(input_files['include']),
                                                  input_files['include'].keys())
                                            if 'data_structures' in input_files['include'].keys():
                                                datasets_info['data_structure'] = \
                                                    str(get_property(input_files['include']['data_structures'])) + \
                                                    str(datasets_info['data_structure'])
                                            else:
                                                pass

                                        if data_format == 'table':
                                            datasets_info['table_name'] = key_check_fn('table_name', dataset_details,
                                                                                       dataset_details['dataset'])
                                        dataset_list.append(datasets_info)
                                    except Exception as e:
                                        print('Exception: ', e, type(e))
                                        logging.error("Please check DATA SOURCES in input section of given YAML FILE")
                                        print("Please check DATA SOURCES in input section of given YAML FILE")
                                        exit(1)
                                        # raise e
                                elif section == 'output':
                                    try:
                                        print("in output section start", dataset_details)
                                        # TODO:: changes addede by Nagarjuna reddy gade, added delimeter in output section

                    ## TODO: New key word comp3_col,headers,insert_string,trigger_script,data_structure,payload,method,date_format are added in target_keywords by Naima V R
                                        if dataset_details is not None:
                                            target_keywords = ["dataset", "file_name", "columns", "filters",
                                                               "table_name", "columns", "filters", "create_table",
                                                               "create_column", "truncate_before_load", "insert_type",
                                                               "insert_cond", "insert_key", "op_output", "data_format",
                                                               "target_filter", "excludecolumns",
                                                               "backup_before_truncate",
                                                               "commit_count_mismatch","delimiter","file_type","comp3_col","headers","insert_string",
                                                               "date_format",
                                                               "data_structure","payload","method","trigger_script","record_length"]
                                            for key in dataset_details.keys():
                                                if key not in target_keywords:
                                                    print(f"\n Invalid keyword '{key}' in output section.\n"
                                                          f"Valid key_words are: {target_keywords}")
                                                    logging.error(f"Invalid keyword '{key}' in output section.\n"
                                                                  f"Valid key_words are: {target_keywords}")
                                                    exit(1)

                                        # columns_selected = key_check_fn('columns', dataset_details, '')
                                        if any('columns' in key for key in dataset_details):
                                            try:
                                                columns_selected = dataset_details['columns']
                                            except KeyError as ke:
                                                columns_selected = ''
                                            columns_excluded = convert_str_to_list(key_check_fn('excludecolumns',
                                                                                                dataset_details, []))
                                        else:
                                            columns_selected = ''
                                            columns_excluded = []
                                        filters_applied = key_check_fn('filters', dataset_details, '')
                                        op_output = key_check_fn('op_output', dataset_details, '')
                                        commit_count_mismatch = key_check_fn('commit_count_mismatch', dataset_details,
                                                                             False)
                                         ##TODO: Change added by Naima VR for COMP3 functionality in output section
                                        comp3_col= key_check_fn('comp3_col', dataset_details, [])

                                          ## Todo # Added by Naima Vr for trigger_script functionality
                                        trigger_script= key_check_fn('trigger_script', dataset_details, None) 
                                        
                                         ## Todo # Added by Naima Vr for api functionality
                                        if conn_details['datatype'] == "api":
                                            payload= key_check_fn('payload', dataset_details, None)
                                            method=  key_check_fn('method', dataset_details, None)
                                            api_dataset=  key_check_fn('dataset', dataset_details, None)
                                            op_output = key_check_fn('op_output', dataset_details, '')
                                            dataset_list.append(dict(
                                                payload=payload,
                                                method=method,
                                                api_dataset=api_dataset,
                                                dataset_format=conn_details['dataset_format'],
                                                op_output=op_output))
                                        elif conn_details['datatype'] == "database":
                                            create_table_flag = key_check_fn('create_table', dataset_details, False)
                                            create_column_flag = key_check_fn('create_column', dataset_details, False)
                                            table_name = key_check_fn('table_name', dataset_details,
                                                                      dataset_details['dataset'])

                                            if re.findall(r'[.]+', table_name):
                                                tb_name = table_name.split('.')
                                                if len(tb_name[1]) >= 30:
                                                    print(
                                                        f"Length of table name '{table_name}' must be less than 30 characters")
                                                    exit(1)
                                            else:
                                                if len(table_name) >= 30:
                                                    print(
                                                        f"Length of table name '{table_name}' must be less than 30 characters")
                                                    exit(1)

                                            truncate_before_load_flag = key_check_fn('truncate_before_load',
                                                                                     dataset_details, False)
                                            backup_before_truncate_flag = key_check_fn('backup_before_truncate',
                                                                                       dataset_details, True)
                                            target_filter_flag = key_check_fn('target_filter', dataset_details, '')

                                            if any('insert_type' in key for key in dataset_details):
                                                insert_type_provided = dataset_details['insert_type'].lower()
                                                # print("insert_type_provided :", insert_type_provided)
                                                insert_types = ['insert', 'insert_with_key', 'upsert',
                                                                'upsert_with_key', 'align_with_source',
                                                                'update_with_source', 'update_target']
                                                if insert_type_provided not in insert_types:
                                                    print(
                                                        f"\n Invalid keyword '{insert_type_provided}' in insert_types\n "
                                                        f"Valid insert_types are {insert_types}")
                                                    logging.error(
                                                        f"Invalid keyword '{insert_type_provided}' in insert_types \n "
                                                        f"Valid insert_types are {insert_types}")
                                                    exit(1)
                                                if any('insert_cond' in key for key in dataset_details):
                                                    insert_cond_given = dataset_details['insert_cond']
                                                    # print("insert_cond_given", insert_cond_given)
                                                    if insert_cond_given:
                                                        for insert_cond in insert_cond_given:
                                                            upsert_columns_given = key_check_fn('upsert_columns',
                                                                                                insert_cond, '')
                                                            insert_cond['upsert_columns'] = upsert_columns_given
                                                            insert_cond['upsert_cond'] = key_check_fn('upsert_cond',
                                                                                                      insert_cond, '')
                                                            if any('upsert_keys' in key for key in insert_cond_given):
                                                                pass
                                                            else:
                                                                logging.error("Upsert keys are not given")
                                                                print(f"Provide the upsert_keys for insert_type:"
                                                                      f" '{insert_type_provided}'")
                                                                exit(1)
                                                else:
                                                    if insert_type_provided == 'upsert' or \
                                                            insert_type_provided == 'upsert_with_key' \
                                                            or insert_type_provided == 'update_target':
                                                        logging.error("Upsert conditions are not given")
                                                        print(f"Provide the conditions for upserting data:"
                                                              f" '{insert_type_provided}'")
                                                        exit(1)
                                                    else:
                                                        insert_cond_given = 'NA'
                                                if any('insert_key' in key for key in dataset_details):
                                                    insert_key_provided = dataset_details['insert_key']
                                                else:
                                                    if insert_type_provided == 'upsert_with_key' or \
                                                            insert_type_provided == 'insert_with_key':
                                                        logging.error("Insert Key is not given")
                                                        print("Provide the Insert Key for upserting data")
                                                        exit(1)
                                                    else:
                                                        insert_key_provided = 'NA'
                                            else:
                                                insert_type_provided = 'insert'
                                                insert_cond_given = 'NA'
                                                insert_key_provided = 'NA'

                                            dataset_list.append(dict(
                                                dataset=dataset_details['dataset'],
                                                dataset_format=conn_details['dataset_format'],
                                                table_name=table_name,
                                                columns=columns_selected,
                                                excludecolumns=columns_excluded,
                                                filters=filters_applied,
                                                create_table=create_table_flag,
                                                create_column=create_column_flag,
                                                op_output=op_output,
                                                truncate_before_load=truncate_before_load_flag,
                                                backup_before_truncate=backup_before_truncate_flag,
                                                insert_type=insert_type_provided,
                                                insert_cond=insert_cond_given,
                                                insert_key=insert_key_provided,
                                                target_filter=target_filter_flag,
                                                commit_count_mismatch=commit_count_mismatch,
                                                comp3_col=comp3_col,
                                                trigger_script=trigger_script
                                                ))
                                        else:
                                            file_name = key_check_fn('file_name', dataset_details,
                                                                     dataset_details['dataset'])

                                            delimiter = key_check_fn('delimiter',dataset_details,'comma')

                                            file_type = key_check_fn('file_type', dataset_details, 'ASCII')

                                          ##Todo # Added by Naima VR  for headers- to remove header info
                                            headers= key_check_fn('headers',dataset_details,True)

                                            ##TODO# Added by Naima VR for insert_string functionality
                                            insert_string=  key_check_fn('insert_string',dataset_details,False)

                                            ##TODO#Added by Naima vr for date_format
                                            date_format=key_check_fn('date_format',dataset_details,None)
                                              
                                            ##TODO# Added by Naima vr for Maintaining spaces as per COPYBOOK
                                            data_structure=  key_check_fn('data_structure',dataset_details,None)
                                            ##TODO#Added by Guru Arun for space padding in comp3 functionality
                                            record_length=key_check_fn('record_length',dataset_details,None)
                                            print("in output section in detailed json genration")
                                            print(dataset_details)

                                            dataset_list.append(dict(
                                                dataset=dataset_details['dataset'],
                                                dataset_format=conn_details['dataset_format'],
                                                file_name=file_name,
                                                columns=columns_selected,
                                                excludecolumns=columns_excluded,
                                                filters=filters_applied,
                                                op_output=op_output,
                                                insert_type='NA',
                                                insert_cond='NA',
                                                insert_key='NA',
                                                target_filter='NA',
                                                delimiter = delimiter,
                                                file_type = file_type,
                                                comp3_col=comp3_col,
                                                headers = headers,
                                                insert_string=insert_string,
                                                date_format=date_format,
                                                trigger_script=trigger_script,
                                                data_structure=data_structure ,
                                                record_length=record_length))
                                    except Exception as e:
                                        print('Exception: ', e)
                                        raise Exception(e)
                                        # logging.error("Please check DATA TARGETS in output section of given YAML FILE")
                                        # print("Please check DATA TARGETS in output section of given YAML FILE")
                                        # exit(1)

                            # Getting connector details
                            db_dataset_details, fs_dataset_details,api_dataset_details = get_connector_details(conn_details,
                                                                                           dataset_list,
                                                                                           db_dataset_details,
                                                                                           fs_dataset_details,api_dataset_details)
                            print(" in detailed 465 line DJG json db_dataset_details", db_dataset_details)

                        if section == 'input':                        
                            data_source_list = {'FileSystem': fs_dataset_details, 'DataBase': db_dataset_details}
                        elif section == 'output':
                            data_target_list = {'FileSystem': fs_dataset_details, 'DataBase': db_dataset_details,'API':api_dataset_details }
                            try:
                                if any('transformations' in key for key in section_details):
                                    transformations_keywords_validation(section_details['transformations'])
                                    transformation = section_details['transformations']

                                    # Getting transformation details in output section
                                    datatransformations = get_transformation_details(transformation, section)
                            except Exception as e:
                                # print('Exception: ', e)
                                logging.error("Please check DATA TRANSFORMATIONS in output section of given YAML FILE")
                                print("Please check DATA TRANSFORMATIONS in output section of given YAML FILE")
                                raise Exception(e)
                    else:
                        if section == "output":
                            try:
                                if any('transformations' in key for key in section_details):
                                    transformation = section_details['transformations']

                                    # Getting transformation details in output section
                                    datatransformations = get_transformation_details(transformation, section)
                            except Exception as e:
                                # print('Exception: ', e)
                                logging.error("Please check DATA TRANSFORMATIONS in output section of given YAML FILE")
                                print("Please check DATA TRANSFORMATIONS in output section of given YAML FILE")
                                raise Exception(e)
                except Exception as e:
                    if 'NoneType' in str(e):
                        pass
                    else:
                        print("Error :", str(e))
                        exit(1)

            elif section == 'data':
                processing = df_config[section]['processing']
                if processing is not None:
                    processing_keywords = ['operations', 'filters', 'derivedcolumns', 'renamecolumns',
                                           'finalcolumns', 'validations', 'excludecolumns']
                    for key in processing.keys():
                        if key not in processing_keywords:
                            print(f"\n Invalid keyword '{key}' in data section.\n"
                                  f"Valid key_words are: {processing_keywords}")
                            logging.error(f"Invalid keyword '{key}' in data section.\n"
                                          f"Valid key_words are: {processing_keywords}")
                            exit(1)
                try:
                    # Checking for data validation conditions
                    if any('validations' in key for key in processing):
                        if processing['validations'] is not None:
                            # val_keywords
                            val_keywords = ["val_seq", "val_type", "val_col", "datasets", "val_output"]
                            for key in processing['validations'][0].keys():
                                if key not in val_keywords:
                                    print(f"\n Invalid keyword '{key}' in validations.\n"
                                          f"Valid key_words are: {val_keywords}")
                                    logging.error(f"Invalid keyword '{key}' in validations.\n"
                                                  f"Valid key_words are: {val_keywords}")
                                    exit(1)
                        # Sorting based on validation sequence number
                        logging.debug("Sorting validations")
                        data_section['Validations'] = sorted(processing['validations'], key=lambda i: i['val_seq'])
                        for validation in data_section['Validations']:
                            validation['val_col'] = key_check_fn('val_col', validation, 'All')
                            validation['val_seq_name'] = key_check_fn('val_seq_name', validation, validation['val_seq'])
                            validation['val_output'] = key_check_fn('val_output', validation, False)

                    # Checking if any operations are given
                    if any('operations' in key for key in processing):
                        # Added on 10/09/2020 to generate a backup file based on user input
                        op_keywords = ["op_seq", "op_type", "op_seq_name", "op_subtype", "op_cond", "datasets",
                                       'transformations', "op_output", "op_col", "op_value", "empty_datasets",
                                       "purge_datasets", "backup_before_truncate"]

                        # Sorting based on operational sequence number
                        logging.debug("Sorting operations")
                        data_section['Operations'] = sorted(processing['operations'], key=lambda i: i['op_seq'])

                        op_seq_names_list = []
                        op_seq_list = []
                        for operation in data_section['Operations']:
                            for key in operation.keys():
                                if key not in op_keywords:
                                    print(f"\n Invalid keyword '{key}' in operations.\n"
                                          f"Valid key_words are: {op_keywords}")
                                    logging.error(f"Invalid keyword '{key}' in operations.\n"
                                                  f"Valid key_words are: {op_keywords}")
                                    exit(1)
                            operation['op_type'] = key_check_fn('op_type', operation, 'read').lower()
                            op_types = ['join', 'union', 'concat', 'fill_null', 'transformations', 'command', 'read',
                                        'delete', 'compare',  # added on 10/09/2020 to compare dataframes
                                        'execute_query']  # added on 12/03/2020 to execute queries
                            if operation['op_type'] not in op_types:
                                print(f"\n Invalid  keyword '{operation['op_type']}' in op_type \n "
                                      f"Valid op_types are {op_types}.")
                                logging.error(f"Invalid keyword '{operation['op_type']}' in op_type \n "
                                              f"Valid op_types are {op_types}.")
                                exit(1)

                            # print("op_cond:", operation['op_cond'])
                            if any('op_cond' in key for key in operation):
                                if type(operation['op_cond'][0]) == dict:

                                    op_conditions_keys = operation['op_cond'][0].keys()

                                    if not {'left_on', 'right_on'}.issubset(set(op_conditions_keys)):
                                        print(f"\n Both left and right join keys should be provided.")
                                        logging.error(f"Both left and right join keys should be provided.")
                                        exit(1)
                                    op_conditions = ['left_on', 'right_on', 'cond', 'left_dtype', 'right_dtype',
                                                     'left_column_keys', 'right_column_keys', 'mapping_keys',
                                                     'suffixes', 'record_inclusion', 'cond_ovr']
                                    for key in op_conditions_keys:
                                        if key not in op_conditions:
                                            print(f"\n Invalid keyword '{key}' in op_condition \n "
                                                  f"Valid op_conditions are {op_conditions}")
                                            logging.error(f"Invalid keyword '{key}' in op_condition \n "
                                                          f"Valid op_conditions are {op_conditions}")
                                            exit(1)

                                    operation['op_cond'][0]['cond_ovr'] = key_check_fn('cond_ovr',
                                                                                       operation['op_cond'][0], False)
                                    override = operation["op_cond"][0]['cond_ovr']
                                    condition_override_defaults = ['left_only', 'right_only']
                                    if type(override) != bool:
                                        if override not in condition_override_defaults:
                                            print(f"\n Invalid keyword '{override}' in condition_override \n "
                                                  f"Valid condition_overrides are {condition_override_defaults}")
                                            logging.error(f"Invalid keyword '{override}' in condition_override \n "
                                                          f"Valid condition_overrides are {condition_override_defaults}")
                                            exit(1)
                                    dtype_values = ['varchar', 'str', 'object', 'character varying', 'char', 'obj',
                                                    'string', 'int', 'numeric', 'number', 'integer', 'date']
                                    for side in ['left_dtype', 'right_dtype']:
                                        if any(side in key for key in operation['op_cond'][0]):
                                            for data_type in operation['op_cond'][0][side]:
                                                if data_type not in dtype_values:
                                                    print(f"\n Invalid datatype: '{data_type}' \n"
                                                          f"Valid datatypes are: {dtype_values}")
                                                    logging.error(f"\n Invalid datatype: '{data_type}' \n"
                                                                  f"Valid datatypes are: {dtype_values}")
                                                    exit(1)
                            # subtype_keywords
                            if operation['op_type'].lower() == 'join':
                                operation['op_subtype'] = key_check_fn('op_subtype', operation, 'left').lower()

                                subtype_keywords = ['inner', 'outer', 'left', 'right']
                                if operation['op_subtype'] not in subtype_keywords:
                                    print(
                                        f"Invalid keyword '{operation['op_subtype']}' in op_subtype\n "
                                        f"Valid op_subtypes are {subtype_keywords}.")
                                    logging.error(
                                        f"Invalid keyword '{operation['op_subtype']}' in op_subtype \n "
                                        f"Valid op_subtypes are {subtype_keywords}.")
                                    exit(1)

                            if operation['op_type'] == 'command':
                                operation['op_subtype'] = key_check_fn('op_subtype', operation, 'pandas')
                                subtype_keywords = ['python', 'pandas', 'py', 'multi_line_command']
                                if operation['op_subtype'] not in subtype_keywords:
                                    print(
                                        f"Invalid  keyword '{operation['op_subtype']}' in op_subtype\n "
                                        f"Valid op_subtypes are {subtype_keywords}.")
                                    logging.error(
                                        f"Invalid keyword '{operation['op_subtype']}' in op_subtype \n "
                                        f"Valid op_subtypes are {subtype_keywords}.")
                                    exit(1)

                            if operation['op_type'] == 'compare':
                                operation['op_cond'][0]['mapping_keys'] = key_check_fn(
                                    'mapping_keys', operation['op_cond'][0], [])
                                operation['op_cond'][0]['suffixes'] = key_check_fn(
                                    'suffixes', operation['op_cond'][0], [])
                                operation['op_cond'][0]['record_inclusion'] = key_check_fn(
                                    'record_inclusion', operation['op_cond'][0], 'mismatched')

                            operation['backup_before_truncate'] = key_check_fn('backup_before_truncate', operation,
                                                                               True)
                            operation['op_seq_name'] = key_check_fn('op_seq_name', operation, operation['op_seq'])

                            if operation['op_seq_name'] in op_seq_names_list:
                                print(f"\n op_seq '{operation['op_seq_name']}' is already exists.")
                                exit(1)
                            op_seq_names_list.append(operation['op_seq_name'])
                            if operation['op_seq'] in op_seq_list:
                                print(f"\n op_seq '{operation['op_seq']}' is already exists.")
                                exit(1)
                            op_seq_list.append(operation['op_seq'])

                            if any('datasets' in key for key in operation):
                                if type(operation['datasets']) == list:
                                    for data_set in operation['datasets']:
                                        try:
                                            if operation['op_seq'] <= int(data_set):
                                                print(f"\n Please check datasets in op_seq {operation['op_seq']} ")
                                                exit(1)
                                        except ValueError:
                                            pass
                                else:
                                    try:
                                        if operation['op_seq'] <= int(operation['datasets']):
                                            print(f"\n Please check datasets in op_seq {operation['op_seq']} ")
                                            exit(1)
                                    except ValueError:
                                        pass
                            else:
                                if operation['op_seq'] == 1:
                                    print(f"\n Please provide 'datasets' for op_seq  {operation['op_seq']}")
                                    logging.error(f"Please provide 'datasets' for op_seq  {operation['op_seq']}")
                                    exit(1)
                                else:
                                    # Setting default value for datasets in operations section
                                    operation['datasets'] = op_seq_list[-2]
                                    print("op_seq :", operation['op_seq'], "dataset :", operation['datasets'])

                            operation['empty_datasets'] = key_check_fn('empty_datasets', operation, False)

                            if operation['op_type'] == 'transformations':
                                if any('transformations' in key for key in operation):
                                    transformations_keywords_validation(operation['transformations'])
                                    transformation = operation['transformations']
                                    del operation['transformations']
                                else:
                                    print(f"\n Please provide 'transformations' for op_seq  {operation['op_seq']}")
                                    logging.error(f"Please provide 'transformations' for op_seq  {operation['op_seq']}")
                                    exit(1)

                                # Getting transformation details
                                # for op_sequence
                                operation['Transformations'] = get_transformation_details(transformation, section)
                            operation['purge_datasets'] = key_check_fn('purge_datasets', operation, None)
                            operation['purge_datasets'] = convert_str_to_list(operation['purge_datasets'])
                            # print(operation['purge_datasets'], type(operation['purge_datasets']), operation['purge_datasets'].sort())
                            # print(convert_str_to_list(operation['purge_datasets']).sort())
                            if not operation['purge_datasets'] is None:
                                operation['purge_datasets'].sort()

                    # Checking if any filters are given
                    data_section['Filters'] = key_check_fn('filters', processing, None)

                    # Checking if any new column is to be append
                    if any('derivedcolumns' in key for key in processing):
                        if processing['derivedcolumns'] is not None:
                            # derived_col_keywords
                            derived_col_keywords = ["formula", "col_name", "formula_type", "module", "engine"]
                            for key in processing['derivedcolumns'][0].keys():
                                if key not in derived_col_keywords:
                                    print(f"\n Invalid keyword '{key}' in derivedcolumns. \n"
                                          f'Valid key_words are: {derived_col_keywords}')
                                    logging.error(f"Invalid keyword '{key}' in derivedcolumns. \n"
                                                  f"Valid key_words are: {derived_col_keywords}")
                                    exit(1)
                            data_section['DerivedColumns'] = processing['derivedcolumns']
                            # API Related formulas mapping
                            data_section = derived_columns_changes(data_section, api_file_path)
                            for i, formulae in enumerate(data_section['DerivedColumns']):
                                # print(i, formulae)
                                if data_section['DerivedColumns'][i]['formula_type'].lower() != 'api':
                                    data_section['DerivedColumns'][i]['col_name'] \
                                        = convert_str_to_list(data_section['DerivedColumns'][i]['col_name'])
                                    data_section['DerivedColumns'][i]['formula'] \
                                        = convert_str_to_list(data_section['DerivedColumns'][i]['formula'])
                                    columns_len = len(data_section['DerivedColumns'][i]['col_name'])
                                    formulas_len = len(data_section['DerivedColumns'][i]['formula'])
                                    if columns_len != formulas_len:
                                        logging.error("Given columns doesn't match with formulas")
                                        print(f"Given columns doesn't match with formulas\n"
                                              f"Check derived column in processing section")
                                        print(data_section['DerivedColumns'][i]['formula_type'])
                                        exit(1)
                                # print("\n", formulae)
                            # exit(1)
                except Exception as e:
                    print('Exception: ', e)
                    print("Please check 'Processing' in data section of given YAML FILE")
                    logging.error("Please check 'Processing' in data section of given YAML FILE")
                    exit(1)
                    # raise e
        detailed_json = {"common": dict(Properties=batch_properties, job_alerts=job_alert_details),
                         "input": dict(DataSources=data_source_list),
                         "data": dict(Processing=data_section),
                         "output": dict(Transformations=datatransformations, DataTargets=data_target_list,
                                        Validations={})}

        # Getting Validation Reports details for saving validation reports
        try:
            if any('output' in key for key in df_config):
                section_details = df_config['output']
                if any('validation_report' in key for key in section_details):
                    validation_report = section_details['validation_report']
                    fs_dataset_details = []
                    db_dataset_details = []
                    #Added by Naima VR for adding api connetion details
                    api_dataset_details=[]

                    for connector in validation_report:
                        conn_details = conn_config[connector]
                        dataset_list = []
                        # print(connector)
                        # print(validation_report)
                        for dataset_details in section_details['validation_report'][connector]:
                            val_output = key_check_fn('val_output', dataset_details, '')
                            columns_selected = key_check_fn('columns', dataset_details, '')
                            create_column_flag = key_check_fn('create_column', dataset_details, False)
                            create_table_flag = key_check_fn('create_table', dataset_details, None)
                            table_name = key_check_fn('table_name', dataset_details, dataset_details['dataset'])

                            dataset_list.append(dict(
                                dataset=dataset_details['dataset'],
                                dataset_format=conn_details['dataset_format'],
                                table_name=table_name,
                                columns=columns_selected,
                                create_table=create_table_flag,
                                create_column=create_column_flag,
                                val_output=val_output))

                        # Getting connector details
                        db_dataset_details, fs_dataset_details,api_dataset_details = get_connector_details(conn_details,
                                                                                       dataset_list,
                                                                                       db_dataset_details,
                                                                                       fs_dataset_details,api_dataset_details)

                    data_validation_reports_list = {'DataBase': db_dataset_details, 'FileSystem': fs_dataset_detailsi,'API':api_dataset_details}
                    detailed_json['output']['Validations'] = data_validation_reports_list
        except Exception as e:
            # print('Exception: ', e)
            if 'NoneType' in str(e):
                pass
            else:
                print("Error :", str(e))
                exit(1)
            # raise e

        json_file_name, json_file_path = generate_file_name(get_property('detail_json_file_path'), 'df_config_details',
                                                            'json')
        json_file_name = os.path.join(json_file_path, json_file_name)
        # json_file_name = json_file_name.replace('.txt', '.json')
        with open(json_file_name, 'w') as file_path:
            logging.info("Saving detailed json to file '" + json_file_name + "' in path " + json_file_path)
            detailed_json = EditDetailedJson.usr_val_to_dtjson(detailed_json)
            json.dump(detailed_json, file_path, indent=4)
            print(json.dumps(detailed_json, indent=4))

        if run_type == 'run':
            print("Saved detailed json to file '" + json_file_name + "' in path " + json_file_path)
            logging.debug("Saved detailed json file")
            return detailed_json
        else:
            print("Saved detailed json to file '" + json_file_name + "' in path " + json_file_path)
            print("Successfully validated the given file")
            logging.debug("Validation completed")
            exit(1)

    except Exception as e:
        print("Exception in main try block")
        print(e)
        raise Exception(e)


@profiling
def get_connector_details(conn_details, dataset_list, db_dataset_details, fs_dataset_details,api_dataset_details):
    print("in if line no 830 in DJG", conn_details)

    """

    :param conn_details:
    :param dataset_list:
    :param db_dataset_details:
    :param fs_dataset_details:
    :param api_dataset_details:
    :return:
    """
    # Database
    if conn_details['datatype'] == "database":

        uuid = conn_details['uuid'] if 'uuid' in conn_details.keys() else None

        db_dataset_details.append(dict(
            alias=conn_details['database'],
            uuid=uuid,
            host=conn_details['hostname'],
            username=conn_details['username'],
            password=conn_details['password'],
            port=conn_details['port'],
            datasets=dataset_list))

    # Filesystem
    elif conn_details['datatype'] == "filesystem":
        uuid = conn_details['uuid'] if 'uuid' in conn_details.keys() else None

        fs_dataset_details.append(dict(
            alias=conn_details['dataset'],
            uuid=uuid,
            path=conn_details['file_path'],
            datasets=dataset_list))
      #api
    elif  conn_details['datatype'] == "api":
        api_dataset_details.append(dict(
            url=conn_details['url'],
            headers=conn_details['headers'],
            datasets=dataset_list))
       # print("api_dataset_details: \n",api_dataset_details)
    return db_dataset_details, fs_dataset_details,api_dataset_details


@profiling
def get_transformation_details(transformation, section):
    """

    :param transformation:
    :param section:
    :return:
    """
    datatransformation = {}

    if transformation:
        # Checking if new columns are to be appended
        try:
            if any('derivedcolumns' in key for key in transformation):
                if transformation['derivedcolumns'] is not None:
                    # derived_col_keywords
                    derived_col_keywords = ["formula", "col_name", "formula_type", "module", "engine"]
                    for key in transformation['derivedcolumns'][0].keys():
                        if key not in derived_col_keywords:
                            print(f"\n Invalid keyword '{key}' in derived columns. \n"
                                  f"Valid key_words are: {derived_col_keywords}")
                            logging.error(f"Invalid keyword '{key}' in derived olumns. \n"
                                          f"Valid key_words are: {derived_col_keywords}")
                            exit(1)
                    formula_type = transformation['derivedcolumns'][0]['formula_type'] = \
                        transformation['derivedcolumns'][0]['formula_type'].lower()

                    formula_types = ['arithmetic', 'arithmetical', 'arithmatic', 'arithmatical', 'api',
                                     'value', 'conditional']
                    if formula_type not in formula_types:
                        print(f"\n Invalid keyword '{formula_type}' in formula_type \n "
                              f"Valid formula_types are {formula_types}")
                        logging.error(f"Invalid keyword '{formula_type}' in formula_type \n "
                                      f"Valid formula_types are {formula_types}")
                        exit(1)
                datatransformation['DerivedColumns'] = transformation['derivedcolumns']

                # API Related formulas mapping
                if datatransformation['DerivedColumns']:
                    datatransformation = derived_columns_changes(datatransformation, api_file_path)
                for i, formulae in enumerate(datatransformation['DerivedColumns']):
                    if datatransformation['DerivedColumns'][i]['formula_type'].lower() != 'api':
                        datatransformation['DerivedColumns'][i]['col_name'] \
                            = convert_str_to_list(datatransformation['DerivedColumns'][i]['col_name'])
                        datatransformation['DerivedColumns'][i]['formula'] \
                            = convert_str_to_list(datatransformation['DerivedColumns'][i]['formula'])
                        columns_len = len(datatransformation['DerivedColumns'][i]['col_name'])
                        formulas_len = len(datatransformation['DerivedColumns'][i]['formula'])
                        if columns_len != formulas_len:
                            logging.error("Given columns doesn't match with formulas")
                            print(f"Given columns doesn't match with formulas\n"
                                  f"Check derived column in transformations of {section} section")
                            print(datatransformation['DerivedColumns'][i])
                            exit(1)
                # exit(1)
        except Exception as e:
            logging.error(f"Derived columns in {section} section of dpl_file is not given properly")
            print(f"\n Please check Derived columns section in {section} section of given YAML FILE")
            print("error", e)
            exit(1)

        # Checking if final columns are selected
        try:
            if any('finalcolumns' in key for key in transformation):
                if transformation['finalcolumns'] is not None:
                    # final_col_keywords
                    final_col_keywords = ["col_list", "col_data_file", "col_headers", "col_separator"]
                    for key in transformation['finalcolumns'][0].keys():
                        if key not in final_col_keywords:
                            print(f"\n Invalid keyword '{key}' in final columns.  \n"
                                  f'Valid key_words are: {final_col_keywords}')
                            logging.error(f"Invalid keyword '{key}' in final columns. \n"
                                          f"Valid key_words are: {final_col_keywords}")
                            exit(1)
                datatransformation['FinalColumns'] = transformation['finalcolumns']
                try:
                    if transformation['finalcolumns']:
                        # removing duplicate columns from column list
                        final_list = list(dict.fromkeys(transformation['finalcolumns'][0]['col_list']))
                        datatransformation['FinalColumns'][0]['col_list'] = final_list
                except Exception as e:
                    # print("Error in op Except :", e)
                    # exit(1)
                    pass
        except Exception as e:
            print('Exception: ', e)
            logging.error(f"Final columns in {section} section of dpl_file is not given properly")
            print(f"\n Please check Final columns section in {section} section of given YAML FILE")
            exit(1)

        # Checking if any filters are applied
        try:
            if any('filters' in key for key in transformation):
                if transformation['filters'] is not None:
                    for key in transformation['filters'][0].keys():
                        if key not in ["fil_list"]:
                            print(f"\n Invalid keyword '{key}' in filters. \n"
                                  f"Valid key_words are: 'fil_list' ")
                            logging.error(f"Invalid keyword '{key}' in filters. \n"
                                          f"Valid key_words are: 'fil_list' ")
                            exit(1)

                datatransformation['Filters'] = transformation['filters']
                if datatransformation['Filters']:
                    for fil in datatransformation['Filters']:
                        if any('fil_list' in key for key in fil):
                            pass
                        else:
                            print(f"\n Please check Filters section in {section} section of given YAML FILE")
                            exit(1)
        except Exception as e:
            print('Exception: ', e)
            logging.error(f"Filters in {section} section of dpl_file is not given properly")
            print(f"\n Please check Filters section in {section} section of given YAML FILE")
            exit(1)

        # checking if any columns are to be renamed or not
        try:
            if any('renamecolumns' in key for key in transformation):
                if transformation['renamecolumns']:
                    if any('col_data_file' in key for key in transformation['renamecolumns']):
                        logging.error("Rename columns file path is not provided")
                        print("Provide columns file path in include section")
                        exit(1)
                    else:
                        datatransformation['RenamedColumns'] = transformation['renamecolumns']
        except Exception as e:
            print('Exception: ', e)
            if str(e) == 'string indices must be integers':
                print("Provide rename columns file in inputs file ")
                logging.error("Rename columns file is not provided in inputs file")
            else:
                logging.error(f"RenamedColumns in {section} section of dpl_file is not given properly")
                print(f"\n Please check RenamedColumns section in {section} section of given YAML FILE")
            exit(1)

        # Checking if final columns are selected
        try:
            if any('excludecolumns' in key for key in transformation):
                if transformation['excludecolumns'] is not None:
                    # final_col_keywords
                    final_col_keywords = ["col_list", "col_data_file", "col_headers", "col_separator"]
                    for key in transformation['excludecolumns'][0].keys():
                        if key not in final_col_keywords:
                            print(f"\n Invalid keyword '{key}' in exclude columns.  \n"
                                  f'Valid key_words are: {final_col_keywords}')
                            logging.error(f"Invalid keyword '{key}' in exclude columns. \n"
                                          f"Valid key_words are: {final_col_keywords}")
                            exit(1)
                datatransformation['ExcludeColumns'] = transformation['excludecolumns']
                try:
                    if transformation['excludecolumns']:
                        # removing duplicate columns from column list
                        final_list = convert_str_to_list(transformation['excludecolumns'][0]['col_list'])
                        final_list = list(dict.fromkeys(final_list))
                        datatransformation['ExcludeColumns'][0]['col_list'] = final_list
                except Exception as e:
                    # print("Error in op Except :", e)
                    # exit(1)
                    pass
        except Exception as e:
            print('Exception: ', e)
            logging.error(f"Exclude columns in {section} section of dpl_file is not given properly")
            print(f"\n Please check Exclude columns section in {section} section of given YAML FILE")
            exit(1)

    return datatransformation


@profiling
def derived_columns_changes(section_details, api_file_path):
    """

    :param section_details:
    :param api_file_path:
    :return:
    """
    i = 0
    for dervied_col_details in section_details['DerivedColumns']:
        formula_details = []
        if dervied_col_details['formula_type'] == 'api':
            """When format is 
            formula_type: API
            engine: api name
            formula: [col_name1:name in api, col_name2:name in api]"""
            if not any('col_name' in key for key in dervied_col_details):
                derived_col = dervied_col_details
                if api_file_path != '':
                    if not any('api_formula' in key for key in derived_col):
                        try:
                            formulas = derived_col['formula']
                            file_name = derived_col['engine']
                            for formula in formulas:
                                col_details = {}
                                col_name = formula.split(':')[0]
                                formula_name = formula.split(':')[1]
                                col_details['col_name'] = col_name
                                col_details['formula_type'] = 'api'
                                col_details['formula'] = file_name + ',' + formula_name
                                col_details['api_name'] = os.path.join(api_file_path, file_name + '.py')
                                formula_file_path = os.path.join(api_file_path, file_name + '.yml')
                                col_details['api_formula'] = api_file(file_path=formula_file_path,
                                                                      formula_name=formula_name)
                                formula_details.append(col_details)
                            for api_formula in formula_details[::-1]:
                                section_details['DerivedColumns'].insert(i, api_formula)
                            section_details['DerivedColumns'].remove(dervied_col_details)
                        except KeyError:
                            """ When format is
                            formula_type: API
                            engine: api name
                            """
                            file_name = derived_col['engine']
                            # print(derived_col)
                            derived_col['col_name'] = ''
                            derived_col['formula'] = file_name + ','
                            derived_col['api_formula'] = ''
                            derived_col['api_name'] = os.path.join(api_file_path, file_name + '.py')
                            derived_col['module'] = key_check_fn('module', derived_col, ["ALL_MODULES"])
                            derived_col['module'] = convert_str_to_list(derived_col['module'])

                else:
                    raise Exception("Please include api_file_path in inputs file")

            else:
                """ When format is 
                col_name: column name
                formula_type: API
                formula: api name, name in api
                """
                formula_given = dervied_col_details['formula']
                file_name = formula_given.split(',')[0]
                formula_name = formula_given.split(',')[1]
                dervied_col_details['api_name'] = os.path.join(api_file_path, file_name + '.py')
                formula_file_path = os.path.join(api_file_path, file_name + '.yml')
                dervied_col_details['api_formula'] = api_file(file_path=formula_file_path, formula_name=formula_name)
        i += 1
    return section_details


@profiling
def api_file(file_path, formula_name):
    """

    :param file_path:
    :param formula_name:
    :return:
    """
    # print(file_path, formula_name)
    metrics_file = read_yaml_file.read_yuml(file_path)
    formulas_in_file = metrics_file['Metrics']
    try:
        for _ in formulas_in_file:
            # print("formula: ", _)
            if _['name'] == formula_name:
                return _['formula']
    except Exception as e:
        raise e


@profiling
def convert_str_to_list(values):
    """
    :param values:
    :return:
    """
    try:
        if type(values) == int or type(values) == float:
            values = [values]
            return values
        elif values is None:
            return values
        else:
            if ',' in values:
                values = values.replace(', ', ',')
                if values[-1] == ',':
                    values = values[:-1]
            if type(values) != list and ',' not in values:
                values = values.split(",")
                return values
            elif type(values) != list and ',' in values:
                values = values.split(",")
                return values
            else:
                # print("in else")
                return values
    except Exception as e:
        print("Exception ", e)
        raise e


@profiling
def key_check_fn(keyword, value_to_be_check, false_value):
    """
    Checks whether given keyword is present or not is given key_value pairs
    :param keyword:
    :param value_to_be_check:
    :param false_value:
    :return: value of the keyword present
             else returns false_value that is given
    """
    if any(keyword in key for key in value_to_be_check):
        return value_to_be_check[keyword]
    else:
        return false_value


@profiling
def column_selection_through_external_file(input_files, df_config):
    """

    :param input_files:
    :param df_config:
    :return:
    """

    # file_path = input_files['include']['column_derivations']
    file_path = get_property(input_files['include']['column_derivations'])

    try:
        # columns selection  in operation-sequences
        if any('data' in key for key in df_config) and any('operations' in key for key in
                                                           df_config['data']['processing']):
            if any("transformations" in key for key in df_config['data']['processing']['operations']):
                for operation in df_config['data']['processing']['operations']:
                    try:
                        if operation['op_type'] == 'transformations':

                            # rename columns
                            if any('renamecolumns' in _ for _ in operation['transformations']):
                                rename_cols_data = operation['transformations']['renamecolumns']

                                if any('col_data_file' in key for key in rename_cols_data[0]):
                                    # Reading column data from external file
                                    rename_file_data = read_external_file(rename_cols_data, file_path)
                                    operation['transformations']['renamecolumns'] = rename_file_data

                            # final column selection
                            if any('finalcolumns' in _ for _ in operation['transformations']):
                                finalcolumns_data = operation['transformations']['finalcolumns']

                                # Reading column data from external file
                                if not any('col_list' in key for key in finalcolumns_data[0]):
                                    finalcolumns_file_data = read_external_file(finalcolumns_data, file_path,
                                                                                'final_columns')
                                    operation['transformations']['finalcolumns'][0]['col_list'] = finalcolumns_file_data
                                    # exit(1)
                    except Exception as e:
                        # print("Error in re :", e)
                        # print('op_type' in str(e))
                        if 'NoneType' in str(e):
                            pass
                        elif 'op_type' in str(e):
                            pass
                        else:
                            print("Error :", str(e))
                            exit(1)
                df_config = df_config

        # Output section
        try:
            if any('output' in key for key in df_config) and any(
                    "transformations" in key for key in df_config['output']):
                # rename column selection in output section
                if any("renamecolumns" in key for key in df_config['output']['transformations']):
                    rename_cols_data = df_config['output']['transformations']['renamecolumns']

                    if any('col_data_file' in key for key in rename_cols_data[0]):
                        # Reading column data from external file
                        logging.debug("Checking whether columns renamed has given through an external file")
                        rename_file_columns = read_external_file(rename_cols_data, file_path)
                        df_config['output']['transformations']['renamecolumns'] = rename_file_columns
                # final column selection in output section
                if any("finalcolumns" in key for key in df_config['output']['transformations']):
                    finalcolumns_data = df_config['output']['transformations']['finalcolumns']

                    if not any('col_list' in key for key in finalcolumns_data[0]):
                        # Reading column data from external file
                        logging.debug("Checking whether final columns has given through an external file")
                        finalcolumns_file_data = read_external_file(finalcolumns_data, file_path, 'final_columns')
                        df_config['output']['transformations']['finalcolumns'][0]['col_list'] = finalcolumns_file_data
                # return df_config
        except Exception as e:
            if 'NoneType' in str(e):
                return df_config
            else:
                print("Error :", str(e))
                exit(1)
        return df_config
    except KeyError as k:
        print(k)
        print("Provide file name of  column selection file in dpl file")
        logging.error("Provide file of columns selection")
        exit(1)


@profiling
def read_external_file(col_data, file_path, return_type=None):
    """

    :param col_data:
    :param file_path:
    :param return_type:
    :return:
    """

    if any('col_data_file' in key for key in col_data[0]):
        columns_file_name = col_data[0]['col_data_file']
        columns_file_location = os.path.join(file_path, columns_file_name)
        logging.info("Getting column_names from external file")
        columns_file_data = read_files.get_file_type(col_data, columns_file_location,
                                                     columns_file_name, return_type)
        return columns_file_data
    else:
        return col_data


# keywords validation function for transformation
def transformations_keywords_validation(keywords_list):
    if keywords_list is not None:
        # transformations_keywords
        transformations_keywords = ["filters", "derivedcolumns", "renamecolumns", "finalcolumns", "excludecolumns"]
        for key in keywords_list.keys():
            if key not in transformations_keywords:
                print(f"\n Invalid keyword '{key}' in transformations. \n"
                      f'Valid key_words are  {transformations_keywords}')
                logging.error(f"Invalid keyword '{key}' in transformations. \n"
                              f'Valid key_words are  {transformations_keywords}')
                exit(1)
    pass
