from odoo import models


class CardUsageXlsx(models.AbstractModel):
    _name = 'report.isy_pos_addon.card_usage_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Card Usage XLSX'

    def generate_xlsx_report(self, workbook, data, wizards):
        wizard = wizards[0]
        sheet = workbook.add_worksheet('Card Usage')

        bold = workbook.add_format({'bold': True})
        title = workbook.add_format({'bold': True, 'font_size': 14})
        header = workbook.add_format({
            'bold': True, 'bg_color': '#D9E1F2', 'border': 1,
            'align': 'center', 'valign': 'vcenter',
        })
        cell = workbook.add_format({'border': 1})
        date_fmt = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd hh:mm'})
        money = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        money_total = workbook.add_format({
            'border': 1, 'bold': True, 'num_format': '#,##0.00', 'bg_color': '#F2F2F2',
        })

        sheet.write(0, 0, 'Period: %s to %s' % (wizard.date_from, wizard.date_to), bold)

        columns = [
            ('Create Date', 15), ('Customer', 20), ('Barcode', 20), ('Order Ref', 30), ('POS', 20),
            ('Payment Type', 20), ('Amount', 20),
        ]
        row = 1
        for col, (label, width) in enumerate(columns):
            sheet.write(row, col, label, header)
            sheet.set_column(col, col, width)
        sheet.freeze_panes(row + 1, 0)

        total = 0.0
        for history in wizard.get_records():
            row += 1
            sheet.write_datetime(row, 0, history.create_date, date_fmt)
            sheet.write(row, 1, history.name or '', cell)
            sheet.write(row, 2, history.barcode or '', cell)
            sheet.write(row, 3, history.order_ref or '', cell)
            sheet.write(row, 4, history.pos_config_id.name or '', cell)
            sheet.write(row, 5, history.ptype or '', cell)
            sheet.write_number(row, 6, history.amount, money)
            total += history.amount

        row += 1
        sheet.write(row, 5, 'Total', bold)
        sheet.write_number(row, 6, total, money_total)
