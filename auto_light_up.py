from datetime import datetime
from time import sleep
import requests

while True:
    sleep(60*10)
    if datetime.now().hour + 1 > 22:
        requests.post("http://192.168.0.201/?auto_power_on=18000000", data="hello_there")
        sleep(60*60*18)

