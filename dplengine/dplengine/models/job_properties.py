# filename: job_properties.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: operations performed on data and on dpl functions frame based on the properties in properties.ini file


import os
import logging
import datetime
import re
import csv
from common.process_tracking import ProcessTracking
from common.profiling import profiling

from models.read_props_file import get_property
import shutil
log_name = get_property('log_name')
logging = logging.getLogger(log_name)
job_properties = ProcessTracking.capture_process('INIT')


class JobProperties:

    def __init__(self):
        self.job_properties = job_properties

    @staticmethod
    @profiling
    def logging_level(logging, log_file_name):
        """
        changes the logging level based on the property given in properties.ini
        :param logging:
        :param log_file_name:
        :return: logging configuration
        """
        log_file_format = '%(levelname)s - [%(asctime)s] - p%(process)s - {%(filename)s: %(funcName)s :%(lineno)d} -> %(message)s'
        try:

            # To Remove all handlers associated with the root logger object.
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)

            debug_level = job_properties['logging_level']
            if debug_level == 'CRITICAL':
                return logging.basicConfig(filename=log_file_name,
                                           format=log_file_format,
                                           level=logging.CRITICAL)
            elif debug_level == 'ERROR':
                return logging.basicConfig(filename=log_file_name,
                                           format=log_file_format,
                                           level=logging.ERROR)
            elif debug_level == 'WARNING':
                return logging.basicConfig(filename=log_file_name,
                                           format=log_file_format,
                                           level=logging.WARN)
            elif debug_level == 'INFO':
                return logging.basicConfig(filename=log_file_name,
                                           format=log_file_format,
                                           level=logging.INFO)
            elif debug_level == 'DEBUG':
                return logging.basicConfig(filename=log_file_name,
                                           format=log_file_format,
                                           level=logging.DEBUG)
        except Exception:
            return logging.basicConfig(filename=log_file_name,
                                       format=log_file_format,
                                       level=logging.DEBUG)

    @staticmethod
    @profiling
    def detailed_null_validation(dataframe, save_path):
        """
        detailed null validations will be saved to a csv file based on flag in properties.ini
        :param dataframe:
        :param save_path:
        :return:
        """
        try:
            detailed_null_file = job_properties['detailed_null_file ']
            if detailed_null_file == 'True':
                dataframe.to_csv(save_path, index=None)
            else:
                pass
        except KeyError:
            return None

    @staticmethod
    @profiling
    def validate_duplicate_join_keys(dataframes, join_on):
        """
        checks weather the key columns in data frames for join have duplicates
        :param dataframes:
        :param join_on:
        :return:
        """
        try:
            validate_duplicate_join_keys = job_properties["validate_duplicate_join_keys"]
            if validate_duplicate_join_keys == 'True':
                if any(df.duplicated(subset=str(join_on)).sum() > 0 for df in dataframes):
                    raise Exception("detected duplicate keys for join")
        except KeyError:
            return None

    @staticmethod
    @profiling
    def read_file_chunk(pandas, path, delimiter, header, data_format):
        """
        reading the file in chunks
        :param path: input path
        :param delimiter:
        :param header:
        :param data_format:
        :return: data frame
        """
        try:
            job_batching = job_properties['data_batching']
            read_batch_size = int(job_properties['read_batch_size'])
            if job_batching == 'True':
                if data_format in ['csv', 'flatfile']:
                    if delimiter is not None:
                        tmp_df = pandas.read_csv(path, sep=delimiter, header=header,
                                             iterator=True, chunksize=read_batch_size,
                                             encoding='unicode_escape')
                    else:
                         tmp_df = pandas.read_csv(path, header=header,
                                             iterator=True, chunksize=read_batch_size,
                                             encoding='unicode_escape')
                    dataframe = pandas.concat([tmp_df], ignore_index=True)
                elif data_format == 'excel':
                    tmp_df = pandas.read_excel(path, index_col=None, header=header)
                    dataframe = pandas.concat([tmp_df], ignore_index=True)
                return dataframe
            else:
                if data_format in ['csv', 'flatfile']:
                    if delimiter is not None:
                        dataframe = pandas.read_csv(path, sep=delimiter,
                                                header=header,
                                                encoding='unicode_escape')
                    else:
                        dataframe = pandas.read_csv(path,
                                                header=header,
                                                encoding='unicode_escape')
                elif data_format == 'excel':
                    dataframe = pandas.read_excel(path, index_col=None, header=None)
                return dataframe
        except Exception as e:
            if data_format in ['csv', 'flatfile']:
                if delimiter is not None:
                    dataframe = pandas.read_csv(path, sep=delimiter,
                                            header=header,
                                            encoding='unicode_escape')
                else:
                    dataframe = pandas.read_csv(path,
                                            header=header,
                                            encoding='unicode_escape')
            elif data_format == 'excel':
                dataframe = pandas.read_excel(path, index_col=None, header=header)
            return dataframe
  ## function added by Naima VR that convert ascii to comp3 value
    @staticmethod
    @profiling
    def to_comp3_using_strings(value: str) -> bytes:

        if int(value) < 0:
            sign = chr(0x0d + ord('0'))
            value = -value
        else:
            sign = chr(0x0c + ord('0'))
            digits = str(value) + sign

        if len(digits) % 2 != 0:
            digits = '0' + digits
        comp3 = bytearray(len(digits) // 2)
        for i in range(0, len(digits), 2):
            comp3[i // 2] = ((ord(digits[i]) - ord('0')) << 4) | (ord(digits[i + 1]) - ord('0'))
       # print("finally comp3:",comp3)
        return comp3
##Code Added by Naima VR  to select specific  columns from file and apply comp3 function on it
    @staticmethod
    @profiling
    def func_apply(pos, data):
        final = []
        for dat in data:
            result = b""
            previous = 0
            for item in pos:
               # print("item :",item)
                if item[0] == 0:
                    res = JobProperties.to_comp3_using_strings(dat[previous:item[1]])
                    result += res
                    previous = item[1]
                    if item[1]==pos[-1][1]:
                        res2=dat[previous:].encode("cp1140")
                       # print("rest of the value needs to be converted as EBCDIC if item[1]< pos[-1][1]: ",dat[previous:])
                        result+=res2

                if item[0] != 0:
                    res = dat[previous:item[0]].encode("cp1140")
                   # print("rest of the value needs to be converted as EBCDIC, if item[0] !=0: ", dat[previous:item[0]])
                    res1 =JobProperties.to_comp3_using_strings(dat[item[0]:item[1]])
                    #print(dat[item[0]:item[1]])
                    #print("res :",res)
                    previous = item[1]
                    result = result + res + res1
                    if item[1]==pos[-1][1] :
                        res2=dat[previous:].encode("cp1140")
                       # print("rest of the value needs to be converted as EBCDIC if item[1]< pos[-1][1]: ",dat[previous:])
                        result+=res2
            #print("complete line: ",result)
            final.append(result)
        return final
    @staticmethod
    @profiling
   ##TODO# new parameters headers,trigger_script,insertr_string,date_format and comp3_col are added by Naima VR
   ## TODO record_length added by Guru Arun
    def save_file_chunk(path, data_frame, delimiter, file_type,headers,insert_string,date_format,trigger_script,comp3_col,record_length):
        """
        saving the file in chunks
        :param path: input path
        :param data_frame:
        :return: data frame
        """

        # TODO:: Changes added by Nagarjuna Gade to copy file default location for reading and writing
        default_path = get_property('default_path')
        def_filename = os.path.basename(path)
        org_filepath = path
        path = os.path.join(default_path, def_filename)

        tg_file_name = os.path.basename(path)
        delimiter = delimiter.lower()
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

        try:
            job_batching = job_properties['data_batching']
            write_batch_size = int(job_properties['write_batch_size'])

            if delimiter_type in ["nodelimiter","flatfile","fixedlengthfile"]:
                if delimiter_type in ["fixedlengthfile"]:
                    columns_data = list(data_frame.columns.tolist())
                    for col in columns_data:
                        col_length = max(data_frame[col].map(str).apply(len))
                        data_frame[col] = data_frame[col].apply(lambda x: '{:>{fill}}'.format(x, fill=col_length))
                        data_frame = data_frame.astype(str)
                data_frame = data_frame.astype(str)
                data_frame['new'] = data_frame.values.sum(axis=1)
                data_frame = data_frame['new']
                delimiter_type = ','

            # TODO:: changes added by nagarjuna for replacing timestamp in output file name
            current_timestamp = datetime.datetime.now()
            current_timestamp = current_timestamp.strftime("%Y-%m-%d_%H-%M-%S-%f")

            if 'timestamp' in path.lower():
                path = path.replace('timestamp',str(current_timestamp))

            if 'date' in path.lower():
                path = path.replace('date',str(datetime.date.today()))
            
            
            if job_batching == 'True':
                 ##TODO#Quoting=csv.QUOTE_NONE added by Naima vr to avoid adding extra ' " '
                data_frame.to_csv(path, index=None, chunksize=write_batch_size, sep=delimiter_type,header=headers,quoting=csv.QUOTE_NONE)
                print("Target file is at: ",path)
            else:
                data_frame.to_csv(path, index=None, sep=delimiter_type,header=headers,quoting=csv.QUOTE_NONE)
                print("Target file is at: ",path)
            ##TODO# Change added by Naima VR for inserting static string at any given location
            if insert_string!= False:
               # print("insert_string given: ",insert_string)

                write_file=path+"_write"
                try:
                    with open(path,"r") as read_file, open(write_file,"w")as output_file:
                        data=read_file.readlines()
                        number_of_lines=len(data)
                        key_val_list=insert_string.split("|,|")
                       # key_val_list=re.split(',(?!\s)', insert_string)
                       # print("key_val_list",key_val_list)
                        keys=[]
                        values=[]
                        default_date_format=datetime.date.today().strftime('%Y%m%d')
                        for item in key_val_list:
                            val=re.split(':(?!\s)',item)
                            keys.append(val[0])
                            values.append(val[1])
                        #print("keys,values:",keys,values)
                    
                        try:
                           
                            for index in range(len(values)):              
                                if 'current_date' in values[index]:
                                    if date_format !=None: 
                                        values[index]=values[index].replace('current_date',str(datetime.datetime.now().strftime(date_format)))
                                    else:
                                        values[index]=values[index].replace('current_date',str(datetime.date.today()))
                                if 'timestamp' in values[index]:
                                  
                                    values[index]=values[index].replace('timestamp',str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")))
                                if 'previous_date' in values[index]:
                                    cur_date= datetime.date.today()
                                    if date_format!=None:
                                        pre_day=(cur_date- datetime.timedelta(days=1)).strftime(date_format)
                                        values[index]=values[index].replace('previous_date',str(pre_day))
                                    else:
                                        pre_day=(cur_date- datetime.timedelta(days=1)).strftime("%m/%d/%y")
                                        values[index]=values[index].replace('previous_date',str(pre_day))
    
                        except Exception as e:
                            print("error occured while replacing :",e)
                    
                        key_val=zip(keys,values)
                        for item in key_val:
                            try:
                                if item[0].lower() =='first':
                                    if delimiter!='fixedlengthfile':
                                        data.insert(0,item[1]+delimiter+ str(default_date_format)+delimiter+"\n")
                                    else:
                                        data.insert(0,item[1]+date_format+"\n")
                                if item[0].lower() not in ['last','last_with_count','first']:
                                    data.insert(int(item[0]),item[1]+"\n")
                                if item[0].lower()== 'last':
                                    data.insert(len(data),item[1]+"\n")
                                if item[0].lower()== 'last_with_count':
                                    if delimiter!='fixedlengthfile':
                                        data.insert(len(data),item[1]+delimiter+str(number_of_lines)+delimiter+"\n")
                                    else:
                                        data.insert(len(data),item[1]+str(number_of_lines)+"\n")
                            except Exception as e:
                                print("Error occured while adding data ",e)
                      
                        for dat in data:
                            ##TODO:: Changes added by Nagarjuna Gade for replaceing double quotes and single quotes in insert string
                            dat = str(dat).replace('@doublequote@','"')
                            dat = dat.replace('@singlequote@',"'")
                            output_file.write(str(dat))
                           
                    os.rename(write_file,path)
                except Exception as e:
                    print("error while inserting string in outputfile: ",e)
            ##Code added by Naima VR for comp3 conversion
            if comp3_col!=[]:
                #print("comp3_col",comp3_col)
                pattern = r'\((\d+,\d+)\)'
                pos = [tuple(map(int, match.split(','))) for match in re.findall(pattern, comp3_col)]
               # print(pos)
               # print(type(pos))
                write_file=path+"_write"
              #  print(path)
                try:
                    with open(path,"r") as input, open(write_file,"wb") as output_file:
                        print("inside path:",path)
                        data1= [dat.strip() for dat in input.readlines()]
                        print("data",data1)
                        if headers==True:
                            data = data1[1:]
                            head=data1[0].encode("cp1140")
                          #  print("head",head)
                            result=JobProperties.func_apply(pos=pos,data=data)
                            result.insert(0,head)
                           # print("%%%%%%%%%%%%%%%%5",result)
                            for line in result:
                                if (record_length!=None)and (len(line) < record_length):
                                 #  print("********LENGTH**********",len(line))
                                    spaces_needed=record_length-len(line)
                                    line=line+ b" " * spaces_needed
                                output_file.write(line)
                        else:
                            result=JobProperties.func_apply(pos=pos, data=data1)
                            print("here result without headers:",result)
                            for line in result:
                                if (record_length!= None) and ( len(line) < record_length):
                                 #  print("********LENGTH**********",len(line))
                                    spaces_needed=record_length-len(line)
                                    line=line+ b" " * spaces_needed
                                output_file.write(line)
                    os.rename(write_file,path)
                except Exception as e:
                    print("Error occured while writing comp3: ",e)

            if file_type.lower() in['zebcdic','ebcdic']:
                print("in ebcdic conversion")
                write_file = path + '_ebc'
                with open(path, 'r') as input_file, open(write_file, 'wb') as output_file:
                    os.rename(path, path + '_asc')
                    line = input_file.read()
                    output_file.write(line.encode('cp1140'))
                    os.remove(path+'_asc')
                os.rename(write_file, path)

              ##TODO# Added by Naima VR for ziping file/ebcdic files

            if file_type.lower() in ['zebcdic', 'zip']:
                os.rename(path, path + '_unziped')
                cmd = 'zip ' + path + ' ' + path + '_unziped'
                os.popen(cmd).read()
                os.remove(path + '_unziped')

                if os.path.exists(path+'.zip'):
                    os.rename(path+'.zip',path)


            # TODO:: Changes added by Nagarjuna Gade to copy file default location for reading and writing
            shutil.copy(path, org_filepath)
            os.remove(path)

            ##Todo#Added by Naima VR for trigger script
            if trigger_script != None:
                if not os.path.dirname(trigger_script):
                    try:
                        root=os.path.split(path)[0]
                        trigger_script= os.path.join(root,trigger_script)
                        print("Trigger file path : ",trigger_script)

                        JobProperties.trigger_scheduler(trigger_script)
                    except Exception as e:
                        print("while looking for trigger_file path the following error occured: ",e)
                else:
                    print("Trigger file path: ",trigger_script)
                    JobProperties.trigger_scheduler(trigger_script) 
            return None
        except Exception:
            if '.xlsx' in tg_file_name:
                print("------ save excel file in else ----")
                data_frame.to_excel(path, index=False)
            else:
                data_frame.to_csv(path, index=None, sep=delimiter_type)
            return None

    @staticmethod
    @profiling
    def read_db_chunk(pandas, query, connection, query_result):
        """
        reading the table in chunks
        :param query: input path
        :param connection:
        :param query_result:
        :return: data frame
        """
        job_batching = None
        try:
            job_batching = job_properties['data_batching']
            read_batch_size = int(job_properties['read_batch_size'])
            if job_batching == 'True':
                # Create empty list
                dfl = []

                # Create empty dataframe
                dataframe = pandas.DataFrame()

                # Start Chunking
                print("start Chunking")
                logging.info(f"Reading dataframe in chunks with chunksize: {read_batch_size}")
                for chunk in pandas.read_sql(query, con=connection, chunksize=read_batch_size):
                    # Start Appending Data Chunks from SQL Result set into List
                    print("Appending batch data-------")
                    dfl.append(chunk)
                # Start appending data from list to dataframe
                dataframe = pandas.concat(dfl, ignore_index=True)

                return dataframe
            else:
                dataframe = pandas.DataFrame(query_result)
                return dataframe

        except Exception as e:
            if 'bool' in str(e):
                dataframe = pandas.DataFrame(query_result)
                return dataframe

            elif job_batching == 'True':
                dataframe = pandas.DataFrame(query_result)
                return dataframe
            else:
                print('Exception: ' + str(e))
                logging.error(f"Exception occurred while reading table: {e}")
                raise Exception(e)

    @staticmethod
    @profiling
    def save_db_chunk(query, values, connection, cursor, dbtype='oracle'):
        """
        saving the data frame to table in chunks
        :param query:
        :param values:
        :param connection:
        :param cursor:
        :return: row count
        """
        # values = [tuple(val) for val in values]
        try:
            job_batching = job_properties['data_batching']
            write_batch_size = int(job_properties['write_batch_size'])
            if job_batching == 'True':
                # Inserting data as batches
                logging.info(f"Saving data into table in batches with batch_size: {write_batch_size}")
                cursor_count = 0
                for num in range(0, len(values), write_batch_size):
                    data = values[num:num + write_batch_size]
                    # cursor.executemany(query, data, batcherrors=True)
                    # Added on 09072020 to insert timestamp column along with nano seconds
                    if dbtype.lower() == 'oracle':
                      cursor.prepare(query)
                      cursor.executemany(None, data, batcherrors=True)
                    else:
                      data = [list(row.values()) for row in values]
                      cursor.executemany(query,data) 
                    cursor_count += cursor.rowcount
                # Ended on 09072020 to insert timestamp column along with nano seconds
                connection.commit()
                if len(values) == 0:
                    return 0
                else:
                    return cursor_count

            else:
                # cursor.executemany(query, values)
                # Added on 09072020 to insert timestamp column along with nano seconds
                if dbtype.lower() == 'oracle':
                      cursor.prepare(query)
                      cursor.executemany(None, values, batcherrors=True)
                else:
                      data = [list(row.values()) for row in values]
                      cursor.executemany(query,data)
                # Ended on 09072020 to insert timestamp column along with nano seconds
                connection.commit()
                if len(values) == 0:
                    return 0
                else:
                    return cursor.rowcount
        except Exception as e:
            logging.warning(f"Error: {e}\nException occurred while inserting data trying to insert again")
            # cursor.executemany(query, values)
            # Added on 09072020 to insert timestamp column along with nano seconds
            if dbtype.lower() == 'oracle':
                      cursor.prepare(query)
                      cursor.executemany(None, values, batcherrors=True)
            else:
                      data = [list(row.values()) for row in values]
                      cursor.executemany(query,data)
            # Ended on 09072020 to insert timestamp column along with nano seconds
            connection.commit()
            if len(values) == 0:
                return 0
            else:
                return cursor.rowcount

    @staticmethod
    @profiling
    def get_memory_resource_limit():
        """
        Getting memory_usage limits from properties.ini file
        If no limits were given by default it sets to 8gb
        :return: soft-limit, hard-limit values
        """
        try:
            try:
                soft_memory_limit = float(job_properties['soft_memory_limit'])
            except KeyError:
                soft_memory_limit = -1
            try:
                hard_memory_limit = float(job_properties['hard_memory_limit'])
            except KeyError:
                hard_memory_limit = -1

            if soft_memory_limit == -1 and hard_memory_limit == -1:
                soft_memory_limit = hard_memory_limit = 8

            if soft_memory_limit == -1:
                soft_memory_limit = hard_memory_limit

            if hard_memory_limit == -1:
                hard_memory_limit = soft_memory_limit

            if soft_memory_limit != -1 and hard_memory_limit != -1:
                if soft_memory_limit > hard_memory_limit:
                    raise Exception("Soft_memory_limit cannot be more than hard_memory_limit")
            logging.info(f"soft_memory: {soft_memory_limit}, hard_memory_limit: {hard_memory_limit}")
            return soft_memory_limit, hard_memory_limit
        except Exception as e:
            raise e
     ##TODO# Added by Naima VR for trigger_file functionality 
    @staticmethod
    @profiling
    def trigger_scheduler(trigger_file):
        try:
            exit_code=os.system(f"bash {trigger_file}")
            if exit_code ==0:
                print("Script excecuted successfully!")
            else:
                print("Script excecution failed!!")
        except Exception as e:
            print("The following error occured while exceuting the script: ",e)
        return None   
