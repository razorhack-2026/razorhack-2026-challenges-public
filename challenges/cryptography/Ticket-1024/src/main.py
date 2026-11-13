from flask import Flask, redirect, request, make_response, render_template
from Crypto.Cipher import DES

app = Flask(__name__)

DES_KEY = b'\xca\x2d\x80\xf4\x31\x97\xff\x02'

@app.route('/')
def index():
    if request.cookies.get('session'):
        sessionCookie = request.cookies.get('session')
        cipher = DES.new(DES_KEY, DES.MODE_ECB)
        encryptedSession = bytes.fromhex(sessionCookie.replace('.', ''))
        decryptedSession = cipher.decrypt(encryptedSession)
        decryptedSession = decryptedSession.rstrip().decode()  # Remove space padding
        session = dict(item.split('=', maxsplit=1) for item in decryptedSession.split('&'))
        return render_template('dashboard.html', crewID=session.get('crewID'), isAdmin=(session.get('role') == 'admin'))
    return render_template('index.html')

@app.route('/requestAccess', methods=['POST'])
def requestAccess():
    crewID = request.form.get('crewID')
    
    cipher = DES.new(DES_KEY, DES.MODE_ECB)
    sessionString = b'salt=1&crewID=%b&role=viewer' % crewID.encode()
    sessionString += b' ' * (8 - len(sessionString) % 8)  # space padding
    encryptedSession = cipher.encrypt(sessionString)
    response = make_response(redirect('/'))
    delimited = '.'.join(encryptedSession.hex()[i:i+16] for i in range(0, len(encryptedSession.hex()), 16))
    response.set_cookie('session', delimited)
    return response

if __name__ == '__main__':
    app.run('0.0.0.0', 8000)