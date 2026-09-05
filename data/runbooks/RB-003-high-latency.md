\# RB-003 High Latency / Packet Loss



id: RB-003

title: High Latency / Packet Loss

applies\_to\_alert\_types: high\_latency, packet\_loss, jitter

applies\_to\_roles: core, pe, ce, switch



\## Symptoms

\- Round-trip time well above baseline

\- Packet loss on WAN or last-mile links

\- Users report slowness, not a hard outage

\- Often appears a few seconds after an upstream link\_down



\## First actions

1\. Note the value and the interface / destination in the alert.

2\. Check whether an upstream neighbor has link\_down or device\_unreachable in the same window.

3\. If upstream is down, treat latency as a symptom — do not tune QoS yet.

4\. If upstream is up, check interface errors, drops, and utilisation on the path.

5\. Compare primary vs backup path latency before changing routing.



\## Escalate when

\- Latency hits a core or PE path and backup is also degraded

\- Loss stays above 2% for more than 15 minutes with no upstream alarm

\- Cause is not covered by this runbook (for example optical-power-low with no other alarms)



\## Never

\- Bounce a core link to "clear latency"

\- Blame the branch CE before checking the WAN toward it

\- Invent a congestion story when a link is already down

