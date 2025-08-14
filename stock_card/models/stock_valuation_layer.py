from odoo import api, fields, models

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Partner',
        related='stock_move_id.picking_id.partner_id', 
        store=True,
        readonly=True
    )
    
    credit = fields.Monetary(
        string='Value Credit',
        compute='_compute_credit_debit',
        store=True,
        currency_field='currency_id'
    )
    
    debit = fields.Monetary(
        string='Value Debit',
        compute='_compute_credit_debit',
        store=True,
        currency_field='currency_id'
    )

    quantity_credit = fields.Float(
        string='Quantity Credit',
        compute='_compute_quantity_credit_debit',
        store=True,
        digits='Product Unit of Measure'
    )

    quantity_debit = fields.Float(
        string='Quantity Debit',
        compute='_compute_quantity_credit_debit',
        store=True,
        digits='Product Unit of Measure'
    )

    # === Running Balance (tanpa store) ===
    running_quantity = fields.Float(
        string='Balance Quantity',
        compute='_compute_running_balance',
        digits='Product Unit of Measure'
    )
    running_value = fields.Monetary(
        string='Balance Value',
        compute='_compute_running_balance',
        currency_field='currency_id'
    )

    @api.depends('value')
    def _compute_credit_debit(self):
        for record in self:
            if record.value > 0:
                record.debit = record.value
                record.credit = 0.0
            else:
                record.debit = 0.0
                record.credit = abs(record.value)

    @api.depends('quantity')
    def _compute_quantity_credit_debit(self):
        for record in self:
            if record.quantity > 0:
                record.quantity_debit = record.quantity
                record.quantity_credit = 0.0
            else:
                record.quantity_debit = 0.0
                record.quantity_credit = abs(record.quantity)

    @api.depends('company_id', 'product_id', 'create_date', 'value', 'quantity')
    def _compute_running_balance(self):
        """
        Hitung saldo berjalan (qty & value) per company+product, terurut by (create_date, id).
        Non-stored agar aman dari isu dependensi lintas-record.
        """
        if not self:
            return
        cr = self.env.cr

        # Kumpulkan partisi yang relevan agar query efisien
        company_ids = tuple(set(self.mapped('company_id').ids)) or (0,)
        product_ids = tuple(set(self.mapped('product_id').ids)) or (0,)
        target_ids = tuple(self.ids) or (0,)

        # Hitung window lalu ambil hanya baris target (filter di luar subquery)
        cr.execute("""
            SELECT id, run_qty, run_val
            FROM (
                SELECT s.id,
                       SUM(s.quantity) OVER (
                           PARTITION BY s.company_id, s.product_id
                           ORDER BY s.create_date, s.id
                       ) AS run_qty,
                       SUM(s.value) OVER (
                           PARTITION BY s.company_id, s.product_id
                           ORDER BY s.create_date, s.id
                       ) AS run_val
                FROM stock_valuation_layer s
                WHERE s.company_id IN %s
                  AND s.product_id IN %s
            ) x
            WHERE x.id IN %s
        """, (company_ids, product_ids, target_ids))
        result = dict((row[0], (row[1] or 0.0, row[2] or 0.0)) for row in cr.fetchall())

        for rec in self:
            rq, rv = result.get(rec.id, (0.0, 0.0))
            rec.running_quantity = rq
            rec.running_value = rv
