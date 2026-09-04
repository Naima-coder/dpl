#import re
#import requests
#from datetime import datetime
import logging
from models.connections import DataBaseConnections as DBConn
from models.read_datasets import ReadDataset

import numpy as np
import pandas as pd
from ast import literal_eval

#from py_expression_eval import Parser
#parser = Parser()

formula = {"orig_order_qty":"CASE WHEN sl_outs = 0 THEN orig_order_qty ELSE CASE WHEN sl_outs_1 >= sl_outs THEN ceil(orig_order_qty * (sl_outs_1 / (sl_outs + sl_outs_1))) ELSE floor(orig_order_qty * (sl_outs_1 / (sl_outs + sl_outs_1))) END END"}

def ifHandling(formula):
    print("Add logic for IF Handling")


def caseHandling(formula):
    print(formula)

    err = ""
    index = 1
    conditions = {}
    results = {}
    #nextStatementArray = {}

    startPoint = len(formula)
    formulaRead = formula.upper()
    formulaRead = formulaRead.strip()[4:len(formulaRead)]   #Strip CASE
    while startPoint > 0:

        #print(formulaRead)
        #print("Start Point - " + str(startPoint))
        nextStatementArray = {}
        if formulaRead.strip()[0:4] == "WHEN":
            # Find WHEN-THEN as start of condition
            cond = formulaRead[formulaRead.find("WHEN") + 4:formulaRead.find("THEN")]
            conditions[index] = cond.strip()

            # StartFrom THEN onwards
            formulaRead = formulaRead[formulaRead.find("THEN") + 4:len(formulaRead)]

            # Find out next statement WHEN ELSE or END
            if formulaRead.find("CASE") >= 0:
                nextStatementArray[formulaRead.find("CASE")] = "CASE"
            if formulaRead.find("WHEN") >= 0:
                nextStatementArray[formulaRead.find("WHEN")] = "WHEN"
            if formulaRead.find("ELSE") >= 0:
                nextStatementArray[formulaRead.find("ELSE")] = "ELSE"
            if formulaRead.find("END") >= 0:
                nextStatementArray[formulaRead.find("END")] = "END"

            # Check which statement came first and start from there
            nextStatement = nextStatementArray[min(nextStatementArray.keys())]
            #print("Next Statement - " + nextStatement)

            # Get Result for cond
            if nextStatement == "CASE":
                result = formulaRead[0:formulaRead.find("END")+3]
                results[index] = result.strip()
                formulaRead = formulaRead[formulaRead.find("END")+3: len(formulaRead)]
            else:
                result = formulaRead[0:formulaRead.find(nextStatement)]
                results[index] = result.strip()
                formulaRead = formulaRead[formulaRead.find(nextStatement): len(formulaRead)]

            # Set startPoint to the point after deriving cond and result

            startPoint = len(formulaRead)  # formulaRead.find(nextStatement) + len(nextStatement)
            index += 1

        elif formulaRead.strip()[0:4] == "ELSE":
            conditions[index] = "1=1"
            results[index] = formulaRead[formulaRead.find("ELSE") + 4:formulaRead.find("END")].strip()
            formulaRead = formulaRead[formulaRead.find("END"):len(formulaRead)]
            startPoint = len(formulaRead)

            # Now formula should have only END left if not then error out
            if formulaRead.strip()[0:3] == "END":
                startPoint = 0
            else:
                err = "END Not found"
            break

        elif formulaRead.strip()[0:3] == "END":
            startPoint = 0

        '''
        #If no WHEN is left
        if formulaRead.find("WHEN") < 0:

            # Check if ELse is defined
            if formulaRead.strip()[0:4] == "ELSE":
                conditions[index] = "1=1"
                results[index] = formulaRead[formulaRead.find("ELSE")+4:formulaRead.find("END")]
                formulaRead = formulaRead[formulaRead.find("END"):len(formulaRead)]
                startPoint = len(formulaRead)
        '''

    return (conditions, results)

def calculateCASE(dataframe, formula, colName):
    #Call caseHandling to get each condition and its result as an array/dictionary
    values = caseHandling(formula)
    conditions = values[0]
    results = values[1]

    #Print for testing purpose
    print("Conditions")
    print( conditions )
    print("results")
    print( results )

    finalresult = ""
    closingBracketCount = 0
    #Start loop on each condition statement and get the result
    for index in range(1, len(conditions)+1, 1):
        print( "evaluate - " + conditions[index])
        print( "result - " + results[index])
        if index != 1:
            finalresult += ","
        #Check if there is inline CASE statement then do calculate it recursively
        if results[index].strip().find("CASE") >= 0:
            print("In If Found CASE")
            finalresult += calculateCASE(dataframe, results[index], colName)
            #dataframe
            #dataframe[colName]  = np.where(dataframe.eval(conditions[index]), resultFrom, None)
        #Check if result is normal string then use it as it is instead of eval
        elif results[index].strip().find("'") >= 0:
            print("ELIF Literal ")
            finalresult += "np.where(dataframe.eval('" + conditions[index] +"')," + results[index].strip()
            closingBracketCount += 1
            dataframe[colName]  = np.where(dataframe.eval(conditions[index]), results[index].strip(), None)
        #else evaluate result as eval
        elif  results[index].strip().find("+") > 0 | results[index].strip().find("-") > 0 | results[index].strip().find("*")  > 0 | results[index].strip().find("/") > 0:
            print("ELIF Arithmetic Operator")
            # print("Eval - " + dataframe.eval('SL_OUTS == 0'))
            # print("Eval1 - " + dataframe.eval(conditions[index]))
            # print("Result - " + dataframe.eval(results[index]))
            finalresult += "np.where(dataframe.eval('" + conditions[index] + "'), dataframe.eval('" + results[index] + "')"
            closingBracketCount += 1
            dataframe[colName] = np.where(dataframe.eval(conditions[index]), dataframe.eval(results[index]), None)
        # else evaluate result as column value
        else:
            print("else")
            #print("Eval - " + dataframe.eval('SL_OUTS == 0'))
            #print("Eval1 - " + dataframe.eval(conditions[index]))
            #print("Result - " + dataframe.eval(results[index]))
            finalresult += "np.where(dataframe.eval('" + conditions[index] + "'), literal_eval(dataframe." + results[index] + ")"
            closingBracketCount += 1
            dataframe[colName] = np.where( dataframe.eval(conditions[index]), literal_eval(dataframe.results[index]), None )

        print(dataframe)
        #if ( (value in (for value in dataframe[colName].all) ) != None):
        #    break
    for index in range(0, closingBracketCount):
        finalresult += ")"

    #print(finalresult)
    #code = compile(finalresult, "<string>", "eval")
    '''
    finalresult = np.where(dataframe.eval('OUTS == WHSE_SCRTCH_QTY & WHSE_SCRTCH_QTY == 0'), 'FF',
             np.where(dataframe.eval('OUTS == WHSE_SCRTCH_QTY & WHSE_SCRTCH_QTY > 0'), 'WS',
                      np.where(dataframe.eval('(WHSE_SCRTCH_QTY == 0 & OUTS > 0) | (WHSE_SCRTCH_QTY > 0 & OUTS == 0)'),
                               'OT1', np.where(dataframe.eval('WHSE_SCRTCH_QTY > 0 & OUTS > 0'), 'OT2',
                                               np.where(dataframe.eval('OUTS < 0'), 'OT3',
                                                        np.where(dataframe.eval('WHSE_SCRTCH_QTY < 0'), 'OT4', None))))))
    '''
    print(finalresult)
    #code = compile(finalresult, "<string>", "eval")
    final_result_value = eval(finalresult)
    #dataframe[colName] =  eval(code) #finalresult  #eval(code)  #code
    dataframe[colName] = final_result_value

    return finalresult #dataframe

def slrc_metric_fn(dataframe, col_name):
    """

    :param dataframe:
    :param col_name:
    :return:
    """
    print("Calculating 'SLRC'....................")

    case_slrc = dataframe.UNAUTH_REASON_CODE.isnull()

    if_cond1 = dataframe.eval('OUTS == WHSE_SCRTCH_QTY and WHSE_SCRTCH_QTY == 0')
    if_cond1_true = 'FF'

    elif_cond1 = dataframe.eval('OUTS == WHSE_SCRTCH_QTY & WHSE_SCRTCH_QTY > 0')
    elif_cond1_true = 'WS'

    #elif_cond2 = dataframe.eval('WHSE_SCRTCH_QTY == 0 & OUTS != 0')
    elif_cond2 = dataframe.eval('(WHSE_SCRTCH_QTY == 0 & OUTS > 0) | (WHSE_SCRTCH_QTY > 0 & OUTS == 0)')
    elif_cond2_true = 'OT1'

    #elif_cond3 = dataframe.eval('WHSE_SCRTCH_QTY > 0 & OUTS != 0')
    elif_cond3 = dataframe.eval('WHSE_SCRTCH_QTY > 0 & OUTS > 0')
    elif_cond3_true = 'OT2'

    elif_cond4 = dataframe.eval('OUTS < 0')
    elif_cond4_true = 'OT3'

    elif_cond5 = dataframe.eval('WHSE_SCRTCH_QTY < 0')
    elif_cond5_true = 'OT4'

    else_cond_val = dataframe.UNAUTH_REASON_CODE

    dataframe[col_name] = np.where(case_slrc,
                                   np.where(if_cond1, if_cond1_true,
                                            np.where(elif_cond1, elif_cond1_true,
                                                     np.where(elif_cond2, elif_cond2_true,
                                                              np.where(elif_cond3, elif_cond3_true,
                                                                       np.where(elif_cond4, elif_cond4_true,
                                                                                np.where(elif_cond5, elif_cond5_true,
                                                                                         None)))))), else_cond_val)

    print(dataframe)
    return dataframe

def calculateMetrics(dataframe, formula):
    print(formula)
    for col in formula.keys():
        columnName = col
        formulaValue = formula[col]
        print("Column Name - " + columnName)
        print("formulaValue - " + formulaValue)
        #Check if fomula is defined using CASE or IF
        formulaValue = formulaValue.upper()
        start = formulaValue.strip()[0:4].strip()
        #print(start)
        if start.find("IF") == 0:
            calculatedValue = ifHandling(formulaValue)
            dataframe[columnName] = calculatedValue
        elif start.find("CASE") == 0:
            if columnName == "slrc":
                dataframeFinal = slrc_metric_fn(dataframe, columnName)
                #continue
                #dataframe[columnName] = calculatedValue
            else:
                 caseStatement = calculateCASE(dataframe, formulaValue, columnName)
                 dataframe[columnName] = caseStatement

        print(dataframeFinal) #.first(20)

    return dataframeFinal

if __name__ == '__main__':
    # CASE WHEN sl_outs = 0 THEN sl_orig_order_qty ELSE CASE WHEN sl_outs_1 >= sl_outs THEN CEIL( sl_orig_order_qty * ( sl_outs_1/ (sl_outs + sl_outs_1 ) ) ) ELSE FLOOR( sl_orig_order_qty * ( sl_outs_1/ (sl_outs + sl_outs_1 ) ) ) END END  sl_orig_order_qty
    formula = {
        "slrc": "CASE WHEN TRIM(unauth_reason_code) IS NULL THEN CASE WHEN (nvl(orig_order_qty,0) - nvl(invoice_qty, 0)) = nvl(whse_scrtch_qty, 0) AND nvl(whse_scrtch_qty, 0) = 0 THEN 'FF' WHEN (nvl(orig_order_qty, 0) - nvl(invoice_qty,           0)) = nvl(whse_scrtch_qty,            0) AND        nvl(whse_scrtch_qty,            0) > 0 THEN    'WS'   WHEN ((nvl(orig_order_qty,  0) - nvl(invoice_qty,    0)) > 0 AND nvl(whse_scrtch_qty,            0) = 0) OR        ((nvl(orig_order_qty,  0) - nvl(invoice_qty,    0)) = 0 AND nvl(whse_scrtch_qty,            0) > 0) THEN   'OT1'   WHEN (nvl(orig_order_qty, 0) - nvl(invoice_qty,  0)) > 0 AND nvl(whse_scrtch_qty,                  0) > 0 THEN   'OT2'   WHEN nvl(orig_order_qty,            0) - nvl(invoice_qty,         0) < 0 THEN   'OT3'   WHEN nvl(whse_scrtch_qty,            0) < 0 THEN   'OT4' END         ELSE unauth_reason_code   END"
       ,"slrc1": "CASE WHEN OUTS == WHSE_SCRTCH_QTY & WHSE_SCRTCH_QTY == 0 THEN 'FF' WHEN OUTS == WHSE_SCRTCH_QTY & WHSE_SCRTCH_QTY > 0 THEN 'WS' WHEN (WHSE_SCRTCH_QTY == 0 & OUTS > 0) | (WHSE_SCRTCH_QTY > 0 & OUTS == 0) THEN 'OT1' WHEN WHSE_SCRTCH_QTY > 0 & OUTS > 0 THEN 'OT2' WHEN OUTS < 0 THEN 'OT3' WHEN WHSE_SCRTCH_QTY < 0 THEN 'OT4' END "
       ,"sl_orig_order_qty": "CASE WHEN sl_outs == 0 THEN sl_orig_order_qty ELSE CASE WHEN sl_outs_1 >= sl_outs THEN ( sl_orig_order_qty * ( sl_outs_1/ (sl_outs + sl_outs_1 ) ) ) ELSE ( sl_orig_order_qty * ( sl_outs_1/ (sl_outs + sl_outs_1 ) ) ) END END"
    }  #.apply(np.ceil)  .apply(np.floor) math.ceil math.floor
    #CASE WHEN TRIM(unauth_reason_code) IS NULL THEN ELSE unauth_reason_code   END
    print("Get formula")
    print(formula)
    cursor, connection, dbtype = DBConn. \
        connect(dbtype="oracle",
                hostname="csdwddb.cswg.com",
                username="ebs_apps",
                password="ebs_apps",
                dbname="DWD_BI",
                port="1521")

           # connect(dbtype="oracle",
           #         hostname="edp3-scan.cswg.com",
           #         username="xxana",
           #         password= "xxana",
           #         dbname="CSDWTS",
           #         port="1521")

    print("Get Connection")
    print("dbType = " + dbtype)

    #"SELECT greatest(nvl(orig_order_qty,0),nvl(bill_qty,0)) sl_orig_order_qty, sd.* FROM sales_denorm sd WHERE ar_ship_date = TO_DATE('10-MAY-2020','DD-MON-RRRR') AND invoice_nbr = '177696' AND whse_item_nbr = '287629' ",
    source_dataframe = \
        ReadDataset.read_sql_data("SELECT ar_ship_date, sd.invoice_nbr, whse_item_nbr, bill_qty, unauth_reason_code, orig_order_qty, invoice_qty, whse_scrtch_qty, sl_orig_order_qty, sl_outs, sl_outs_1, outs  FROM sl_bucket_daily_denorm sd WHERE ar_ship_date = TO_DATE('10-MAY-2020','DD-MON-RRRR') AND invoice_nbr = '177696' AND whse_item_nbr = '287629' ",
                                  connection,
                                  cursor,
                                  dbtype,
                                  logging)
    print("Get Dataframe")

    '''DBConn. \
        close_connection(connection)
    '''
    #Empty Dataframe
    df = pd.DataFrame()
    print(source_dataframe) #.first(10)
    calculateMetrics(source_dataframe, formula)
