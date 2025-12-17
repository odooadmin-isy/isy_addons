# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        self.isy_card_payment(order, ui_paymentline)
        return super()._payment_fields(order, ui_paymentline)

    def isy_card_payment(self, order, ui_paymentline):
        payment_method_id = ui_paymentline['payment_method_id']
        if self.env['pos.payment.method'].sudo().search([('id', '=', payment_method_id)], limit=1).use_card:
            partner = order.partner_id
            amount = ui_paymentline['amount']
            if partner.card_balance >= amount:
                partner.card_balance -= amount
            else:
                raise UserError(f"Insufficient card balance for customer {partner.name}. Required: {amount}, Available: {partner.card_balance}")

class PosOrderLineActionHelper(models.AbstractModel):
    _name = 'pos.order.line.action.helper'

    @api.model
    def get_my_pos_order_lines(self):
        user = self.env.user
        allowed_pos = user.allowed_pos
        domain = [
            ('order_id.session_id.config_id', 'in', allowed_pos.ids)
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Order lines',
            'res_model': 'pos.order.line',
            'view_mode': 'tree,pivot',
            'domain': domain,
        }