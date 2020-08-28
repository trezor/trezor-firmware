# Sessions

Trezor has limited support for logical sessions. The main purpose is to enable seamless
operation with multiple passphrases.

**Warning: Session isolation does not exist.** Host software is responsible for
maintaining isolation. Running multiple host-side applications at the same time is not
recommended.

See "Caveats" section below for details.

Support for isolated sessions is in the works, see
[#79](https://github.com/trezor/trezor-firmware/issues/79).

## Session lifecycle

After Trezor starts up, no session exists. Any attempt to use session data (i.e., the
seed) will be rejected with `InvalidSession` error code.

New session is started by calling `Initialize` with no arguments. The response is a
`Features` message, which contains a 32-byte `session_id`. All subsequent commands
happen within the given session.

To resume a previous session (after creating a new one), call `Initialize` with a stored
`session_id` as an argument.

Attempt to resume an unknown session ID will transparently allocate a new session ID.

Since firmwares 1.9.4 / 2.3.4, it is possible to destroy the current session via the
`EndSession` call. The session and all its associated data is wiped from Trezor memory,
and it is impossible to resume the session. Trezor returns to the initial state and
all requests will return `InvalidSession`.

There is no explicit way to leave a session and keep its data for later resumption.
Instead, you can switch to a new session via `Initialize` with no arguments.

At the moment, both T1 and TT allow for 10 sessions to exist at the same time. When a
new session needs to be allocated and there is no space in the cache, the least recently
used session is evicted.

Sessions only exist in RAM and are lost when Trezor is disconnected.

All commands are performed in the context of the current session, until one of the
following happens:

* Host calls `EndSession`. The current session is destroyed and Trezor returns to the
  initial state.
* Host calls `Initialize` with no arguments, or with an unknown `session_id`. A new
  session is allocated and its id returned in the `Features` message.
* Host calls `Initialize` with a known `session_id`. The specified session is resumed
  and its `session_id` is returned in the `Features` message.
* Trezor is disconnected.

## Caveats

* Sessions only exist on the protobuf message level. **There is no proper isolation.**
  Multiple host applications can insert commands into each other's sessions.

  It is recommended to send `Initialize` to resume a session immediately before each
  flow. However, even this does not guarantee that another application doesn't insert
  its own `Initialize` in the time it takes you to send the next command.

  The reverse is also true: session management does not prevent other applications from
  inserting commands under the currently active session (and therefore passphrase),
  without knowledge of the session ID or the passphrase.

* It is impossible to run complex flows concurrently. If an application is in the middle
  of Bitcoin signing, sending `Initialize` will cancel the signing flow. Resuming the
  appropriate session later will _not_ continue where it left off.

## Examples

Allocate a new session, perform a command, and end the session:
```
Initialize()
--------->          Features(..., session_id=AAAA)
                       <---------
    ---<now in session AAAA>---
Request
--------->          Response
                       <---------
EndSession()
--------->          Success()
                       <---------
    ---<now in no session>---
```

Allocate two new sessions, resume the first one later:
```
Initialize()
--------->          Features(..., session_id=AAAA)
                       <---------
    ---<now in session AAAA>---
Request
--------->          Response
                       <---------

Initialize()
--------->          Features(..., session_id=BBBB)
                       <---------
    ---<now in session BBBB>---
Request
--------->          Response
                       <---------

Initialize(session_id=AAAA)
--------->          Features(..., session_id=AAAA)
                       <---------
    ---<now in session AAAA>---
Request
--------->          Response
                       <---------
```

Attempt to resume session that is not in the cache:
```
Initialize()
--------->          Features(..., session_id=AAAA)
                       <---------
    ---<now in session AAAA>---
EndSession()
--------->          Success()
                       <---------
    ---<now in no session>---
Initialize(session_id=AAAA)
--------->          Features(..., session_id=BBBB)
                       <---------
    ---<now in session BBBB>---
```
