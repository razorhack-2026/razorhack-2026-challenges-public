import os, requests
def solve():
    url=os.environ.get("CORE_URL","http://127.0.0.1:8082")
    tokens=(__import__("pathlib").Path(__file__).with_name("prerequisites.txt").read_text(encoding="utf-8").splitlines())
    if len([t for t in tokens if t])!=7: raise ValueError("seven earlier challenge tokens were not configured")
    auth=requests.post(url+"/api/override/auth",json={"tokens":tokens},timeout=3).json()
    grid=auth["grid"]; n=len(grid); moves=[]
    for r in range(n-1):
        for c in range(n):
            if grid[r][c]:
                moves.append([r+1,c])
                for rr,cc in ((r+1,c),(r,c),(r+2,c),(r+1,c-1),(r+1,c+1)):
                    if 0<=rr<n and 0<=cc<n: grid[rr][cc]^=1
    if any(any(row) for row in grid): raise ValueError("grid solver did not clear board")
    return requests.post(url+"/api/override/grid",json={"session":auth["session"],"moves":moves},timeout=3).json()["flag"]
