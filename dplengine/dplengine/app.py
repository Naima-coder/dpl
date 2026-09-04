# filename: app.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: This is the main file which runs the dpl engine using a yml/dpl config file given as a system argument
# through command line.


import json
import logging
import os
import sys
import shutil
# import resource
from datetime import datetime

import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

from common.file_name_generation import generate_file_name, set_time
from models.connections import get_run_id
from models.job_properties import JobProperties
from models.read_props_file import get_property
from models.verbose_to_log import Logger
from resources import data_operations
from resources import data_target
from resources import data_validations
from resources import detailed_json_generation
from resources.add_variable_to_json import EditDetailedJson
from common.process_tracking import ProcessTracking
from common.auto_task_ticket_creation import raise_auto_task_ticket
from common.auto_task_ticket_creation import get_job_alert_details

params_dict = None

# Limiting the memory usage of app.py
# soft, hard from properties

# capturing apps log
#log_file_name, log_file_path = generate_file_name(directory_name=get_property('logs_file_path'), file_type='log_file',
#                                                file_extension='log')

# setting the log level through properties.ini
#JobProperties.logging_level(logging, os.path.join(log_file_path, log_file_name))

soft, hard = JobProperties.get_memory_resource_limit()
# resource.setrlimit(resource.RLIMIT_AS, (1073741824*soft, 1073741824*hard))
print(f"memory limits, soft: {soft}, hard: {hard}")

log_name = get_property('log_name')
logging = logging.getLogger(log_name)


def dplengine_main(url_file_name, arguments1=None, arguments2=None):
    params_dict = None
    try:
        sys.argv = ['app.py', url_file_name]
        
        # log_name = get_property('log_name')
        # gcloud_logging_client = google.cloud.logging.Client()
        # # Create a handler for Google Cloud Logging.
        # gcloud_logging_handler = CloudLoggingHandler(
        #     gcloud_logging_client, name=log_name)
        # stream_handler = logging.StreamHandler(sys.stdout)
        # stream_handler.setLevel(logging.INFO)

        # logger = logging.getLogger(log_name)
        # logger.setLevel(logging.INFO)
        # logger.addHandler(gcloud_logging_handler)
        # logger.addHandler(stream_handler)

        # logging = logging.getLogger(log_name)
        set_time()
        # capturing stdout to a log file
        logs_file_path = '/tmp/'
        verbose_file_name, verbose_file_path = generate_file_name(directory_name=logs_file_path, file_type='vlog',
                                                                file_extension='log')
        sys.stdout = Logger(os.path.join(verbose_file_path, verbose_file_name))

        job_start_time = datetime.now()
        print('---------------------------------------------------------------------------------------------------------------')

        # initial_config.yml is passed as argument
        file_name = ''
        file_ext = ''
        try:
            df_config_file = url_file_name
            logging.info("file name :" + df_config_file )
            file_name, file_ext = os.path.splitext(df_config_file)
            if file_ext not in ['.json', '.yml']:
                print(f"file format must be 'json' and 'yaml")
                logging.error(f"file format '{file_ext}' must be 'json' and 'yaml")
                exit()
            # Getting filename if file path is given
            base_file_name = os.path.basename(df_config_file)

        except Exception as e:
            # print("Exception", e)
            logging.error("Please provide DPL file name")
            exit()

        # run type argument
        run_type = None
        params_dict = None
        try:
            run_type = arguments1
            if run_type != 'validate' and run_type != 'run':
                run_time_variables_list = run_type.split(',')
                print("given run time variables", run_time_variables_list)
                logging.info(f"given run time variables {run_time_variables_list}")
                # adding the variables to detailed json which are passed as system argument
                params_dict = EditDetailedJson.sys_arg_vars_to_dtjson(run_time_variables_list)

                run_type = 'run'
            elif run_type == 'run' or 'validate':
                try:
                    run_time_variables_list = arguments2.split(',')
                    print("given run time variables", run_time_variables_list)
                    logging.info(f"given run time variables {run_time_variables_list}")

                    # adding the variables to detailed json which are passed as system argument
                    EditDetailedJson.sys_arg_vars_to_dtjson(run_time_variables_list)

                except Exception as e:
                    run_type = run_type
        except Exception as e:
            run_type = 'run'

        # capturing apps log
        log_file_name, log_file_path = generate_file_name(directory_name=get_property('logs_file_path'), file_type='log_file',
                                                        file_extension='log')

        # setting the log level through properties.ini
        # JobProperties.logging_level(logging, os.path.join(log_file_path, log_file_name))

        # Getting run_id
        run_id = 0  #get_run_id(base_file_name)

        logging.info("Generating detailed json file----------")
        start_time = datetime.now()

        # Generates detailed json from input json and connectors configuration file
        if file_ext == '.json':
            with open(df_config_file, 'r') as f:
                json_detailed = json.load(f)
        else:
            json_detailed = detailed_json_generation.generate_detailed_json(
                df_config_file, run_type)

        ###Print statement##
        print(json_detailed)
        end_time = datetime.now()
        difference = end_time - start_time
        logging.info("Time taken for generating json file: " + str(difference.total_seconds()) + " sec")

        start_time = datetime.now()

        # Data validations
        data_validation = data_validations.validate_data(json_detailed, run_id, logging)

        end_time = datetime.now()
        difference = end_time - start_time
        logging.info("Time taken for validations: " + str(difference.total_seconds()) + " sec")

        logging.debug("Doing data operations (such as join, union, filters, appending new columns) if available")

        # Connecting to Database and Filesystem and listing all data
        # frames and finally union or join  all data frames

        start_time = datetime.now()
        final_dataframe = data_operations.get_dataframe(json_detailed, logging)
        if final_dataframe is None or str(type(final_dataframe)) != "<class 'pandas.core.frame.DataFrame'>":
            raise Exception("Final Dataframe in None")

        end_time = datetime.now()
        difference = end_time - start_time
        logging.info("Time taken for performing data_operations: " + str(difference.total_seconds()) + " sec")

        logging.debug("Saving final dataframe to datatargets")

        start_time = datetime.now()

        # saving the final/result data frame to a target
        data_target.target(final_dataframe, json_detailed['output'], logging)

        end_time = datetime.now()
        difference = end_time - start_time
        logging.info("Time taken for saving data into targets: " + str(difference.total_seconds()) + " sec")
        logging.debug("Data saved, Work completed")

        job_end_time = datetime.now()
        run_time = job_end_time - job_start_time
        logging.info("Total time taken: " + str(run_time))
        logging.info("Log file with profiling data: '" + log_file_name + "' path: " + log_file_path)
    except Exception as e:
        logging.error("job failed", e)
        logging.info("Creating an auto task ticket")

        if os.path.isfile(verbose_file_name):
            logs_path = get_property('logs_file_path')
            logging.info(f"logs file path...............{logs_path}")
            file_name = os.path.basename(verbose_file_name)
            bucket_path = os.path.join(logs_path,file_name)
            logging.info(f"Bucket path.........{bucket_path}")
            shutil.move(verbose_file_name,bucket_path)

        raise_auto_task_ticket(get_job_alert_details(json_detailed))
        ProcessTracking.send_job_status_mail(status_code=1, email=params_dict)
        # sys.exit(1)
    except BaseException as e:
        logging.error("job failed", e)

        if os.path.isfile(verbose_file_name):
            logs_path = get_property('logs_file_path')
            logging.info(f"logs file path...............{logs_path}")
            file_name = os.path.basename(verbose_file_name)
            bucket_path = os.path.join(logs_path,file_name)
            logging.info(f"Bucket path.........{bucket_path}")
            shutil.move(verbose_file_name,bucket_path)

        ProcessTracking.send_job_status_mail(status_code=1, email=params_dict)
        # if 'Empty file' in str(e):
        #     sys.exit(2)
        # sys.exit(1)
    else:
        if os.path.isfile(verbose_file_name):
            logs_path = get_property('logs_file_path')
            logging.info(f"logs file path...............{logs_path}")
            file_name = os.path.basename(verbose_file_name)
            bucket_path = os.path.join(logs_path,file_name)
            logging.info(f"Bucket path.........{bucket_path}")
            shutil.move(verbose_file_name,bucket_path)
        logging.info("job succeeded")
        ProcessTracking.send_job_status_mail(status_code=0, email=params_dict)
        # sys.exit(0)
    # print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    # return("success")
