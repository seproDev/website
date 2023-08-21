---
title: "Breaking Subtitle Encryption on Pirate Streaming Site"
date: 2022-09-08T00:00:00+00:00
tags: ["drm", "subtitles", "piracy"]
description: "How pirates protect their booty"
---

At first glance [HiTV](https://www.gohitv.com/) might look like a regular legal streaming site.
They have a slick website, an [iOS](https://apps.apple.com/app/hitv-massive-video-library/id6443464106) and [Android](https://play.google.com/store/apps/details?id=com.gohitv.hitv) app, and various social media accounts.

![gohitv web interface](gohitv.com.png#center)

But looking deeper you find shows such as [Squid Game](https://www.gohitv.com/series/C2jw_KP3jjx9dIcgZivo), which Netflix surely didn't license to them.
So just a regular pirate streaming site, they download videos and subtitles from legal sites and illegally redistribute them, what gives?

Well, here is the thing: they have subtitles for shows in languages that are not officially available.
The subtitle quality is not great, but for many people not great is better than no subs at all.
If I had to guess I would say these subs are probably machine translated, but they could also be hiring some very cheap translators.

Producing their own subs the operators of HiTV now have an interesting dilemma: They don't want other pirate streaming sites to take their work and earn money with it.
To combat this they are using their own form of DRM to encrypt the subtitles.
Kind of ironic, isn't it?

This is also notable since there are barely any legal streaming sites protecting their subtitles.
Sites like Netflix don't even bother encrypting their audio tracks and instead only encrypt the video.

Let's take a look at how their subtitle protection works and how we can break it.

Taking a look at the network traffic we can quickly identify the flow of data.
The page HTML contains a `sid` (series ID) and a `eid` (episode ID).
Using the `eid`, details for the episode can be requested from their API:
```plain
https://api.gohitv.com/s1/w/series/api/episode/detail?eid={eid}
```
Importantly the request contains a `did` header.
Returned is a timestamp and a base64 blob containing encrypted data.

Looking for `did` in the source code there is only one relevant result:
```javascript
var Or = function(e, t) {
    var n = e.app
        , r = e.$axios
        , o = e.i18n
        , c = e.redirect
        , l = function(e) {
        if (1100 === e) {
            var t = n.$routeNav ? n.$routeNav.getNoServiceUrl() : "";
            t && c(t)
        }
    }
        , f = {
        platform: "pc",
        lth: o.localeProperties.iso,
        did: xr(),
        "Cache-Control": "no-cache, no-store"
    }
        , h = "https://api.gohitv.com/".replace(/\/$/, "").replace(/(https:\/\/)|(http:\/\/)/, "")
        , d = r.create({
        timeout: 3e4,
        baseURL: "https://api.gohitv.com/",
        headers: JSON.parse(JSON.stringify(f))
    });
    d.interceptors.response.use((function(e) {
        var code = e.status;
        if (code >= 200 && code < 300 || 304 === code) {
            var t = e.data
                , data = wr(t.ts.toString(), xr(), btoa("Wcb26arWkvkcAZc378eR"), t.data);
            return Promise.resolve({
                ts: t.ts,
                rescode: t.rescode,
                data: data
            })
        }
        return Promise.reject(e)
    }
```
This looks to be the function for sending out API requests using [Axios](https://axios-http.com/).
The `did` header is defined by `xr()` which just generates a random 24 char long ID:
```javascript
var _r = "";
/* ... */
function xr() {
    return _r || (_r = function(e) {
        e = e || 32;
        for (var t = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678", n = t.length, r = "", i = 0; i < e; i++)
            r += t.charAt(Math.floor(Math.random() * n));
        return r
    }(24)),
    _r
}
```
Maybe `did` stands for device ID? Who knows.

Looking a bit further in the code snippet above, we also find the response handler which is calling the `wr` function:
```javascript
wr(timestamp, did, btoa("Wcb26arWkvkcAZc378eR"), b64_data);
```
Looking at the `wr` function we can see that it is using AES to decrypt the data:
```javascript
function wr(e, t, n, data) {
    if (!data)
        return {};
    var r = yr.MD5("".concat(yr.MD5("".concat(t).concat(e))).concat(atob(n))).toString()
        , o = function(e, t, n) {
        var r = "";
        try {
            e = vr.enc.Utf8.parse(e),
            t = vr.enc.Utf8.parse(t);
            var o = vr.enc.Base64.parse(n)
                , c = vr.enc.Base64.stringify(o);
            r = vr.AES.decrypt(c, e, {
                iv: t,
                mode: vr.mode.CBC,
                padding: vr.pad.Pkcs7
            }).toString(vr.enc.Utf8)
        } catch (e) {}
        return r
    }(r.slice(0, 16), r.slice(16), data);
    return o ? JSON.parse(o) : {}
}
```
With this we have everything we need to decrypt the data ourselves.
Here a small python script to do just that:

```python
AES_KEY = 'Wcb26arWkvkcAZc378eR'

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
print(detail_dec)
```
The decrypted data looks like this:
```JSON
{
  "episode": {
    "eid": "mHEdvAp026I45zcCVWct",
    "sid": "12cQHnWGN_O15Cj9IZ2QUk",
    "sidAlias": "work-later,-drink-now",
    "serialNo": 1,
    "title": "1",
    "publishTime": 1645011706485,
    "createTime": 1645011706485,
    "sources": [
      {
        "scid": "sc_bTZjM8TQJ7RSmhxuCEub",
        "eid": "mHEdvAp026I45zcCVWct",
        "videoSkip": 0,
        "srcPrior": 1,
        "endBreak": 10000,
        "langCodes": [
          "none"
        ],
        "patches": [
          
        ],
        "qualities": [
          /* ... */
        ]
      }
    ]
  }
}
```
Importantly we get a new value `scid` which will be used in the next request:
```plain
https://api.gohitv.com/s1/w/series/api/series/rslv?sid={sid}&eid={sid}&scid={scid}&sq=1&sign={sign}
```
`sq` seems to always be 1, while the `sign` parameter is some kind of signature.
```javascript
var m = btoa("appkey");
/* ... */
function v(eid, sid, scid, sq, h) {
    return "eid=".concat(eid, "&scid=").concat(scid, "&sid=").concat(sid, "&sq=").concat(sq, "&").concat((l = m, atob(l)), "=").concat(atob(h));
}
/* ... */
d = f()(v(r, o, c, l, h)),
e.next = 4,
n.get("/s1/w/series/api/series/rslv", {
    sid: o,
    eid: r,
    scid: c,
    sq: l,
    sign: d
});
```
Setting a breakpoint on this function we find that `h` is hardcoded to `btoa("bywebabcd1234")` and `f()` just returns a md5 hash function.
With this info we can now recreate the signature ourselves, and decrypt the response using the same method as before.
```python
APP_KEY = 'bywebabcd1234'

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
print(rslv_dec)
```
The decrypted response data looks something like this:
```JSON
{
  "usageType": 11,
  "language": -1,
  "langCode": "none",
  "quality": 1,
  "qualityResolution": "360P",
  "format": 2,
  "codec": 1,
  "umk": "default",
  "qualities": [ /* ... */ ],
  "datas": [
    {
      "smid": "sm_SlE15vHa6SoO5jRpi30P",
      "data": "https://s1.hitv.io/m3u8/265ab13473f608a0345f4b823057c613.m3u8",
      "duration": 1620
    }
  ],
  "subtitles": [
    {
      "subtitleId": 13563,
      "langCode": "en-US",
      "translationType": 101,
      "offset": 0,
      "url": "https://s.gohitv.com/subtitle/18bb3df119004d289d2860a1433e74eb1653977424428.xml",
      "format": 2,
      "key": "ce0b5ab9f40a3e53cf05ab5b06f93466"
    },
    /* ... */
  ]
}
```
The video is a bog-standard unencrypted m3u8 playlist.
The subtitles are a bit more interesting, with the XML looking something like this:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sub format="1">
   <note height="1080" width="1920" />
   <dia>
      <st>0:00:00.14</st>
      <et>0:00:01.22</et>
      <con>ohC6SzuBu9pWCoaSfKA2Z5Judp9J5tCKpc8pqTkiosw=</con>
      <style>
         <font name="Arial" size="75" bold="0" italic="0" underline="0" strikeout="0" spacing="1.2" angle="0" />
         <color primary="&amp;H00FFFFFF" secondary="&amp;H00000000" outline="&amp;H97000000" back="&amp;H00F3F3F6" />
         <scale x="100" y="100" />
         <border style="3" outline="2" shadow="0" />
         <position type="1" alignment="2" ml="30" mr="30" mv="150" />
      </style>
   </dia>
...
```
As far as I can tell this is a custom subtitle format.
It is seemingly derived from the ASS subtitle format, based on the way color is represented and the three margin directions.
Either way `con` likely stands for content and is an encrypted base64 string.
Taking one last look at the JavaScript code we quickly find that key from above gets split into two 16 character long parts.
With the first part being the key and the second part being the IV in an AES CBC decryption.
Strangely both parts get interpreted as strings and not as hexadecimal digits.

And with that we have successfully reverse engineered their subtitle protection system.
The code to download the subtitle files and retrieve the key can be found [here](gohitv_download.py).
I have also written a quick and dirty converter to decrypt each line and save the subtitle file as either SRT or ASS which can be found [here](gohitv_convert.py).

It is interesting to see pirate sites better protect their content than some legal sites.
However, being pirate sites they don't have access to modern DRM solutions like Widevine and PlayReady and thus need to implement their own version of copy protection.
Some form of obfuscation other than the typical JavaScript bundling could have made this significantly more annoying.
