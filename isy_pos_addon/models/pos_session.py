# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero

from odoo import api, fields, models, _

class PosSession(models.Model):
    _inherit = 'pos.session'

    commission_move_id = fields.Many2one('account.move', string='Commission Entry', readonly=True, copy=False)
    card_sale_payment_move_id = fields.Many2one('account.move', string='Card Sale Payment Entry', readonly=True, copy=False)

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        result = super()._validate_session(balancing_account, amount_to_balance, bank_payment_method_diffs)
        if result is True:
            self._create_commission_account_move()
            self._create_card_sale_payment_account_move()
        return result

    def _get_vendor_payment_default_account(self, payment_method):
        return payment_method.with_company(self.company_id).journal_id.default_account_id

    def _get_payment_totals_by_account(self):
        """Aggregate closed-order payment amounts by payment method account.

        Returns dict of account -> {'amount': session currency, 'amount_converted': company currency}.
        """
        self.ensure_one()
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        account_totals = defaultdict(amounts)
        for payment_method in self.payment_method_ids:
            payment_account = self._get_vendor_payment_default_account(payment_method)
            for order in self._get_closed_orders():
                for payment in order.payment_ids:
                    if payment.payment_method_id != payment_method:
                        continue
                    if float_is_zero(payment.amount, precision_rounding=self.currency_id.rounding):
                        continue
                    account_totals[payment_account] = self._update_amounts(
                        account_totals[payment_account],
                        {'amount': payment.amount},
                        payment.payment_date,
                    )
        return {
            account: totals
            for account, totals in account_totals.items()
            if not float_is_zero(totals['amount'], precision_rounding=self.currency_id.rounding)
        }

    def _prepare_journal_line_vals(self, name, account, amount, amount_converted, credit=True, partner=False):
        """Build move line vals with currency conversion support."""
        partial_vals = {
            'name': name,
            'account_id': account.id,
        }
        if partner:
            partial_vals['partner_id'] = partner.id
        if credit:
            return self._credit_amounts(partial_vals, amount, amount_converted)
        return self._debit_amounts(partial_vals, amount, amount_converted)

    # For Vendor Payable Journal
    def _create_card_sale_payment_account_move(self):
        self.ensure_one()
        if self.card_sale_payment_move_id:
            return self.card_sale_payment_move_id

        config = self.config_id
        if not config.is_vendor_payment:
            return self.env['account.move']

        pos_payment_account = config.pos_payment_account_id
        vendor_control_account = config.vendor_control_account_id
        if not pos_payment_account or not vendor_control_account:
            raise UserError(_(
                'Please configure POS Payment Account and Vendor Control Account on POS config "%s".',
                config.display_name,
            ))

        account_totals = self._get_payment_totals_by_account()
        date = fields.Date.context_today(self)
        is_card_sale_payment = False
        for payment_method in self.payment_method_ids:
            if payment_method.use_card:
                default_account_id = payment_method.journal_id.default_account_id
                if default_account_id not in account_totals:
                    break

                is_card_sale_payment = True
                card_sale_payment_amount = account_totals[default_account_id]['amount']
                card_sale_payment_amount_converted = self._amount_converter(card_sale_payment_amount, date, True)

                line_vals = []
                # Credit line for Card Sale Payment
                line_vals.append((0, 0, self._prepare_journal_line_vals(
                    _('Card Sale Payment - %s', self.name),
                    vendor_control_account,
                    card_sale_payment_amount,
                    card_sale_payment_amount_converted,
                    credit=True,
                )))

                # Debit line for Card Sale Payment
                line_vals.append((0, 0, self._prepare_journal_line_vals(
                    _('Card Sale Payment - %s', self.name),
                    pos_payment_account,
                    card_sale_payment_amount,
                    card_sale_payment_amount_converted,
                    credit=False,
                )))

        if is_card_sale_payment:
            move = self.env['account.move'].sudo().with_company(self.company_id).create({
                'journal_id': payment_method.journal_id.id,
                'date': date,
                'ref': _('Card Sale Payment %s', self.name),
                'line_ids': line_vals,
            })
            move.action_post()
            self.card_sale_payment_move_id = move.id
            return move

        return self.env['account.move']

    # For Commission Journal
    def _create_commission_account_move(self):
        self.ensure_one()
        if self.commission_move_id:
            return self.commission_move_id

        config = self.config_id
        if not config.is_vendor_payment:
            return self.env['account.move']

        commission_percentage = config.commission_percentage
        commission_journal = config.commission_journal_id
        adjustment_account = config.adjustment_account_id
        vendor_control_account = config.vendor_control_account_id
        vendor = config.vendor_id

        if not commission_percentage:
            return self.env['account.move']
        if not commission_journal or not commission_journal.default_account_id or\
                not adjustment_account or not vendor_control_account or not vendor:
            raise UserError(_(
                'Please configure Commission Journal (with default account), Adjustment Account, Vendor Control Account, and Vendor on POS config "%s".',
                config.display_name,
            ))

        account_totals = self._get_payment_totals_by_account()
        if not account_totals:
            return self.env['account.move']

        date = fields.Date.context_today(self)
        line_vals = []
        total_commission_amount = 0.0
        total_commission_amount_converted = 0.0

        is_card_sale_payment = False
        card_sale_payment_amount = 0.0
        card_sale_payment_amount_converted = 0.0

        # POS Payment lines
        for payment_account, totals in account_totals.items():
            total_amount = totals['amount']
            total_amount_converted = totals['amount_converted']
            commission_amount = self.currency_id.round(total_amount * commission_percentage / 100.0)
            commission_amount_converted = self._amount_converter(commission_amount, date, True)

            total_commission_amount += commission_amount
            total_commission_amount_converted += commission_amount_converted

            #Credit line for POS Payment - Payment Account
            line_vals.append((0, 0, self._prepare_journal_line_vals(
                _('POS Payment %s - %s', payment_account.display_name, self.name),
                payment_account,
                total_amount,
                total_amount_converted,
                credit=True,
            )))

            #Debit line for POS Payment - Vendor Control Account
            line_vals.append((0, 0, self._prepare_journal_line_vals(
                _('POS Payment - %s', self.name),
                vendor_control_account,
                total_amount,
                total_amount_converted,
                credit=False,
                partner=vendor,
            )))

        # Credit line for Commission
        if not float_is_zero(total_commission_amount, precision_rounding=self.currency_id.rounding):
            line_vals.append((0, 0, self._prepare_journal_line_vals(
                _('%s Commission - %s percent', vendor.name, commission_percentage),
                commission_journal.default_account_id,
                total_commission_amount,
                total_commission_amount_converted,
                credit=True,
                partner=vendor,
            )))

        # Debit line for Commission
        if not float_is_zero(total_commission_amount, precision_rounding=self.currency_id.rounding):
            line_vals.append((0, 0, self._prepare_journal_line_vals(
                _('POS Payment Commission for %s', vendor.name),
                vendor_control_account,
                total_commission_amount,
                total_commission_amount_converted,
                credit=False,
                partner=vendor,
            )))

        move = self.env['account.move'].sudo().with_company(self.company_id).create({
            'journal_id': commission_journal.id,
            'date': date,
            'ref': _('Commission %s', self.name),
            'line_ids': line_vals,
        })
        move.action_post()
        self.commission_move_id = move.id
        return move

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

        if not partner_id and self.config_id.is_vendor_payment:
            partner_id = self.config_id.vendor_id.id

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

    def _get_balancing_account(self):
        result = super(PosSession, self)._get_balancing_account()
        if self.config_id.is_vendor_payment:
            return self.config_id.adjustment_account_id
        return result