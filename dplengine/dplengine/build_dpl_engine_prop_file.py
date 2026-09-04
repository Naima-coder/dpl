import os
from models.read_props_file import read_property

def build_dpl_engine_prop_file():
    try:
        properties = read_property('../dpl_env.properties')
        DPL_ROOT = properties['dpl_root']
        prop_file_path = os.path.join(DPL_ROOT, r'dplengine\\')
        print(prop_file_path)
        prop_file = 'dpl_engine.properties'
        prop_file_keys ={
                        'connectors_file_path': DPL_ROOT + '/config/connectors/conn_config.yml',
                        'column_derivations_file_path': DPL_ROOT+'/config/denorms/schemas/',
                        'job_properties_file_path': DPL_ROOT+'/dplengine/properties.ini',
                        'data_structures_file_path': DPL_ROOT + '/config/denorms/schemas/',
                        'apis_file_path': DPL_ROOT + '/config/denorms/apis/',
                        'logs_file_path': DPL_ROOT + '/logs/dplengine/appslog/',
                        'detail_json_file_path': DPL_ROOT + '/logs/dplengine/detail_json_files/',
                        'process_tracking_file_path': DPL_ROOT + '/logs/dplengine/process_tracking/',
                        'profiling_file_path': DPL_ROOT + '/logs/dplengine/profiling/',
                        'backup_file_path': DPL_ROOT + '/backup/',
                        'validation_db_name': 'oracle' ,
                        'validation_db_host': '',
                        'validation_db_user': '',
                        'validation_db_password': '',
                        'validation_db_port': '',
                        'validation_db_service_name': '',
                        'validation_db_table_name' : 'data_validation_rpt',
                        'api_url': 'http://localhost:5029/dplui/retrive_rules_test',
                        'email_sender': 'noreply_dpl@cswg.com',
                        'prod_servers': 'localhost',
                        'smtp_host' : 'smtp-relay.cswg.com',
                        'smtp_port' : '25',
                        'alternate_dsefs_connections': '10.0.42.61:5598,10.0.42.62:5598,10.0.42.63:5598,10.0.42.64:5598',
                        'default_df_save_chunk_size': None,
                        'keyword_mapping_file_path': DPL_ROOT + '/dplui/pivot_configuration/defaultview/keyword_mapping.yml',
                        'dplui_conn_config_path': DPL_ROOT +'/dplui/'
                        }
        with open(prop_file_path+prop_file, "w") as ui_prop_file:
            for key in prop_file_keys:
                ui_prop_file.write(key + ' = '+str(prop_file_keys[key])+'\n')
        print('properties file named "'+prop_file+'" created in path : '+prop_file_path)
    except Exception as e:
        print('Error occured while creating properties file :: '+str(e))
        raise Exception(e)

if __name__ == '__main__':
    build_dpl_engine_prop_file()
