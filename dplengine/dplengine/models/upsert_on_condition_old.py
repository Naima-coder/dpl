# filename: read_ini_files.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description:

import pandas as pd

from common.profiling import profiling


@profiling
def upsert_fun(source_df, target_df, conditions):
    """
    upserting the data into a table based on a condition
    :param source_df: 
    :param target_df: 
    :param conditions: conditions on which the upsert takes place
    :return: data frame
    """""
    split_types = ['>', '<']

    column_names_in_both_df = list(set(source_df.columns.values.tolist()) | set(target_df.columns.values.tolist()))

    dataframes = []
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
            if 'object' in str(source_df[col_names[0]].dtype):
                source_df[col_names[0]] = (source_df[col_names[0]].astype('str').str.strip())
            if 'object' in str(target_df[col_names[0]].dtype):
                target_df[col_names[0]] = (target_df[col_names[0]].astype('str').str.strip())

            source_cond_df = source_df.query(cond)
            target_cond_df = target_df.query(cond)
        except Exception as e:
            source_cond_df = source_df
            target_cond_df = target_df

        for i in upsert_keys:
            print(i, source_df[i].dtype, target_df[i].dtype)
        df_a = target_cond_df.merge(source_cond_df, on=upsert_keys, how='outer',
                                    suffixes=['_a', ''])
        col_name = df_a.filter(regex='_a', axis=1).head().columns.values.tolist()
        for col in col_name:
            df_a[col[:-2]] = df_a[col[:-2]].fillna(df_a[col])
        for col in col_name:
            del df_a[col]
        dataframes.append(df_a)
    df = pd.DataFrame()
    if len(dataframes) != 1:
        if not dataframes[1].empty:
            df = pd.concat(dataframes)
            print("upsert conditional df")
            print(df)
            return df
        else:
            return dataframes[0]
    else: return dataframes[0]
