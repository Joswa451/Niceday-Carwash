
from scapy.all import *
import time

target = "google.com"
results = []

for i in range(5):
    start = time.time()
    reply = sr1(IP(dst=target)/ICMP(), timeout=1, verbose=0)
    end = time.time()

    if reply:
        results.append(end - start)

if results:
    print("Average Latency:", sum(results) / len(results))
else:
    print("No response received")
