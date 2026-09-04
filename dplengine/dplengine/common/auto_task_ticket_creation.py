import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from models.read_props_file import get_property
from common.process_tracking import ProcessTracking


def get_job_alert_details(detailed_json):
    """
    Gets detailed json as input and return the job alert details in common
    :param detailed_json:
    :return: job alerts dictionary
    """

    # job alerts dictionary (from yaml file)
    job_alert_details = detailed_json['common']['job_alerts']
    create_ticket = None
    if job_alert_details == []:
        create_ticket = True
    else:
        create_ticket = job_alert_details['create_ticket']

    if not create_ticket:
        return False

    # job properties from ini files
    job_properties = ProcessTracking.get_job_props()
    try:
        job_alert_properties = job_properties['AUTOTASK']
    except Exception as error:
        print("unable to fetch job alert details from ini files", error)
        return None
    else:
        if job_alert_details is None or job_alert_details == []:
            job_alert_details = {}
            for property in job_alert_properties:
                job_alert_details[f"{property}"] = job_alert_properties[f"{property}"]
        elif job_alert_details != []:
            for property in job_alert_properties:
                if property != 'summary' or property != 'description':
                    job_alert_details[f"{property}"] = job_alert_properties[f"{property}"]

    file_names = get_file_names(detailed_json)
    return job_alert_details, file_names


def get_file_names(json_detailed):
    file_names = []
    if not json_detailed['input']['DataSources']['FileSystem']:
        file_names = False
    else:
        file_system_list = json_detailed['input']['DataSources']['FileSystem']
        if file_system_list != []:
            file_names = []
            for i in file_system_list:
                for j in i['datasets']:
                    if str(j['dataset_format']) in ['file', 'flatfile', 'csv', 'excel', 'URL']:
                        file_names.append(j['file_name'])
    return file_names


def raise_auto_task_ticket(job_alert_details, file_names=None):
    """
    :param job_alert_details:
    :param file_names:
    :return:
    """

    if type(job_alert_details) == tuple:
        file_names = job_alert_details[1]
        job_alert_details = job_alert_details[0]

    if job_alert_details is not None and job_alert_details:
        servers_list = get_property("prod_servers").split(",")
        if str(socket.gethostname()) in servers_list:
            try:
                # set up the SMTP server
                s = smtplib.SMTP(host=get_property("smtp_host"), port=get_property("smtp_port"))
                s.starttls()

                # create a message
                msg = MIMEMultipart()

                if file_names:
                    file_names = ','.join(file_names)
                    description = f"{job_alert_details['description']}" + "\n" + \
                                  "\n" + f"FILE NAME={file_names}"
                else:
                    description = f"{job_alert_details['description']}"

                message = f"%SUMMARY={job_alert_details['summary']}" + "\n" + \
                          "\n" + f"%DESCRIPTION={description}" + "\n" + \
                          "\n" + f"%CATEGORY={job_alert_details['category']}" + "\n" + \
                          "\n" + f"%SUBISSUETYPE={job_alert_details['subissuetype']}" + "\n" + \
                          "\n" + f"%TYPE={job_alert_details['type']}" + "\n" + \
                          "\n" + f"%PRIORITY={job_alert_details['priority']}" + "\n" + \
                          "\n" + f"%GROUP={job_alert_details['group']}" + "\n" + \
                          "\n" + f"%FROM_EMAIL={job_alert_details['from_email']}"

                # setup the parameters of the message
                msg['From'] = job_alert_details['from_email']
                msg['To'] = job_alert_details['to_email']
                msg['Subject'] = job_alert_details['subject']

                print("sending auto task ticket creation mail to", "TO :", msg['To'])

                # add in the message body
                msg.attach(MIMEText(message))

                # send the message via the server set up earlier.
                s.send_message(msg)
                del msg
            except Exception as e:
                print('Failed to send Mail', e)

            else:
                # Terminate the SMTP session and close the connection
                s.quit()
    elif not job_alert_details:
        print("Auto task ticket creation disabled by the user")
        pass
    else:
        print("Auto task ticket is not created due to missing properties in ini/yaml files")
        pass
