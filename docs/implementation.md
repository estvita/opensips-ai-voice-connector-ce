# AI Voice Connector - Community Edition - Implementation

The engine is implemented in Python using
[Asyncio](https://docs.python.org/3/library/asyncio.html) co-routines in order
to ensure I/O operations efficiency.

## OpenSIPS

Communication to OpenSIPS is being done over Datagram. The engine subscribes
to OpenSIPS over the [MI
Datagram](https://opensips.org/docs/modules/3.6.x/mi_datagram.html) interface
and exposes an [Event
Datagram](https://opensips.org/docs/modules/3.6.x/event_datagram.html) socket
for the
[E_UA_SESSON](https://opensips.org/docs/modules/3.6.x/b2b_entities#event_E_UA_SESSION)
event.

## AI Engine

The engine requires each AI Flavor to implement the [AIEngine](../src/ai.py)
abstract class.

## Codecs

The engine needs the ability to perform decapsulation and framing for the
codecs that are being used in a call. It is currently able to handle the
following codecs:

* g711 mulaw - PCMU
* g711 alaw - PCMA
* Opus

New codecs can be easily handled by implementing the
[GenericCodec](../src/codec.py) class.

Particularities of each AI engine is treated by its implementation.
