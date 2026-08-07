# -*- coding: utf-8 -*-
{
    'name': 'Sale Down Payment Auto Final Invoice',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Automatically create the final (deduction) invoice when a 100% percentage down payment invoice is created',
    'description': """
Sale Down Payment Auto Final Invoice
=====================================

Problem
-------
When a Sale Order is invoiced using "Down Payment (Percentage)" set to 100%,
the order's Invoice Status remains "To Invoice" instead of "Fully Invoiced".
This happens because the down payment invoice line is a generic down payment
product, not tied to the quantity of the original order lines, so
`qty_invoiced` on the real order lines is never updated.

What this module does
----------------------
After a percentage down payment invoice is created, this module checks the
cumulative amount already invoiced via down payment lines on the order. If
that cumulative amount has reached (or exceeded) the order's untaxed total,
it automatically triggers the creation of the final (regular) invoice, which
deducts the existing down payments. The resulting invoice is created in
draft state, with an amount close to zero, and sets `qty_invoiced` on the
real order lines, making the order's Invoice Status correctly show
"Fully Invoiced".

Scope
-----
- Only applies to the "Down Payment (Percentage)" invoicing method.
- Down Payment (Fixed Amount) and Regular/Delivered invoicing are untouched.
- Cumulative down payments across multiple invoices on the same order are
  taken into account.
- Credit notes issued against down payment invoices are not accounted for
  in the cumulative calculation (by design).
""",
    'author': 'limawira',
    'license': 'LGPL-3',
    'depends': ['sale'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
