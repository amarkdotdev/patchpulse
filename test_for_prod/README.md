# PatchPulse Production Test Environment

This directory contains everything needed to test PatchPulse end-to-end with a local Kubernetes cluster.

## Quick Start

```bash
# 1. Start local cluster (k3d - lightweight, fast)
./setup_cluster.sh

# 2. Deploy PatchPulse
./deploy_patchpulse.sh

# 3. Trigger test events
./trigger_test_events.sh

# 4. View results
open http://localhost:8000/ui
```

## Requirements

- Docker Desktop running
- kubectl installed
- k3d installed (`brew install k3d` or see https://k3d.io)

## What Gets Tested

1. Agent collects cluster signals
2. Git integration detects PR changes
3. Policy engine evaluates risk
4. Decisions are created and displayed
5. Slack notifications (if configured)

