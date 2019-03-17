---
name: Bug
about: Report a bug
title: "[OS] title"
labels: 'bug'
assignees: 'giampaolo'

---
**Platform**
* { OS version }     (also add appropriate OS issue label (linux, windows, ...))
* { psutil version }  (use "pip show psutil")

**Bug description**
{ a clear and concise description of what the bug is }

```
traceback message (if any)
```

```python
code to reproduce the problem (if any)
```

**Test results**
```
output of `python -c psutil.tests` (failures only, not full result)
```
{ you may want to do this in order to discover other issues affecting your platform }
{ if failures look unrelated with the issue at hand open another ticket }
