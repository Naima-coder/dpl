# filename: dataframe_modifications.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: modifying the data frame based on different conditions


class ModifyDataFrame:

    def __init__(self):
        pass

    @staticmethod
    def sync_key_columns(dataframes, columns):
        """
        synchronizing the column data types on both the data frames during the join operation
        :param dataframes:
        :param columns:
        :return: data frames
        """
        try:
            final_dfs = []
            if type(dataframes) == list and len(dataframes) == 2 and columns is not None and type(columns) == list:
                left_df = dataframes[0]
                right_df = dataframes[1]
                left_columns = []
                right_columns = []
                if not left_df.empty and not right_df.empty and type(columns) == list:
                    for col in columns:
                        if type(col) == dict:
                            if type(col["left_on"]) == list and type(col["right_on"]) == list:
                                left_columns = col["left_on"]
                                right_columns = col["right_on"]
                            elif type(col["right_on"]) == str and type(col["left_on"]) == str:
                                left_columns.append(col["left_on"])
                                right_columns.append(col["right_on"])
                            else:
                                raise Exception("invalid column format")
                        elif type(col) == str:
                            left_columns.append(col)
                            right_columns.append(col)
                        else:
                            raise Exception("invalid column format")
                if left_columns and right_columns and len(left_columns) == len(right_columns):
                    for left_col, right_col in  zip(left_columns, right_columns):
                        right_df[str(right_col)] = right_df[str(right_col)].astype(str(left_df[left_col].dtype))
                        final_dfs.append(left_df)
                        final_dfs.append(right_df)
                    return final_dfs
        except Exception as error:
            return dataframes
