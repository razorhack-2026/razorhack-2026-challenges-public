import re
import requests
from pathlib import Path
def solve():
    url=__import__("os").environ.get("LIFE_URL","http://127.0.0.1:8081")
    status=requests.get(url+"/api/status",timeout=3).json()
    k,base=map(float,re.fullmatch(r"O2 = ([0-9.]+) \* trace \+ ([0-9.]+)",status["constraints"][1]).groups())
    ar=float(status["constraints"][2].split(" = ")[1]); trace=float(status["constraints"][3].split(" = ")[1])
    o2=k*trace+base; n2=100-o2-ar-trace
    result=requests.post(url+"/api/mix",json={"id":status["id"],"N2":n2,"O2":o2},timeout=3).json()
    return result["flag"]
