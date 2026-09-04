# filename: process_tracking.py
# author: aswini pinnamraju
# date: 23-06-2020
# version: 1.0
# description: captures the properties in the properties.ini file and based on the properties, tracks the dpl process
# and saves it into a log file.

import glob
import logging
import os
import re
import smtplib
import socket
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from common.file_name_generation import generate_file_name
from models.read_ini_file import IniFiles
from models.read_props_file import get_property
log_name = get_property('log_name')
logging = logging.getLogger(log_name)

# getting process tracking file name and file path
pt_file_name, pt_file_path = generate_file_name(get_property('process_tracking_file_path'), 'process_tracking', 'log')
ini_file_path = str(os.getcwd())


class ProcessTracking:
    def __init__(self):
        pass

    # capturing status of the job at each process
    @staticmethod
    def capture_process(status, excepetion=None, trace_back=None, subject=None):
        
        """
        :param status:
        :param excepetion:
        :param trace_back:
        :param subject:
        :return:
        """
        # fetching properties from the .ini file under INIT section
        prop_file_path = None
        if re.match(r'^INIT', status):
            properties_json = {}
            if ProcessTracking.get_prop_file_path() is not None:
                prop_file_path = str(ProcessTracking.get_prop_file_path())
            else:
                prop_file_path = str(get_property('job_properties_file_path'))
            if os.path.exists(str(prop_file_path)):
                properties = IniFiles.read(str(prop_file_path))
                try:
                    for key in properties['INIT']:
                        properties_json[key] = properties['INIT'][key]
                    return properties_json
                except Exception as error:
                    print('error', error)
                    return False
            else:
                return False

        # fetching properties from the .ini file under RUNTIME section
        elif re.match(r'^RUNTIME', status):
            properties_json = {}
            print("properties file path", os.path.join(os.getcwd(), 'properties.ini'))
            if os.path.exists(str(os.path.join(os.getcwd(), 'properties.ini'))):
                properties = IniFiles.read(str(os.path.join(os.getcwd(), 'properties.ini')))
                try:
                    for key in properties['RUNTIME']:
                        properties_json[key] = properties['RUNTIME'][key]
                except Exception:
                    return False
                return properties_json
            else:
                return False

        # saving the process tracking return codes to a file
        elif re.match(r'^\[job', status):
            ProcessTracking.track_process(str(status), excepetion, trace_back, subject)
            if ProcessTracking.get_prop_file_path() is not None:
                prop_file_path = str(ProcessTracking.get_prop_file_path())
            else:
                prop_file_path = str(get_property('job_properties_file_path'))
            if os.path.exists(str(prop_file_path)):
                properties = IniFiles.read(str(prop_file_path))
                try:
                    if properties['INIT']['process_tracking'].upper() == 'TRUE':
                        with open(str(os.path.join(pt_file_path, pt_file_name)), 'a+') as file:
                            file.write(str(status) + '\n')
                except Exception as e:
                    logging.error(str(e))
            pass
        pass

    @staticmethod
    def track_process(return_string, excepetion, trace_back, subject):
        """
        To track status
        :param return_string:
        :param excepetion:
        :param trace_back:
        :param subject:
        :return:
        """
        tracking_dict = ProcessTracking.status_string_to_dict(return_string)
        if tracking_dict["pyreturncodeval"] == 1 or tracking_dict["pyreturncodeval"] == '1':
            try:
                # print("an excepetion has occured", str(tracking_dict["Exception"]))
                ProcessTracking.send_mail(subject, 'Exception : ' + '\n' + str(excepetion) + '\n'
                                          + '\n' + 'Exception log : ' + '\n' + str(trace_back))
            except Exception as error:
                print("error n sending mail", error)
                logging.debug(f"error in sending email alerts {error}")
        else:
            pass
        pass

    @staticmethod
    def status_string_to_dict(status_string):
        """
        Converts str to dict
        :param status_string:
        :return:
        """
        my_list = status_string.split("][")

        my_dict = {}
        for i in my_list:
            i = i.replace("]", "").replace("[", "")
            dict_key = i.split(":")[0]
            dict_value = i.split(":")[1]
            my_dict[f"{dict_key}"] = dict_value
        return my_dict

    @staticmethod
    # exceptionmails
    def send_mail(subject, message):
        """
        To send exception emails
        :param subject:
        :param message:
        :return:
        """

        try:
            job_properties = ProcessTracking.get_job_props()
            try:
                non_excep_email_subj = job_properties['INIT']['non_exception_email_subj']
                non_excep_email_subj = non_excep_email_subj.replace(', ', ',') \
                    .split(",")
            except Exception as error:
                non_excep_email_subj = []
            cond_non_excep_email_subj = [True if i == subject else False for i in non_excep_email_subj]
            # Made changes on 06/10/2020
            # To raise/stop certain exception emails(like Empty_datasets) when mentioned in the properties.ini file
            if True not in cond_non_excep_email_subj:
                try:
                    emails = job_properties['INIT']['emails']
                    print("email alters will be sent to :", emails)
                except Exception as error:
                    return False

                try:
                    email_cc = job_properties['INIT']['email_cc']
                except Exception as error:
                    email_cc = None

                try:
                    email_bcc = job_properties['INIT']['email_bcc']
                except Exception as error:
                    email_bcc = None
            else:
                try:
                    emails = job_properties['INIT']['non_exception_email_recipients']
                except Exception as error:
                    try:
                        emails = job_properties['INIT']['emails']
                    except Exception as error:
                        return False

                try:
                    email_cc = job_properties['INIT']['non_exception_email_cc_recipients']
                except Exception as error:
                    email_cc = None

                try:
                    email_bcc = job_properties['INIT']['non_exception_email_bcc_recipients']
                except Exception as error:
                    email_bcc = None
            try:
                email_subj = job_properties['INIT']['email_subj']
            except Exception as error:
                email_subj = subject

            try:
                email_sender = job_properties['INIT']['email_sender']
            except Exception as error:
                email_sender = str(get_property('email_sender'))

            if email_sender == False:
                email_sender = "noreply_dpl@cswg.com"

            if emails != "False":
                # set up the SMTP server
                s = smtplib.SMTP(host=get_property("smtp_host"), port=get_property("smtp_port"))
                s.starttls()
                # For each contact, send the email:
                msg = MIMEMultipart()  # create a message
                message = message
                # Prints out the message body for our sake
                # setup the parameters of the message
                msg['From'] = email_sender
                msg['To'] = emails
                msg['Subject'] = email_subj
                msg['cc'] = email_cc
                msg['Bcc'] = email_bcc

                print("sending exception emails to", "TO :", msg['To'], "CC :", msg['cc'])

                # add in the message body
                """Made changes on 10/09/2020 to integrate with UI"""
                try:
                    msg.attach(MIMEText('Dpl host : ' + socket.gethostname() + '\n' + '\n' + 'config file : ' + str(sys.argv[1]) + '\n' + '\n' + message, 'plain'))
                except Exception as e:
                    msg.attach(MIMEText('Dpl host : ' + socket.gethostname() + '\n' + '\n' + 'Requested from UI (detailed json)'+ '\n' + '\n' + message, 'plain'))

                # send the message via the server set up earlier.

                s.send_message(msg)
                del msg
                # Terminate the SMTP session and close the connection
                s.quit()
        except Exception as e:
            print('Failed to send Mail', e)

        finally:
            pass

    @staticmethod
    def get_prop_file_path():
        """
        To get properties.ini file path based on DPL Config file
        :return:
        """
        file_path = None
        search_path = None
        try:
            current_directory = os.getcwd()
            yml_file_name = os.path.basename(sys.argv[1])
            yml_file_path = sys.argv[1]

            if len(yml_file_name) < len(yml_file_path):
                search_path = yml_file_path.strip(yml_file_name)
            elif len(yml_file_name) == len(yml_file_path):
                search_path = current_directory
            os.chdir(search_path)
            for file in glob.glob("*.ini"):
                file_name = file
                if file_name is not None:
                    file_path = os.path.join(search_path, file_name)
                break
            return file_path
        except Exception as e:
            return file_path


    @staticmethod
    def get_job_props():
        """
        To get properties in properties.ini files
        :return:
        """
        prop_file_path = ProcessTracking.get_prop_file_path()
        if prop_file_path is not None:
            properties = IniFiles.read(str(prop_file_path))
            return properties
        elif prop_file_path is None:
            properties = IniFiles.read(str(get_property('job_properties_file_path')))
            return properties
        else:
            return None

    @staticmethod
    def send_job_status_mail(status_code=None, email=None):
        """
        Sends job_status as mail to requester
        :param status_code:
        :param email:
        :return:
        """
        send_email = None
        try:
            if any(key == 'email' for key in email.keys()):
                send_email = email['email']
        except Exception as e:
            send_email = None

        message = None
        if status_code == 0:
            message = 'job successfull'
        elif status_code == 1:
            message = 'job failed'

        email_sender = str(get_property('email_sender'))
        if email_sender == False:
            email_sender = "noreply_dpl@cswg.com"

        if send_email != None:
            try:
                # set up the SMTP server
                s = smtplib.SMTP(host=get_property("smtp_host"), port=get_property("smtp_port"))
                s.starttls()
                # For each contact, send the email:
                msg = MIMEMultipart()  # create a message
                message = message
                # Prints out the message body for our sake
                # setup the parameters of the message
                msg['From'] = email_sender
                msg['To'] = send_email
                msg['Subject'] = 'job status'
                # msg['cc'] = email_cc
                # msg['Bcc'] = email_bcc

                # add in the message body
                """Made changes on 10/09/2020 to integrate with UI"""
                try:
                  msg.attach(MIMEText(
                    'Dpl host : ' + socket.gethostname() + '\n' + '\n' + 'config file : ' + str(sys.argv[1]) + '\n' + '\n' + message,
                    'plain'))
                except Exception as e:
                   msg.attach(MIMEText(
                    'Dpl host : ' + socket.gethostname() + '\n' + '\n' + 'Requested from UI (detailed json) ' + '\n' + '\n' + message,
                    'plain'))

                # send the message via the server set up earlier.
                s.send_message(msg)
                del msg

            except Exception as e:
                print('Failed to send Mail', e)

            else:
                # Terminate the SMTP session and close the connection
                s.quit()

        else:
            pass


    @staticmethod
    def get_prop_value(property_name, default_property_name):
        """
        Returns property value for given property_name
        First checks in properties.ini . If not available in properties.ini then
        checks in dplengine.properties .
        :param property_name:
        :param default_property_name:
        :return:
        """
        properties = ProcessTracking.get_job_props()
        try:
            property_value = properties['INIT'][property_name]
        except Exception as e:
            logging.warning(f"Exception occurred while get property value: {property_name}\n{e}")
            try:
                property_value = get_property(default_property_name)
            except Exception as e2:
                logging.warning(f"Exception occurred while get property value: {default_property_name}"
                                f"\n{e2}")
                property_value = None
        return property_value
