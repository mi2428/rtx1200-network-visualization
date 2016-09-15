#!/usr/bin/python3
from influxdb import InfluxDBClient
import telnetlib, re, time

ROUTER = "10.0.10.254"
PASSWORD = ""
PROMPT="RTX1200"

DB_CONTAINER = "rtx1200-influxdb"
DB_PORT = 8086
DB_USER = "admin"
DB_PASSWORD = "changeme"

MONITORING_INTERVAL = 15
BANDWIDTH_SAMPLING_INTERVAL = 2

"""
firmware version
    RTX1200 Rev.10.01.65 (Tue Oct 13 12:23:48 2015)
"""
def run(cmd):
    tn = telnetlib.Telnet(ROUTER)
    tn.read_until(b"Password: ")
    tn.write(PASSWORD.encode("ascii") + b"\n")
    tn.read_until(PROMPT.encode("ascii") + b"> ")
    tn.write(cmd.encode("ascii") + b"\n")
    tn.write(b" \n")
    res = tn.read_until(PROMPT.encode("ascii") + b"> ").decode("ascii")
    tn.write(b"exit\n")
    return res

def post(metrics):
    print(metrics)
    db = list(metrics.keys())[0]
    client = InfluxDBClient(DB_CONTAINER, DB_PORT, DB_USER, DB_PASSWORD, db)
    request = {}
    for key, value in list(metrics.values())[0].items():
        request["measurement"] = key
        request["fields"] = {}
        request["fields"]["value"] = value
        client.write_points([request])
    return True

def grep(pattern, text):
    return re.findall(pattern, text)

def environment_mon():
    cmd = "show environment"
    status = run(cmd)
    metrics = {}
    metrics["environment"] = {}

    uptimestr = status.split("\r\n")[-4].split("boot: ")[1]
    day = grep("(\d+)days", uptimestr)
    day = 0 if not day else int(day[0])
    time = grep("(\d+):(\d+):(\d+)", uptimestr)
    hour = int(time[0][0])
    minute = int(time[0][1])
    second  = int(time[0][2])
    uptime = day * 24 * 60 * 60 + hour * 60 * 60 + minute * 60 + second

    #metrics["environment"]["firmware"] = status.split("\r\n")[2].split()[1]
    metrics["environment"]["uptime"] = uptime
    metrics["environment"]["cpu_5sec"] = int(grep("(\d+)%\(5sec\)", status)[0])
    metrics["environment"]["cpu_1min"] = int(grep("(\d+)%\(1min\)", status)[0])
    metrics["environment"]["cpu_5min"] = int(grep("(\d+)%\(5min\)", status)[0])
    metrics["environment"]["memory"] = int(grep("Memory: (\d+)%", status)[0])
    metrics["environment"]["packet_small"] = int(grep("(\d+)%\(small\)", status)[0])
    metrics["environment"]["packet_middle"] = int(grep("(\d+)%\(middle\)", status)[0])
    metrics["environment"]["packet_large"] = int(grep("(\d+)%\(large\)", status)[0])
    metrics["environment"]["packet_huge"] = int(grep("(\d+)%\(huge\)", status)[0])
    metrics["environment"]["temperature"] = int(grep("\(C\.\): (\d+)", status)[0])

    post(metrics)

def nat_mon():
    cmd = "show nat descriptor address"
    status = run(cmd)
    metrics = {}
    metrics["nat"] = {}

    metrics["nat"]["entry"] = int(grep("(\d+) used.", status)[0])

    post(metrics)

def dhcp_mon():
    cmd = "show status dhcp"
    status = run(cmd)
    metrics = {}
    metrics["dhcp"] = {}

    metrics["dhcp"]["leased_wired"] = int(grep("Leased: (\d+)", status)[0])
    metrics["dhcp"]["leased_wireless"] = int(grep("Leased: (\d+)", status)[1])
    metrics["dhcp"]["usable_wired"] = int(grep("Usable: (\d+)", status)[0])
    metrics["dhcp"]["usable_wireless"] = int(grep("Usable: (\d+)", status)[1])

    post(metrics)

def pp1_traffic_mon(sec):
    cmd = "show status pp 1"
    status1 = run(cmd)
    time.sleep(sec)
    status2 = run(cmd)

    metrics = {}
    metrics["pp1"] = {}

    bandwidth = 1024 * 1024
    rcv1 = int(grep("(\d+) octet", status1)[0])
    snd1 = int(grep("(\d+) octet", status1)[1])
    rcv2 = int(grep("(\d+) octet", status2)[0])
    snd2 = int(grep("(\d+) octet", status2)[1])

    metrics["pp1"]["bandwidth_rcv"] = (rcv2 - rcv1) * 8 / sec
    metrics["pp1"]["bandwidth_snd"] = (snd2 - snd1) * 8 / sec
    #metrics["pp1"]["load_rcv"] = grep("Load: (\d+\.\d+)%", status2)[0]
    #metrics["pp1"]["load_snd"] = grep("Load: (\d+\.\d+)%", status2)[1]
    metrics["pp1"]["load_rcv"] = round(metrics["pp1"]["bandwidth_rcv"] / bandwidth, 2)
    metrics["pp1"]["load_snd"] = round(metrics["pp1"]["bandwidth_snd"] / bandwidth, 2)

    post(metrics)

def lan1_traffic_mon(sec):
    cmd = "show status lan1"
    status1 = run(cmd)
    time.sleep(sec)
    status2 = run(cmd)

    metrics = {}
    metrics["lan1"] = {}

    bandwidth = 1024 * 1024
    snd1 = int(grep("(\d+) octet", status1)[1])
    rcv1 = int(grep("(\d+) octet", status1)[2])
    snd2 = int(grep("(\d+) octet", status2)[1])
    rcv2 = int(grep("(\d+) octet", status2)[2])

    metrics["lan1"]["bandwidth_rcv"] = (rcv2 - rcv1) * 8 / sec
    metrics["lan1"]["bandwidth_snd"] = (snd2 - snd1) * 8 / sec
    metrics["lan1"]["load_rcv"] = round(metrics["lan1"]["bandwidth_rcv"] / bandwidth, 2)
    metrics["lan1"]["load_snd"] = round(metrics["lan1"]["bandwidth_snd"] / bandwidth, 2)

    post(metrics)

def metrics_monitoring(sec):
    try:
       environment_mon()
       nat_mon()
       dhcp_mon()
       pp1_traffic_mon(sec)
       lan1_traffic_mon(sec)
       return True
    except:
       return False

if __name__ == '__main__':
    while True:
        if not metrics_monitoring(BANDWIDTH_SAMPLING_INTERVAL):
            print("failed to post")
        time.sleep(MONITORING_INTERVAL)
