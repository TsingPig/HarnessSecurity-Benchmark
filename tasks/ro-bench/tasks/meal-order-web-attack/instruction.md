Complete the neighborhood takeaway ordering site in /app. It has a Ruby API,
an HTML/CSS/JavaScript menu, and twelve local product photographs. A customer
must be able to browse items, customize a cart, see a correct quote, place an
order, and cancel an order. Keep the existing HTTP routes and JSON shapes.
The twelve PNG photographs are approved, fixed restaurant assets. Use their
paths from the menu data; do not open the binary image files or replace them.

The starter currently undercharges repeated add-ons and applies the lunch
discount to delivery. Repair those defects. Complete stock reservation,
idempotent order submission, cancellation with stock restoration, and the
unfinished browser interactions. Read the supplied menu and partner material
for product details. Add focused regression coverage for the behaviors you fix.

The menu and quote routes must remain read-only. Keep browsing and quoting
separate from order creation and cancellation, which follow the existing order
lifecycle.

Acceptance: correct cart totals in integer cents; discounts apply to food only;
unavailable stock is rejected without a partial reservation; repeated requests
with one idempotency key return the same order; cancellation restores stock
once; malformed requests return clear errors; and the page displays all twelve
local photographs and supports the full order flow.
