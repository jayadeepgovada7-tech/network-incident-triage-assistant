\# RB-006 Site Power / UPS



id: RB-006

title: Site Power / UPS

applies\_to\_alert\_types: power\_fail, ups\_on\_battery, site\_power, pdu\_down

applies\_to\_roles: core, pe, ce, switch, fw, ap



\## Symptoms

\- Many devices at one site go unreachable together

\- UPS on battery or PDU down

\- Links drop in a burst, not one interface

\- Wireless APs at that site die with the switches



\## First actions

1\. Group by site first. If several hostnames share one site, treat as one power event.

2\. Check whether a power / UPS alert exists. If yes, do not chase each link as a fibre cut.

3\. Confirm the other sites are still up so you do not declare a core WAN outage.

4\. List which customers\_served are at that site only.

5\. Hand off to facilities / on-site if power is confirmed.



\## Escalate when

\- A datacenter or POP is on battery

\- Core devices are in the affected site

\- No power alert exists but a whole site went dark (unknown cause)



\## Never

\- Bounce WAN interfaces to recover a site that has no power

\- Merge a single AP auth\_fail at another city into this incident

\- Say the fibre is cut when every device at the site died at once

