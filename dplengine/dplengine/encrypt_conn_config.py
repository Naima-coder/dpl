#import logging

import yaml

from common.cipher import AESCipher
from models.read_props_file import get_property
from models.read_yaml_file import read_yuml


def encrypt_config_yml():
    try:
        # getting config file path
        connector_file_path = get_property('connectors_file_path')
        #logging.info(f"Connector file for encryption: {connector_file_path}")
        print(f"Connector file for encryption: {connector_file_path}")

        # reading yaml file into a json
        yml_json = read_yuml(connector_file_path)
        #logging.info(f"Read yaml into json for file path: {connector_file_path}")

        # creating a cipher object to encrypt/decrypt
        cipher = AESCipher()
        #logging.info("Creating cipher object")

        # looping of json to encrypt password and username
        #logging.info("Looping for encrypting password and username")
        print('Encrypting passwords')
        encryption_count = 0
        for key in yml_json.keys():
            for j in yml_json[f'{key}']:
                if yml_json[f'{key}'][j] == 'database':
                    print(yml_json[f'{key}']['password'][0:2])
                    if yml_json[f'{key}']['password'][0:2] != '~~':
                        encrypted_password = cipher.encrypt(yml_json[f'{key}']['password'])
                        encrypted_password = encrypted_password[2:-1]
                        encrypted_password = '~~' + encrypted_password
                        yml_json[f'{key}']['password'] = encrypted_password
                        encryption_count += 1
                    else:
                        #logging.info("Password is not encrypted")
                        pass
        print('Encryption completed')
        print(f'Encrypted {encryption_count} passwords')
        #logging.info("encryption completed for yaml file")
        #logging.info("Replacing the old yaml with new yaml, with encrypted passwords and usernames")
        # open config file to replace encrypted passwords and usernames
        print('Opening yml file')
        yml_file = open(f'{connector_file_path}', 'w+')

        #logging.info("Converting json to yaml")
        # creating yaml from json
        yaml.dump(yml_json, yml_file)

        # closing fle
        yml_file.close()
        print('Closed yml file')
        #logging.info("Yaml file has been closed")
    except Exception as error:
        raise Exception("An exception occurred while encrypting the yaml file")


if __name__ == '__main__':
    encrypt_config_yml()
