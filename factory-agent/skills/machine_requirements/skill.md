# Skill: Machine Requirements for One Order

## Purpose
Calculate the machine time (setup and cycle) required to fulfil a specific customer order.

## Supported User Questions
- "What machines are needed for order ORD-1001?"
- "How much machine time is required for order ORD-1001?"
- "What are the machine requirements for ORD-1001?"
- "Calculate machine hours for order ORD-1001"

## Required Inputs
- `order_id`: The order identifier to check

## Required Data Catalogs
- `orders.md`
- `process.md`
- `machines.md`

## Required Datasets
- `orders` (to get product name and quantity)
- `process` (to get BOM with machine IDs and times)
- `machines` (to get machine names, rates, and status)

## Required Tools
- `order_tools.get_order_product_quantity`
- `process_tools.get_machines_for_product`
- `machine_tools.calculate_machine_hours`
- `machine_tools.get_machine`
- `calculation_tools.multiply`

## Execution Steps
1. Load the `orders` dataset.
2. Look up the order by `order_id` to get `product_name` and `quantity`.
3. Validate the order exists and has status `active`.
4. Load the `process` dataset.
5. Get the machines required for the product from the BOM.
6. For each machine, extract `setup_time_min` and `cycle_time_min`.
7. Calculate total machine hours: setup + (cycle × quantity).
8. Load the `machines` dataset.
9. Get each machine's current status and hourly rate.
10. Calculate estimated cost.

## Business Rules
- Only active orders are eligible.
- Machine time = setup_time + (cycle_time × order_quantity).
- Machine time is reported in hours.
- If a machine is in `maintenance` or `offline` status, a warning is raised.
- Cost estimation uses `hourly_rate × total_hours`.

## Validation Rules
- `order_id` must exist in orders.
- Order must be `active`.
- Product must exist in process data.
- Machine IDs must exist in machines dataset.
- Times must be positive numbers.
- Quantities must be positive.

## Output Schema
```json
{
  "skill": "machine_requirements",
  "order_id": "ORD-1001",
  "product_name": "Chair",
  "order_quantity": 100,
  "machines": [
    {
      "machine_id": "CUT-001",
      "machine_name": "Cutting Machine",
      "status": "operational",
      "setup_hours": 0.5,
      "cycle_hours": 8.33,
      "total_hours": 8.83,
      "hourly_rate": 50.0,
      "estimated_cost": 441.5
    }
  ],
  "total_hours": 8.83,
  "total_cost": 441.5
}
```

## Error Cases
- Order ID not found.
- Order not active.
- Product not in process data.
- Machine ID not in machines dataset.
- Missing time data (setup_time_min, cycle_time_min).

## Guardrails
- Read-only data access.
- Validate all identifiers.
- Log every calculation.
- Warn about unavailable machines.

## Example Queries
- "What machinery is required for order ORD-1001?"
- "Machine time estimate for ORD-1001"

## Example Outputs
```
Order: ORD-1001 (Chair, 100 pieces)
Machine: Cutting Machine (CUT-001) — 8.83 hrs @ $50/hr = $441.50
Total machine time: 8.83 hours
Total estimated cost: $441.50
```

## Evaluation Cases
- Active order with valid machines → correct hours.
- Machine in maintenance → output with warning.
- Order not found → error.
