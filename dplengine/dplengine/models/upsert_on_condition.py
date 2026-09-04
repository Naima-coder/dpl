# filename: upsert_on_condition.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: performing upsert operation on a given table.

import pandas as pd
import cx_Oracle
import logging
from common.profiling import profiling
from models import save_datasets
from models.job_properties import JobProperties
from models import process_datasets

from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

@profiling
def upsert_fun(source_df, target_df, conditions, datatypes, table_name, connection, cursor, dbtype, insert_key):
    """
    upserting the data into a table based on a condition
    :param source_df: 
    :param target_df: 
    :param conditions: conditions on which the upsert takes place
    :return: data frame
    """""
    split_types = ['>', '<']

    column_names_in_both_df = list(set(source_df.columns.values.tolist()) | set(target_df.columns.values.tolist()))

    for condition in conditions:
        print(condition)
        upsert_keys = condition['upsert_keys']

        try:
            cond = condition['cond']
            for s_type in split_types:
                # print(s_type)
                if s_type in cond:
                    column = cond.split(s_type)[0]
            col_names = []
            for col in column_names_in_both_df:
                if col in cond:
                    col_names.append(col)
            print(col_names)
            #
            if 'object' in str(source_df[col_names[0]].dtype):
                source_df[col_names[0]] = (source_df[col_names[0]].astype('str').str.strip())
            if 'object' in str(target_df[col_names[0]].dtype):
                target_df[col_names[0]] = (target_df[col_names[0]].astype('str').str.strip())
            source_cond_df = source_df.query(cond)
            target_cond_df = target_df.query(cond)
            print("source df with condition applied", source_cond_df)
            print("target df with condition applied", target_cond_df)
        except Exception as e:
            print("Exception", e, "--------------------")
            source_cond_df = source_df
            target_cond_df = target_df
            print(source_cond_df)
            print(target_cond_df)
        print('------------  source and target ---------------')

        for i in condition['upsert_keys']:
            print(i, source_cond_df[i].dtype, target_cond_df[i].dtype)
            # print('upsert keys')
            try:
                #    source_cond_df = source_cond_df.reindex()
                #    target_cond_df = target_cond_df.reindex()
                #    source_df_dtype = source_cond_df[i].dtype
                #    target_cond_df[i] = target_cond_df[i].astype(source_df_dtype)
                if source_cond_df[i].dtype == 'object':
                    print('try block')
                    source_cond_df[i] = source_cond_df[i].astype('str').str.strip()
                else:
                    print('source else')
                    source_cond_df[i] = source_cond_df[i]
                if target_cond_df[i].dtype == 'object':
                    print('target if')
                    target_cond_df[i] = target_cond_df[i].astype('str').str.strip()
                else:
                    print('target else')
                    target_cond_df[i] = target_cond_df[i]

            except:
                print('except block')
                source_cond_df[i] = source_cond_df[i]
                target_cond_df[i] = target_cond_df[i]

            #    if source_cond_df[i].dtype == 'datetime64[ns]' or target_cond_df[i].dtype == 'datetime64[ns]':
            #        source_cond_df[i] = pd.to_datetime(source_cond_df[i])
            #        target_cond_df[i] = pd.to_datetime(target_cond_df[i])
            #    if source_cond_df[i].dtype == 'int64' or target_cond_df[i].dtype == 'int64':
            #        source_cond_df[i] = source_cond_df[i].astype('str').astype(int)
            #        target_cond_df[i] = target_cond_df[i].astype('str').astype(int)
            #    if source_cond_df[i].dtype == 'float64' or target_cond_df[i].dtype == 'float64':
            #        source_cond_df[i] = source_cond_df[i].astype('str').astype(float)
            #        target_cond_df[i] = target_cond_df[i].astype('str').astype(float)
            #    if source_cond_df[i].dtype == 'object' or target_cond_df[i].dtype == 'object':
            #        source_cond_df[i] = source_cond_df[i].astype('str').str.strip()
            #        target_cond_df[i] = target_cond_df[i].astype('str').str.strip()
        # except:
        #     source_cond_df[i] = source_cond_df[i]
        #     target_cond_df[i] = target_cond_df[i]

        cond = {}
        try:
            cond['on'] = [{'left_on': upsert_keys, 'right_on': upsert_keys}]
        except KeyError:
            cond['on'] = None
        try:
            cond['how'] = 'inner'
        except KeyError:
            cond['how'] = None

        if not target_cond_df.empty and not source_cond_df.empty:
            print("Both source and target df are not empty")

            common_df = process_datasets.merge_data_frames([target_cond_df, source_cond_df], cond)
            common_df = pd.merge(target_cond_df, source_cond_df, how='inner', on=upsert_keys)
            print(common_df)
            if not common_df.empty:
                print("if merged df is not empty")

                df_update = common_df.loc[:, common_df.columns.str.endswith('_y')].dropna(axis=0, how='all')
                df_update[upsert_keys] = common_df[upsert_keys].iloc[df_update.index]
                df_update.columns = df_update.columns.str.strip('_y')

                df_insert = pd.concat([source_cond_df, df_update], sort=False)
                df_insert = df_insert.drop_duplicates(keep=False)
                print('df_update and df_insert')
                # insert_key column adding in df_update
                print("insert key in upsert", insert_key)
                if insert_key is not None:
                    df_update[insert_key] = common_df[insert_key].iloc[df_update.index]

                print('df_update')
                print(df_update)
                print('df_insert')
                print(df_insert)

                # removing common columns in target and upsert keys (the only columns that will update)
                updating_columns = list(set(target_cond_df) - set(upsert_keys))

                print(target_df.columns)
                if not target_df.empty and insert_key in target_df.columns:
                    try:
                        print(insert_key, 'max_insert_key')
                        max_insert_key = int(target_df[insert_key].max()) + 1
                    except ValueError as ve:
                        print('exception in insert key')
                        if str(ve) == 'cannot convert float NaN to integer':
                            max_insert_key = 1
                        else:
                            raise Exception(ve)
                else:
                    print('else insert key')
                    max_insert_key = 1

                # inserting into db
                if not df_insert.empty:
                    # inserting add_id
                    print("insert key", insert_key)
                    if insert_key is not None:
                        df_insert = save_datasets.incremental_column_value_generation(insert_key, table_name, cursor,
                                                                                      connection, df_insert,
                                                                                      None, None, max_insert_key)
                    save_datasets.insert_into_db(df_insert.columns.to_list(), df_insert, datatypes, table_name,
                                                 connection, cursor, dbtype)

                # updating into db
                if not df_update.empty:
                    update_table(df_update, updating_columns, upsert_keys, table_name, datatypes, connection, cursor)

            else:
                if not source_cond_df.empty:
                    print("if target table is empty, inserting delta df into DB")
                    # inserting add_id
                    if insert_key is not None:
                        try:
                            query = 'SELECT MAX(' + insert_key + ') FROM ' + table_name
                            cursor.execute(query)
                            max_col_value = cursor.fetchone()
                            max_insert_key = max_col_value[0] + 1
                            print(max_insert_key)
                        except Exception as e:
                            print(e)
                            max_insert_key = 1
                        source_cond_df = save_datasets.incremental_column_value_generation(insert_key, table_name,
                                                                                           cursor, connection,
                                                                                           source_cond_df, None, None,
                                                                                           max_insert_key)
                    save_datasets.insert_into_db(source_cond_df.columns.to_list(), source_cond_df, datatypes,
                                                 table_name, connection, cursor, dbtype)

        if target_cond_df.empty and not source_cond_df.empty:
            print("if target table is empty, inserting delta df into DB")
            # inserting add_id
            if insert_key is not None:
                try:
                    query = 'SELECT MAX(' + insert_key + ') FROM ' + table_name
                    cursor.execute(query)
                    max_col_value = cursor.fetchone()
                    max_insert_key = max_col_value[0] + 1
                    print(max_insert_key)
                except Exception as e:
                    print(e)
                    max_insert_key = 1
                source_cond_df = save_datasets.incremental_column_value_generation(insert_key, table_name, cursor,
                                                                                   connection, source_cond_df, None,
                                                                                   None, max_insert_key)
            save_datasets.insert_into_db(source_cond_df.columns.to_list(), source_cond_df, datatypes, table_name,
                                         connection, cursor, dbtype)


# update table with conditional columns
@profiling
def update_table(update_df, updating_columns, conditional_columns, table_name, datatypes, connection, cursor):
    """
    updating the data into a table
    :param update_df: 
    :param updating_columns: 
    :param conditional_columns: conditions on which the upsert takes place
    :return: data frame
    """""
    # Preparing update query
    # columns_to_update = updating_columns
    columns_to_update = list(set(update_df) - set(conditional_columns))
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
    where_col_string = where_col_string[:-4]
    df_columns_order = columns_to_update + conditional_columns
    update_df = update_df[df_columns_order]

    values = save_datasets.convert_nan_to_none(update_df, datatypes, df_columns_order)

    # update_df.fillna(value=-9999, inplace=True)
    #
    # print(f"------------------updating df-----------------\n{update_df}")
    #
    # update_df = save_datasets.convert_datatype_df_to_db(datatypes=datatypes, dataframe=update_df, column_names_list=df_columns_order)
    #
    # values = [tuple(x) for x in update_df.values]
    #
    # reps = {'nan': None, '-9999': None, '-9999.0': None, '1969-12-31': None, 'Nan': None, 'NaT': None, 'nat': None,
    #         -9999: None, -9999.0: None}
    # values = [[reps.get(x, x) for x in a] for a in values]
    #
    # try:
    #     values = [[x[:-2] if str(x).endswith('.0') else x for x in l] for l in values]
    # except TypeError as te:
    #     # logging.error(te)
    #     print("error", te)
    #     values = values

    update_query = f"update {table_name} set {set_col_string} where {where_col_string}"
    print(update_query)
    print('---------------------------\nUPSERT_DF\n', update_df, '\n---------------------------\n')
    # cursor.executemany(update_query, values)

    # Added on 12092020 to insert timestamp column along with nano seconds
    logging.info("Setting input sizes to insert timestamp column along with nano seconds")
    date_columns = [col for col in update_df.columns if update_df[col].dtype == 'datetime64[ns]']
    convert_list = {}
    for column in date_columns:
        convert_list[column] = cx_Oracle.TIMESTAMP
    cursor.setinputsizes(**convert_list)
    # Ended on 12092020 to insert timestamp column along with nano seconds

    JobProperties.save_db_chunk(update_query, values, connection, cursor)
    # connection.commit()
