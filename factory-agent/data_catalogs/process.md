# Process / BOM Catalog

## Dataset Name
process

## Description
Bill of Materials (BOM) and process routing data. Defines the materials, quantities, and machines required to produce each product.

## File Location
`data/process.csv`

## Schema

### Columns

| Column | Meaning | Data Type | Required | Primary Key | Unit |
|---|---|---|---|---|---|
| product_name | Name of the product being manufactured | string | yes | composite | - |
| material_id | Unique identifier of the required material | string | yes | composite | - |
| material_name | Human-readable name of the material | string | yes | no | - |
| quantity_per_unit | Quantity of material needed per unit of product | float | yes | no | per unit column |
| unit | Unit of measure for the material quantity | string | yes | no | - |
| machine_id | Identifier of the machine used in this process step | string | yes | composite | - |
| machine_name | Human-readable name of the machine | string | yes | no | - |
| setup_time_min | Machine setup time in minutes per batch | float | yes | no | minutes |
| cycle_time_min | Machine cycle time in minutes per unit | float | yes | no | minutes |

### Primary Keys
Composite: `(product_name, material_id, machine_id)`

### Relationships
- `product_name` → `orders.product_name`
- `material_id` → `inventory.item_id`
- `material_id` → `materials.material_id`
- `machine_id` → `machines.machine_id`

## Update Frequency
When product designs or processes change.

## Last Updated
2026-07-23

## Data Quality Status
Verified

## Example Queries
```sql
SELECT * FROM process WHERE product_name = 'Chair';
SELECT material_id, SUM(quantity_per_unit) FROM process WHERE product_name = 'Table' GROUP BY material_id;
```

## Access Permissions
Read-only for agent harness.
