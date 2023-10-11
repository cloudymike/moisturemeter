from flask import Flask, render_template, Response, request
from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField, RadioField
from wtforms.validators import DataRequired,Optional
import sys
import os
import config
import json

from concurrent.futures import TimeoutError

import redis

from prometheus_client import Gauge, generate_latest

import prometheus_client


# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = Flask(__name__)
# Required for forms
app.config['SECRET_KEY'] = 'cEumZnHA5QvxVDNXfazEDs7e6Eg368yD'

REDIS_SERVER = os.getenv('REDIS_SERVER', 'localhost')
datastore = redis.Redis(host=REDIS_SERVER, port=6379, decode_responses=True)

datastore.set('CurrentDevice',config.device_name)

# Initialize prometheus
prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)

actual_temperature=Gauge('actual_temperature','Actual Temperature',['device_name'])

# Initialize labels
# Use devices i config to avoid raceconditions
for device_name in config.device_list:
    actual_temperature.labels(device_name=device_name)

################### Form classes ###################

# Form to set the device
class deviceForm(FlaskForm):

    deviceList = datastore.lrange('DeviceList',0,999)
    print('deviceList in deviceForm{}'.format(deviceList))
    choicesList = []
    for deviceName in deviceList:
        choicesList.append((deviceName,deviceName))
    device = RadioField('Device', choices=choicesList)
    submit = SubmitField('Select')

#################### Helper functions ###################
def getStatusValue(status,device_name):
    value=datastore.get('{}:{}'.format(device_name,status))
    if value is None:
        value = 0
    return(value)

################### routes ###################
@app.route('/')
@app.route('/index')
def index():
    """Return a friendly HTTP greeting."""
    return render_template('index.html', title='Home page',device_name=datastore.get('CurrentDevice'))

@app.route('/graph')
def graph():
    #prom_url = "http://{}:9090/graph?g0.expr=%7Bdevice_name%3D~%22{}%22%7D%20%20%20&g0.tab=0&g0.stacked=0&g0.show_exemplars=0&g0.range_input=12h".format(config.hostname, datastore.get('CurrentDevice'))
    prom_url = "http://{}:3000/d/FERMCTRLVAR/fermctrlvar?orgId=1&refresh=1m&var-device={}".format(config.hostname, datastore.get('CurrentDevice'))
    print(prom_url)

    return render_template('graph.html', title='Graph',device_name=datastore.get('CurrentDevice'), frame_url=prom_url)


@app.route('/displaytemp')
def displayTemp():
    deviceName = datastore.get('CurrentDevice')
    TEMPERATURE = getStatusValue('TEMPERATURE',device_name)
    return render_template('displaytemp.html', title='Current',
        temperature=TEMPERATURE,
        device_name=deviceName
        )


@app.route('/device', methods=['GET', 'POST'])
def setDevice():
    form = deviceForm(device=datastore.get('CurrentDevice'))
    if form.validate_on_submit():
        print('Got device {}'.format(form.device.data))

        device = str(form.device.data)
        datastore.set('CurrentDevice',  device.encode("utf-8"))

    return render_template(
        'device.html', 
        title='Device', 
        form=form,
        device_name=datastore.get('CurrentDevice')
        )


@app.route('/metrics')
def clientmetrics():
    deviceList = datastore.lrange('DeviceList',0,999)
    for device_name in deviceList:
        actual_temperature.labels(device_name=device_name).set( getStatusValue('TEMPERATURE',device_name))

    return generate_latest()


#################### Main section. ###################
# Host 0.0.0.0 makes it available on the network, may not be a safe thing
#    change to 127.0.0.1 to be truly local
# Note,this is now handled in flask command in docker-compose and runweb.sh

app.run(host='0.0.0.0', port=8081)
