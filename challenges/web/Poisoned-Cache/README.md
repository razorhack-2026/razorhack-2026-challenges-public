# Poisoned Cache

**Category:** Web  
**Author:** Lt. Rico Kopernicus

Something *really* bad is happening! Our shields just shut down and something
foreign is broadcasting beacon data from our damage control system. I tried to
restart the system, but it just keeps erroring. Bring our shields back up,
track down the beacon, and remove it - quickly!

Also, just so you know, our shield emitter system only arms with a specific
hardware activation code, don't ask me why. The person who made it left the
company decades ago. All we know is that it's the first 16 hex characters
(lowercase) of:

`HMAC-SHA256(key = firmware:key, message = hull:serial + ":" + reactor:seed)`

You might be able to find those values on the shield system's cache. I don't
remember what its caching service is called though. Something like Regex?
Redux? Red Ice?

**Connection:** http://{host}:{port}

_This README was generated from challenge.yml for the public release._
