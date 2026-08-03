# Skill: Material Sufficiency Check

## Purpose
Determine whether sufficient materials are available in inventory to fulfill a specific customer order.

## Supported User Questions
- "Do we have enough fabric for order ORD-1001?"
- "Can we fulfil order ORD-1001 with current stock?"
- "Is there sufficient material for order ORD-1001?"
- "Check material availability for order ORD-1001"
- "Material sufficiency check for ORD-1001"

## Required Inputs
- `order_id`: The order identifier to check (e.g., ORD-1001)

## Required Data Catalogs
- `orders.md`
- `process.md`
- `inventory.md`

## Required Datasets
- `orders` (to get product name and quantity)
- `process` (to get BOM materials and quantities)
- `inventory` (to get current stock levels)

## Required Tools
- `order_tools.get_order_product_quantity`
- `process_tools.get_materials_for_product`
- `process_tools.get_total_material_requirement`
- `inventory_tools.get_item_quantity`
- `calculation_tools.subtract`

## Execution Steps
1. Load the `orders` dataset.
2. Look up the order by `order_id` to get `product_name` and `quantity`.
3. Validate the order exists and has status `active`.
4. Load the `process` dataset.
5. Get the BOM for the product to determine required materials and quantities per unit.
6. Calculate total material requirement: `quantity_per_unit * order_quantity`.
7. Load the `inventory` dataset.
8. For each required material, look up `quantity_on_hand`.
9. Compare required vs. available.
10. Determine if there is a shortage or sufficiency for each material.

## Business Rules
- Only orders with `status = 'active'` are eligible.
- Partial fulfilment: if at least one material is short, the entire order cannot be fulfilled.
- Materials with zero or negative stock are treated as insufficient.
- The check is point-in-time based on current inventory snapshot.

## Validation Rules
- `order_id` must match pattern `ORD-\d+` or similar.
- Order must exist in the dataset.
- Order status must be `active`.
- Quantities must be positive numbers.
- Units must match between BOM and inventory.
- Material IDs in BOM must exist in inventory.

## Output Schema
```json
{
  "skill": "material_sufficiency",
  "order_id": "ORD-1001",
  "product_name": "Chair",
  "order_quantity": 100,
  "order_unit": "pieces",
  "overall_status": "insufficient",
  "materials": [
    {
      "material_id": "FAB-001",
      "material_name": "Fabric",
      "required": 500.0,
      "available": 420.0,
      "shortage": 80.0,
      "unit": "metres",
      "status": "insufficient"
    }
  ],
  "data_last_updated": "2026-07-23T09:30:00",
  "recommendation": "Purchase or reallocate 80.0 metres of Fabric."
}
```

## Error Cases
- Order ID not found.
- Order status is not active.
- Product not found in process data.
- Material ID in BOM not found in inventory.
- Unit mismatch between BOM and inventory.
- Missing columns in any required dataset.

## Guardrails
- Read-only access to inventory, orders, and process data.
- Do not modify any quantities.
- Log every lookup and calculation.
- Validate all identifiers before lookup.
- Report if inventory data is stale (>7 days).

## Example Queries
- "Check material sufficiency for ORD-1001"
- "Do we have enough wood for order ORD-1002?"
- "Can we produce order ORD-1003 with current stock?"

## Example Outputs
```
Order: ORD-1001 (Chair, 100 pieces)
Status: INSUFFICIENT
Material Fabric: need 500m, have 420m, shortage 80m
Material Wood: need 200kg, have 350kg, sufficient
```

## Evaluation Cases
- One material insufficient → overall insufficient.
- All materials sufficient → overall sufficient.
- Order not found → error.
- Order cancelled → skip.
- Negative stock → insufficient.
