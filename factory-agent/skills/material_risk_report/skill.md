# Skill: Material Risk Report for All Active Orders

## Purpose
Generate a comprehensive risk report identifying material shortages across all active orders.

## Supported User Questions
- "Generate a material risk report"
- "What materials are at risk of shortage?"
- "Show all material risks across active orders"
- "Risk report for pending orders"
- "Which materials need to be reordered for active orders?"

## Required Inputs
None (operates on all active orders automatically)

## Required Data Catalogs
- `orders.md`
- `process.md`
- `inventory.md`
- `materials.md`

## Required Datasets
- `orders` (all active orders)
- `process` (BOM for every product)
- `inventory` (current stock levels)
- `materials` (cost, lead time, supplier info)

## Required Tools
- `order_tools.get_active_orders`
- `process_tools.get_bom_for_product`
- `process_tools.get_total_material_requirement`
- `inventory_tools.get_item_quantity`
- `calculation_tools.subtract`
- `calculation_tools.multiply`
- `calculation_tools.days_until`

## Execution Steps
1. Load all datasets (orders, process, inventory, materials).
2. Filter orders to `status = 'active'`.
3. For each active order:
   a. Get the product name and quantity.
   b. Get the BOM for that product.
   c. Calculate total material requirements.
   d. For each material, compare required vs. available.
   e. Record any shortages.
4. Aggregate across all orders to identify:
   - Materials that are insufficient for any order.
   - Total shortage per material.
   - Orders affected per material.
5. Enrich with material reference data (cost, lead time, supplier).
6. Calculate risk score per material based on shortage severity and lead time.

## Business Rules
- Only `status = 'active'` orders are considered.
- Risk score: `shortage_ratio × lead_time_days` (higher = more critical).
- Materials with shortage > 0 are flagged as "at risk".
- Materials below `min_stock_level` are flagged even if currently sufficient for orders.
- Output is sorted by risk score descending.

## Validation Rules
- All order IDs must be valid.
- Product names must exist in process data.
- Material IDs must exist in inventory and materials datasets.
- Quantities must be positive.

## Output Schema
```json
{
  "skill": "material_risk_report",
  "generated_at": "2026-07-23T10:00:00",
  "total_active_orders": 10,
  "materials_at_risk": [
    {
      "material_id": "FAB-001",
      "material_name": "Fabric",
      "total_required": 5000.0,
      "total_available": 4200.0,
      "total_shortage": 800.0,
      "unit": "metres",
      "affected_orders": ["ORD-1001", "ORD-1003"],
      "lead_time_days": 14,
      "supplier": "TextileCo",
      "unit_cost": 5.0,
      "risk_score": 160.0,
      "risk_level": "critical"
    }
  ],
  "summary": {
    "total_materials_at_risk": 3,
    "critical": 1,
    "high": 1,
    "medium": 1,
    "low": 0
  }
}
```

## Error Cases
- No active orders found.
- Product in order not found in process data.
- Material not found in inventory or materials reference.
- Missing supplier or cost data.

## Guardrails
- Read-only access to all datasets.
- Do not modify orders or inventory.
- Log all calculations.
- Validate all identifiers.
- Include data timestamps.

## Example Queries
- "Show me material risks"
- "Risk report"
- "What materials should I reorder?"

## Example Outputs
```
Material Risk Report — 2026-07-23
Total active orders: 10
Materials at risk: 3
- Fabric: shortage 800m, critical risk (score 160)
- Wood: shortage 200kg, high risk (score 40)
- Paint: shortage 50L, medium risk (score 15)
```

## Evaluation Cases
- No active orders → empty report.
- All materials sufficient → empty at-risk list.
- Multiple orders using same material → aggregated shortage.
- Material below min_stock → flagged regardless of orders.
