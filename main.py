#!/usr/bin/python3
from time import sleep
import telnetlib, re

ROUTER = "10.0.10.254"
PASSWORD = ""
PROMPT="RTX1200"
DB = "10.0.10.101"

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
    print(metrics.keys())
    print(metrics.values())

def grep(pattern, text):
    return re.findall(pattern, text)

def environment_mon():
    cmd = "show environment"
    status = run(cmd)
    metrics = {}
    metrics["environment"] = {}

    metrics["environment"]["firmware"] = status.split("\r\n")[2].split()[1]
    metrics["environment"]["uptime"] = status.split("\r\n")[-4].split("boot: ")[1]
    metrics["environment"]["cpu_5sec"] = grep("(\d+)%\(5sec\)", status)[0]
    metrics["environment"]["cpu_1min"] = grep("(\d+)%\(1min\)", status)[0]
    metrics["environment"]["cpu_5min"] = grep("(\d+)%\(5min\)", status)[0]
    metrics["environment"]["memory"] = grep("Memory: (\d+)%", status)[0]
    metrics["environment"]["packet_small"] = grep("(\d+)%\(small\)", status)[0]
    metrics["environment"]["packet_middle"] = grep("(\d+)%\(middle\)", status)[0]
    metrics["environment"]["packet_large"] = grep("(\d+)%\(large\)", status)[0]
    metrics["environment"]["packet_huge"] = grep("(\d+)%\(huge\)", status)[0]
    metrics["environment"]["temperature"] = grep("\(C\.\): (\d+)", status)[0]

    post(metrics)

def nat_mon():
    cmd = "show nat descriptor address"
    status = run(cmd)
    metrics = {}
    metrics["nat"] = {}

    metrics["nat"]["entry"] = grep("(\d+) used.", status)[0]

    post(metrics)

def dhcp_mon():
    cmd = "show status dhcp"
    status = run(cmd)
    metrics = {}
    metrics["dhcp"] = {}

    metrics["dhcp"]["leased_wired"] = grep("Leased: (\d+)", status)[0]
    metrics["dhcp"]["leased_wireless"] = grep("Leased: (\d+)", status)[1]
    metrics["dhcp"]["usable_wired"] = grep("Usable: (\d+)", status)[0]
    metrics["dhcp"]["usable_wireless"] = grep("Usable: (\d+)", status)[1]

    post(metrics)

def pp1_traffic_mon(sec):
    cmd = "show status pp 1"
    status1 = run(cmd)
    sleep(sec)
    status2 = run(cmd)

    metrics = {}
    metrics["pp1"] = {}

    rcv1 = int(grep("(\d+) octet", status1)[0])
    snd1 = int(grep("(\d+) octet", status1)[1])
    rcv2 = int(grep("(\d+) octet", status2)[0])
    snd2 = int(grep("(\d+) octet", status2)[1])

    metrics["pp1"]["bandwidth_rcv"] = (rcv2 - rcv1) * 8 / sec
    metrics["pp1"]["bandwidth_snd"] = (snd2 - snd1) * 8 / sec
    metrics["pp1"]["load_rcv"] = grep("Load: (\d+\.\d+)%", status2)[0]
    metrics["pp1"]["load_snd"] = grep("Load: (\d+\.\d+)%", status2)[1]

    post(metrics)

def lan1_traffic_mon(sec):
    cmd = "show status lan1"
    status1 = run(cmd)
    sleep(sec)
    status2 = run(cmd)

    metrics = {}
    metrics["lan1"] = {}

    bandwidth = 1024 * 1024
    rcv1 = int(grep("(\d+) octet", status1)[0])
    snd1 = int(grep("(\d+) octet", status1)[1])
    rcv2 = int(grep("(\d+) octet", status2)[0])
    snd2 = int(grep("(\d+) octet", status2)[1])

    metrics["lan1"]["bandwidth_rcv"] = (rcv2 - rcv1) * 8 / sec
    metrics["lan1"]["bandwidth_snd"] = (snd2 - snd1) * 8 / sec
    metrics["lan1"]["load_rcv"] = metrics["lan1"]["bandwidth_rcv"] / bandwidth
    metrics["lan1"]["load_snd"] = metrics["lan1"]["bandwidth_snd"] / bandwidth

    post(metrics)

if __name__ == '__main__':
    sec = 5
    environment_mon()
    nat_mon()
    dhcp_mon()
    pp1_traffic_mon(sec)
    lan1_traffic_mon(sec)
