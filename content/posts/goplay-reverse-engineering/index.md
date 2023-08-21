---
title: "How Pirate Sites Use Legal Sites as Their CDN"
date: 2023-08-04T00:00:00+00:00
tags: ["drm", "piracy"]
description: "Taking more than just the content"
---
A significant cost of delivering video online is the storage, bandwidth, and compute.
This also applies to pirate sites, which is why the video quality on many of them is so low.
However some sites have found a way to get around this by piggybacking off of legal sites.
In this post we will take a closer look at [GoPlay](https://goplay.pw/) and see how they manage to host a pirate streaming site without paying for bandwidth.

Investigating GoPlay is a bit more difficult, as they use JavaScript to block opening the browsers dev tools.
We will get to how to defeat this later, but to start let's just take a look around the website.
The videos are categorized by "server". Sometimes the same show can be on multiple servers, sometimes only on one.
Some of the servers also require installing a [Chrome Extension](https://chrome.google.com/webstore/detail/goplay-extension/edhdonadgbpnhhkdobemjnjdpmfdjnmf).
This gives the first hint as to what is going on:
![GoPlay Exentension Permissions](permissions.png#center)

Looking at the code of the extension we can see that the extension modifies request headers to add a `Referer` and response headers to set `Access-Control-Allow-Origin` to `*`.
This is done for requests to the CDN servers from Viki, VIU, and GagaOOLala. Three legal streaming sites.

With this the modus operandi of GoPlay becomes clear.
They only serve as a proxy for legal streaming sites, using paid accounts to request the video URL and then serving just the playlist to their users letting the legal sites pay for the bandwidth.

Looking around online we can also find this graphic showing all the servers they proxy:
![List of sites they proxy](serverguide.png#center)

Now let's see if we can get around their protection measures and maybe figure out how they deal with DRM that some of the proxied sites use.


As mentioned before, GoPlay uses JavaScript to block the dev tools.

![Developer tools blocked](devtools.png#center)

In addition, we can see that the console gets cleared regularly by `dttr.js`.
Taking a look at the code we can quickly identify it as [devtools-detector](https://github.com/AEPKILL/devtools-detector).
This is a library that detects if the dev tools are open and can then prevent the user from properly debugging the site.

Instead of setting up some reverse proxy setup to remove or disable this file, I decided to use uBlock Origin, to block the script from loading.
```plain
||assets.goplay.pw/ddtr.js$script,domain=goplay.pw
```

However, with `dttr.js` removed videos no longer play.
![Video playback disabled](no-video.png#center)

Looking at the remaining JavaScript files we find heavily obfuscated code.
Running the code through [synchrony](https://github.com/relative/synchrony), we get surprisingly readable code.
So seems like they used some off the shelf deobfuscator.

Looking at the deobfuscated code we can easily identify the part that is responsible for blocking video playback when `ddtr.js` is not loaded:
```javascript
var myint,
  zt3 = 0
function tmr() {
  var _0x1dc940 = new Function('debugger')
  zt3 = 341
  _0x1dc940()
}
if (typeof ddtr === 'undefined') {
  var kt = new Function('$("#container").remove();')
  setInterval(kt, 1)
} else {
  typeof d1af === 'undefined' &&
    (ddtr.addListener(function (_0xea637) {
      if (_0xea637) {
        $('#container').remove()
        window.stop()
        myint = setInterval(tmr, 1)
      } else {
        if (zt3 > 300) {
          location.reload()
        }
        clearInterval(myint)
      }
    }),
    ddtr.launch())
}
```

We have identified the part of the code that is responsible for blocking video playback, how do we remove it?
There are many possible solutions here, the main one that probably comes to mind is using a MITM proxy that replaces the JavaScript files with custom ones.
While that would work fine, I wanted to try something else, utilizing both uBlock Origin and UserScripts.

First we can block all original JavaScript files from loading:
```plain
||assets.goplay.pw/ddtr.js$script,domain=goplay.pw
||assets.goplay.pw/functions.js?*$script,domain=goplay.pw
||assets.goplay.pw/det_incog.js?*$script,domain=goplay.pw
||assets.goplay.pw/chromecast_integrate.js?*$script,domain=goplay.pw
```

And then use a UserScript to inject our own modified JavaScript.
For this I took the deobfuscated code and commented out multiple sections related to the DevTools detection and command line clearing. 
With this I was able to successfully open the DevTools and debug the site.
Looking at the network traffic, we can see that they use an additional protection layer by encrypting the video data containing the video URL and subtitles.
Since we can easily adjust the executed JavaScript now, I quickly modified the code to print the decrypted data whenever the decryption function is called:
```javascript
function dcr(_0x4651a8, _0x131974) {
  var _0x20d447 = atob(_0x4651a8)
  var _0xa2b872 = btoa(_0x20d447.substring(48))
  if ($('#jstup').attr('class') && _0x131974) {
    var _0x4105be = CryptoJS.enc.Utf8.parse($('#jstup').attr('class'))
  } else {
    var _0x4105be = CryptoJS.enc.Base64.parse(
      'jkAtoi2EKbwG5GXwqdUc3G2r7OhxAtQ4rRXvaPsfq+8='
    )
  }
  var _0x27ee44 = CryptoJS.enc.Hex.parse(bin2hex(_0x20d447.substring(0, 16)))
  var _0x2c8383 = { iv: _0x27ee44 }
  var _0x287787 = CryptoJS.AES.decrypt(_0xa2b872, _0x4105be, _0x2c8383)
  var _0x287787 = CryptoJS.enc.Utf8.stringify(_0x287787)
  console.log("Decrypted Data:")
  if (!_0x131974 || _0x131974 == null) {
    console.log(_0x287787)
    return _0x287787
  } else {
    console.log(JSON.parse(_0x287787))
    return JSON.parse(_0x287787)
  }
}
```
And with that, success!
![Decrypted video data](decrypted_data.png#center)
We can see the decrypted video data in the console.
This looks very much like [jwplayer configuration data](https://docs.jwplayer.com/players/reference/setup-options).
Both the subtitle and dash manifest URLs are hosted by goplay.
The manifest seems to be a rewritten version of the manifest available by the official streaming site.
However, the individual segments still link to the original CDN server.
This CDN server is crucially paid for by the legal streaming sites, so GoPlay is essentially just leeching off of them.
Now the requirement for the extension also make sense, as the CDN was likely configured to only allow requests coming from the legal streaming sites.

One last question remains, how do they deal with DRM?
Multiple of the legal streaming sites proxied by GoPlay use Widevine and PlayReady to protect their content.
As we can see in the jwplayer config, GoPlay provides the decryption keys as clearkey keys.
This means they have a working device provision to request (and likely cache) keys from the legal streaming site.
They then forward the keys directly to their users, which can use them to play back DRM protected contet.

## Conclusion

We saw a new kind of pirate streaming site, which does not directly host the content but instead proxies it from legal streaming sites.
This gives them the advantage of providing a large library of content without having to host it themselves.
They can also provide the content in higher quality than most other pirate streaming sites.
However, this comes at the cost of legal streaming sites who are now paying for the bandwidth of the pirate streaming site.

Possible solutions for the legal streaming sites would be to try and identify the accounts used by GoPlay to access their content and then suspend them.
In addition, IP blocks could be used to block the GoPlay servers from accessing the content.
Furthermore, increased security measures could be employed on the Widvine and PlayReady license endpoints to prevent the keys from being leaked.
