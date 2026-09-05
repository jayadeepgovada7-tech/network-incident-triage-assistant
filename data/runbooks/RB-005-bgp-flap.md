\# RB-005 BGP / Neighbor Flap



id: RB-005

title: BGP / Neighbor Flap

applies\_to\_alert\_types: bgp\_down, bgp\_flap, neighbor\_down, ospf\_neighbor\_down

applies\_to\_roles: core, pe, ce



\## Symptoms

\- BGP or IGP neighbor down

\- Route withdrawals toward a site

\- Often paired with link\_down on the same interface

\- Downstream high\_latency or device\_unreachable may follow



\## First actions

1\. Match the neighbor name to a device in inventory and to a topology link.

2\. Check if the underlying interface is already down. If yes, this is a symptom of the link — do not debug BGP first.

3\. If the interface is up, check hold timer, prefixes, and recent flaps.

4\. Confirm whether the backup neighbor (second core / second link) is still established.

5\. Do not clear BGP on a core or PE until backup forwarding is confirmed.



\## Escalate when

\- Both primary and backup BGP sessions are down

\- Neighbor is unknown / not in topology

\- Session flaps more than 3 times in 15 minutes with the interface up



\## Never

\- Clear BGP to "fix" a down fibre

\- Treat BGP-down as a separate incident when the same peer already has link\_down

\- Announce a routing attack without evidence in the alerts

