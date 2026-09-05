# Network Incident Triage Assistant

**NexusTiq24 Hackathon — Track PS07**

> A real-time Network Operations Center (NOC) triage assistant that groups alert storms, retrieves grounded runbook steps, and escalates unknown incidents without inventing fixes.

---

## 🎥 Demo Video

[**Watch the 2–3 minute demo here**](https://drive.google.com/file/d/14YP32JL-lOEPavV5mT8REk5KUC0vUs4E/view?usp=sharing)

---

## 🚨 Problem

Modern NOCs receive hundreds or thousands of alerts during a single network incident.

A single underlying failure can generate multiple alerts such as:

* Link down
* Device unreachable
* BGP neighbor down
* High latency
* Packet loss

Without correlation, engineers waste time investigating duplicate alerts instead of identifying the actual incident.

At the same time, AI-generated troubleshooting can be risky if the AI invents solutions that are not supported by the organization's runbooks.

### Our solution

The **Network Incident Triage Assistant** combines deterministic network logic with AI summarization to provide:

* Alert deduplication
* Incident correlation
* Topology-aware grouping
* Runbook-based troubleshooting
* Noise filtering
* Unknown-alert escalation
* Real-time incident monitoring

---

## 💡 Key Idea

The system follows a simple principle:

> **AI summarizes known information. It does not invent network fixes.**

The workflow is:

```text
Incoming Alerts
       ↓
Normalization
       ↓
Deduplication
       ↓
Topology + Time Correlation
       ↓
Incident Grouping
       ↓
Runbook Matching
       ↓
Gemini Summarization
       ↓
Engineer Decision
```

If no suitable runbook exists, the incident is escalated instead of generating a potentially unsafe solution.

---

## 🏗️ Architecture

```text
                ┌──────────────────┐
                │  Incoming Alerts │
                └────────┬─────────┘
                         ↓
                ┌──────────────────┐
                │ Alert Processing │
                │ & Normalization  │
                └────────┬─────────┘
                         ↓
                ┌──────────────────┐
                │ Correlation      │
                │ Engine            │
                │                  │
                │ Time + Topology  │
                └────────┬─────────┘
                         ↓
                ┌──────────────────┐
                │ Incident Groups  │
                └────────┬─────────┘
                         ↓
                ┌──────────────────┐
                │ Runbook Retrieval│
                └────────┬─────────┘
                         ↓
                ┌──────────────────┐
                │ Gemini AI        │
                │ Summarization    │
                └────────┬─────────┘
                         ↓
                ┌──────────────────┐
                │ NOC Dashboard    │
                └──────────────────┘
```

---

## 🔥 Core Features

### 1. Alert Correlation

Multiple alerts caused by the same underlying failure are grouped into a single incident.

Correlation considers:

* Device
* Device role
* Network topology
* Alert type
* Time window

This prevents alert storms from overwhelming the NOC.

---

### 2. Topology-Aware Detection

The system uses the network topology to determine whether alerts are related.

For example:

```text
Router A
   │
   │ Fibre Link
   │
Router B
   │
   ↓
Multiple downstream alerts
```

If Router A experiences a fibre failure, related BGP, reachability, and latency alerts can be grouped into the same incident.

---

### 3. Runbook-Grounded Troubleshooting

The system does not blindly ask the LLM to solve the incident.

Instead:

```text
Alert
  ↓
Identify alert type
  ↓
Identify device role
  ↓
Find matching runbook
  ↓
Extract approved troubleshooting steps
  ↓
Gemini summarizes the steps
```

This makes the AI response grounded in known operational procedures.

---

### 4. Safe Unknown-Alert Handling

If an alert does not have a matching runbook:

```text
Unknown Alert
      ↓
No Runbook Found
      ↓
Escalate to Engineer
      ↓
No Invented Fix
```

The system deliberately leaves troubleshooting steps empty rather than hallucinating an answer.

---

### 5. Noise Filtering

Not every alert represents the same incident.

For example, access-point authentication failures should not automatically be merged with a WAN outage.

The system keeps unrelated alerts separate.

---

### 6. Real-Time Inbox

Alerts can be submitted through:

```http
POST /api/ingest
```

The frontend continuously polls:

```http
GET /api/inbox
```

This allows incidents to appear on the dashboard in near real time.

---

# 🧪 Demo Scenarios

## Scenario 1 — Fibre Cut

The demo sends multiple related alerts:

* `link_down`
* `bgp_down`
* `unreachable`
* `latency`

The system:

1. Receives the alerts.
2. Correlates them using topology and time.
3. Groups them into one **Critical** incident.
4. Identifies relevant runbooks.
5. Displays grounded troubleshooting steps.

Referenced runbooks include:

* RB-001 — Link Down
* RB-002 — Device Unreachable
* RB-003 — High Latency / Packet Loss
* RB-005 — BGP / Neighbor Flap

---

## Scenario 2 — Unknown Fault

The demo generates unknown alert types such as:

* `optical_power_low`
* `fabric_crc_storm`

No matching runbook is available.

Instead of generating a random fix, the system:

```text
Runbook: Not Found
        ↓
Escalation Required
        ↓
Engineer Investigation
```

This demonstrates the system's safe-failure behavior.

---

## Scenario 3 — Authentication Noise

The system receives AP authentication failures.

These alerts are not incorrectly merged into the WAN incident.

They remain separate as **Noise**.

This demonstrates intelligent alert filtering and correlation.

---

## Scenario 4 — Multiple Sites

Alerts from different sites are generated, such as:

* Mumbai latency
* Bangalore latency
* Firewall CPU

The system keeps unrelated site incidents separate rather than creating one large false incident.

---

# 📚 Runbooks

The project contains the following runbooks:

| ID     | Runbook                    | Purpose                              |
| ------ | -------------------------- | ------------------------------------ |
| RB-001 | Link Down                  | Troubleshoot interface/link failures |
| RB-002 | Device Unreachable         | Investigate unreachable devices      |
| RB-003 | High Latency / Packet Loss | Diagnose network performance issues  |
| RB-004 | Authentication Failures    | Handle AP/authentication issues      |
| RB-005 | BGP / Neighbor Flap        | Troubleshoot BGP problems            |
| RB-006 | Power / Site               | Investigate power/site failures      |
| RB-007 | DNS / Resolver             | Troubleshoot DNS issues              |

---

# 🤖 AI Safety Design

A major design decision is separating **deterministic logic** from **AI generation**.

### Python handles:

* Alert normalization
* Deduplication
* Correlation
* Topology analysis
* Runbook matching
* Incident classification
* Escalation decisions

### Gemini handles:

* Summarizing matched information
* Creating concise triage notes
* Presenting the available troubleshooting information clearly

### Gemini does NOT decide:

* Which alerts belong together
* Which runbook should be used
* Whether an unknown alert has a solution
* What an unsupported network fix should be

This reduces the risk of hallucinated operational instructions.

---

# 🛠️ Tech Stack

### Backend

* Python 3.11
* FastAPI
* Uvicorn

### AI

* Google Gemini
* `gemini-3.0-flash`

### Frontend

* HTML
* CSS
* Vanilla JavaScript

### Data

* JSON
* Markdown runbooks
* In-memory inbox

---

# 📁 Project Structure

```text
network-incident-triage/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── src/
│   ├── config.py
│   ├── data_loader.py
│   ├── correlator.py
│   ├── runbooks.py
│   ├── gemini_client.py
│   ├── triage.py
│   ├── inbox.py
│   └── models.py
│
├── data/
│   ├── devices.json
│   ├── topology.json
│   ├── sample_alerts.json
│   │
│   └── runbooks/
│       ├── RB-001.md
│       ├── RB-002.md
│       ├── RB-003.md
│       ├── RB-004.md
│       ├── RB-005.md
│       ├── RB-006.md
│       └── RB-007.md
│
└── frontend/
    ├── index.html
    ├── app.js
    └── style.css
```

---

# ⚙️ Installation

Clone the repository and enter the project directory.

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 🔑 Gemini API Key

Set your Gemini API key as an environment variable.

### Windows CMD

```cmd
set GEMINI_API_KEY=your-key-here
```

### Windows PowerShell

```powershell
$env:GEMINI_API_KEY="your-key-here"
```

### Linux / macOS

```bash
export GEMINI_API_KEY=your-key-here
```

Then start the application:

```bash
python app.py
```

The application will start the FastAPI server.

---

# 🔧 Configuration

The Gemini model can optionally be configured using:

```bash
GEMINI_MODEL
```

Default:

```text
gemini-3.0-flash
```

If Gemini is unavailable, the application still provides the rule-based runbook steps.

---

# 🔒 Security

**Never commit your Gemini API key to GitHub.**

Use environment variables instead:

```text
GEMINI_API_KEY=your-key-here
```

Make sure `.env` and other secret files are included in `.gitignore`.

---

# 🎯 Why This Approach?

Traditional alert systems often produce:

```text
100 alerts → 100 notifications
```

Our system aims to produce:

```text
100 alerts
     ↓
Correlation
     ↓
1 meaningful incident
     ↓
Relevant runbook
     ↓
Actionable triage information
```

The result is reduced alert fatigue and faster incident understanding.

---

# 🚀 Future Improvements

Potential future enhancements include:

* Persistent incident storage
* Historical incident analytics
* More advanced topology correlation
* SNMP/syslog integration
* Ticketing-system integration
* Slack/Teams notifications
* Engineer feedback loops
* Runbook version management
* Role-based access control
* Production-grade authentication
* Distributed event processing

---

# 🏆 Hackathon Highlights

### What makes the solution different?

**Deterministic first, AI second.**

The system does not rely on an LLM to make every decision.

Instead, it combines:

* Network topology
* Time-based correlation
* Deterministic rules
* Grounded runbooks
* AI summarization
* Safe escalation

This provides a practical balance between **automation and operational safety**.

---

# 👨‍💻 Team

**NexusTiq24 Hackathon**

**Track:** PS07

**Project:** Network Incident Triage Assistant

---

## 📌 Summary

The Network Incident Triage Assistant helps NOC engineers handle alert storms by:

✅ Correlating related alerts
✅ Reducing duplicate incidents
✅ Using network topology
✅ Retrieving grounded runbook steps
✅ Using Gemini for controlled summarization
✅ Filtering unrelated noise
✅ Escalating unknown alerts safely
✅ Providing a real-time incident dashboard

> **Correlate. Ground. Summarize. Escalate safely.**
