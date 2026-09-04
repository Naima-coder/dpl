# filename: read_files.py
# author: saranya siragam
# date: 23-06-2020
# version: 1.0
# description: reads the yaml files

import yaml

from common.profiling import profiling


@profiling
def read_yuml(filename):
    """

    Reads the yaml files
    :param filename:
    :return:
    """

    if any(item in filename.split('.') for item in ['yuml', 'yml']):
        print("Reading yaml file: ", filename)
        try:
            with open(filename, 'r') as stream:
                return yaml.safe_load(stream)
        except yaml.MarkedYAMLError as e:
            print(e)

            if 'mapping values are not allowed' in str(e):
                print(f"\n{filename} is not a valid yaml config file \n unexpected indent or missing ':' "
                      f"\n {str(e.problem_mark)}")

            elif "could not find expected ':'" in str(e):
                print(f"\n{filename} is not a valid yaml config file \n "
                      f"could not find expected ':' \n {str(e.context_mark)}")

            elif "found '-'" in str(e):
                print(f"\n{filename} is not a valid yaml config file \n missing '-' at \n {str(e.problem_mark)}")

            elif "found '<block sequence start>'" in str(e) or "'<block mapping start>'" in str(e):
                print(f"\nAlignment issue inside the {filename} \n {str(e.problem_mark)}")

            elif " cannot start any token" in str(e):
                print(f"\nDo not use '@' and '%' for indentation inside the {filename} \n {str(e.problem_mark)}")

            else:
                print(f"\n{filename} is not a valid yaml config file \n Error: {str(e)} ")
            exit(1)
    else:
        raise TypeError(f'Check file format {filename}')
