from odoo import models, api

class SaleDiscountWizard(models.TransientModel):
    _inherit = 'sale.order.discount'
    
    def action_apply_discount(self):
        order = self.env['sale.order'].browse(self._context.get('active_id'))
        lines = order.order_line.filtered(lambda l: not l.display_type)
        
        percentage = float(self.discount_percentage)
        if percentage < 1.0:  
            percentage = percentage * 100
        
        for line in lines:
            if line.price_unit:
                discount_fixed = (percentage / 100.0) * float(line.price_unit)
                
                vals = {
                    'discount_fixed': discount_fixed,
                    'discount': percentage,  # Simpan persentase yang benar
                    'primary_discount_type': 'percentage',
                    'original_discount': percentage,
                    'original_discount_fixed': discount_fixed,
                }
                line.write(vals)
        
        return super().action_apply_discount()

    @api.model
    def create(self, vals):
        return super(SaleDiscountWizard, self.with_context(
            no_recompute=True
        )).create(vals)