---
description: Verify System Integrity (JSON, Drive, Outliers)
---
1. Quick DB Health Check
// turbo
python scripts/db_health_check.py

2. Audit Google Drive
// turbo
python scripts/audit_drive.py

3. Full Validation Report
// turbo
python scripts/generate_validation_report.py --format text
