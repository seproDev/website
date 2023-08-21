---
title: "Hosting and Recording an Online Game Show"
date: 2021-08-16T00:00:00+00:00
tags: ["gambitgame", "jitsi"]
description: "Zoom but in complicated"
showToc: true
---

I was recently involved in producing a live online game show called [Gambit Game](https://www.youtube.com/@thegambitgame).
The series was inspired by the Korean TV Series [The Genius](https://en.wikipedia.org/wiki/The_Genius_(TV_series)) and was hosted online with 10 participants.
The basic concept is that the contestants compete in various challenges which test their strategic thinking and social skills.
In the real world contestants can move between different rooms to talk to each other, but since this was online, we had to find a way to replicate that.
Since some interesting technical challenges came up during the production, I thought I'd write about them here.

Before I joined, the plan was to use Zoom and have different breakout rooms function as the rooms on set.
That seemed like quite an inelegant solution, because it would require one person recording for each breakout room, and also leaves us with little room to play with in terms of customization.

I did look into other off-the-shelf solutions (Teams, Webex, Discord, Nextcloud Talk...), but none at the time had all the features we were looking for:
 - Ability to have different rooms with easy way for participants to move
 - Recording of rooms, ideally all done by one person and with separate audio channels (to better isolate/edit dialogue)
 - Possibility of customization/modification

While you may assume that the most important thing to have is rooms and the ability to record, that is actually not the case. If the software is modifiable enough, we can just add any missing features ourselves.

With that in mind, I started experimenting with Jitsi. Jitsi is an open source conferencing software that I initially discarded since a new instance has neither easy room switching nor functioning recordings.
But I did see that there is a software called Jibri that supposedly allows creating recordings right inside of Jitsi. For the room switching functionality, I hoped that I could somehow hack something together. Worst case since Jitsi is open source I could just create a fork, implement the features we need and then run the modded version.


## Different Rooms

Jitsi is entirely browser based. You open a link and can instantly join a meeting. My idea for implementing different rooms was quite simple: have a meeting running for each room and switch between them by loading different iFrames from one main page.

This got made especially easy by Jitsi having quite a good iFrame API. <https://jitsi.github.io/handbook/docs/dev-guide/dev-guide-iframe>

Within a couple of hours I had rented a server, installed Jitsi and got a first prototype up and running that allowed switching between different meetings from a single page.

We also wanted rooms to feel different, so it's clear in what room one is for both the players and viewers.

Unfortunately, with the iFrame API it's only possible to set different background colors and not pictures. But I can work around that.
By giving each room a unique color and injecting a custom CSS in to the Jitsi page, I can just detect that color and then set the background image accordingly.
```css
#largeVideoContainer[style^="background-color: rgb(0, 0, 3); display: inline-block;"] {
  background-image: url(/recording/assets/poolhall.jpg);
}
```
And with that the room switching problem is solved.


![One of the first versions with working room support](early.png#center))

That went way easier than expected, so how hard can recording be?


## Recording

Jitsi has built in recording support, but out of the box it doesn't work (well at least it didn't when we recorded this. Maybe it has improved since).
It requires a separate server running Jibri. Jibri effectively works by starting a Chrome instance, invisibly joining the meeting, capturing the browser window and then encoding the video feed with ffmpeg/x264.
This would have meant we would need quite a beefy server to have 7 recordings running simultaneously.

After learning about this and some other inflexibilities of Jibri I decided to try another approach: directly capturing the media streams in browser.
This would have the advantage of us capturing the originally transmitted data without re-encoding, preserving quality and lowering CPU usage drastically.

Let's give it a go...

With much pain and googling, I was able to save the video and audio streams directly without re-encoding.
From a technical side this works by having a Chrome extension that injects code in to the site, adds event listeners on the internal Jitsi events `TRACK_ADDED` and `TRACK_REMOVED` and then uses the MediaRecorder API to capture those tracks.
The final extension is quite simple, with not even 100 lines of code, but figuring this all out took quite a while.

But all that effort felt like it was for nothing once I discovered that we can't use the resulting recordings.

The problem is that Jitsi, like most calling software, dynamically changes resolution depending on the connection quality. Since nearly nothing supports variable resolution video (I had media players crash on playback), these files would have been an absolute pain to work with.
So back to the drawing board.

The main problem I had with Jibri is that by default it uses x264 for encoding, which requires a bunch of CPU power when recording 7 rooms simultaneously.

Now it is possible to recompile Jibri with support for NVENC (Nvidia's hardware based video encoder), but then we would also need to rent a server with a GPU, which also gets expensive.

How about we use NVENC, but without Jibri and without a dedicated recording server.
Nearly every consumer GPU released in the last few years has native hardware acceleration for video encoding.
So the plan was to have a second endpoint that only contains the Jitsi iFrame, but has even more of the Jitsi interface disabled, and you always join invisibly.
That endpoint can then be loaded inside an OBS (Game streaming/recording software) instance and recorded with NVENC.
Only one small problem: Nvidia wants to sell you their data-center GPUs.
By default, only 3 (used to be 2) NVENC sessions can be run at the same time on consumer GPUs. The graphics card can handle way more, but to artificially segment their product stack, Nvidia doesn't allow that.

Luckily, some people were equally annoyed as I was upon learning this and figured out how to patch the drivers and unlock unlimited NVENC sessions https://github.com/keylase/nvidia-patch

![4 rooms open in 4 OBS instances](obs.png#center))

This still leaves one last problem: separate audio channels.
If we record with OBS we only get one audio track per room.
Luckily, I already did all the work. With some minor adjustments to my code from earlier to capture the media streams, I was able to record just the audio streams for each person.
A python script was required to process the audio files further, but with that the recording setup was done.
7 OBS instances and a Chrome extension is all it took. I can see why people like the ease of pressing "record" in zoom.


## More Customization

Since we now have so much control over the actual site, I also implemented some other custom features:
 - Dealer webcam is automatically disabled and instead a custom profile picture is loaded
 - Mute all Button for Dealers
 - Only 2 people can join the dealer room at a time
 - Integration with Discord webhooks/bots
 - Invisible spectators
 - Updating info text panel for rules and confessional questions
 - Embedded YouTube live stream
 - Admin Panel
 - Some more Jitsi CSS mods (custom borders, nametag position, hide more elements...)

In the end the site ended up looking like this:
![Website Interface](interface.png#center))

The great thing about this setup is how much flexibility it gives. While the things done here were fairly rudimentary as it was just me with my (at the time) fairly limited web experience, with this being a regular website anything from an inventory system to on page games could be implemented.

The not so great thing about this setup is that it requires us to setup and maintain our own server. More about that in the next section..


## Hosting

For my testing, I just rented a cheap server from Hetzner, a hosting company in Germany. This gave me incredibly good latency (~5-10ms) and speed.
But since latency is quite important for video calls I also needed to consider the latency of the participants. If we went with this server for actual recording, this would have meant great latency for everyone in Europe, medium latency from the East Coast and quite bad latency from the West Coast.

Since we expected most participants to be from the East Coast, I wanted to ideally rent a server from there. This would mean great latency for everyone from there, with medium latency for everyone else (well except Asia & Oceania, sorry).

With that in mind, I started creating a spreadsheet to find a good value VPS on the East Cost.
The problem I ran in to was that all the US hosting providers I found (at least at the time) were way more expensive than their European counterparts. The only thing that was sort of competitive was OVHs (European provider) servers in Montreal.
But due to us only needing high performance once a week for a couple of hours, an alternative option became available: find a hosting provider that allows both up- and downgrading of instances and just let the cheapest instance run while we are not using the site.
You may be thinking that stopping the VPS instance would be even cheaper, but for all providers I found that isn't the case, and they will charge you full cost even if the server is off.
In the end I went with UpCloud which resulted in a monthly server cost (if I didn't forget to downgrade, oops) of ~7 USD. Their prices are more expensive than that of most other providers, but due to the upgrading and downgrading we were able to save quite a lot. For recordings, I scaled up to 6 cores, 16GB memory to give us ample headroom, while only using the smallest 1 core 1GB instance when idling. 

## Updates and Disaster

Since recording of Gambit Game went on for a couple of months, updates to Jitsi came out while recording.
The update process was relatively straightforward `apt update && apt upgrade`, inject the custom CSS in to the Jitsi page again, check if everything is still working/needs adjustments, see if there are any new features that might be useful.

To give myself ample time to figure stuff out, I never updated right before recording. I also first updated our testing/backup server (Hetzner) and only after verifying everything works updated the main server (UpCloud).

Jitsi version 2.0.5765 seemed like a great update to do. It brought improvements to the iFrame API simplifying some of my code, and a redesign to the call interface.
After the update and some adjustments, everything seemed to work great...

Until two hours before the scheduled recording, when I noticed that inside OBS players never get disconnected from a room:
![Many clients not disconnecting](bug.png#center))
This problem seemed to be isolated to OBS, which was strange since the OBS browser uses the chromium embedded framework (CEF) which should be identical to Chrome in terms of compatibility.
After attaching a debugger to the OBS Browser I isolated the problem to a new JavaScript prototype function that was only introduced in Chrome version 76, while OBS is running on effectively Chrome 75 which is from 2019.

I tried both the OBS beta release and the Streamlabs fork, but both had the outdated CEF version, so the only way we could record with our current setup was to downgrade.

Since I had bad experiences with software downgrades in the past, I attempted the downgrade on our backup/testing server first.
The result: Jitsi wouldn't start and a bunch of non-descriptive errors came up in the logs.

With now only 30 minutes to go, one server that is not working at all and one server where recording doesn't work, I was beginning to get really worried.
At this point I had two options: try to make the downgrade successfully on the main server or figure out an alternative way of recording.

I decided to go with the second option. The solution I came up with was having 6 Chrome windows open, each sized to roughly 1080p and using regular window captures to record the videos.


![recording the painful way](recording_the_painful_way.png#center)

After the recording was done, it took me a couple of hours to figure out what configuration file was changed during the Jitsi update to successfully complete the downgrade.
Going the ghetto route with the recording was definitely the right call.
Since OBS didn't update the CEF during the months we recorded (at least on Windows, I looked in to it, and it seems to be not their fault but instead the fault of the Chromium team) we stuck with the outdated version of Jitsi till the end.

&nbsp;


I hope you found this look behind the scenes of Gambit Game at least somewhat interesting.
I won't be publishing the source code, since at least in its current state it's a cobbled together mess of various files that would be extremely hard to get running on your own (not to mention that by now it's pretty outdated).
