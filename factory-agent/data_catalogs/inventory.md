# Inventory Catalog

## Dataset Name
inventory

## Description
Current stock levels of all raw materials, components, and finished goods in the factory.

## File Location
`data/inventory.csv`

## Schema

### Columns

| Column | Meaning | Data Type | Required | Primary Key | Unit |
|---|---|---|---|---|---|
| item_id | Unique identifier for each inventory item | string | yes | yes | - |
| item_name | Human-readable name of the item | string | yes | no | - |
| category | Classification category (raw_material, component, finished_good, packaging) | string | yes | no | - |
| unit | Unit of measure (metres, kg, pieces, litres) | string | yes | no | - |
| quantity_on_hand | Current available stock quantity | float | yes | no | per unit column |
| location | Warehouse storage location | string | no | no | - |
| last_updated | Date and time of last inventory update | datetime | yes | no | - |

### Primary Keys
- `item_id`

### Relationships
- `item_id` → `process.material_id` (materials used in production)
- `item_id` → `materials.material_id` (material reference data)

## Update Frequency
Daily, with real-time adjustments during production.

## Last Updated
2026-07-23

## Data Quality Status
Verified

## Example Queries
```sql
SELECT * FROM inventory WHERE quantity_on_hand < 100;
SELECT item_name, quantity_on_hand FROM inventory WHERE category = 'raw_material';
```

## Access Permissions
Read-only for agent harness. Write access restricted to Upload Service.
