# Sessions (the lack of them)

Currently the communication protocol lacks sessions, which are planned to be introduced in the near future (see [#79](https://github.com/trezor/trezor-firmware/issues/79)).

To ensure the device is in the expected state we use something called _session_id_. Session id is a 32 bytes long random blob which identifies the internal device state (mainly its caches). This is primarily useful for passphrase to make sure the same passphrase is cached in the device as the one the user entered a few minutes ago. See [passphrase.md](passphrase.md) for more on that.

On first initialization the Host does not have a session id and starts the communication with an empty Initialize:

```
Initialize()
--------->          Features(..., session_id)
                       <---------
```

After the first Features message is received the Host might store the session_id. To ensure the device state Host must send the Initialize message again including that particular session_id:

```
Initialize(session_id) 
--------->          Features(..., session_id)
                       <---------
Request
--------->          Response
                       <---------
```

So to make sure the device state has not changed, the Host must send the Initialize message with the correctly stored session_id before each request. Yes, this is stupid.

As mentioned, sessions will be introduced soon™ and fix that. We will probably take the first few bytes of the session_id, declare it a session id, and the rest will remain, without the annoying requirement of sending Initialize before every message.

----

The session is terminated and therefore the caches are cleared if:
- Initialize.session_id is empty.
- Initialize.session_id is different then the one cached in Trezor.
- Trezor is replugged (session is not persistent).
- ClearSession is received.
