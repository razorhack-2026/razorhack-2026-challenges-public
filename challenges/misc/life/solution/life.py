import re
import requests

body = requests.get('http://localhost:8081/api/status').json()

print(body)

multiplier, oxygen_factor = map(float, re.fullmatch(r"O2 = ([0-9.]+) \* trace \+ ([0-9.]+)", body['constraints'][1]).groups())
argon = float(body['constraints'][2].split(' = ')[1])
trace = float(body['constraints'][3].split(' = ')[1])

print(str(oxygen_factor) + ", " + str(argon) + ", " + str(trace))

oxygen = multiplier * trace + oxygen_factor
nitrogen = 100 - oxygen - argon - trace

res = requests.post('http://localhost:8081/api/mix', json={'N2': nitrogen, 'O2': oxygen, 'id': body['id']})

print(res.text)
