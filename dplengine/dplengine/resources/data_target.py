# filename: data_target.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: saving the data frame to a particular target mentioned in the dpl config/yml file

import os
import logging
import requests
from common.profiling import profiling
from models.connections import DataBaseConnections as DBConn
from models.save_datasets import SaveDataFrame
from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

@profiling
def target(final_dataframe, data, logging=logging):
    """
    :param final_dataframe:
    :param data:
    :param logging:
    :return:
    """

    source = data['DataTargets']
    logging.info("Saving to given data target")
    ##target_saving_status,target_file_dataset_name,target_dataset_name are added by Naima VR
    target_saving_status= False
    target_dataset_name=[]
    for entry in source:
        for datatarget in source[entry]:
            datasets = datatarget['datasets']
            for dataset in datasets:
                if dataset['op_output'] == '':
                    try:

                        if entry == 'FileSystem':
                            logging.info("Saving to given filesystem")

                            path = os.path.join(datatarget['path'], dataset['dataset'])
                          # saves final dataframe to the desired path
                         ## comp3_col,insert_string ,date_format,data_structure are added by Naima VR 
                         ##record_length Added by Guru Arun 
                            SaveDataFrame.save_to_file(path=path,
                                                   dataframe=final_dataframe,
                                                   filters=dataset['filters'],
                                                   columns=dataset['columns'],
                                                   delimiter = dataset['delimiter'],
                                                   file_type = dataset['file_type'],
                                                   headers=dataset['headers'],
                                                   logging=logging,
                                                   dataset=dataset['dataset'],
                                                   comp3_col=dataset['comp3_col'],
                                                   insert_string=dataset['insert_string'],
                                                   date_format=dataset['date_format'],
                                                   data_structure=dataset['data_structure'],
                                                   trigger_script=dataset['trigger_script'],
                                                   record_length=dataset['record_length'])
                            target_saving_status= True
                            target_dataset_name.append( dataset['dataset'])

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

                                SaveDataFrame.save_to_db(table_name=dataset['dataset'],
                                                     columns=dataset['columns'],
                                                     filters=dataset['filters'],
                                                     create_table=dataset['create_table'],
                                                     create_column=dataset['create_column'],
                                                     connection=connection,
                                                     dataframe=final_dataframe,
                                                     cursor=cursor,
                                                     dbtype=dbtype,
                                                     insert_type=dataset['insert_type'],
                                                     insert_cond=dataset['insert_cond'],
                                                     insert_key=dataset['insert_key'],
                                                     truncate_before_load=dataset['truncate_before_load'],
                                                     target_filter=dataset['target_filter'],
                                                     excludecolumns=dataset['excludecolumns'],
                                                     trigger_script=dataset['trigger_script'],
                                                     save_conditions=dataset) # Added on 10/09/2020 to generate a backup file based on user input

                                DBConn. \
                                    close_connection(connection)
                                target_saving_status= True
                                target_dataset_name.append(dataset['dataset'])

                            except Exception as e:
                                raise e
                    ##TODO #Added By Naima VR for api functionality
                        if entry == 'API':
                            api_dataset= dataset['api_dataset'].split(",")
                            print(f"api_datset: {api_dataset},target_dataset_name: {target_dataset_name}")
                            if target_saving_status== True and (set(api_dataset).issubset(set(target_dataset_name))):

                                responce=make_api_call(url=datatarget['url'],
                                                      headers= datatarget['headers'],
                                                      payload=dataset['payload'],
                                                      method=dataset['method']
                                                       )
                            elif  api_dataset[0].lower()== 'empty' :
                                responce=make_api_call(url=datatarget['url'],
                                                      headers= datatarget['headers'],
                                                      payload=dataset['payload'],
                                                      method=dataset['method']
                                                      )
                            else:
                                print("There is a mismatch of dataset name given, please verify !!! ")
 
                   
                    except Exception as e:
                        print("error occured while saving to target: ",e)         

def make_api_call(url,headers,method,payload=None):

    if headers =='None':
        headers= None

   # if payload is not None:
   #     payload = payload
   #     print("type of payload",type(payload))
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers)
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, json=payload)
        elif method.lower() == "put":
            response = requests.put(url, headers=headers, json=payload)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=headers)
        elif method.lower() == "patch":
            response = requests.patch(url, headers=headers, json=payload)
        else:
            print(f"HTTP method '{method}' not supported.")
        print("*****************************************************************************")
        print("Service call status code: ", response.status_code)
        print("service call responce: ",response.json())
        # Check the status code of the response
        if response.status_code == 200:
            print('service call status: Success!')
        elif response.status_code == 404:
            print('service call status: Not Found.')
        return response

    except Exception as e:
        print("An error occured while calling given api : ", e)


