\# RB-002 Device Unreachable



id: RB-002

title: Device Unreachable

applies\_to\_alert\_types: device\_unreachable, node\_down, ping\_fail

applies\_to\_roles: core, pe, ce, switch, fw



\## Symptoms

\- NMS cannot ping the device

\- SNMP timeout

\- Alerts from neighbors about this device going down

\- Often follows a link\_down on the path toward this device



\## First actions

1\. Confirm the alert is still active (not a one-probe blip).

2\. Ping from a second source (another site / mgmt VRF), not only the NMS.

3\. Check upstream neighbor: is the interface toward this device down?

4\. If upstream link is down, treat this as a path failure — do not reboot the unreachable box yet.

5\. If upstream is up and device is still dark, check site power / console / last known CPU and memory.



\## Escalate when

\- Device role is core or PE

\- Device stays unreachable more than 10 minutes

\- Backup path is also affected

\- Device is not in inventory



\## Never

\- Reload a box you cannot reach

\- Open a hardware ticket before checking the upstream link

\- Merge this with unrelated Wi-Fi auth failures

