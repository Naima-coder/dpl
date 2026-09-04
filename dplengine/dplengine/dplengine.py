# filename: dplengine.py
# author: Gade Nagarjuna reddy
# date: 23-06-2020
# version: 1.0

import logging
import os
import sys
import signal
from datetime import datetime
from flask import Flask, jsonify, request, abort, Flask, redirect
from flask_cors import CORS
from flask_restful import Api

import logging

import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler


from app import dplengine_main

from models.read_props_file import get_property


import socket
IP = socket.gethostbyname(socket.gethostname())


app = Flask(__name__)
api = Api(app)
CORS(app)


@app.route('/dpl', methods=['GET'])
def dpl_call():
    try:
        logging.info('dpl call start')
        # sys.path.insert(1, '/app/dpl/')
        logging.info(f'present dir : {os.getcwd()}')
        #threading.Thread(target=call_async_fun, args=(request.args.get('file_name'),)).start()
        dplengine_main(request.args.get('file_name'))
        logging.info('dpl call end')
        return jsonify({'data':'dpl is running'})
    except Exception as e:
        print("e",e)
        return jsonify({"error while running file": str(e)})


def shutdown_handler(signal, frame):
    '''SIGTERM handler'''
    print('Caught SIGTERM signal.', flush=True)
    return

#Register SIGTERM Handler
signal.signal(signal.SIGTERM, shutdown_handler)

log_name = get_property('log_name')

# # gcloud_logging_client = google.cloud.logging.Client.from_service_account_json(service_key_path)
gcloud_logging_client = google.cloud.logging.Client()

# Create a handler for Google Cloud Logging.
gcloud_logging_handler = CloudLoggingHandler(
    gcloud_logging_client, name=log_name
)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)

logger = logging.getLogger(log_name)
logger.setLevel(logging.INFO)
logger.addHandler(gcloud_logging_handler)
logger.addHandler(stream_handler)

if __name__ == '__main__':
    hostname = get_property('hostname')
    port = int(get_property('dplengine_api_port'))
    app.run(host=hostname, port=port, debug=False, use_reloader=False)
    #app.run(host=hostname, port=port, debug=True, use_reloader=True)
