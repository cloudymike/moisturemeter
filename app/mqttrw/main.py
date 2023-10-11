
import sys
import os
import config
import json
import time

from concurrent.futures import TimeoutError
import paho.mqtt.client as mqtt

import redis

REDIS_SERVER=os.getenv('REDIS_SERVER', 'localhost')

datastore = redis.Redis(host=REDIS_SERVER, port=6379, decode_responses=True)

# Set default current device list
datastore.ltrim('DeviceList',-1,-2)
for device_name in config.device_list:
    datastore.lpush('DeviceList',device_name)
    print('adding device {}'.format(device_name))


################### mqtt section ###################
# Should be run in different loop / container
# Remove printstatement when finished. For now it is good debugging
def on_message(client, userdata, message):
    TEMPERATURE='? '

    topic = message.topic
    try:
        data = json.loads(message.payload)
    except:
        data = {}
    #print("message received ", data)
    print("message topic=", topic)
    #print("message qos=",message.qos)
    #print("message retain flag=",message.retain)
    #print(type(data))
    print("Data dictionary {}".format(data))

    deviceName = topic.split('/')[1]
    print('Device Name: {}'.format(deviceName))

    TEMPERATURE=str(data.get('temperature','?'))
    datastore.set('{}:TEMPERATURE'.format(deviceName), TEMPERATURE)
    print("Temperature:{}".format(TEMPERATURE))


# Main section. Should probably be broken out as main but wait until mqtt removed
# Host 0.0.0.0 makes it available on the network, may not be a safe thing
#    change to 127.0.0.1 to be truly local



broker_address=config.hostname
print("creating new instance")
client = mqtt.Client("fermctrlwebserver") #create new instance
client.on_message=on_message #attach function to callback
print("connecting to broker on {}".format(broker_address))
client.connect(broker_address) #connect to broker
client.loop_start() #start the loop

deviceList = datastore.lrange('DeviceList',0,999)
for deviceName in deviceList:
    deviceTopic = "{}/{}/{}".format(config.project,deviceName,config.device_data)
    print("Subscribing to topic",deviceTopic)
    client.subscribe(deviceTopic)

print('Staring loop')
while(1):

    time.sleep(1)