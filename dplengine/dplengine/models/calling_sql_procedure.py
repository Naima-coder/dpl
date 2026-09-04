# filename: calling_sql_procedure.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: performs an oracle procedure when called

import cx_Oracle


def or_procedures(cursor, proc_name, proc_params=None):
    """
    performs oracle procedures
    :param cursor: database cursor
    :param proc_name: procedure name
    :param proc_params: procedure parameters
    :return: decorator function
    """
    try:
        entry_date = cursor.var(str)
        if proc_params:
            cursor.callproc(str(proc_name),
                            proc_params)
        else:
            cursor.callproc(str(proc_name))
        return entry_date.getvalue()
    except cx_Oracle.Error as error:
        print(error)

