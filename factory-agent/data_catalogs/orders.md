# Orders Catalog

## Dataset Name
orders

## Description
Customer orders with product details, quantities, due dates, and current status.

## File Location
`data/orders.csv`

## Schema

### Columns

| Column | Meaning | Data Type | Required | Primary Key | Unit |
|---|---|---|---|---|---|
| order_id | Unique identifier for each customer order (e.g. ORD-1001) | string | yes | yes | - |
| product_name | Name of the product to be manufactured | string | yes | no | - |
| quantity | Order quantity | float | yes | no | per unit column |
| unit | Unit of measure for the product | string | yes | no | - |
| due_date | Customer-requested delivery date | datetime | yes | no | - |
| status | Order status (active, completed, cancelled, on_hold) | string | yes | no | - |
| priority | Priority level (urgent, high, normal, low) | string | yes | no | - |
| customer | Customer name or identifier | string | no | no | - |

### Primary Keys
- `order_id`

### Relationships
- `product_name` → `process.product_name` (bill of materials)

## Update Frequency
Real-time as orders are created, modified, or fulfilled.

## Last Updated
2026-07-23

## Data Quality Status
Verified

## Example Queries
```sql
SELECT * FROM orders WHERE status = 'active' AND priority = 'urgent';
SELECT product_name, SUM(quantity) FROM orders WHERE status = 'active' GROUP BY product_name;
```

## Access Permissions
Read-only for agent harness.
