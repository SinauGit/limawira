from odoo import models


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def compute_landed_cost(self):
        if self.env.user.has_group('stock.group_stock_manager'):
            return super().compute_landed_cost()
        return super(StockLandedCost, self.sudo()).compute_landed_cost()

    def button_validate(self):
        if self.env.user.has_group('stock.group_stock_manager'):
            return super().button_validate()
        return super(StockLandedCost, self.sudo()).button_validate()
