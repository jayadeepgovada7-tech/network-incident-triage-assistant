\# RB-001 Link Down / Interface Down



id: RB-001

title: Link Down / Interface Down

applies\_to\_alert\_types: link\_down, interface\_down, if\_down

applies\_to\_roles: core, pe, ce



\## Symptoms

\- Interface protocol down

\- Neighbor loss on the same link

\- CRC / error burst then silence

\- Downstream devices report high latency or unreachable shortly after



\## First actions

1\. Confirm interface admin status and last flap time on the local device.

2\. Check far-end device reachability (mgmt VRF ping).

3\. If both ends down → suspect fibre or power, not config.

4\. If one end up → check SFP, light levels, error counters.

5\. If the device is core or PE: confirm the backup path is forwarding before any bounce.



\## Escalate when

\- Both primary and backup paths are down

\- customers\_served is greater than 500

\- Interface keeps flapping after the first check



\## Never

\- Bounce a core interface without confirming backup forwarding

\- Invent a root cause that is not in the alerts

