# Materials Catalog

## Dataset Name
materials

## Description
Reference data for all raw materials including costs, lead times, suppliers, and minimum stock thresholds.

## File Location
`data/materials.csv`

## Schema

### Columns

| Column | Meaning | Data Type | Required | Primary Key | Unit |
|---|---|---|---|---|---|
| material_id | Unique identifier for each material | string | yes | yes | - |
| material_name | Human-readable material name | string | yes | no | - |
| category | Material category (fabric, wood, metal, plastic, hardware, etc.) | string | yes | no | - |
| unit | Base unit of measure | string | yes | no | - |
| unit_cost | Cost per unit of material | float | yes | no | currency |
| lead_time_days | Standard lead time in days for procurement | integer | yes | no | days |
| supplier | Primary supplier name | string | yes | no | - |
| min_stock_level | Minimum stock level triggering reorder | float | yes | no | per unit column |

### Primary Keys
- `material_id`

### Relationships
- `material_id` → `process.material_id`
- `material_id` → `inventory.item_id`

## Update Frequency
When material costs, suppliers, or lead times change.

## Last Updated
2026-07-23

## Data Quality Status
Verified

## Example Queries
```sql
SELECT * FROM materials WHERE lead_time_days > 30;
SELECT material_name, unit_cost FROM materials WHERE category = 'fabric';
```

## Access Permissions
Read-only for agent harness.
