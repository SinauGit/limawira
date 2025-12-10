                                     
                                                                   

from odoo import fields
from odoo.tests import common


class TestPurchaseRequestProcurement(common.TransactionCase):
    def setUp(self):
        super().setUp()

                            
        self.pr_model = self.env["purchase.request"]
        self.prl_model = self.env["purchase.request.line"]
        self.product_uom_model = self.env["uom.uom"]
        self.location = self.env.ref("stock.stock_location_stock")
        self.customer_location = self.env.ref("stock.stock_location_customers")

                                 
        self.product_1 = self.env.ref("product.product_product_16").copy()
        self.product_1.purchase_request = True
        self.route_buy = self.env.ref("purchase_stock.route_warehouse0_buy")
        self.rule_buy = self.route_buy.rule_ids.filtered(
            lambda rule: rule.location_dest_id == self.location
        )
                         
        self.supplier = self.env["res.partner"].create(
            {"name": "Supplier", "is_company": True, "company_id": False}
        )

                                   
        self.product_1.write(
            {
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.supplier.id,
                            "price": 100.0,
                            "company_id": False,
                        },
                    )
                ]
            }
        )

    def _procurement_group_run(self, origin, product, qty):
                                                    
        move = self.env["stock.move"].create(
            {
                "reservation_date": fields.Datetime.now(),
                "location_dest_id": self.customer_location.id,
                "location_id": self.location.id,
                "name": product.name,
                "origin": origin,
                "procure_method": "make_to_order",
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": qty,
                "route_ids": [(4, self.route_buy.id)],
            }
        )
        move._action_confirm()
        return move

    def test_orderpoint(self):
                                                                                     
        qty = 5
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": __name__,
                "warehouse_id": self.env.ref("stock.warehouse0").id,
                "location_id": self.location.id,
                "product_id": self.product_1.id,
                "product_min_qty": 1,
                "product_max_qty": qty,
            }
        )
        self.env["procurement.group"].run_scheduler()
        self.assertEqual(
            self.env["purchase.request"]
            .search([("product_id", "=", self.product_1.id)])
            .line_ids.product_qty,
            qty,
        )
        self.assertEqual(orderpoint.qty_forecast, qty)

    def test_procure_purchase_request(self):
                                                            
        move = self._procurement_group_run(
            "Test Purchase Request Procurement",
            self.product_1,
            10,
        )
        self.assertTrue(move.created_purchase_request_line_id)
        pr = move.created_purchase_request_line_id.request_id
        self.assertTrue(pr.to_approve_allowed)
        self.assertEqual(pr.origin, "Test Purchase Request Procurement")

                                                                     
        activity = self.env.ref("mail.mail_activity_data_todo")
        self.env["mail.activity"].search(
            [("activity_type_id", "=", activity.id)]
        ).unlink()
        self.assertFalse(move.created_purchase_request_line_id.request_id.activity_ids)
        move._action_cancel()
        self.assertTrue(move.created_purchase_request_line_id.request_id.activity_ids)

    def test_procure_purchase_request_with_fixed_group(self):
\
\
\
\
\
           
        group = self.env["procurement.group"].create({})
        self.rule_buy.write(
            {
                "group_id": group.id,
                "group_propagation_option": "fixed",
            }
        )
        move = self._procurement_group_run(
            False,
            self.product_1,
            10,
        )
        pr = move.created_purchase_request_line_id.request_id
        self.assertEqual(pr.group_id, group)

                                                      
        move2 = self._procurement_group_run(
            "Test Origin",
            self.product_1,
            10,
        )
        pr2 = move2.created_purchase_request_line_id.request_id
        self.assertEqual(pr2, pr)

                                                       
        pr.group_id = self.env["procurement.group"].create({})

                                                                    
        move3 = self._procurement_group_run("Test with group", self.product_1, 10)
        pr3 = move3.created_purchase_request_line_id.request_id
        self.assertEqual(pr3.group_id, group)
        self.assertNotEqual(pr3, pr)

    def test_origin(self):
                                                                                  
        move = self._procurement_group_run("Test Origin", self.product_1, 10)
        pr = move.created_purchase_request_line_id.request_id
        self.assertEqual(pr.origin, "Test Origin")

                                                                 
        move2 = self._procurement_group_run("Test, Split", self.product_1, 10)
        self.assertEqual(move2.created_purchase_request_line_id.request_id, pr)
        self.assertEqual(pr.origin, "Test Origin, Test, Split")

                                                                        
        move3 = self._procurement_group_run(False, self.product_1, 10)
        self.assertEqual(move3.created_purchase_request_line_id.request_id, pr)
        self.assertEqual(pr.origin, "Test Origin, Test, Split")

                                                                           
        move4 = self._procurement_group_run("Split", self.product_1, 10)
        self.assertEqual(move4.created_purchase_request_line_id.request_id, pr)
        self.assertEqual(pr.origin, "Test Origin, Test, Split")
