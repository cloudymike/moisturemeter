# Complete project details at https://RandomNerdTutorials.com

import time
import machine
import ntptime
import json
import wlan
import tempreader
import internaltempreader
import relay
import mqtt_local
import LED
import textout
import bignumber
import savestate
import config
import esp32

VERSION=0.1

# enable watchdog with a timeout of 5min
# Keep a long timeout so you can reload software before timeout
wdt = machine.WDT(timeout=300000)

class mainloop:
    def __init__(self):
        self.rtc = machine.RTC()

        self.txt = textout.textout()
        self.txt.text('Starting....')

        try:
            ntptime.settime()
        except:
            pass

        self.unit='F'
        self.temp=0.0
        self.tempDevice = tempreader.tempreader(self.unit)
        try:
            dummy=self.tempDevice.get_temp()
        except:
            self.tempDevice = internaltempreader.internaltempreader(self.unit)
        self.profile = {'0':0}
        self.lastmessage = ""

        self.m = mqtt_local.MQTTlocal(config.device_name, config.hostname, 1883, config.device_topic, config.app_topic)

    def get_temp(self):
        self.temp = self.tempDevice.get_temp()
        return(self.temp)

    def run_time(self):
        year,month,day,hour,minute,second,dummy1,dummy2 = time.localtime(time.time())
        return((hour,minute,second))

    def run(self):

        old_second = 99
        old_min = 99
        while True:

            hour,minute,second = self.run_time()

            # Cycle over x time
            if second != old_second:
                old_second = second
                LED.LED.value(abs(LED.LED.value()-1))
                wdt.feed()

                self.get_temp()

                publish_json = {}
                publish_json["temperature"] = self.temp
                print("Publishing: {}".format(publish_json))
                self.m.publish(publish_json)
 

if __name__ == "__main__":
    wlan.do_connect(config.device_name)
    print("Connected to WIFI")
    LED.LED.value(1)
    print("Starting mainloop")
    m = mainloop()
    LED.LED.value(0)
    m.run()
