# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
import requests
from datetime import datetime, timezone

from data_tools import *

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from flask import Flask, render_template

# [START gae_python38_datastore_store_and_fetch_times]
# [START gae_python3_datastore_store_and_fetch_times]
from google.cloud import datastore

datastore_client = datastore.Client('rwatch-backend')

# [END gae_python3_datastore_store_and_fetch_times]
# [END gae_python38_datastore_store_and_fetch_times]
app = Flask(__name__)


# Log the current runtime in datastore
def log_runtime():
    # Create a key
    key = datastore_client.key(constants.RUNTIME)

    # Create an entity
    entity = datastore.Entity(key=key)

    # Set the entity properties
    entity['runtime'] = datetime.now(timezone.utc)

    # Save the entity
    datastore_client.put(entity)

def refresh_data():
    forecast_data = get_river_data(constants.ARGW1_URL)
    store_data(forecast_data, datastore_client)
    issue_alerts(datastore_client)
    log_runtime()

    return requests.get(constants.ARGW1_URL).content

@app.route('/')
def root():

    return render_template(
        'index.html')

@app.route('/data_request')
def refresh_data_request():
    refresh_data()
    return ('', 201)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)