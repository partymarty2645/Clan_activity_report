---
description: Run the full Clan Stats Pipeline (Harvest -> Report -> Export -> Verify)
---

# Run Pipeline

1. Run the main automation script
// turbo
python main.py

2. Verify the output was created
python scripts/verify_json_msgs.py
