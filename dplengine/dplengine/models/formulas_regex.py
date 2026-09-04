import re
import logging
from datetime import datetime
from dateutil.parser import parse as date_parser

import pandas as pd
import numpy as np

from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)


def parenthetic_contents(string):
    """
    Generate parenthesized contents in string as pairs (level, contents).
    :param string:
    :return: values between all the parenthesis in the given string
    """
    logging.info("Getting the values between all the parenthesis in the given string")
    stack = []
    for i, c in enumerate(string):
        if c == '(':
            stack.append(i)
        elif c == ')' and stack:
            start = stack.pop()
            yield [start + 1, i, len(stack), string[start + 1: i]]


def split_if_then_else(metric_formula):
    """
    Splits given formula into condition, true_value, false_value
    :param metric_formula:
    :return:
    """

    logging.info("Splitting given formula into condition, true_value, false_value")
    metric_formula = re.sub('if ', 'If ', metric_formula, flags=re.I)
    metric_formula = re.sub(' Then ', ' then ', metric_formula, flags=re.I)
    metric_formula = re.sub(' Else ', ' else ', metric_formula, flags=re.I)
    print(metric_formula)
    conditional = re.search("If (.+?) then (.+?)", f"{metric_formula}", re.IGNORECASE)

    if conditional:
        condition = metric_formula.split('If', 1)[1].split('then', 1)[0]
        print(f"condition............{condition}")
        conditional_values = metric_formula.split('then', 1)[1]
        print(f"conditional_values................{conditional_values}")
        try:
            values_list = list(parenthetic_contents(conditional_values.strip()))
            for value in values_list:
                print(value)
            print([i[3] for i in values_list if i[0] == 1][0])
            true_value = [i[3] for i in values_list if i[0] == 1][0]
            false_value = [i[3] for i in values_list if i[1] == len(conditional_values.strip()) - 1 and i[0] != 1]
            if false_value != []:
                false_value = false_value[0]
            else:
                false_value = None
            # false_value = conditional_values.replace(f'({true_value}) else ', '', 1).strip()[1:-1]
        except IndexError as e:
            print(e)
            try:
                true_value = conditional_values.split('else', 1)[0]
                false_value = conditional_values.split('else', 1)[1]
            except IndexError as I:
                true_value = conditional_values
                false_value = None
        print(f"\ncondition...\n{condition}\ntrue_value.....\n{true_value}\nfalse_value.....\n{false_value}")
        return condition, true_value, false_value


def get_complete_conditions_tval_fval(tval, fval, initial_then=None, initial_else=None):
    """
    Generates the nested if else conditions, true_values and false values
    :param tval:
    :param fval:
    :param initial_then:
    :param initial_else:
    :return:
    """

    logging.info("Generating the nested if else conditions, true_values and false values")
    t_count = 0
    f_count = 0
    tval_check = re.search("If (.+?) then (.+?)", f"{tval}", re.IGNORECASE)
    fval_check = re.search("If (.+?) then (.+?)", f"{fval}", re.IGNORECASE)
    print(tval_check, fval_check)

    try:

        if tval_check and fval_check:
            if initial_else is not None:
                initial_else = fval
            condition, tval, fval = split_if_then_else(tval)
            condition_values_list.append(condition.strip())
            get_complete_conditions_tval_fval(tval, fval, initial_else=initial_else)
            condition, tval, fval = split_if_then_else(initial_else)
            condition_values_list.append(condition.strip())
            get_complete_conditions_tval_fval(tval, fval)
            pass

        else:
            while t_count != 1 or f_count != 1:
                tval_check = re.search("If (.+?) then (.+?)", f"{tval}", re.IGNORECASE)
                fval_check = re.search("If (.+?) then (.+?)", f"{fval}", re.IGNORECASE)
                if tval_check and not fval_check:
                    f_count = 1
                    # list_1.append(tval)
                    if fval is not None:
                        fval = fval.strip()
                    fvalues_list.append(fval)
                    condition, tval, fval = split_if_then_else(tval)
                    condition_values_list.append(condition.strip())
                    t_count = 0

                elif fval_check and not tval_check:
                    t_count = 1
                    if tval is not None:
                        tval = tval.strip()
                    tvalues_list.append(tval)
                    condition, tval, fval = split_if_then_else(fval)
                    condition_values_list.append(condition.strip())
                    f_count = 0

                elif not tval_check and not fval_check:
                    f_count = 1
                    t_count = 1
                    if tval is not None:
                        tval = tval.strip()
                    tvalues_list.append(tval)
                    if fval is not None:
                        fval = fval.strip()
                    fvalues_list.append(fval)

                print(t_count, f_count)
        print("returning................................")
        return condition_values_list, tvalues_list, fvalues_list
    except Exception as e:
        print(e)
        logging.error(e)
        raise BaseException(e)


def generate_max_min_string(formula, key_word):
    """
    Checks whether a max/min values of any columns are to be derived
    If true returns the formula in required format
    Else returns the same formula
    :param formula:
    :param key_word: Either min/max
    :return:
    """
    if re.search(f"{key_word}(\(.+?)", f"{formula}", re.IGNORECASE):
        formula = re.sub(f'{key_word}\(', f'{key_word}(', formula, flags=re.I)
        to_check = formula.split(f'{key_word}(', 1)[1].split(')', 1)[0]
        replace_str = "'" + to_check.replace(', ', "', '") + "'"
        if any(i in replace_str for i in [';', ',']):
            replace_str = replace_str[1:-1]
            replace_str = replace_str.replace(';', ',')
            replace_str = replace_str.split(',')
            formula = formula.replace(f'{key_word}({to_check})', f'data_frame[{replace_str}].{key_word}(axis=1)')
        else:
            formula = formula.replace(f'{key_word}({to_check})', f'data_frame[{replace_str}].{key_word}(axis=0)')
    return formula


def calculate_formulas(data_frame, formula, formula_type):
    """
    Calculates the formula for both condition and values
    :param data_frame:
    :param formula:
    :param formula_type:
    :return:
    """
    alter_dtype = False
    alter_column_name = None
    dtype_before = None

    # print(formula)
    logging.info("Calculating the formula for both condition and values")
    if re.search(f"abs(.+?)", f"{formula}", re.IGNORECASE):
        formula = re.sub(f'abs\(', f'abs(', formula, flags=re.I)
        to_check = formula.split(f'abs(', 1)[1].split(')', 1)[0]
        replace_str = "'" + to_check.replace(', ', "', '") + "'"
        formula = formula.replace(f'abs({to_check})', f'data_frame[[{replace_str}]].abs()')

    if re.search(f"len(.+?)", f"{formula}", re.IGNORECASE):
        formula = re.sub(f'len\(', f'len(', formula, flags=re.I)
        column_name = formula.split(f'len(', 1)[1].split(')', 1)[0]
        print("DATATYPE: ", data_frame[column_name].dtype)
        if data_frame[column_name].dtype != object:
            alter_dtype = True
            alter_column_name = column_name
            dtype_before = data_frame[column_name].dtype
            data_frame[column_name] = data_frame[column_name].astype('str')
        formula = formula.replace(f'len({column_name})', f'{column_name}.str.len()')

    formula = generate_max_min_string(formula, 'min')
    formula = generate_max_min_string(formula, 'max')

    if formula_type == 'conditional':
        while 'is not null' in formula or 'not null' in formula:
            formula = re.sub("|".join(sorted([' is not null', ' not null'], key=len, reverse=True)), '.notnull()',
                             formula)
            # formula = formula.replace(' is not null', '.notnull()').replace(' not null', '.notnull()')
        while 'is null' in formula or ' null' in formula:
            formula = re.sub("|".join(sorted([' is null', ' null'], key=len, reverse=True)), '.isnull()', formula)
            # formula = formula.replace(' is null', '.isnull()').replace(' null', '.isnull()')
        while ' = ' in formula:
            formula = formula.replace(' = ', '==')
        formula = formula.strip()
        # print("data_frame..........................\n", data_frame)
        try:
            condition_value = data_frame.eval(formula)
        except Exception as e:
            print(e, type(e))
            print(formula)
            print(data_frame)
            logging.error(f"Exception occurred while calculating formula.....\n{e}")
            raise Exception(e)
        if alter_dtype:
           data_frame[alter_column_name] = data_frame[alter_column_name].astype(dtype_before)
        return condition_value
    if formula_type == 'values':
        print(formula, type(formula), formula)
        try:
            if any(operator in str(formula) for operator in ["+", "-", "*", "/", "%"]):
                try:
                    date_parser(str(formula), fuzzy=False)
                    value_to_be_appended = formula
                    # print(value_to_be_appended)
                except (ValueError, TypeError) as e:
                    print("error after date_parser", e, type(e))
                    value_to_be_appended = data_frame.eval(formula)
            else:
                # print("in else block of values")
                try:
                    # print("trying data_frame.eval")
                    # print(data_frame.eval(formula))
                    value_to_be_appended = data_frame.eval(formula)
                except Exception as exception:
                    logging.warning(exception)
                    try:
                        value_to_be_appended = pd.eval(formula)
                        # print("value_to_be_appended", value_to_be_appended, type(value_to_be_appended))
                    except Exception as e:
                        logging.warning(e)
                        # print(formula in data_frame.columns)
                        if formula in data_frame.columns:
                            value_to_be_appended = data_frame[formula]
                        else:
                            try:
                                value_to_be_appended = int(formula)
                            except ValueError as ve:
                                value_to_be_appended = formula
                            except TypeError as te:
                                value_to_be_appended = None
        # print(value_to_be_appended)
        except Exception as e:
            print(f'Exception while calculating the formula/value.... \n{e}')
            logging.error(f'Exception while calculating the formula/value.... \n{e}')
            raise BaseException(e)
        if alter_dtype:
           data_frame[alter_column_name] = data_frame[alter_column_name].astype(dtype_before)
        return value_to_be_appended


def generate_np_where_values(data_frame, condition_values, tvalues, fvalues):
    """
    Calculates the values of conditions, true values, false values
    :param data_frame:
    :param condition_values:
    :param tvalues:
    :param fvalues:
    :return:
    """
    # print(condition_values, tvalues, fvalues)
    # print(f"conditions.......\n\t{condition_values}\ntvalues_list............\n\t{tvalues}\n"
    #       f"fvalues_list...............\n\t{fvalues}\n")
    logging.info("Calculating the values of conditions, true values, false values")
    case_var_values = {}
    t_var_values = {}
    f_var_values = {}
    # print("cond:0", len(tvalues) == len(condition_values))
    # print("cond:1", len(tvalues) == len(condition_values) - 1)
    if len(tvalues) == len(condition_values):
        for i in range(len(condition_values)):
            globals()['case_%s' % i] = calculate_formulas(data_frame, condition_values[i], 'conditional')
            globals()['case_%s_tval' % i] = calculate_formulas(data_frame, tvalues[i], 'values')
            case_var_values[f'case_{i}'] = globals()['case_%s' % i]
            t_var_values[f'case_{i}_tval'] = globals()['case_%s_tval' % i]
        globals()['else_value'] = calculate_formulas(data_frame, fvalues[0], 'values')
        f_var_values[f'else_value'] = globals()['else_value']
    elif len(tvalues) == len(condition_values) - 1:
        globals()['first_case'] = calculate_formulas(data_frame, condition_values[0], 'conditional')
        case_var_values['first_case'] = first_case  # globals()['first_case']
        # last_count = 1
        for i in range(1, len(condition_values) - 1):
            # print("in looop")
            # print(condition_values[i], tvalues[i - 1])
            globals()['case_%s' % i] = calculate_formulas(data_frame, condition_values[i], 'conditional')
            globals()['case_%s_tval' % i] = calculate_formulas(data_frame, tvalues[i - 1], 'values')

            case_var_values[f'case_{i}'] = globals()['case_%s' % i]
            t_var_values[f'case_{i}_tval'] = globals()['case_%s_tval' % i]
            last_count = i
        if len(condition_values) - 1 == 1:
            last_count = 0
        # print(f"lastcount......{last_count}")
        globals()['case_%s' % (last_count + 1)] = calculate_formulas(data_frame, condition_values[last_count + 1],
                                                                     'conditional')
        globals()['case_%s_tval' % last_count] = calculate_formulas(data_frame, tvalues[last_count - 1], 'values')
        globals()['case_%s_tval' % (last_count + 1)] = calculate_formulas(data_frame, tvalues[last_count], 'values')

        case_var_values[f'case_{last_count + 1}'] = globals()['case_%s' % (last_count + 1)]
        t_var_values[f'case_{last_count}_tval'] = globals()['case_%s_tval' % last_count]
        t_var_values[f'case_{last_count + 1}_tval'] = globals()['case_%s_tval' % (last_count + 1)]

        # globals()['true_value'] = calculate_formulas(dataframe, tvalues[0], 'values')
        # f_var_values[f'true_value'] = globals()['true_value']
        globals()['case_%s_fval' % (last_count + 1)] = calculate_formulas(data_frame, fvalues[1], 'values')
        f_var_values[f'case_{last_count + 1}_fval'] = globals()['case_%s_fval' % (last_count + 1)]

        globals()['else_value'] = calculate_formulas(data_frame, fvalues[0], 'values')
        f_var_values[f'else_value'] = globals()['else_value']

    print(f"\ncase_var_values................\n\t{case_var_values}\n"
          f"\nt_var_values................\n\t{t_var_values}\n"
          f"\nf_var_values...............\n\t{f_var_values}\n")
    return [case_var_values, t_var_values, f_var_values]


def generate_np_string(np_var_values, condition_values_len, tvalues_len, fvalues_len):
    """
    Generates the np.where string to evaluate formula based on the input
    :param np_var_values:
    :param condition_values_len:
    :param tvalues_len:
    :param fvalues_len:
    :return:
    """
    logging.info("Generating the np.where string to evaluate formula based on the input")
    case_var_values = list(np_var_values[0].keys())
    t_var_values = list(np_var_values[1].keys())
    # print(t_var_values)
    f_var_values = list(np_var_values[2].keys())
    np_where_base_string = 'np.where(condition, true, false)'
    np_string = np_where_base_string

    if condition_values_len == tvalues_len:
        for i in range(condition_values_len):
            # print(i, condition_values_len)
            if i != condition_values_len - 1:
                np_string = np_string.replace('condition', case_var_values[i]). \
                    replace('true', f'{t_var_values[i]}').replace('false', np_where_base_string)
            # print(np_string)
            else:
                np_string = np_string.replace('condition', case_var_values[i]). \
                    replace('true', f'{t_var_values[i]}').replace('false', f'{f_var_values[0]}')

    elif tvalues_len == condition_values_len - 1:
        np_string = np_string.replace('condition', case_var_values[0]) \
            .replace('false', f'else_value').replace('true', np_where_base_string)
        for i in range(1, condition_values_len - 1):
            np_string = np_string.replace('condition', case_var_values[i]). \
                replace('true', f'{t_var_values[i - 1]}').replace('false', np_where_base_string)
            # print(np_string)
        np_string = np_string.replace('condition', case_var_values[-1]). \
            replace('true', f'{t_var_values[-1]}').replace('false', f'{f_var_values[0]}')

    print(np_string)
    return np_string


def calculate_return_df(dataframe, formula, col_name):
    """

    :param dataframe:
    :param formula:
    :param col_name:
    :return:
    """
    try:
        global condition_values_list
        global tvalues_list
        global fvalues_list

        condition_values_list = []
        tvalues_list = []
        fvalues_list = []

        conditional = re.search("If (.+?) then (.+?)", f"{formula}", re.IGNORECASE)
        if conditional:
            condition, main_tval, main_fval = split_if_then_else(formula)
            condition_values_list.append(condition.strip())
            condition_values_list, tvalues_list, fvalues_list = \
                get_complete_conditions_tval_fval(main_tval, main_fval)

            np_var_values = generate_np_where_values(dataframe, condition_values_list, tvalues_list, fvalues_list)
            np_string = generate_np_string(np_var_values, len(condition_values_list), len(tvalues_list),
                                           len(fvalues_list))
            # print(f"input_dataframe............\n{dataframe}")
            eval_string = f'\ndataframe["{col_name}"]={np_string}\n'
            logging.info(f"eval_string:\n{eval_string}")
            print(eval_string)
            # dataframe['result'] = exec(np_string)
            exec(eval_string)
        else:
            # print(f"input_dataframe............\n{dataframe}")
            formula = calculate_formulas(dataframe, formula, 'values')
            print(formula)
            dataframe[col_name] = formula
        print(f"final_df............\n{dataframe}")

        return dataframe
    except Exception as e:
        print(e)
        logging.error(f"Exception occurred while calculating the formula..........\n{e}")
        raise Exception(e)
