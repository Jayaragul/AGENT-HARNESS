# Machines Catalog

## Dataset Name
machines

## Description
Factory machine inventory including specifications, status, maintenance schedules, and operational costs.

## File Location
`data/machines.csv`

## Schema

### Columns

| Column | Meaning | Data Type | Required | Primary Key | Unit |
|---|---|---|---|---|---|
| machine_id | Unique identifier for each machine (e.g. SAW-001) | string | yes | yes | - |
| machine_name | Human-readable machine name | string | yes | no | - |
| type | Machine type/classification (cutting, assembly, finishing, packaging) | string | yes | no | - |
| status | Current operational status (operational, maintenance, offline) | string | yes | no | - |
| location | Factory floor location | string | no | no | - |
| hourly_rate | Operating cost per hour | float | yes | no | currency/hour |
| maintenance_last | Date of last scheduled maintenance | datetime | yes | no | - |
| maintenance_next | Date of next scheduled maintenance | datetime | yes | no | - |

### Primary Keys
- `machine_id`

### Relationships
- `machine_id` → `process.machine_id`

## Update Frequency
Weekly, or when machine status changes.

## Last Updated
2026-07-23

## Data Quality Status
Verified

## Example Queries
```sql
SELECT * FROM machines WHERE status = 'operational';
SELECT * FROM machines WHERE maintenance_next < '2026-08-01';
```

## Access Permissions
Read-only for agent harness.
