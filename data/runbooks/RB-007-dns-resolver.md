\# RB-007 DNS / Resolver Failures



id: RB-007

title: DNS / Resolver Failures

applies\_to\_alert\_types: dns\_fail, resolver\_down, nxdomain\_spike

applies\_to\_roles: fw, core, pe



\## Symptoms

\- DNS lookup failures

\- Resolver timeout

\- Clients online but apps fail to resolve names

\- Usually not the same as a link\_down



\## First actions

1\. Confirm whether WAN / core links are up. If the path is down, DNS is a symptom.

2\. Check which resolver IP is in the alert and whether it is in inventory.

3\. Try a second resolver before restarting the first.

4\. Do not change routing to fix DNS.

5\. If only one branch reports DNS and the WAN is up, check the local CE/firewall DNS setting.



\## Escalate when

\- Resolver is unknown or has no runbook coverage beyond this

\- Both resolvers fail

\- DNS fails with no matching alert type in any runbook



\## Never

\- Restart a core router for a DNS ticket

\- Group DNS with Wi-Fi auth failures unless the same firewall is alerting

