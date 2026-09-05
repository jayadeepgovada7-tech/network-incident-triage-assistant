\# RB-004 Repeated Authentication Failures



id: RB-004

title: Repeated Authentication Failures

applies\_to\_alert\_types: auth\_fail, authentication\_failure, radius\_reject, 8021x\_fail

applies\_to\_roles: ap, switch, fw



\## Symptoms

\- Many failed logins or 802.1X rejects on one AP or switch

\- Burst of the same username or MAC

\- Usually local to one floor or one branch

\- Can be a bad client, a wrong PSK, or a real RADIUS outage



\## First actions

1\. Count how many failures and on how many devices.

2\. If it is one AP and a low customer count, treat as noise or P4 unless it grows.

3\. Check whether a AAA / RADIUS server is also alerting. If not, do not declare an AAA outage.

4\. Do not merge these alerts with WAN link\_down or core unreachable events at another site.

5\. If many APs or a firewall show auth\_fail at once, then check RADIUS reachability.



\## Escalate when

\- Auth failures hit several sites at the same time

\- A RADIUS or AAA device itself is alerting

\- Failures continue after the local AP is isolated



\## Never

\- Group a single AP auth storm into a WAN fibre incident

\- Reset core routing because Wi-Fi clients cannot log in

\- Invent a security breach from one noisy AP

