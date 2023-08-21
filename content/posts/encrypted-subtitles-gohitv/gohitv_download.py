import requests
import random
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
import json

sid = '12cQHnWGN_O15Cj9IZ2QUk'
eid = 'mHEdvAp026I45zcCVWct'

# Hard coded in JavaScript. Might need to be updated in the future
AES_KEY = 'Wcb26arWkvkcAZc378eR'
APP_KEY = 'bywebabcd1234'

did = ''.join(random.choices('ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678', k=24))

def md5(string):
    return hashlib.md5(string.encode()).hexdigest()

def decryptResponse(data, ts, did):
    timestamp = str(ts)

    protokey = md5(md5(did + timestamp) + AES_KEY)
    key_text = protokey[:16]
    iv_text = protokey[16:]

    data = b64decode(data)
    key = key_text.encode()
    iv = iv_text.encode()
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    pt = unpad(cipher.decrypt(data), AES.block_size)
    return pt

headers = {
    'accept': 'application/json, text/plain, */*',
    'did': did,
    'lth': 'en-US',
    'platform': 'pc',
}

detail = requests.get(f'https://api.gohitv.com/s1/w/series/api/episode/detail?eid={eid}', headers=headers).json()
detail_dec = json.loads(decryptResponse(detail['data'], detail['ts'], did))

scid = detail_dec['episode']['sources'][0]['scid']

signString = f'eid={eid}&scid={scid}&sid={sid}&sq=1&appkey={APP_KEY}'

rslvParams = {
    'sid': sid,
    'eid': eid,
    'scid': scid,
    'sq': 1,
    'sign': md5(signString),
}

rslv = requests.get('https://api.gohitv.com/s1/w/series/api/series/rslv', params=rslvParams, headers=headers).json()

rslv_dec = json.loads(decryptResponse(rslv['data'], rslv['ts'], did))

# Download all subtitles and include key in filename
for track in rslv_dec['subtitles']:
    filename = f"{track['subtitleId']}_{track['key']}_{track['langCode']}.xml"
    print(f'Downloading {filename}')
    r = requests.get(track['url'])
    with open(filename, 'wb') as f:
        f.write(r.content)
