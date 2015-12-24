odoo.define('web.attr_hierarchy_form_widgets', function (require) {
"use strict";

var core = require('web.core');
var crash_manager = require('web.crash_manager');
var data = require('web.data');
var datepicker = require('web.datepicker');
var ProgressBar = require('web.ProgressBar');
var Dialog = require('web.Dialog');
var common = require('web.form_common');
var formats = require('web.formats');
var framework = require('web.framework');
var Model = require('web.DataModel');
var Priority = require('web.Priority');
var pyeval = require('web.pyeval');
var session = require('web.session');
var utils = require('web.utils');

var _t = core._t;
var QWeb = core.qweb;

var AttrHierarchy = common.FormWidget.extend({
    template: '',
    
)};

core.form_widget_registry
    .add('attrhierarchy', AttrHierarchy)

});
