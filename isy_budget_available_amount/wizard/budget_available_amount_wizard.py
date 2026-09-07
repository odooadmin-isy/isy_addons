# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class BudgetAvailableAmountWizard(models.TransientModel):
    _name = 'budget.available.amount.wizard'
    _inherit = 'budget.available.amount.mixin'
    _description = 'Budget Available Amount Wizard'

    @api.model
    def _get_current_fiscal_year(self, company=None, companies=None):
        current_date = fields.Date.context_today(self)
        domain = [
            ('date_from', '<=', current_date),
            ('date_to', '>=', current_date),
        ]
        FiscalYear = self.env['account.fiscal.year']
        if 'company_id' not in FiscalYear._fields:
            return FiscalYear.search(domain, limit=1, order='date_from desc, id desc')

        company_ids = companies.ids if companies else ([company.id] if company else [])
        if company_ids:
            for company_id in company_ids:
                fiscal_year = FiscalYear.search(
                    domain + [('company_id', '=', company_id)],
                    limit=1,
                    order='date_from desc, id desc',
                )
                if fiscal_year:
                    return fiscal_year
            fiscal_year = FiscalYear.search(
                domain + [('company_id', '=', False)],
                limit=1,
                order='date_from desc, id desc',
            )
            if fiscal_year:
                return fiscal_year

        return FiscalYear.search(domain, limit=1, order='date_from desc, id desc')

    @api.model
    def _default_fiscal_year_id(self):
        fiscal_year = self._get_current_fiscal_year(
            company=self.env.company,
            companies=self.env.companies,
        )
        return fiscal_year.id if fiscal_year else False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        companies = self.env.companies
        if 'company_ids' in fields_list and not res.get('company_ids'):
            res['company_ids'] = [(6, 0, companies.ids)]
        if 'fiscal_year_id' in fields_list and not res.get('fiscal_year_id'):
            fiscal_year = self._get_current_fiscal_year(companies=companies)
            if fiscal_year:
                res['fiscal_year_id'] = fiscal_year.id
        self._clear_user_reports()
        return res

    company_ids = fields.Many2many(
        'res.company',
        'budget_available_amount_wizard_company_rel',
        'wizard_id',
        'company_id',
        string='Companies',
        required=True,
        default=lambda self: self.env.companies,
        domain=lambda self: [('id', 'in', self.env.companies.ids)],
    )
    fiscal_year_id = fields.Many2one(
        'account.fiscal.year',
        string='Fiscal Year',
        required=True,
        default=_default_fiscal_year_id,
        readonly=True,
    )

    @api.constrains('company_ids')
    def _check_company_access(self):
        allowed_companies = self.env.companies
        for wizard in self:
            invalid = wizard.company_ids - allowed_companies
            if invalid:
                raise UserError(_(
                    'You do not have access to company "%(company)s".',
                    company=invalid[0].display_name,
                ))

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        if self.company_ids:
            self.fiscal_year_id = self._get_current_fiscal_year(companies=self.company_ids)

    @api.model
    def _clear_user_reports(self, companies=None):
        domain = [('create_uid', '=', self.env.user.id)]
        if companies:
            domain.append(('company_id', 'in', companies.ids))
        self.env['budget.available.amount'].search(domain).unlink()

    @api.model
    def _get_budget_group_name(self, budget):
        if 'x_studio_group' in budget._fields and budget.x_studio_group:
            return budget.x_studio_group.display_name
        if budget.group_id:
            return budget.group_id.display_name
        return False

    def _build_report_vals_for_company(self, company, date_from, date_to):
        budget_env = self.env['budgetextension.budget'].with_company(company)
        budget_domain = [
            ('start_date', '>=', date_from),
            ('end_date', '<=', date_to),
            ('state', '=', '2'),
            ('planned_amount', '>', 0),
            '|',
            ('company_id', '=', company.id),
            ('company_id', '=', False),
        ]
        budgets = budget_env.search(budget_domain, order='account_id')

        report_vals_list = []
        for budget in budgets.with_company(company):
            account = budget.account_id
            if not account or (account.company_id and account.company_id != company):
                continue

            report_vals_list.append({
                'name': account.name,
                'account_code': account.code,
                'group_name': self._get_budget_group_name(budget),
                'budget_id': budget.id,
                'company_id': company.id,
                'fiscal_year_id': self.fiscal_year_id.id,
            })
        return report_vals_list

    def action_generate(self):
        self.ensure_one()
        if not self.company_ids:
            raise ValidationError(_('Please select at least one company.'))
        if not self.fiscal_year_id:
            raise ValidationError(_('Please select a fiscal year.'))

        allowed_companies = self.env.companies
        invalid_companies = self.company_ids - allowed_companies
        if invalid_companies:
            raise UserError(_(
                'You do not have access to company "%(company)s".',
                company=invalid_companies[0].display_name,
            ))
        if (
            'company_id' in self.fiscal_year_id._fields
            and self.fiscal_year_id.company_id
            and self.fiscal_year_id.company_id not in self.company_ids
        ):
            raise ValidationError(_(
                'Fiscal year "%(fiscal_year)s" does not belong to any selected company.',
                fiscal_year=self.fiscal_year_id.display_name,
            ))

        self._clear_user_reports(self.company_ids)

        date_from = self.fiscal_year_id.date_from
        date_to = self.fiscal_year_id.date_to
        report_vals_list = []

        for company in self.company_ids:
            report_vals_list.extend(
                self._build_report_vals_for_company(company, date_from, date_to))

        if not report_vals_list:
            raise ValidationError(_(
                'No current year budget records found for the selected companies and fiscal year.',
            ))

        reports = self.env['budget.available.amount'].create(report_vals_list)
        reports.refresh_reserved_lines()

        if len(self.company_ids) == 1:
            title = _('Budget Available Amount - %s', self.company_ids.display_name)
        else:
            title = _('Budget Available Amount - %s', ', '.join(self.company_ids.mapped('name')))

        tree_view = self.env.ref(
            'isy_budget_available_amount.view_budget_available_amount_tree')
        form_view = self.env.ref(
            'isy_budget_available_amount.view_budget_available_amount_form')
        search_view = self.env.ref(
            'isy_budget_available_amount.view_budget_available_amount_search')
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'budget.available.amount',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'search_view_id': search_view.id,
            'target': 'current',
            'domain': [
                ('create_uid', '=', self.env.user.id),
                ('company_id', 'in', self.company_ids.ids),
            ],
            'context': {
                **self.env.context,
                'allowed_company_ids': self.company_ids.ids,
                'search_default_group_group': 1,
            },
        }
