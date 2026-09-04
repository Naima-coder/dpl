import pycurl
import os
from io import BytesIO
from models.connections import DataBaseConnections
import pandas as pd
import requests
from models.read_props_file import get_property
from datetime import datetime
from common.process_tracking import ProcessTracking
import logging

log_name = get_property('log_name')
logging = logging.getLogger(log_name)

class DSEFS:

    @staticmethod
    def check_connection(url):
        my_request = requests.get(f'{url}')
        status_code = my_request.status_code
        return status_code

    @staticmethod
    def get_alternate_connections(url):
        url_list = []
        modified_url = ''
        alternate_urls = str(get_property('alternate_dsefs_connections')).split(",")
        if '/' in str(url):
            url_list = url.split("/")
        elif '\\' in str(url):
            url_list = url.split("\\")

        file_name = url_list[-1]

        try:
            for alt_url in alternate_urls:
                url_list[2] = alt_url
                if '/' in str(url):
                    modified_url = '/'.join(url_list)
                elif '\\' in str(url):
                    modified_url = '\\'.join(url_list)
                status_code = DSEFS.check_connection(modified_url)
                if status_code == 401:
                    print("URL used for fetching the file from DSEFS", modified_url)
                    return modified_url, file_name
                else:
                    pass
            raise Exception("Unable to connect to the DSEFS")
        except Exception as error:
            raise Exception("Unable to connect to the DSEFS", error)

    @staticmethod
    def get_file(file_url):
        try:
            file_url, file_name = DSEFS.get_alternate_connections(file_url)
            url = str(file_url) + '?op=OPEN&noredirect=true'
            buffer = BytesIO()
            c = pycurl.Curl()
            c.setopt(c.VERBOSE, True)
            c.setopt(c.URL, url)
            c.setopt(c.USERPWD, 'sdspark:sdsp1rk')
            c.setopt(c.WRITEDATA, buffer)
            c.perform()
            body = buffer.getvalue()
            status_code = c.getinfo(pycurl.HTTP_CODE)
            c.close()
            if int(status_code) != 200:
               raise Exception(f"unable to get file from DSEFS, response code: {status_code}")
        except Exception as error:
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=f"empty file {file_name}",
                                            subject='Exception-critical')
            raise Exception("unable to get file from DSEFS")
        else:
            if not body:
                logging.info(f"Empty file :{file_name}")
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                f"[timestamp:{datetime.now()}]", excepetion=f"empty file {file_name}",
                                                subject='Exception-critical')
                raise BaseException(f"Empty file :{file_name}")
            return body

    @staticmethod
    def put_file(file_location, file_name):
        pass

    @staticmethod
    def get_file_name(file_url):
        file_id = DSEFS.file_url_to_id(file_url)
        try:
            file_id = int(file_id)
        except Exception as error:
            return file_url
        else:
            print("connecting to cassandra")
            cursor, connection, dbtype = DataBaseConnections.connect(dbtype='cassandra', hostname='enjcosdbcasrpt01adev',
                                                                     username='sdspark', password='sdsp1rk',
                                                                     dbname='rpt_configurations', port=9042)

            sql_query = f"select * from rpt_configurations .file_streaming_tracker where file_id={int(file_id)};"
            query_result = cursor.execute(sql_query)
            connection.shutdown()

            file_streaming_tbl = pd.DataFrame(query_result)
            print("file stream table", file_streaming_tbl)
            file_name = file_streaming_tbl.loc[file_streaming_tbl['validation_status'] == 'Ingested', 'file_name'].iloc[0]
            file_name = file_name.strip()

            print("file name ", file_name)
            print("file id", file_id)
            file_url = file_url.replace(str(file_id), file_name)
            return file_url

    @staticmethod
    def file_url_to_id(file_url):
        if '\\' in file_url:
            urls = file_url.split('\\')
            print("url last", urls[-1])
            file_id = urls[-1]
            return file_id
        elif '/' in file_url:
            urls = file_url.split('/')
            file_id = urls[-1]
            return file_id

