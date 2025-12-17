/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { Order } from "@point_of_sale/app/store/models";

import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async _isOrderValid(isForceValidate) {
        console.log("Custom _isOrderValid reached!");

        if (this.currentOrder.get_orderlines().length === 0 && this.currentOrder.is_to_invoice()) {
            await this.popup.add(ErrorPopup, {
                title: _t("Empty Order"),
                body: _t("There must be at least one product in your order before it can be validated and invoiced."),
            });
            return false;
        }

        if ((await this._askForCardIfRequired()) === false) {
            return false;
        }

        return super._isOrderValid(...arguments);
    },

    async _askForCardIfRequired() {
        console.log("Custom _askForCardIfRequired reached!");
        console.log("this.paymentLines:", this.paymentLines);
        const useCard = this.paymentLines.filter(
            (payment) => payment.payment_method.use_card
        );
        const splitPayments = this.paymentLines.filter(
            (payment) => payment.payment_method.split_transactions
        );
        console.log("useCard:", useCard);
        console.log("splitPayments:", splitPayments);
        if (useCard.length) {
            console.log("Barcode payment method selected!");
            const { confirmed, payload: barcode } = await this.popup.add(TextInputPopup, {
                title: _t("Scan Card Barcode"),
                startingValue: '',
                placeholder: _t("Enter or scan card barcode..."),
            });
            console.log("Popup result:", confirmed, barcode);
    
            if (!confirmed || !barcode) {
                return false;
            }
    
            // Fetch customer by barcode
            const [partner] = await this.orm.searchRead(
                'res.partner',
                [['card_barcode', '=', barcode]],
                ['id', 'name', 'card_balance']
            );
    
            if (!partner) {
                await this.popup.add(ErrorPopup, {
                    title: _t("Card Not Found"),
                    body: _t("No customer found with this card."),
                });
                return false;
            }

            const total_amount = this.currentOrder.get_total_with_tax();
            console.log("total_with_tax:", this.currentOrder.get_total_with_tax());
            console.log("partner.card_balance:", partner.card_balance);
            if (partner.card_balance < total_amount) {
                await this.popup.add(ErrorPopup, {
                    title: _t("Insufficient Balance"),
                    body: _t(`Customer ${partner.name} has only ${partner.card_balance}, which is less than the required amount ${total_amount}.`),
                });
                return false;
            }
    
            this.currentOrder.set_partner(partner); // Assign the customer to the order
    
            // Store card usage in order for later balance deduction
            this.currentOrder.card_used = {
                partner_id: partner.id,
                amount: total_amount,
            };
        }
    },
});

patch(Order.prototype, {
    /**
     * Override updatePricelistAndFiscalPosition to prevent crashes
     * when partner pricelist is empty or null.
     */
    updatePricelistAndFiscalPosition(newPartner) {
        let newPartnerPricelist, newPartnerFiscalPosition;
        const defaultFiscalPosition = this.pos.fiscal_positions.find(
            (position) => position.id === this.pos.config.default_fiscal_position_id[0]
        );
        if (newPartner) {
            newPartnerFiscalPosition = newPartner.property_account_position_id
                ? this.pos.fiscal_positions.find(
                      (position) => position.id === newPartner.property_account_position_id[0]
                  )
                : defaultFiscalPosition;
            // ISY: Fix for pricelist
            const partnerPricelistId = newPartner && newPartner.property_product_pricelist ? newPartner.property_product_pricelist[0] : false;
            newPartnerPricelist = this.pos.pricelists.find(
                (pricelist) => pricelist.id === partnerPricelistId
            ) || this.pos.default_pricelist;

        } else {
            newPartnerFiscalPosition = defaultFiscalPosition;
            newPartnerPricelist = this.pos.default_pricelist;
        }
        this.set_fiscal_position(newPartnerFiscalPosition);
        this.set_pricelist(newPartnerPricelist);
    },
});
