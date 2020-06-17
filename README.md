# printer_forwarder
Forwards printer traffic with callbacks and packet inspection

## Why?
**Printer On Demand**

This tools listens on a tcp-port for incoming print requests and
forwards them to the destination in the arguments. So far so good.

But before forwarding it, it calls a PrinterController to "activate"
the printer first, think WakeOnLan or a Relais to power the printer on
first, so that it isn't idle (and making noise / drawing power). After
the job and a timeout, it deactivates the printer again.

But it also inspects the requests if they are print-requests or
some random data or TCP-Scans. Since you don't want clicking relais and
waking printers just because some network-scan. Currently trivially
checks for some PrintJet arguments.

## TODO:
- relais implementation via GPIO of Raspberry Pi
