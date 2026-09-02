# FalconPy Developer Lab

Hands-on notebooks for the CrowdStrike FalconPy SDK developer lab. Everything
runs in your browser.

## What is FalconPy?

[FalconPy](https://developer.crowdstrike.com/sdks/python/) is the official
CrowdStrike Python SDK. It gives you a Pythonic interface to every
CrowdStrike Falcon API service collection — Host management, Real Time
Response, Vulnerability Management, and more.

## The Case

A host just threw a privilege-escalation alert. Notebooks 01–05 walk that
incident end to end, live against a real tenant — from the alert that
started it to the fix that closes it.

| # | Notebook | Topic |
|---|----------|-------|
| 00 | Welcome | Start here |
| 00a | JupyterHub Intro | Tour of the JupyterLab environment (optional but recommended) |
| 00b | Notebook Intelligence Intro | Tour of the in-notebook AI assistant, if enabled (optional) |
| 01 | Triage the Queue | Find the alert that started it all |
| 02 | Scope the Host | Understand what's actually going on |
| 03 | Assess Exposure | Check the host's exposure and vulnerability status |
| 04 | Get Remediation | Pull remediation guidance for what you found |
| 05 | Close the Case | Wrap up and document the fix |
| 06 | AI Assistants with FalconPy | Use the AI assistant alongside the SDK, if enabled |
| 07 | Exercises | Extra practice once you've finished the case |

## Access the Lab

Your instructor will hand you a printed card with an access code in
`FALCON-XXXX-XXXX` format. Use that code as **both your username and
password**.

| Environment | URL |
|---|---|
| **Primary** | http://falconpy-lab-alb-1692897027.us-east-1.elb.amazonaws.com |
| **Standby (overflow)** | http://falconpy-lab-standby-alb-1815909331.us-east-1.elb.amazonaws.com |

Use the **Primary** URL unless your instructor hands you a card marked
**STANDBY** — that means you're on the overflow environment, which is a
separate, fully independent copy of the same lab.

> **Note:** these links are only reachable from the event's Wi-Fi network.
> If a page won't load, double-check you're connected to the venue network,
> not your phone's cellular connection or a hotel/home network.
>
> These environments are temporary and torn down after the event — the URLs
> above will stop working once the lab concludes.

## Getting Started

1. Open the lab URL from the table above and log in with your access code
2. New to JupyterLab? Open `00a_jupyterhub_intro.ipynb` for a quick tour
3. If the AI assistant is enabled, open `00b_notebook_intelligence_intro.ipynb`
4. Open `01_triage_the_queue.ipynb` to begin the case
5. Work through each notebook at your own pace, carrying your findings
   forward into the next
6. Finished early? Try `06_ai_assistants_with_falconpy.ipynb` or the extra
   exercises in `07_exercises.ipynb`

## Your Environment

Pre-configured with:

- Python 3.11
- `crowdstrike-falconpy` (latest)
- `pandas`, `rich`, `matplotlib`, `requests`
- Falcon API credentials already loaded — no setup, just run the cells

Notebooks fall back to saved sample responses if API credentials are ever
unavailable, so you can keep working either way.

## Resources

- [FalconPy on Devloper Portal](https://developer.crowdstrike.com/sdks/python/)
- [FalconPy on GitHub](https://github.com/CrowdStrike/falconpy)
- [CrowdStrike Developer Portal](https://developer.crowdstrike.com)
