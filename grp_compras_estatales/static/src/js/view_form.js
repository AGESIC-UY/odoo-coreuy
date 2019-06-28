
openerp.grp_compras_estatales = function(instance) {

var _t = instance.web._t,
    _lt = instance.web._lt;
var QWeb = instance.web.qweb;

//instance.web.form.WidgetButton = instance.web.form.FormWidget.extend({
//}

//instance.web.form.WidgetButton = instance.web.form.FormWidget.extend({
//
//instance.web.form.WidgetButtonGrp = instance.web.form.WidgetButton.extend({

instance.web.form.WidgetButton.include({
//instance.web.account.bankStatementReconciliation.include({

    init: function(parent, context) {
        this._super(parent, context);
    },

    execute_action: function() {
        var self = this;
        var exec_action = function() {
            if (self.node.attrs.confirm) {
                var def = $.Deferred();
                var dialog = new instance.web.Dialog(this, {
                    title: _t('Confirm'),
                    buttons: [
                        {text: _t("Ok"), click: function() {
                                var self2 = this;
                                self.on_confirmed().always(function() {
                                    self2.parents('.modal').modal('hide');
                                });
                            }
                        },
                        {text: _t("Cancel"), click: function() {
                                this.parents('.modal').modal('hide');
                            }
                        },
                    ],
                }, $('<div/>').text(self.node.attrs.confirm)).open();
                dialog.on("closing", null, function() {def.resolve();});
                return def.promise();
            } else {
                return self.on_confirmed();
            }
        };
        if (!this.node.attrs.special) {
            return this.view.recursive_save().then(exec_action);
        } else {
            return exec_action();
        }
    },
});

instance.web.ListView.include({
    configure_pager: function(dataset){
        // Solución bug de Odoo v8. Al eliminar agrupaciones no vuelve
        // a visualizar los botones de paginado.
        this._super(dataset);
        var total = dataset.size();
        var limit = this.limit() || total;
        this.$pager.find('.oe_pager_group').toggle(total > limit);
    }
});

};
