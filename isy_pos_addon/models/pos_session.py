# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero

from odoo import api, fields, models, _

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _accumulate_amounts(self, data):
        data = super(PosSession, self)._accumulate_amounts(data)
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        sales = defaultdict(amounts)
        flag = False
        for order in self.order_ids:
            if not order.is_invoiced:
                flag = True
                for order_line in order.lines:
                    line = self._prepare_line(order_line)
                    # Combine sales/refund lines
                    sale_key = (
                        # account
                        line['income_account_id'],
                        # sign
                        -1 if line['amount'] < 0 else 1,
                        # for taxes
                        tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
                        line['base_tags'],
                        line.get('partner_id', False), 
                        order.currency_id.id,
                        order_line.customer_note or '',
                    )
                    sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']}, line['date_order'], round=False)
                    sales[sale_key].setdefault('tax_amount', 0.0)
                    # Combine tax lines
                    for tax in line['taxes']:
                        tax_key = (tax['account_id'] or line['income_account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
                        sales[sale_key]['tax_amount'] += tax['amount']
        if flag:
            data.update({'sales': sales})
        return data

    def _get_sale_vals(self, key, amount, amount_converted):
        # ISY CUSTOMIZED
        account_id, sign, tax_keys, base_tag_ids, partner_id, currency_id, customer_note = key
        # ISY CUSTOMIZED END
        tax_ids = set(tax[0] for tax in tax_keys)
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        title = 'Sales' if sign == 1 else 'Refund'
        name = '%s untaxed' % title
        if applied_taxes:
            name = '%s with %s' % (title, ', '.join([tax.name for tax in applied_taxes]))
        partial_vals = {
            'name': name+' ['+customer_note+']' if customer_note else name,
            'account_id': account_id,
            'partner_id': partner_id,
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tax_tag_ids': [(6, 0, base_tag_ids)],
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)

    #Override function to pass the new param: use_card
    def _loader_params_pos_payment_method(self):
        return {
            'search_params': {
            'domain': ['|', ('active', '=', False), ('active', '=', True)],
            'fields': ['name', 'is_cash_count', 'use_payment_terminal', 'split_transactions', 'type', 'image', 'sequence', 'use_card'],
            },
        }

    def _create_split_account_payment(self, payment, amounts):
        payment_method = payment.payment_method_id
        if not payment_method.journal_id:
            return self.env['account.move.line']
        outstanding_account = payment_method.outstanding_account_id or self.company_id.account_journal_payment_debit_account_id
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        destination_account = accounting_partner.property_account_receivable_id

        # if float_compare(amounts['amount'], 0, precision_rounding=self.currency_id.rounding) < 0:
        #     # revert the accounts because account.payment doesn't accept negative amount.
        #     outstanding_account, destination_account = destination_account, outstanding_account

        account_payment = self.env['account.payment'].create({
            'amount': abs(amounts['amount']),
            'partner_id': accounting_partner.id,
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'ref': _('%s POS payment of %s in %s', payment_method.name, payment.partner_id.display_name, self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
        })
        account_payment.action_post()
        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == account_payment.destination_account_id)
