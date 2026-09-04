# filename: process_datasets.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: operations are performed on the given data frames i.e. join, filter, concat etc.

import logging
import os
import re
import sys
import traceback
from datetime import datetime
from functools import reduce

import pandas as pd
import numpy as np

from common.process_tracking import ProcessTracking
from common.profiling import profiling
from common.regex_operations import dataframe_columns_mapping
from models.job_properties import JobProperties
from models import formulas_regex
from resources.data_checking import DataCheck
from models.derive_data_dataframe_columns import DeriveDataFrameColumns

from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

df_config_file = None

try:
    df_config_file = sys.argv[1]
    file_name, file_ext = os.path.splitext(df_config_file)
    # Getting filename if file path is given
    base_file_name = os.path.basename(df_config_file)
    job_properties = ProcessTracking.capture_process('INIT')
except Exception as error:
    pass


@profiling
def merge_data_frames(data_frames, condition):
    """
    Code of data_operation type "join"
    :param data_frames:
    :param condition:
    :return:
    """
    logging.info("Joining dataframes")
    print("Performing join operations")

    try:
        print(condition)
        join_on = condition['on']
        join_type = condition['how']

        if join_on is not None:
            # Conditional join code
            logging.info("Performing conditional join")
            if type(join_on[0]) == dict:
                left_join_on = join_on[0]['left_on']
                if ',' in left_join_on and type(left_join_on) != list:
                    left_join_on = left_join_on.split(",")

                right_join_on = join_on[0]['right_on']
                if ',' in right_join_on and type(right_join_on) != list:
                    right_join_on = right_join_on.split(",")

                # Making join_keys case-insensitive with dataframe
                left_join_on = dataframe_columns_mapping(data_frames[0], left_join_on)
                right_join_on = dataframe_columns_mapping(data_frames[1], right_join_on)

                print("left_join_on :", left_join_on)
                logging.info(f"performing conditional join: left join on {left_join_on}")
                print("right_join_on :", right_join_on)
                logging.info(f"performing conditional join: right join on {right_join_on}")

                # Converting datatypes to user given datatypes
                if any('left_dtype' in key for key in join_on):
                    try:
                        left_dtype = join_on[0]['left_dtype']
                        for join_key in range(len(left_join_on)):
                            data_frames[0] = convert_datatype(data_frames[0], data_type=left_dtype[join_key],
                                                              column_name=left_join_on[join_key])
                    except Exception as error:
                        print("data type conversion error", error)
                        logging.debug(f"conditional join: left data type error - {error}")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'conditional join'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{join_type}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                                        trace_back=traceback.format_exc(), subject='Exception-critical')

                if any('right_dtype' in key for key in join_on):
                    right_dtype = join_on[0]['right_dtype']
                    try:
                        for join_key in range(len(right_join_on)):
                            data_frames[1] = convert_datatype(data_frames[1], data_type=right_dtype[join_key],
                                                              column_name=right_join_on[join_key])
                    except Exception as error:
                        print("data type conversion error", error)
                        logging.debug(f"conditional join: right data type error - {error}")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'conditional join'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{join_type}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                                        trace_back=traceback.format_exc(), subject='Exception-critical')

                # Joining dataframes based on condition
                # Added on 11/13/2020 to include left dataframe records if provided
                try:
                    join_cond = condition['on'][0]['cond']
                    join_cond_check = True
                except KeyError:
                    join_cond_check = None
                # Ended on 11/13/2020 to include left dataframe records if provided

                if join_cond_check is not None:
                # if any('cond' in key for key in join_on[0]):
                    join_cond = condition['on'][0]['cond']
                    df1 = data_frames[0]
                    df2 = data_frames[1]
                    try:
                        DataCheck.validate_dtypes(data_frames, join_cond, 'conditional_join')
                    except Exception as error:
                        logging.debug(f"data types validation in conditional join error: {error}")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'conditional join'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{join_cond}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                                        trace_back=traceback.format_exc(), subject='Exception-info')
                    # Adding group_id for groups
                    df2['grp_id'] = df2.groupby(right_join_on).ngroup()

                    # Getting duplicated group_ids leaving first record
                    df2_duplicates = df2.loc[df2.duplicated(['grp_id'], keep='first')]
                    print('\n------------------------df2_duplicates-------------------------\n', df2_duplicates)

                    # Removing duplicated group_ids leaving first record
                    df2_unique = df2.drop_duplicates(['grp_id'], keep='first')
                    print('\n------------------------df2_without_duplicates-------------------------\n', df2_unique)

                    # Joining unique with left_df
                    merged_df = None
                    try:
                        merged_df = reduce(lambda left_dataframe, right_dataframe:
                                           pd.merge(left_dataframe, right_dataframe,
                                                    how='left', left_on=left_join_on,
                                                    right_on=right_join_on),
                                           [df1, df2_unique])
                    except Exception as error:
                        logging.debug(f"exception with left join in conditional {error}")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'conditional join'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{join_cond}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                                        trace_back=traceback.format_exc(), subject='Exception-info')

                    print('\n------------------------merged_df-------------------------\n', merged_df)
                    cond_match_df = merged_df.query(join_cond)
                    print('\n------------------------cond_match_df-------------------------\n', cond_match_df)

                    # Filtering records that not satisfied cond
                    cond_mismatch_df = merged_df.loc[~(merged_df.eval(join_cond))]
                    print('\n------------------------cond_mismatch_df-------------------------\n', cond_mismatch_df)

                    print('df2_duplicates.empty', df2_duplicates.empty)
                    # print('DUPLICATES BEFORE..............\n', df2_duplicates)

                    i = 1
                    while not df2_duplicates.empty:
                        print('loop_count.....', i)
                        update_df = df2_duplicates.drop_duplicates(['grp_id'], keep='first')
                        # print('\n---------------------------update_df---------------------------\n', update_df)

                        # updated merged df
                        update_merged_df = None
                        try:
                            update_merged_df = reduce(lambda left_dataframe, right_dataframe:
                                                      pd.merge(left_dataframe, right_dataframe,
                                                               how='left', left_on=left_join_on,
                                                               right_on=right_join_on),
                                                      [df1, update_df])
                        except Exception as error:
                            logging.debug(f"exception in merge data frames {error}")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'conditional join'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                            f"[dploperation:{'none'}][pyoperation:{join_cond}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]", excepetion=error,
                                                            trace_back=traceback.format_exc(), subject='Exception-info')

                        # print('\n---------------------------update_merged_df---------------------------\n', update_merged_df)

                        # Concating with filtered_df
                        cond_match_df = pd.concat([cond_match_df, update_merged_df.query(join_cond)])

                        # print(cond_match_df.shape)
                        # print('\n------------------------cond_match_df-------------------------\n', cond_match_df)

                        df2_duplicates = df2_duplicates.loc[df2_duplicates.duplicated(['grp_id'], keep='first')]
                        # print('\n------------------------df2_duplicates-------------------------\n', df2_duplicates)
                        i += 1

                    final_df = cond_match_df
                    # final_df = final_df.drop(columns=['grp_id'])

                    # Added on 11/13/2020 to include left dataframe records if provided
                    try:
                        if join_on[0]['cond_ovr'] == 'left_only':
                            cond_mismatch_df = concat_data_frames([cond_mismatch_df, final_df])
                            cond_mismatch_df = cond_mismatch_df.drop_duplicates(subset=['grp_id'], keep=False)
                            final_df = concat_data_frames([final_df, cond_mismatch_df]).drop_duplicates()
                    except KeyError:
                        final_df = cond_match_df

                    final_df = final_df.drop(columns=['grp_id'])
                    return final_df

        print(
            "----------------------------------- Commencing Duplicate/Null Data Check----------------------------------------------------------")
        try:
            data_frames = DataCheck.joinKeyValidation(data_frames, condition['on'])
            # pass
        except Exception as error:
            if str(error) == 'Null records on key columns for join':
                logging.error(
                    "Error while Commencing Duplicate/Null Data Check in join operations: \n Error: " + str(error))
                print("---- Exception in data validation ----")
                raise Exception(error)
            else:
                logging.warning(error)
                data_frames = data_frames
        print(
            "----------------------------------- Exiting Duplicate/Null Data Check-----------------------------------------------------------")

        if join_type is None:
            join_type = 'left'
        else:
            join_type = join_type

        if join_on is None:
            # validating duplicate keys for joins
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{'none'}][pyoperation:{join_type}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}][Exception:{'none'}]")

            result_df = None
            try:
                result_df = reduce(lambda left_dataframe, right_dataframe:
                                   pd.merge(left_dataframe, right_dataframe, how=join_type), data_frames)
            except Exception as error:
                logging.debug(f"join operation when join_on is None:{error}")
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                f"[dploperation:{'none'}][pyoperation:{join_type}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]", excepetion=error,
                                                trace_back=traceback.format_exc(), subject='Exception-critical')
            return result_df
        else:
            if type(join_on) == list:
                join_on = condition['on']
            else:
                join_on = condition['on']
                join_on = join_on.split(",")
            try:
                result_df = None
                # When both left and right join keys are provided
                if type(join_on[0]) == dict:
                    print("----------------------------------------------")

                    left_join_on = join_on[0]['left_on']
                    if ',' in left_join_on and type(left_join_on) != list:
                        left_join_on = left_join_on.split(",")

                    right_join_on = join_on[0]['right_on']
                    if ',' in right_join_on and type(right_join_on) != list:
                        right_join_on = right_join_on.split(",")

                    # Making join_keys case-insensitive with dataframe
                    left_join_on = dataframe_columns_mapping(data_frames[0], left_join_on)
                    right_join_on = dataframe_columns_mapping(data_frames[1], right_join_on)

                    print("left_join_on :", left_join_on)
                    print("right_join_on :", right_join_on)

                    # Converting datatypes to user given datatypes
                    if any('left_dtype' in key for key in join_on):
                        left_dtype = join_on[0]['left_dtype']
                        for join_key in range(len(left_join_on)):
                            data_frames[0] = convert_datatype(data_frames[0], data_type=left_dtype[join_key],
                                                              column_name=left_join_on[join_key])

                    if any('right_dtype' in key for key in join_on):
                        right_dtype = join_on[0]['right_dtype']
                        for join_key in range(len(right_join_on)):
                            data_frames[1] = convert_datatype(data_frames[1], data_type=right_dtype[join_key],
                                                              column_name=right_join_on[join_key])
                    try:
                        result_df = reduce(lambda left_dataframe, right_dataframe:
                                           pd.merge(left_dataframe, right_dataframe,
                                                    how=join_type, left_on=left_join_on,
                                                    right_on=right_join_on), data_frames)
                    except Exception as error:
                        logging.debug(f"join data frames when both left and right join keys are provided {error}")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{'join when both left and right keys are provided'}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                                        trace_back=traceback.format_exc(), subject='Exception-critical')

                    return result_df
                else:
                    join_on = dataframe_columns_mapping(data_frames, join_on)
                    try:
                        result_df = reduce(lambda left_dataframe, right_dataframe:
                                           pd.merge(left_dataframe, right_dataframe,
                                                    how=join_type, on=join_on),
                                           data_frames)  # for joining multiple data_frames
                    except Exception as error:
                        print(error)
                        logging.debug(f"join error {error}")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{'join when both left and right keys are not provided'}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                                        trace_back=traceback.format_exc(), subject='Exception-critical')

                    return result_df
            except Exception as e:
                print("Error :", e, type(e))
                logging.debug(str(e))
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                f"[dploperation:{'none'}][pyoperation:{'join operations'}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]", excepetion=e,
                                                trace_back=traceback.format_exc(), subject='Exception-info')
                if type(e) == KeyError:
                    columns_names = []
                    for df in data_frames:
                        if df.empty:
                            logging.error("empty data frame in join operation")
                            raise Exception("Dataframe is empty")
                        columns_names += df.columns.values.tolist()
                    logging.error(f'No such column {e} is available \n'
                                  f'Please select the column from available list'
                                  f'{columns_names}')
                    raise Exception(f'No such column {e} is available \n'
                                    f'Please select the column from available list'
                                    f'{columns_names}')
                elif type(e) == TypeError:
                    logging.error("Error caused due to TTypeError")
                    for df in data_frames:
                        print(dict(df.dtypes))
                    raise Exception(f'{e}')

                else:
                    logging.error("Error while performing join operations: \n" + str(e))

                    raise Exception(f'{e}')
    except Exception as e:
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'join operations'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=e,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        if type(e) == KeyError:
            columns_names = []
            for df in data_frames:
                if df.empty:
                    raise Exception("Dataframe is empty")
                columns_names += df.columns.values.tolist()
            logging.error(f'No such column {e} is available \n'
                          f'Please select the column from available list'
                          f'{columns_names}')
            raise Exception(f'No such column {e} is available \n'
                            f'Please select the column from available list'
                            f'{columns_names}')

        elif type(e) == pd.errors.MergeError:
            print("No common key fields to merge")
            logging.warning("No common key fields to merge")
            return reduce(lambda left_dataframe, right_dataframe:
                          pd.merge(left_dataframe, right_dataframe,
                                   how='left'),
                          data_frames)
        elif type(e) == TypeError:
            for df in data_frames:
                print(dict(df.dtypes))
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                            f"[dploperation:{'none'}][pyoperation:{'join operations failure'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}][Exception:{e}]", excepetion=e,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            raise Exception(f'{e}')
        else:
            logging.error("Error while performing join operations: \n" + str(e))
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                            f"[dploperation:{'none'}][pyoperation:{'join operations failure'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}][Exception:{e}]", excepetion=e,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            raise Exception(f'{e}')


@profiling
def compare_data_frames(data_frames, condition):
    """
    Code of data_operation type "compare"
    :param data_frames:
    :param condition:
    :return:
    """
    # logging.debug("Comparing dataframes")
    print("Performing compare operations")
    try:

        cond = {}
        try:
            cond['on'] = condition
        except KeyError:
            cond['on'] = None
        try:
            cond['how'] = 'inner'
        except KeyError:
            cond['how'] = None

        left_checking_columns = condition[0]['left_column_keys']
        right_checking_columns = condition[0]['right_column_keys']
        logging.info(f"Left dataframe checking columns: {left_checking_columns}")
        logging.info(f"Right dataframe checking columns: {left_checking_columns}")

        left_df_keys = condition[0]['left_on'] + left_checking_columns
        right_df_keys = condition[0]['right_on'] + right_checking_columns
        logging.info(f"Left dataframe left_df_keys: {left_df_keys}")
        logging.info(f"Right dataframe right_df_keys: {right_df_keys}")

        if 'suffixes' in condition[0]:
            suffixes = condition[0]['suffixes']
        else:
            suffixes = ['_X', '_Y']
        logging.info(f"Suffixes given: {suffixes}")

        df1 = data_frames[0]  # .head(10)
        df2 = data_frames[1]  # .head(10)

        df1 = df1[left_df_keys]
        df2 = df2[right_df_keys]
        print("in df")
        print(df1)
        print(df2)

        merged_df = merge_data_frames([df1, df2], cond)
        print(merged_df)
        print('-------after join condition---------')

        # if merged_df == None:
        #    return 'merged_df is empty'
        print('after merged df')
        # getting left and right df based on suffixes
        logging.info("getting left and right df based on suffixes")
        df_left = merged_df.loc[:, merged_df.columns.str.endswith('_x')].dropna(axis=0, how='all')
        df_left.columns = df_left.columns.str.split('_x').str[0]

        remaining_left_cols = [i for i in left_checking_columns if i not in df_left.columns.values.tolist()]
        # df_left[keys+remaining_left_cols] = merged_df[(keys+remaining_left_cols)].iloc[df_left.index]
        if df_left.empty:
            df_left[condition[0]['left_on'] + remaining_left_cols] = merged_df[
                (condition[0]['left_on'] + remaining_left_cols)]
        else:
            df_left[condition[0]['left_on'] + remaining_left_cols] = \
                merged_df[(condition[0]['left_on'] + remaining_left_cols)].iloc[df_left.index]

        df_right = merged_df.loc[:, merged_df.columns.str.endswith('_y')].dropna(axis=0, how='all')
        df_right.columns = df_right.columns.str.split('_y').str[0]

        remaining_right_cols = [i for i in right_checking_columns if i not in df_right.columns.values.tolist()]
        # df_right[keys + remaining_right_cols] = merged_df[(condition[0]['left_on'] + remaining_right_cols)].iloc[df_right.index]
        if df_right.empty:
            df_right[condition[0]['right_on'] + remaining_right_cols] = merged_df[
                (condition[0]['right_on'] + remaining_right_cols)]
        else:
            print("in else", condition[0]['right_on'] + remaining_right_cols)
            df_right[condition[0]['right_on'] + remaining_right_cols] = \
                merged_df[(condition[0]['right_on'] + remaining_right_cols)].iloc[df_right.index]

        # print("df_right", df_right)

        # CHECKING AND MODIFYING DATA TYPES
        print('CHECKING AND MODIFYING DATA TYPES')
        for i in range(len(left_checking_columns)):
            print(i, df_left[left_checking_columns[i]].dtype, df_right[right_checking_columns[i]].dtype)

            try:
                if df_left[left_checking_columns[i]].dtype == 'datetime64[ns]' or df_right[
                    right_checking_columns[i]].dtype == 'datetime64[ns]':
                    df_left[left_checking_columns[i]] = pd.to_datetime(df_left[left_checking_columns[i]])
                    df_right[right_checking_columns[i]] = pd.to_datetime(df_right[right_checking_columns[i]])
                if df_left[left_checking_columns[i]].dtype == 'int64' or df_right[
                    right_checking_columns[i]].dtype == 'int64':
                    df_left[left_checking_columns[i]] = df_left[left_checking_columns[i]].astype('str').astype(int)
                    df_right[right_checking_columns[i]] = df_right[right_checking_columns[i]].astype('str').astype(int)
                if df_left[left_checking_columns[i]].dtype == 'float64' or df_right[
                    right_checking_columns[i]].dtype == 'float64':
                    df_left[left_checking_columns[i]] = df_left[left_checking_columns[i]].astype('str').astype(int)
                    df_right[right_checking_columns[i]] = df_right[right_checking_columns[i]].astype('str').astype(int)
                if df_left[left_checking_columns[i]].dtype == 'object' or df_right[
                    right_checking_columns[i]].dtype == 'object':
                    df_left[left_checking_columns[i]] = df_left[left_checking_columns[i]].astype('str').str.strip()
                    df_right[right_checking_columns[i]] = df_right[right_checking_columns[i]].astype('str').str.strip()
            except:
                df_left[left_checking_columns[i]] = df_left[left_checking_columns[i]]
                df_right[right_checking_columns[i]] = df_right[right_checking_columns[i]]



        # Adding mapping to column names
        if 'mapping_keys' in condition[0]:
            mapping_keys = condition[0]['mapping_keys']
            mapping_keys_original =[list(i.keys())[0] for i in mapping_keys]
            mapping_keys_mapping = [mapping_keys_original[i] + '_y' + '_original' for i in
                                    range(len(mapping_keys_original))]
            for i in range(len(mapping_keys_original)):
                if mapping_keys_original[i] in df_right:
                    df_right[mapping_keys_mapping[i]] = df_right[mapping_keys_original[i]]


        # Mapping column values
        if 'mapping_keys' in condition[0]:
            logging.info(f"Mapping column values: {condition[0]['mapping_keys']}")
            mapping_keys = condition[0]['mapping_keys']
            for mapping_key in mapping_keys:
                for x in mapping_key.keys():
                    for y in mapping_key[x].keys():
                        # df1.loc[df1[x] == y, x] = mapping_key[x][y]
                        # df2.loc[df2[x] == y, x] = mapping_key[x][y]
                        #if x in df_left.columns.values.tolist():
                        #    df_left.loc[df_left[x] == y, x] = mapping_key[x][y]
                        if x in df_right.columns.values.tolist():
                            df_right.loc[df_right[x] == y, x] = mapping_key[x][y]

        # print(df_left)
        # print(df_right)
        df_left_main = df_left[left_df_keys].copy()
        df_right_main = df_right[right_df_keys].copy()
        print('------ LEFT AND RIGHT DATAFRAMES AFTER MERGE ------')
        df_left['DATA_MATCH_ALL'] = 'Y'
        for i in range(len(left_checking_columns)):
            logging.info("Checking whether records have differences or not")
            # print(df_left[left_checking_columns[i]], df_right[right_checking_columns[i]])
            cnd = pd.eval('df_left[left_checking_columns[i]] == df_right[right_checking_columns[i]]')
            df_left = df_left.reindex()
            df_right = df_right.reindex()
            """
            Added on 09/11/2020 to add data_match validation 
            column for each column in comparision"""
            df_left[f'DATA_MATCH_{left_checking_columns[i]}'] = np.where(cnd, 'Y', 'N')
            match_cond = df_left.eval(f"DATA_MATCH_ALL == 'Y'")
            match_cond_check = df_left.eval(f"DATA_MATCH_{left_checking_columns[i]} == 'N'")
            df_left['DATA_MATCH_ALL'] = np.where(match_cond, np.where(match_cond_check, 'N', 'Y'), 'N')
            # df_right['DATA_MATCH'] = np.where(cnd, 'Y', 'N')
            # print("df_left....\n", df_left)
            # print("df_right....\n", df_right)
            # df_left['DATA_MATCH'] = np.where(cnd, 'Y', 'N')
            # df_right['DATA_MATCH'] = np.where(cnd, 'Y', 'N')
        """
        Added on 09/11/2020 to add data_match validation 
        column for each column in comparision"""
        final_df = merge_data_frames([df_left, df_right], cond)
        final_df = final_df.sort_index(axis=1)

        df_left_mismatch = pd.concat([df1, df_left_main])
        df_left_mismatch = df_left_mismatch.drop_duplicates(keep=False)
        df_right_mismatch = pd.concat([df2, df_right_main])
        df_right_mismatch = df_right_mismatch.drop_duplicates(keep=False)
        df_left_mismatch = df_left_mismatch[left_df_keys]
        df_right_mismatch = df_right_mismatch[right_df_keys]

        if condition[0]['record_inclusion'].lower() == 'both':
            final_df = final_df
            # df_left = df_left
            # df_right = df_right
        elif condition[0]['record_inclusion'].lower() == 'matched':
            final_df = final_df.query("DATA_MATCH_ALL == 'Y'")
            # df_left = df_left.query("DATA_MATCH == 'Y'")
            # df_right = df_right.query("DATA_MATCH == 'Y'")
        elif condition[0]['record_inclusion'].lower() == 'mismatched':
            final_df = final_df.query("DATA_MATCH_ALL == 'N'")
            # df_left = df_left.query("DATA_MATCH == 'N'")
            # df_right = df_right.query("DATA_MATCH == 'N'")
        # final_df = merge_data_frames([df_left, df_right], cond)
        # final_df = final_df.sort_index(axis=1)
        # return final_df
        return ({"final_df": final_df,
                 "final_df_count": final_df.shape[0],
                 "left_mismatch_df": df_left_mismatch,
                 "left_mismatch_df_count": df_left_mismatch.shape[0],
                 "right_mismatch_df": df_right_mismatch,
                 "right_mismatch_df_count": df_right_mismatch.shape[0]})

    except Exception as e:
        if type(e) == KeyError:
            columns_names = []
            for df in data_frames:
                if df.empty:
                    raise Exception("Dataframe is empty")
                columns_names += df.columns.values.tolist()
            exception_issue = f'No such column {e} is available \n' \
                              f'Please select the column from available list' \
                              f'{columns_names}'
            logging.error(exception_issue)
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                            f"[dploperation:{'none'}][pyoperation:{'join operations failure'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}][Exception:{e}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            raise Exception(exception_issue)
        #        elif type(e) == pd.errors.MergeError:
        #        print("No common key fields to merge")
        #        logging.warning("No common key fields to merge")
        else:
            logging.error("Error while comparing dataframes: \n" + str(e))
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{1}]"
                                            f"[dploperation:{'none'}][pyoperation:{'join operations failure'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}][Exception:{e}]", excepetion=e,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            raise Exception(f'{e}')


@profiling
def concat_data_frames(data_frames):
    """
    Code of data_operation type "union"
    :param data_frames:
    :param logging:
    :return:
    """
    logging.debug("Concating dataframes")
    print("Concating dataframes")
    resutl_df = None
    try:
        resutl_df = pd.concat(data_frames, sort=False)
    except Exception as error:
        logging.error(f"data frame concatnation error {error}")
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'data frame concatnation'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')

    return resutl_df


@profiling
def convert_datatype(data_frame, data_type, column_name):
    """
    Convert datatype of the column into given datatype
    :param data_frame:
    :param data_type:
    :param column_name:
    :return:
    """
    try:
        print("data_type", data_type, "column_name", column_name)
        logging.info(f"Converting {column_name} datatype into --> {data_type}")
        if data_type.lower() in ['varchar', 'str', 'object', 'character varying', 'char', 'obj', 'string']:
            data_type = 'str'
        elif data_type.lower() in ['int', 'numeric', 'number', 'integer']:
            data_type = 'int'
        else:
            data_type = data_type
        print("join_key", data_type, "dtype", data_type)
        if data_type == 'date':
            data_frame[column_name] = pd.to_datetime(data_frame[column_name])
        else:
            data_frame[column_name] = data_frame[column_name].astype(data_type)

        return data_frame
    except Exception as error:
        print("Error: ", error)
        logging.error("Error occured while converting datatypes.....\n\t" + str(error))
        print("Error occured while converting datatypes.....\n\t" + str(error))
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'data frame concatnation'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=error,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        raise Exception(f"Error occured while converting datatypes.....\n\t{error}")


@profiling
def commands_execute(dataframes, command, command_type, dfs_required=None):
    """
     Executing user given commands on dataframe
    :param dataframes:
    :param command:
    :param command_type:
    :param dfs_required:
    :return:
    """
    try:
        intm_dataframe = None
        if command_type in ['pandas']:
            print('command: ', command)
            while 'df.' in command:
                command = command.replace('df.', 'dataframes.')
            while 'df' in command:
                command = command.replace('df', 'dataframes')
            # print('command after replacement: ', command)
            logging.info(f"Executing {command_type}-command {command} on dataframe")

            try:
                intm_dataframe = pd.eval(command)
            except Exception as error:
                logging.error(f"pandas command error: {error}")
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                f"[dploperation:{'none'}][pyoperation:{'pandas command'}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]", excepetion=error,
                                                trace_back=traceback.format_exc(), subject='Exception-critical')
            print(type(intm_dataframe))
            if 'matplotlib' in str(type(intm_dataframe)):
                plt.show()

            return intm_dataframe

        elif command_type in ['python', 'py']:
            command_value = None
            try:
                command_value = eval(command)
            except Exception as error:
                logging.error(f"python command error: {error}")
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                f"[dploperation:{'none'}][pyoperation:{'python command'}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]", excepetion=error,
                                                trace_back=traceback.format_exc(), subject='Exception-critical')

            logging.info(f"Executing {command_type}-command {command} on dataframe")
            print(command_value)
            return command_value

        elif command_type == 'multi_line_command':

            try:
                ds_names = dataframes.keys()
                print(ds_names)

                # convert dictionary into variable = value
                globals().update(dataframes)
                print(f"""{command}""")
                command = command.strip()
                command = command.replace(';', '\n')
                print(type(command))
                print("commands after replace...........................\n", f"""{command}""")

                # executing commands
                exec(command, globals())
                # Generating key-value paris for required variables
                returning_dfs = {}
                for df in dfs_required:
                    # Getting variable values
                    returning_dfs[df] = eval(df)
                return returning_dfs
            except Exception as error:
                logging.error(f"multiline command error: {error}")
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                f"[dploperation:{'none'}][pyoperation:{'multiline command'}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]", excepetion=error,
                                                trace_back=traceback.format_exc(), subject='Exception-critical')
                raise Exception(error)
    except Exception as e:
        exception_issue = f"Error occured while executing given commands\n" \
                          f"Error: {e}\nType of error: {type(e)}"
        logging.error(exception_issue)
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'multiline command'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        raise Exception(exception_issue)


@profiling
def filter_data_frame(data_frame, filters, logging=logging):
    """
    Applying filters to the dataframe
    :param data_frame:
    :param filters:
    :param logging:
    :return:
    """

    try:
        print("Applying Filters.....")
        # filters = dataframe_columns_mapping(data_frame_columns=data_frame.columns.tolist(),
        #                                     string=filters)
        filters = dataframe_columns_mapping(data_frame, filters)
        print("filters", filters)
        # print(dict(data_frame.dtypes))
        # If filters have like condition
        logging.debug(f"Applying Filters....\n Filters: '{filters}'")

        # Filter condition when len and trim functions are used
        if any(x in filters for x in ['Len(Trim(', 'len(trim(', 'LEN(TRIM(']):
            filters = filters.replace('len(trim(', 'Len(Trim(')
            filters = filters.replace('LEN(TRIM(', 'Len(Trim(')
            column_name = filters.split('Len(Trim(', 1)[1].split('))')[0]
            value_in_filters = 'Len(Trim(' + str(column_name) + '))'
            value_to_be_replaced = '(' + str(column_name) + \
                                   '.astype("str").str.strip()).str.len()'
            filters = filters.replace(value_in_filters, value_to_be_replaced)

            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{'none'}][pyoperation:{filters}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]")

        for keyword in ['AND', 'OR', 'LIKE', 'NULL', 'NOT', 'BETWEEN', 'And', 'Or', 'Like', 'Null', 'Not', 'Between']:
            filters = filters.replace(f" {keyword} ", f" {keyword.lower()} ")

        while ' not between ' in filters:
            """
            Converting between condition to .sql format
            """
            logging.debug("Converting between condition to .sql format")
            filters = re.sub(r'[(|)|]', r'', filters)
            split = re.split(' not between | and ', filters)
            column_name = split[0]
            value1 = split[1]
            value2 = split[2]
            between_condition = column_name + ' < ' + value1 + ' or ' + column_name + ' > ' + value2
            filters = filters.replace(filters, between_condition)

        while ' between ' in filters:
            """
            Converting between condition to .sql format
            """
            logging.debug("Converting between condition to .sql format")
            # con = filters.split("between", 1)[1]
            print("--------------------- in between con' ---------------")
            print("filters after remove :", filters)
            filters = re.sub(r'[(|)|]', r'', filters)
            split = re.split(' between | and ', filters)
            column_name = split[0]
            value1 = split[1]
            value2 = split[2]
            between_condition = column_name + ' >= ' + value1 + ' and ' + column_name + ' <= ' + value2
            filters = filters.replace(filters, between_condition)

        while 'like' in filters:
            """
            Finding the value given for like condition
            """
            logging.debug("Converting like condition to '.str' format")
            like_cond = re.search(" like '(.+?)'", filters, flags=re.IGNORECASE)
            like_cond = like_cond.group(1)
            if like_cond.startswith('%') and like_cond.endswith('%'):
                filters = filters.replace(f" like '{like_cond}'",
                                          f'.str.contains("{like_cond[1:-1]}")')

            elif like_cond.startswith('%'):
                filters = filters.replace(f" like '{like_cond}'",
                                          f'.str.endswith("{like_cond[1:]}")')

            elif like_cond.endswith('%'):
                filters = filters.replace(f" like '{like_cond}'",
                                          f'.str.startswith("{like_cond[:-1]}")')

            else:
                filters = filters

        else:
            try:
                # print(filters, type(filters))
                # print(data_frame.shape)
                return data_frame.query(filters)
            except Exception as e:
                # print("error", e, type(e))
                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")
                logging.warning("Warning: " + str(e))
                if 'cannot assign without a target object' in str(e) \
                        or 'invalid syntax (<' in str(e):
                    logging.warning("Warning: " + str(e))

                    print("filters in exception", filters)
                    if '=' in filters and '!=' not in filters:
                        print("replacing ")
                        filters = filters.replace('=', ' == ')
                        filters = filters.replace(' = ', ' == ')
                        print(filters, type(filters))
                        return data_frame.query(filters)

                    elif '  CURRENT_DATE' in filters:
                        split_list = filters.split("'")
                        column_name = split_list[0].strip(" ")
                        current_date = datetime.date(datetime.now())
                        print("column name for filtering", column_name)
                        print("date for filtering", data_frame[str(column_name)])
                        try:
                            data_frame[str(column_name)] = data_frame[str(column_name)].astype({column_name: str})
                            data_frame[str(column_name)] = data_frame[str(column_name)].str.strip()
                            data_frame[str(column_name)] = pd.to_datetime(data_frame[str(column_name)])
                        except Exception as error:
                            print("error in date filter", error)
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                            f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]", excepetion=e,
                                                            trace_back=traceback.format_exc(),
                                                            subject='Exception-critical')
                        if split_list[1] == '<':
                            print("date filter in <")
                            data_frame = data_frame[data_frame[column_name] < str(current_date)]
                            # data_frame[str(column_name)] = data_frame[str(column_name)].str.replace(r'[-, /, ., ,]*', "")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                            f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]")
                            return data_frame
                        elif split_list[1] == '>':
                            data_frame = data_frame[data_frame[column_name] > str(current_date)]
                            # data_frame[str(column_name)] = data_frame[str(column_name)].str.replace(r'[-, /, ., ,]*', "")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                            f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]")
                            return data_frame
                        elif split_list[1] == '==':
                            data_frame = data_frame[data_frame[column_name] == str(current_date)]
                            # data_frame[str(column_name)] = data_frame[str(column_name)].str.replace(r'[-, /, ., ,]*', "")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                            f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]")
                            return data_frame
                        elif split_list[1] == '!=':
                            data_frame = data_frame[data_frame[column_name] != str(current_date)]
                            # data_frame[str(column_name)] = data_frame[str(column_name)].str.replace(r'[-, /, ., ,]*', "")
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                            f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]")
                            return data_frame
                        else:
                            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                            f"[pyprocessstep:{'none'}]"
                                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                            f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                            f"[pyobject:{'none'}]"
                                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                            f"[dpldataset:{'none'}]"
                                                            f"[timestamp:{datetime.now()}]")
                            return data_frame

                elif "name 'null' is not defined" in str(e):
                    if 'is null' in filters:
                        logging.warning("Converting 'is null' to "
                                        "'.isnull' of applying filters")
                        filters = filters.replace(" is null", ".isnull()")
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]")
                        return data_frame.query(filters)
                    elif 'is not null' in filters or 'not null' in filters:
                        logging.warning("Converting 'is not null' to "
                                        "'.notnull()' of applying filters")
                        filters = filters.replace(" is not null", ".notnull()")
                        filters = filters.replace(" not null", ".notnull()")

                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]")
                        return data_frame.query(filters)

                    else:
                        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                        f"[pyprocessstep:{'none'}]"
                                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                        f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                        f"[pyobject:{'none'}]"
                                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                        f"[dpldataset:{'none'}]"
                                                        f"[timestamp:{datetime.now()}]")
                        raise e

                else:
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                                    f"[dploperation:{'none'}][pyoperation:{filters}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{'none'}]"
                                                    f"[timestamp:{datetime.now()}]", excepetion=e,
                                                    trace_back=traceback.format_exc(), subject='Exception-critical')
                    logging.error("Error: " + str(e))
                    raise e
    except Exception as error:
        exception_issue = f"Error occurred while filterting data\n" \
                          f"Error: {error}\nType of error: {type(error)}"
        logging.error(exception_issue)
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'filters'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        raise Exception(exception_issue)


@profiling
def rename_columns(data_frame, renamed_col):
    """
    Renaming dataframe columns
    :param data_frame:
    :param renamed_col:
    :return:
    """
    renamed_cols = None
    try:
        print("Renaming columns.............")
        # Converts
        # [{'old_col_name': 'old_column_name',
        # 'new_col_name': 'new_column_name'}]
        # to {'old_column_name': 'new_column_name'}
        df_columns = data_frame.columns.values.tolist()
        if any('old_col_name' in key for key in renamed_col):
            renamed_cols = {column['old_col_name']: column['new_col_name']
                            for column in renamed_col}

            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{'none'}][pyoperation:{renamed_cols}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}][Exception:{'none'}]")
        else:
            renamed_cols = {}
            col_list = []
            renamed_col = dataframe_columns_mapping(data_frame, renamed_col)

            for col in renamed_col:
                print(col, col.split(':'))
                col_list.append(col.split(':')[0])

                if len(col.split(':')) == 2:
                    old_col_name = col.split(':')[0]
                    new_col_name = col.split(':')[1]

                    if new_col_name != '':
                        renamed_cols[old_col_name] = new_col_name
                if len(col.split(':')) == 3:
                    old_col_name = col.split(':')[0]
                    new_col_name = col.split(':')[1]
                    if old_col_name == '':
                        derived_col_name = new_col_name
                    else:
                        derived_col_name = old_col_name
                        if new_col_name != '':
                            renamed_cols[old_col_name] = new_col_name
                    if col.split(':')[2] != '':
                        print(col.split(':')[2])
                        formula = col.split(':')[2]
                        formula = formula.replace('@', ':')
                        derived_formula = dict(col_name=derived_col_name,
                                               formula_type="derivation_through_column_rename",
                                               formula=formula)
                        data_frame = derived_columns(data_frame,
                                                     derived_formula)

            result = all(elem in df_columns for elem in col_list)
            if result is False:
                column_not_in_df = list(set(col_list) - set(df_columns))
                print(f"These '{column_not_in_df}' columns does not exists. ")
                logging.error(f"These '{column_not_in_df}' columns does not exists.")
                exit(1)
        logging.debug(f"Renaming columns: {renamed_cols}")
        return data_frame.rename(columns=renamed_cols)
    except Exception as e:
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{renamed_cols}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=e,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')
        logging.error("Exception: " + str(e))


@profiling
def derived_columns(data_frames, derived_column):
    """
    Deriving new columns with given conditions
    Dataframe.eval converts given mathematical operation into
     pandas mathematical operations
    :param data_frames:
    :param derived_column:
    :return:
    """

    try:
        print("\n Appending new columns........")
        # print(derived_column)
        column = derived_column['col_name']
        column = dataframe_columns_mapping(data_frames, column)
        formulas_given = derived_column['formula']

        # column = dataframe_columns_mapping_two(data_frames.columns.tolist(), column)
        # formulas_given = dataframe_columns_mapping(data_frames, formulas_given)
        # formulas_given = dataframe_columns_mapping_two(data_frames.columns.tolist(), formulas_given)
        formula_type = derived_column['formula_type']
        # print(column)
        print('formula_type', formula_type)
        if formula_type in ['arithmetic', 'arithmetical', 'arithmatic', 'arithmatical']:
            derived_df = data_frames
            for formula, column_name in zip(derived_column['formula'], derived_column['col_name']):
                # derived_formula = f'{column} = {formulas_given}'
                # print('derived_formula', derived_formula)
                # derived_formula = dataframe_columns_mapping(data_frames, derived_formula)
                # print('derived_formula after :', derived_formula)
                derived_formula = f'{column_name} = {formula}'
                print('derived_formula', derived_formula)
                derived_formula = dataframe_columns_mapping(derived_df, derived_formula)
                print('derived_formula after :', derived_formula)

                ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                f"[pyprocessstep:{'none'}]"
                                                f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                f"[dploperation:{'none'}][pyoperation:{formula_type}]"
                                                f"[pyobject:{'none'}]"
                                                f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                f"[dpldataset:{'none'}]"
                                                f"[timestamp:{datetime.now()}]")
                derived_df = derived_df.eval(derived_formula)
                logging.debug(f"Appending new columns........ \n'{derived_formula}'")

        elif formula_type == 'api':
            column = derived_column['col_name']
            column = dataframe_columns_mapping(data_frames, column)
            formulas_given = derived_column['formula']

            # api_file_path = derived_column['api_file_path']
            api_formula = derived_column['api_formula']
            logging.debug("Appending new columns from YAML FILE")

            api_file_name = formulas_given.split(',')[0]

            api_path = derived_column['api_name']
            api_path = api_path.strip(api_file_name + '.py')

            # Appending external file path
            sys.path.insert(1, api_path)

            # Importing api file
            api = __import__(api_file_name)

            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{'none'}][pyoperation:{column}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]")
            # Calling external API function
            if column != '':
                derived_df = api.complex_formula_api(api_formula,
                                                     data_frames,
                                                     formulas_given,
                                                     column)
            else:
                for module in derived_column['module']:
                    data_frames = api.calculate_metrics(data_frames, module)
                derived_df = data_frames
            logging.debug(f"Appending new columns........ \n '{api_formula}'")

        elif formula_type == 'value':
            for formula, column_name in zip(derived_column['formula'], derived_column['col_name']):
                if formula in ['dpl_date', 'dpl_timestamp', 'dpl_time']:
                    if formula == 'dpl_timestamp':
                        current_timestamp = datetime.now()
                        formula = str(current_timestamp)
                    elif formula == 'dpl_date':
                        current_date = datetime.now().date()
                        formula = current_date
                    elif formula == 'dpl_time':
                        current_time = datetime.now().time()
                        formula = current_time
                    else:
                        formula = formula
                elif formula in data_frames.columns:
                    value = formula
                    formula = data_frames[value]
                else:
                    try:
                        formula = int(formula)
                    except Exception as e:
                        formula = formula
                print(formula_type)
                print(f'{column_name} = {formula}')
                # data_frames[column_name] = formula
                print("formula type: ", type(formula))
                if type(formula) != str:
                    data_frames[column_name] = formula
                else:
                    formula = dataframe_columns_mapping(data_frames, formula)

                    data_frames = formulas_regex.calculate_return_df(dataframe=data_frames, formula=formula,
                                                                     col_name=column_name)
                    ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                                    f"[pyprocessstep:{'none'}]"
                                                    f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                                    f"[dploperation:{'none'}][pyoperation:{formula_type}]"
                                                    f"[pyobject:{'none'}]"
                                                    f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                                    f"[dpldataset:{'none'}]"
                                                    f"[timestamp:{datetime.now()}]")
                logging.debug(f"Appending new column ........ \n '{column} = {formulas_given}' ")
                # return derived_df
            derived_df = data_frames

        elif formula_type == 'derivation_through_column_rename':

            # creating derivation object
            deriving_df = DeriveDataFrameColumns()

            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'0'}]"
                                            f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]")
            # creating dataframe after derivating column from the derivation column
            derived_df = deriving_df.dataframe_derivation(column,
                                                          formulas_given,
                                                          data_frames)
            logging.debug(f"Appending new column ........ \n '{column} = {formulas_given}' ")

        else:

            formulas = []
            true_values = []
            false_values = []
            print("formula given", formulas_given)
            """
            Commented on 08/16/2020
            Using formulas_regex.py to calculate conditional formulas
            for if/else, nestedif/else, if/nested else scenarios"""
            for formula, column_name in zip(derived_column['formula'], derived_column['col_name']):
                # print("formula for splitting", _)
                try:
                    formula.split(';')[0]
                    formula.split(';')[1]
                    try:
                        formula.split(';')[2]
                        formula = formula.replace(';', ' then (', 1).replace(';', ') else (')
                    except IndexError as ie:
                        formula = formula.replace(';', ' then (', 1)
                    formula = f'If {formula} )'
                except IndexError as ie:
                    pass
                formula = dataframe_columns_mapping(data_frames, formula)

                data_frames = formulas_regex.calculate_return_df(dataframe=data_frames, formula=formula,
                                                                 col_name=column_name)
            # for _ in formulas_given:
            #     print("formula for splitting", _)
            #     formulas.append(_.split(';')[0])
            #
            #     true_values.append(_.split(';')[1])
            #     false_values.append(_.split(';')[2])
            #
            # formulas = dataframe_columns_mapping(data_frames, formulas)
            # # formulas = dataframe_columns_mapping_two(data_frames.columns.tolist(), formulas)
            # for formulae, tvalue, fvalue in zip(formulas, true_values, false_values):
            #     print(formulae, type(formulae), tvalue, type(tvalue), fvalue, type(fvalue))
            #     if any(operator in str(tvalue) for operator in ["+", "-", "*", "/", "%"]):
            #         try:
            #             tvalue = data_frames.eval(tvalue)
            #         except Exception as error:
            #             tvalue = tvalue
            #     elif tvalue in data_frames.columns:
            #         tvalue = data_frames[tvalue]
            #     else:
            #         try:
            #             tvalue = int(tvalue)
            #         except Exception as e:
            #             if tvalue == 'None':
            #                 tvalue = None
            #             else:
            #                 tvalue = tvalue
            #
            #     if any(operator in str(fvalue) for operator in ["+", "-", "*", "/", "%"]):
            #         try:
            #             fvalue = data_frames.eval(fvalue)
            #         except Exception as error:
            #             fvalue = fvalue
            #     elif fvalue in data_frames.columns:
            #         fvalue = data_frames[fvalue]
            #     else:
            #         try:
            #             fvalue = int(fvalue)
            #         except Exception as e:
            #             fvalue = fvalue
            #     try:
            #         if tvalue != 'None':
            #             data_frames.loc[data_frames.eval(formulae), column] = tvalue
            #     except Exception as error:
            #         data_frames.loc[data_frames.eval(formulae), column] = tvalue
            #     # data_frames[column].fillna(fvalue, inplace=True)
            #     print("false value", fvalue, type(fvalue))
            #     try:
            #         if fvalue != 'None':
            #             print("in none")
            #             data_frames.loc[~(data_frames.eval(formulae)), column] = fvalue
            #     except Exception as error:
            #         data_frames.loc[~(data_frames.eval(formulae)), column] = fvalue
            #     logging.debug(
            #         f" Appending new column ........ \n '{column} = if {formulae} Then {tvalue} Else {fvalue}' ")
            # # derived_df = data_frames.eval(derived_formula), formulas_list[1]
            derived_df = data_frames

        return derived_df
    except Exception as e:
        print("error :", str(e), type(e))
        if 'UndefinedVariableError' in str(type(e)):
            print("-------------- error in UndefinedVariableError ------------")
            columns_names = []

            columns_names += data_frames.columns.values.tolist()
            exception_issue = f'No such column {e} is available \n' \
                              f'Please select the column from available list' \
                              f'{columns_names}'
            logging.error(exception_issue)
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            raise Exception(exception_issue)
        else:
            exception_issue = f"Exception occured in dervied column section...\n" \
                              f"Error: {e}\nType of error: {e}\n"
            logging.error(exception_issue)
            ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                            f"[pyprocessstep:{'none'}]"
                                            f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                            f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                            f"[pyobject:{'none'}]"
                                            f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                            f"[dpldataset:{'none'}]"
                                            f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                            trace_back=traceback.format_exc(), subject='Exception-critical')
            raise Exception(exception_issue)


@profiling
def exclude_column(dataframe, column_names):
    """
    Excludes columns from given dataframes
    :param dataframe:
    :param column_names:
    :return:
    """
    print("Excluding unnecessary columns................")
    logging.info("Excluding unnecessary columns................")
    try:
        print(column_names)
        column_names = dataframe_columns_mapping(dataframe, column_names)
        if column_names is not None:
            dataframe = dataframe.drop(columns=column_names)
        return dataframe
    except Exception as e:
        exception_issue = f"Excluding unnecessary columns from dataframe failed with following error" \
                          f"\nError: {e}\nType of error: {type(e)}"
        print(f"Exception...............\n{exception_issue}")
        logging.error(exception_issue)
        ProcessTracking.capture_process(f"[jobname:{'jobname'}][jobdate:{datetime.now()}]"
                                        f"[pyprocessstep:{'none'}]"
                                        f"[pyreturncode:{'RC'}][pyreturncodeval:{'1'}]"
                                        f"[dploperation:{'none'}][pyoperation:{'none'}]"
                                        f"[pyobject:{'none'}]"
                                        f"[pyconnection:{'none'}][dpldbtype:{'none'}]"
                                        f"[dpldataset:{'none'}]"
                                        f"[timestamp:{datetime.now()}]", excepetion=exception_issue,
                                        trace_back=traceback.format_exc(), subject='Exception-critical')


@profiling
def nullcount(data_frames, datasets, date_values, run_id, query, logging, column=None):
    """

    :param data_frames:
    :param datasets:
    :param date_values:
    :param run_id:
    :param query:
    :param logging:
    :param column:
    :return:
    """
    values_list = []
    df = data_frames

    run_time_date = date_values[0]
    day_start_date = date_values[1]
    day_end_date = date_values[2]
    week_start_date = date_values[3]
    week_end_date = date_values[4]

    if any(mod in datasets.upper() for mod in ['EMPLOYEE']):
        module = 'EMPLOYEE'

    elif any(mod in datasets.upper() for mod in ['STORE', 'ITEM', 'SALES']):
        module = 'SALES'

    else:
        module = None

    # Checking whether to find for a particular column null values
    logging.debug("Performing null check on given dataset")
    print("Performing null check on given dataset")
    if column is None:
        count_of_null = df.isnull().sum()

        total_count = df.count() + count_of_null
        null_dataframe = df[df.isnull().any(axis=1)]
        print("\ncount_of_null")
        print(count_of_null)
        if not null_dataframe.empty:
            date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            null_values_file_name = base_file_name + '_null_values_' + str(datasets) + '_' + str(date_time) + '.csv'

            validation_results_folder = 'validations'

            # Creating detail_json_files folder if doesn't exists
            if not os.path.exists(validation_results_folder):
                os.makedirs(validation_results_folder)

            validation_results_folder_path = os.path.join(validation_results_folder, null_values_file_name)
            validation_report_file_path = os.path.join(os.getcwd(), validation_results_folder_path)

            JobProperties.detailed_null_validation(null_dataframe, validation_report_file_path)

        values_list.append(
            (f'{datasets.split(".")[1].upper()}_DATA_QUALITY', f'{datasets.split(".")[1].upper()}_NULL',
             f'{datasets.split(".")[1].upper()}',
             None, f'{datasets.split(".")[1].upper()} IS NULL', int(count_of_null), f'{datasets.split(".")[1].upper()}',
             None,
             f'{datasets.split(".")[1].upper()} IS NULL',
             None, run_time_date, day_start_date, day_end_date, week_start_date, week_end_date, run_id, module))

    else:
        if type(column) != list:
            column = column.split(",")
        else:
            column = column

        for col in column:
            count_of_null = df[col].isnull().sum()
            print("\ncount_of_null")
            print(col + ": " + str(count_of_null))
            total_count = df[col].count() + count_of_null
            null_dataframe = df[df[col].isnull()]
            src_query = query.replace('where ', f'where {col} is null and ')
            if src_query[-5:] == ' and ':
                src_query = src_query[:-5]
            if not null_dataframe.empty:
                date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                null_values_file_name = base_file_name + '_null_values_' + str(datasets) + '_' + str(
                    col) + '_' + str(date_time) + '.csv'

                validation_results_folder = 'null_validation_results'

                # Creating detail_json_files folder if doesn't exists
                if not os.path.exists(validation_results_folder):
                    os.makedirs(validation_results_folder)
                validation_results_folder_path = os.path.join(validation_results_folder, null_values_file_name)
                validation_report_file_path = os.path.join(os.getcwd(), validation_results_folder_path)
                if job_properties is not False \
                        and job_properties['detailed_null_file'] == 'True':
                    null_dataframe.to_csv(validation_report_file_path, index=None)
                # null_dataframe.to_csv(validation_report_file_path, index=None)

            values_list.append(
                (f'{datasets.split(".")[1].upper()}_DATA_QUALITY', f'{col}_NULL', f'{datasets.split(".")[1].upper()}',
                 f'{col}', f'{col} IS NULL', int(count_of_null), f'{datasets.split(".")[1].upper()}', f'{col}',
                 f'{col} IS NULL',
                 None, run_time_date, day_start_date, day_end_date, week_start_date, week_end_date, run_id, module,
                 src_query))

    null_values_dataframe = pd.DataFrame(values_list,
                                         columns=['VALUE_MAP_CODE', 'DATA_QUALITY_CODE', 'SRC_TABLE_NAME',
                                                  'SRC_COLUMN_NAME', 'SRC_COLUMN_CONDITION', 'SRC_RECORD_COUNT',
                                                  'TRG_TABLE_NAME', 'TRG_COLUMN_NAME', 'TRG_COLUMN_CONDITION',
                                                  'TRG_RECORD_COUNT', 'RUN_TIME_DATE', 'DAY_START_DATE', 'DAY_END_DATE',
                                                  'WEEK_START_DATE', 'WEEK_END_DATE', 'REQUEST_ID', 'MODULE',
                                                  'SRC_QUERY'])
    print(null_values_dataframe)
    # return values_list
    for date_col in ['RUN_TIME_DATE', 'DAY_START_DATE', 'DAY_END_DATE', 'WEEK_START_DATE', 'WEEK_END_DATE']:
        null_values_dataframe[date_col] = pd.to_datetime(null_values_dataframe[date_col])
    return null_values_dataframe

##TODO: New function added by Naima vr for comp3 conversion
@profiling
def decimal_to_comp3(value):

    """ value: decimal value needs to be converted """

    
    if int(value) <0:
        sign=chr(0x0d+ord('0'))
        value=-int(value)
    else:
       sign =chr(0X0c+ ord('0'))
    digits=str(value) +sign
    if len(digits)%2!=0:
       digits="0"+digits
    comp3= bytearray(len(digits)//2)
    for i in range(0,len(digits),2):
       comp3[i//2] = (( ord(digits[i])-ord('0')) <<4) |(ord(digits[i+1])- ord('0'))
    #binary="".join(format(byte,'08b') for byte in comp3)
    #print(type(binary))
    #print(comp3)
    #return str(binary)
    result=comp3.decode('latin-1')
    return result 
##TODO #Added by Naima VR for aligning spaces in dataframe as per copybook.
@profiling
def align_copybook_to_dataframe(data_structure,dataframe):
    print("data_structure inside func: ",data_structure)
    try:
        copybook_spacing_file_df=pd.read_csv(data_structure)
        copybook_spacing_df__col__list=copybook_spacing_file_df.columns
        print('copybook_spacing_df__col__list',copybook_spacing_df__col__list)
        dataframe_col_list=dataframe.columns
        print("dataframe_col_list",dataframe_col_list)
        dataframe = dataframe.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        final_column=[col for col in copybook_spacing_df__col__list if col.upper() in dataframe_col_list]
        other_columns= list(set(dataframe_col_list)-set(final_column))
        df_col_pattern=final_column+other_columns
        print(f"{df_col_pattern},{final_column}")
        for col in final_column:
            width = copybook_spacing_file_df.loc[0, col]  # assuming the widths are stored in the first row
            dataframe[col] =dataframe[col].astype(str).str.ljust(width, fillchar=' ')
            print( "each col: ",dataframe[col] )
        dataframe=dataframe.reindex(columns=df_col_pattern)
        print("applied data structure")
        print(dataframe)
        return dataframe
    except Exception as e:
        print("An Exception occured while alligning dataframe with copybook: ", e)

