# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class BudgetAvailableAmountMixin(models.AbstractModel):
    _name = 'budget.available.amount.mixin'
    _description = 'Budget Reserved Amount Computation'

    @api.model
    def _convert_to_company_currency(self, amount, currency, company, date):
        if currency and company and currency != company.currency_id:
            return currency._convert(
                amount, company.currency_id, company, date or fields.Date.today())
        return amount

    @api.model
    def _get_reserved_details(self, account, date_from, date_to, company):
        """Return reserved document lines and their total amount."""
        details = []
        env = self.env(context=dict(self.env.context, allowed_company_ids=[company.id]))

        po_domain = [
            ('product_id.property_account_expense_id', '=', account.id),
            ('order_id.state', '!=', 'cancel'),
            ('order_id.invoice_count', '=', 0),
            ('company_id', '=', company.id),
        ]
        po_amounts = {}
        for line in env['purchase.order.line'].search(po_domain):
            order = line.order_id
            subtotal = self._convert_to_company_currency(
                line.price_subtotal, order.currency_id, order.company_id, order.date_order)
            po_amounts[order.id] = po_amounts.get(order.id, 0.0) + subtotal
        for order_id, amount in po_amounts.items():
            order = env['purchase.order'].browse(order_id)
            details.append({
                'document_type': 'purchase_order',
                'document_name': order.name,
                'amount': amount,
                'res_model': 'purchase.order',
                'res_id': order_id,
            })

        advance_domain = [
            ('x_studio_anticipated_account_code.property_account_expense_id', '=', account.id),
            ('state', 'not in', ('cancel', 'reject', 'cleared')),
            ('company_id', '=', company.id),
        ]
        for advance in env['employee.advance.expense'].search(advance_domain):
            amount = self._convert_to_company_currency(
                advance.total_amount_expense, advance.currency_id,
                advance.company_id, advance.request_date)
            details.append({
                'document_type': 'advance',
                'document_name': advance.name,
                'amount': amount,
                'res_model': 'employee.advance.expense',
                'res_id': advance.id,
            })

        reimbursement_domain = [
            ('product_id.property_account_expense_id', '=', account.id),
            ('advance_line_id.state', 'not in', ('cancel', 'reject', 'cleared')),
            ('advance_line_id.company_id', '=', company.id),
        ]
        reimbursement_amounts = {}
        for line in env['advance.expense.line'].search(reimbursement_domain):
            parent = line.advance_line_id
            amount = self._convert_to_company_currency(
                line.total_amount, parent.currency_id, parent.company_id, parent.request_date)
            reimbursement_amounts[parent.id] = reimbursement_amounts.get(parent.id, 0.0) + amount
        for advance_id, amount in reimbursement_amounts.items():
            advance = env['employee.advance.expense'].browse(advance_id)
            details.append({
                'document_type': 'reimbursement',
                'document_name': advance.name,
                'amount': amount,
                'res_model': 'employee.advance.expense',
                'res_id': advance_id,
            })

        aml_domain = [
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'draft'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', company.id),
        ]
        move_amounts = {}
        for aml in env['account.move.line'].search(aml_domain):
            move = aml.move_id
            move_amounts[move.id] = move_amounts.get(move.id, 0.0) + (aml.debit - aml.credit)
        for move_id, amount in move_amounts.items():
            move = env['account.move'].browse(move_id)
            details.append({
                'document_type': 'draft_move',
                'document_name': move.name or move.ref or _('Draft'),
                'amount': amount,
                'res_model': 'account.move',
                'res_id': move_id,
            })

        reserved_total = sum(item['amount'] for item in details)
        return details, reserved_total


class BudgetAvailableAmount(models.TransientModel):
    _name = 'budget.available.amount'
    _inherit = ['budget.available.amount.mixin']
    _description = 'Budget Available Amount Report'
    _order = 'group_name, company_id, account_code'

    account_code = fields.Char(string='Account Code', readonly=True)
    name = fields.Char(string='Account Name', readonly=True)
    group_name = fields.Char(string='Group', readonly=True)
    planned_amount = fields.Float(
        related='budget_id.planned_amount_100',
        string='Planned Amount',
        readonly=True,
        store=True,
        digits=0,
    )
    allowed_amount = fields.Float(
        related='budget_id.planned_amount',
        string='Allowed Amount',
        readonly=True,
        store=True,
        digits=0,
    )

    display_planned_amount = fields.Float(
        string='Planned Amount',
        compute='_compute_display_amount',
        store=True,
        digits=0,
    )

    display_allowed_amount = fields.Float(
        string='Allowed Amount',
        compute='_compute_display_amount',
        store=True,
        digits=0,
    )

    practical_amount = fields.Float(
        related='budget_id.practical_amount',
        string='Practical Amount',
        readonly=True,
        store=True,
        digits=0,
    )
    remaining_amount = fields.Float(
        related='budget_id.different_amount',
        string='Remaining Amount',
        readonly=True,
        store=True,
        digits=0,
    )
    reserved_amount = fields.Float(
        string='Reserved Amount',
        compute='_compute_reserved_available',
        store=True,
        readonly=True,
        digits=0,
    )
    available_amount = fields.Float(
        string='Available Amount',
        compute='_compute_reserved_available',
        store=True,
        readonly=True,
        digits=0,
    )
    company_id = fields.Many2one(
        'res.company', string='Company', readonly=True, required=True)
    fiscal_year_id = fields.Many2one(
        'account.fiscal.year', string='Fiscal Year', readonly=True,
        check_company=True)
    budget_id = fields.Many2one(
        'budgetextension.budget', string='Budget', readonly=True,
        check_company=True)
    reserved_line_ids = fields.One2many(
        'budget.available.amount.line', 'report_id', string='Reserved Details', readonly=True)

    @api.depends('allowed_amount', 'planned_amount', 'budget_id.account_id.account_type')
    def _compute_display_amount(self):
        for record in self:
            if record.budget_id.account_id.account_type == 'expense':
                record.display_allowed_amount = -record.allowed_amount
                record.display_planned_amount = -record.planned_amount
            else:
                record.display_allowed_amount = record.allowed_amount
                record.display_planned_amount = record.planned_amount

    @api.depends('reserved_line_ids.amount', 'budget_id.different_amount')
    def _compute_reserved_available(self):
        for report in self:
            report.reserved_amount = sum(report.reserved_line_ids.mapped('amount'))
            remaining = report.budget_id.different_amount if report.budget_id else 0.0
            report.available_amount = remaining - report.reserved_amount

    def refresh_reserved_lines(self):
        """Rebuild reserved lines from current PO, advance, reimbursement, and draft moves."""
        Line = self.env['budget.available.amount.line']
        for report in self:
            budget = report.budget_id
            company = report.company_id
            if not budget or not budget.account_id or not company:
                report.reserved_line_ids.unlink()
                continue

            details, _total = report.with_company(company)._get_reserved_details(
                budget.account_id,
                budget.start_date,
                budget.end_date,
                company,
            )
            report.reserved_line_ids.unlink()
            if details:
                Line.create([dict(detail, report_id=report.id) for detail in details])

        self._compute_reserved_available()
        return True

    def action_refresh(self):
        reports = self
        if not reports:
            domain = [('create_uid', '=', self.env.user.id)]
            allowed_company_ids = self.env.context.get('allowed_company_ids')
            if allowed_company_ids:
                domain.append(('company_id', 'in', allowed_company_ids))
            reports = self.search(domain)
        reports.refresh_reserved_lines()
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class BudgetAvailableAmountLine(models.TransientModel):
    _name = 'budget.available.amount.line'
    _description = 'Budget Available Amount Reserved Detail'
    _order = 'document_type, document_name'

    report_id = fields.Many2one(
        'budget.available.amount', string='Report', ondelete='cascade',
        readonly=True, check_company=True)
    company_id = fields.Many2one(
        related='report_id.company_id', store=True, readonly=True)
    document_type = fields.Selection([
        ('purchase_order', 'Purchase Order'),
        ('advance', 'Advance'),
        ('reimbursement', 'Reimbursement'),
        ('draft_move', 'Draft Entry'),
    ], string='Type', readonly=True)
    document_name = fields.Char(string='Document', readonly=True)
    amount = fields.Float(string='Amount', readonly=True, digits=0)
    res_model = fields.Char(string='Related Model', readonly=True)
    res_id = fields.Integer(string='Related Record', readonly=True)

    def action_open_document(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        company = self.report_id.company_id
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                **self.env.context,
                'allowed_company_ids': [company.id],
                'default_company_id': company.id,
            },
        }
