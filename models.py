from django.db import models
from django.template.defaultfilters import default
import datetime
from django.shortcuts import get_object_or_404


# Create your models here.

class transaction_rule(models.Model):
    name = models.CharField(max_length=200, default='')
    transaction_rule_code = models.IntegerField(default=0)
    data = models.TextField(default='{}')
    data1 = models.TextField(default='{}')
    data2 = models.TextField(default='{}')
    def __str__(self):
        return self.name

class ttype_department(models.Model):
    name = models.CharField(max_length=200, default='')
    report_data = models.TextField(default='{}')
    data = models.TextField(default='{}')
    data1 = models.TextField(default='{}')
    def __str__(self):
        return self.name

class transaction_type(models.Model):
    name = models.CharField(max_length=200, default='')
    transaction_type_ref_no = models.IntegerField(default=0, null=True, unique=True)
    ttype_department_ref = models.ForeignKey(ttype_department, null = True)
    last_ref_no = models.IntegerField(default=0)
    transaction_rule = models.ForeignKey(transaction_rule, null=True)
    debit_ttype1_ids = models.CharField(max_length=100, default='', null=True)
    debit_ttype2_ids = models.CharField(max_length=100, default='', null=True)
    debit_ttype3_ids = models.CharField(max_length=100, default='', null=True)
    data = models.TextField(default='{}')
    data1 = models.TextField(default='{}')
    def __str__(self):
        return self.name

class item_department(models.Model):
    name = models.CharField(max_length=200, default='')
    flite_360_dep_id = models.IntegerField(default=0, null=True)
    data = models.TextField(default='{}')
    def __str__(self):
        return self.name
    
class uom(models.Model):
    name = models.CharField(max_length=10, default='')
    def __str__(self):
        return self.name

class coa_group(models.Model):
    name = models.CharField(max_length=100, default='', unique = True)
    coa_group_no = models.IntegerField(default=0, null=True, unique=True)
    parent_coa_group = models.ForeignKey('self', null=True)
    data = models.TextField(default='{}', null = True)
    def parent_name(self):
        return self.parent_coa_group.coa_group_name
    def __str__(self):
        return self.name
 
class coa(models.Model):
    name = models.CharField(max_length=100, default='', unique = True)
    coa_group = models.ForeignKey(coa_group, null=True)
    coa_no = models.IntegerField(default=0, unique = True)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class item_group(models.Model):
    name = models.CharField(max_length=200, default='')
    imported_unique = models.IntegerField(null = True, unique = True)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class tax_head(models.Model):
    name = models.CharField(max_length=200, default='Tax Head')
    active = models.BooleanField(default=False)
    tax_head_no = models.IntegerField(default=0)
    add_to_valuation = models.BooleanField(default=False)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class tax_format(models.Model):
    name = models.CharField(max_length=200, default='')
    active = models.BooleanField(default=False)
    app_other_charges = models.BooleanField(default=False)
    data = models.TextField(default='{}', null = True)
    '''data['apply'] contains the data of format / order in which taxes are to be applied, the format is given below:
    [('tax_head', ('rate of addition', 'value of addition'), (tax applied on summation of x,y,z.. heads))]'''
    def __str__(self):
        return self.name

class item_master(models.Model):
    name = models.CharField(max_length=200, default='')
    item_group = models.ForeignKey(item_group, null=True)
    item_code = models.CharField(max_length=200, default='')
    imported_item_code = models.CharField(max_length=200, default='-')
    imported_item_finish = models.CharField(max_length=200, default='-', null = False)
    created_date = models.DateTimeField(null = True)
    last_updated = models.DateTimeField(null = True)
    bom_last_updated = models.DateTimeField(null = True)
    price_last_updated = models.DateTimeField(null = True)
    description = models.TextField(default='Enter Description', null = True)
    uom = models.ForeignKey(uom, null=True)
    process_valuation_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    input_factor = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    bom_input_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    bom_sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    adhoc_sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    current_stock_inhouse = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    safety_stock = models.IntegerField(default=0)
    re_order_level = models.IntegerField(default=0)
    bom = models.TextField(default='[]', null = True)
    imported_bom = models.TextField(default='[]', null = True)
    infinite_bom = models.TextField(default='[]', null = True)
    imported_infinite_bom = models.TextField(default='[]', null = True)
    scrap = models.TextField(default='[]', null = True)
    imported_scrap = models.TextField(default='[]', null = True)
    nested_bom = models.TextField(default='[]', null = True)
    imported_nested_bom = models.TextField(default='[]', null = True)
    nested_scrap = models.TextField(default='[]', null = True)
    imported_nested_scrap = models.TextField(default='[]', null = True)
    offcut = models.TextField(default='[]', null = True)
    imported_offcut = models.TextField(default='[]', null = True)
    slug_waste = models.TextField(default='[]', null = True)
    imported_slug_waste = models.TextField(default='[]', null = True)
    tax_format = models.ForeignKey(tax_format, null = True)
    remarks = models.TextField(default='', null = True, blank = True)
    block_rate_update = models.BooleanField(default = False)
    bom_sp_his = models.TextField(default='[]', null = True, blank = True)
    weight_factor = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    item_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    volume_factor = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    item_volume = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class accounts_voucher_type(models.Model):
    name = models.TextField(default='', null = True)
    data = models.TextField(default='{}', null = True, blank = True)
    def __str__(self):
        return self.name
    
class country(models.Model):
    name = models.CharField(max_length=20, default = 'Enter Country Name', unique = True, null = True)
    data = models.TextField(default='', null = True, blank = True)
    def __str__(self):
        return self.name

class state(models.Model):
    name = models.CharField(max_length=20, default = 'Enter State Name', unique = True, null = True)
    country = models.ForeignKey(country, null = True)
    data = models.TextField(default='', null = True, blank = True)
    def __str__(self):
        return self.name

class city(models.Model):
    name = models.CharField(max_length=20, default = 'Enter City Name', unique = True, null = True)
    state = models.ForeignKey(state, null = True)
    data = models.TextField(default='', null = True, blank = True)
    def __str__(self):
        return self.name

class work_center(models.Model):
    name = models.CharField(max_length=50, default = 'Enter Vendor Name', unique = True, null = True)
    manager = models.CharField(max_length=100, default = 'Contact Person', null = True)
    address_line1 = models.CharField(max_length=200, default = 'Address Line 1', null = True)
    address_line2 = models.CharField(max_length=200, default = 'Address Line 2', null = True)
    remarks = models.TextField(default='', null = True)
    data = models.TextField(default='', null = True, blank = True)
    def __str__(self):
        return self.name

class plant(models.Model):
    name = models.CharField(max_length=50, default = 'Enter Plant Name', unique = True, null = True)
    data = models.TextField(default='{}', null = True, blank = True)
    def __str__(self):
        return self.name

class payment_terms(models.Model):
    name = models.CharField(max_length=200, default = 'Enter Payment Terms', unique = True, null = True)
    data = models.TextField(default='', null = True, blank = True)
    def __str__(self):
        return self.name

class other_terms(models.Model):
    name = models.CharField(max_length=200, default = 'Enter Other Terms', unique = True, null = True)
    data = models.TextField(default='', null = True, blank = True)
    def __str__(self):
        return self.name

class mode_of_dispatch(models.Model):
    name = models.CharField(max_length=200, default = 'Enter Vendor Name', unique = True, null = True)
    data = models.TextField(default='', null = True, blank = True)
    def __str__(self):
        return self.name

class vendor_price(models.Model):
    vendor = models.ForeignKey(coa, null=True)
    item = models.ForeignKey(item_master, null=True)
    job_work_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    purchase_factor = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    block_rate_update = models.BooleanField(default = False)
    job_work_tax_format = models.ForeignKey(tax_format, null = True, related_name = 'jw_tax')
    purchase_tax_format = models.ForeignKey(tax_format, null = True, related_name = 'purchase_tax')
    remarks = models.TextField(default='', null = True, blank = True)
    pur_rate_history = models.TextField(default='[]', null = True, blank = True)
    jw_rate_history = models.TextField(default='[]', null = True, blank = True)
    last_updated = models.DateTimeField(null = True)
    data = models.TextField(default='{}', null = True)
    def item_name(self):
        return self.item.name
    def name(self):
        ret_name = self.item.name + '(' + str(self.vendor.name) + ')'
        return ret_name
    def __str__(self):
        return self.item.name

class work_center_price(models.Model):
    work_center = models.ForeignKey(work_center, null=True)
    item = models.ForeignKey(item_master, null=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    block_rate_update = models.BooleanField(default = False)
    remarks = models.TextField(default='', null = True, blank = True)
    rate_history = models.TextField(default='[]', null = True, blank = True)
    last_updated = models.DateTimeField(null = True)
    data = models.TextField(null = True, default = '{}')
    def __str__(self):
        return self.item.name

class location_type(models.Model):
    name = models.CharField(max_length=200)
    short_hand = models.CharField(max_length=200, null=True)
    data = models.TextField(null = True, default = '{}')
    def __str__(self):
        return self.name

class location(models.Model):
    name = models.CharField(max_length=200)
    location_type_ref = models.ForeignKey(location_type, null=True)
    ref_no = models.IntegerField(default=0, null=True)
    data = models.TextField(null = True, default = '{}')
    def __str__(self):
        ret_str = self.location_type_ref.name + ' - ' + str(self.ref_no)
        return ret_str

class current_stock(models.Model):
    name = models.CharField(max_length=200)
    location_ref = models.ForeignKey(location, null=True)
    item_master_ref = models.ForeignKey(item_master, null=True)
    tpl_ref_no = models.IntegerField(default=0, null=True)
    cur_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    safety_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    re_order_level = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    cur_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    tot_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    data = models.TextField(null = True, default = '{}')
    def __str__(self):
        return self.item_master_ref.name

class transaction_ref(models.Model):
    name = models.CharField(max_length=200, null=True)
    ref_name = models.CharField(max_length=200, null=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    submit_date = models.DateTimeField('Submitted Date', auto_now=True)
    release_date = models.DateTimeField('Release Date', null=True, blank=True)
    transaction_type = models.ForeignKey(transaction_type, null=True)
    chain_tref = models.IntegerField(default=0, null=True)
    ref_no = models.IntegerField(default=0, null=True)
    active = models.BooleanField(default=False)
    submit = models.BooleanField(default=False)
    remarks = models.TextField(default='', null = True)
    force_close = models.BooleanField(default=False)
    overall_surcharge_remark = models.CharField(max_length=200, null=True)
    overall_surcharge = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    other_charge_remark = models.CharField(max_length=200, null=True)
    other_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    other_charge_tax_ref = models.ForeignKey(tax_format, default=1, null=True)
    debit_transaction1 = models.ForeignKey('self', related_name = 'debit_1', null=True)
    debit_transaction2 = models.ForeignKey('self', related_name = 'debit_2', null=True)
    debit_transaction3 = models.ForeignKey('self', related_name = 'debit_3', null=True)
    data = models.TextField(default='{}', null = True)
    def ttype_ref_no(self):
        return transaction_type.transaction_type_ref_no
    def __str__(self):
        return self.name
    
class accounts_journal(models.Model):
    coa = models.ForeignKey(transaction_ref, null=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    remarks = models.TextField(default='', null = True, blank = True)
    def __str__(self):
        return self.coa.name

class inventory_journal(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    transaction_ref = models.ForeignKey(transaction_ref, null=True)
    location_ref_val = models.CharField(max_length=50, default = '0', null = True)
    tpl_ref_no = models.IntegerField(default=0, null=True)
    item_master = models.ForeignKey(item_master, null=True)
    issue_qty = models.DecimalField(max_digits=15, decimal_places=6, default=0.0)
    balance_qty = models.DecimalField(max_digits=15, decimal_places=6, default=0.0)
    debit_journal1 = models.ForeignKey('self', related_name = 'debit_1', null=True)
    debit_journal2 = models.ForeignKey('self', related_name = 'debit_2', null=True)
    debit_journal3 = models.ForeignKey('self', related_name = 'debit_3', null=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True, blank=True)
    discount = models.DecimalField(max_digits=8, decimal_places=4, default=0.0, null=True, blank=True)
    surcharge = models.DecimalField(max_digits=6, decimal_places=2, default=0.0, null=True, blank=True)
    special_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True, blank=True)
    overall_surcharge = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True, blank=True)
    tax_format = models.ForeignKey(tax_format, default = 1, null=True, blank=True)
    tax_split = models.TextField(default='{}', null = True)
    other_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True, blank=True)
    taxed_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    taxed_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, null=True)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.item_master.name

class imported_quotes(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    quote = models.IntegerField(null = True)
    project = models.IntegerField(null = True)
    quote_name = models.CharField(max_length=200, default = 'Quotation Name')
    project_name = models.CharField(max_length=200, default = 'Project Name Name')
    ord_con = models.IntegerField(null = True)
    ord_con_name = models.CharField(max_length=200, default = 'Order Confirmation Name')
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class rmp_auto(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name', unique = True)
    rmp_sale_rate = models.DecimalField(max_digits=12, decimal_places=4, default=0.0)
    rate_uom = models.CharField(max_length=200, default = 'UOM')
    constant_value = models.BooleanField(default=False)
    rmp_pk_360 = models.IntegerField(default = 1, unique=True)
    created_date = models.DateTimeField(null = True)
    last_updated = models.DateTimeField(null = True)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class constants(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    constant_value = models.DecimalField(max_digits=12, decimal_places=4, default=0.0)
    created_date = models.DateTimeField(null = True)
    last_updated = models.DateTimeField(null = True)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class process_type(models.Model):
    name = models.CharField(max_length=200, default = 'Process Name')
    remarks = models.CharField(max_length=200, default = 'Remarks')
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class auto_price_list(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    item_group = models.ForeignKey(item_group, null=True)
    item_coa_group = models.ForeignKey(coa_group, null=True)
    flite_360_price_list_id = models.IntegerField(null = True)
    allow_auto_sync = models.BooleanField(default = True)
    spec_code = models.CharField(max_length=200, default = '', null = True, unique = True)
    created_date = models.DateTimeField(null = True)
    last_updated = models.DateTimeField(null = True)
    weight_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    volume_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    input_rate_sale = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    adhoc_sale_price_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    sale_price_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    job_work_price_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    purchase_factor_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    purchase_price_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    shop_order_price_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    input_factor_calc_eqn = models.CharField(max_length=200, default = 0, null = True)
    sale_margin = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    docfile = models.FileField(upload_to='documents/%Y/%m/%d', null=True)
    process = models.ForeignKey(process_type, null=True, default = 1)
    item_department_ref = models.ForeignKey(item_department, null=True)
    p1 = models.ForeignKey(rmp_auto, null=True, related_name = 'p1', default = 1)
    p2 = models.ForeignKey(rmp_auto, null=True, related_name = 'p2', default = 1)
    p3 = models.ForeignKey(rmp_auto, null=True, related_name = 'p3', default = 1)
    p4 = models.ForeignKey(rmp_auto, null=True, related_name = 'p4', default = 1)
    p5 = models.ForeignKey(rmp_auto, null=True, related_name = 'p5', default = 1)
    p6 = models.ForeignKey(rmp_auto, null=True, related_name = 'p6', default = 1)
    p7 = models.ForeignKey(rmp_auto, null=True, related_name = 'p7', default = 1)
    p8 = models.ForeignKey(rmp_auto, null=True, related_name = 'p8', default = 1)
    p9 = models.ForeignKey(rmp_auto, null=True, related_name = 'p9', default = 1)
    p10 = models.ForeignKey(rmp_auto, null=True, related_name = 'p10', default = 1)
    p11 = models.ForeignKey(rmp_auto, null=True, related_name = 'p11', default = 1)
    p12 = models.ForeignKey(rmp_auto, null=True, related_name = 'p12', default = 1)
    p13 = models.ForeignKey(rmp_auto, null=True, related_name = 'p13', default = 1)
    p14 = models.ForeignKey(rmp_auto, null=True, related_name = 'p14', default = 1)
    p15 = models.ForeignKey(rmp_auto, null=True, related_name = 'p15', default = 1)
    p16 = models.ForeignKey(rmp_auto, null=True, related_name = 'p16', default = 1)
    p17 = models.ForeignKey(rmp_auto, null=True, related_name = 'p17', default = 1)
    p18 = models.ForeignKey(rmp_auto, null=True, related_name = 'p18', default = 1)
    p19 = models.ForeignKey(rmp_auto, null=True, related_name = 'p19', default = 1)
    p20 = models.ForeignKey(rmp_auto, null=True, related_name = 'p20', default = 1)
    k1 = models.ForeignKey(constants, null=True, related_name = 'k1', default = 1)
    k2 = models.ForeignKey(constants, null=True, related_name = 'k2', default = 1)
    k3 = models.ForeignKey(constants, null=True, related_name = 'k3', default = 1)
    k4 = models.ForeignKey(constants, null=True, related_name = 'k4', default = 1)
    k5 = models.ForeignKey(constants, null=True, related_name = 'k5', default = 1)
    k6 = models.ForeignKey(constants, null=True, related_name = 'k6', default = 1)
    k7 = models.ForeignKey(constants, null=True, related_name = 'k7', default = 1)
    k8 = models.ForeignKey(constants, null=True, related_name = 'k8', default = 1)
    k9 = models.ForeignKey(constants, null=True, related_name = 'k9', default = 1)
    k10 = models.ForeignKey(constants, null=True, related_name = 'k10', default = 1)
    k11 = models.ForeignKey(constants, null=True, related_name = 'k11', default = 1)
    k12 = models.ForeignKey(constants, null=True, related_name = 'k12', default = 1)
    k13 = models.ForeignKey(constants, null=True, related_name = 'k13', default = 1)
    k14 = models.ForeignKey(constants, null=True, related_name = 'k14', default = 1)
    k15 = models.ForeignKey(constants, null=True, related_name = 'k15', default = 1)
    k16 = models.ForeignKey(constants, null=True, related_name = 'k16', default = 1)
    k17 = models.ForeignKey(constants, null=True, related_name = 'k17', default = 1)
    k18 = models.ForeignKey(constants, null=True, related_name = 'k18', default = 1)
    k19 = models.ForeignKey(constants, null=True, related_name = 'k19', default = 1)
    k20 = models.ForeignKey(constants, null=True, related_name = 'k20', default = 1)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class packing_set(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    parent_auto_pl_item = models.ForeignKey(auto_price_list, related_name='parent_auto_pl_id', null = True)
    max_weight = models.DecimalField(max_digits=8, decimal_places=2, default=0.0, null = False)
    min_weight = models.DecimalField(max_digits=8, decimal_places=2, default=0.0, null = False)
    max_volume = models.DecimalField(max_digits=8, decimal_places=2, default=0.0, null = False)
    min_volume = models.DecimalField(max_digits=8, decimal_places=2, default=0.0, null = False)
    max_qty = models.DecimalField(max_digits=8, decimal_places=2, default=0.0, null = False)
    min_qty = models.DecimalField(max_digits=8, decimal_places=2, default=0.0, null = False)
    def __str__(self):
        return self.name

class packing_items(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    packing_auto_pl = models.ForeignKey(auto_price_list, related_name='packing_auto_pl_id', null = True)
    packing_set_ref = models.ForeignKey(packing_set, related_name='packing_set_ref', null = True)
    d1 = models.CharField(max_length=200, default = '0')
    d2 = models.CharField(max_length=200, default = '0')
    d3 = models.CharField(max_length=200, default = '0')
    d4 = models.CharField(max_length=200, default = '0')
    qty = models.CharField(max_length=200, default = '0')
    def __str__(self):
        return self.name

class auto_slug_waste_calc(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    parent_auto_pl = models.ForeignKey(auto_price_list, related_name='parent')
    slug_auto_pl = models.ForeignKey(auto_price_list, related_name='slug_waste')
    d1 = models.CharField(max_length=200, default = '0')
    d2 = models.CharField(max_length=200, default = '0')
    d3 = models.CharField(max_length=200, default = '0')
    d4 = models.CharField(max_length=200, default = '0')
    qty = models.CharField(max_length=200, default = '0')
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class vendor_price_list_auto(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    auto_pl = models.ForeignKey(auto_price_list, null=True)
    vendor = models.ForeignKey(coa, null=True)
    data = models.TextField(default='{}', null = True)
    def pl_auto_name(self):
        return self.auto_pl.name
    def __str__(self):
        return self.name

class work_center_price_list_auto(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    auto_pl = models.ForeignKey(auto_price_list, null=True)
    work_center = models.ForeignKey(work_center, null=True)
    data = models.TextField(default='{}', null = True)
    def pl_auto_name(self):
        return self.auto_pl.name
    def __str__(self):
        return self.name

class vendor_rmp_auto(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    rmp = models.ForeignKey(rmp_auto, null=True)
    vendor = models.ForeignKey(coa, null=True)
    rate = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class work_center_rmp_auto(models.Model):
    name = models.CharField(max_length=200, default = 'Item Master Name')
    rmp = models.ForeignKey(rmp_auto, null=True)
    work_center = models.ForeignKey(work_center, null=True)
    rate = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    data = models.TextField(default='{}', null = True)
    def __str__(self):
        return self.name

class available_rm_sizes(models.Model):
    name = models.CharField(max_length=200, default = 'Board Name')
    auto_pl = models.ForeignKey(auto_price_list, null=True)
    d1 = models.IntegerField(default=0)
    d2 = models.IntegerField(default=0)
    d3 = models.IntegerField(default=0)
    d4 = models.IntegerField(default=0)
    exclude_size = models.BooleanField(default=False) 
    data = models.TextField(default='{}', null = True)
    class Meta:
        ordering = ('name', 'auto_pl')
    def spec_code(self):
        return self.auto_pl.spec_code
    def __str__(self):
        return self.name

class doctype(models.Model):
    name = models.CharField(max_length=200, default = 'Board Name')
    def __str__(self):
        return self.name

class document(models.Model):
    name = models.CharField(max_length=200, default = 'Board Name')
    doctype = models.ForeignKey(doctype, null=True)
    docfile = models.FileField(upload_to='documents/auto_pl/preview')
    tab_name = models.CharField(max_length=200, default = '')
    tab_id = models.IntegerField(default=0)
    def __str__(self):
        return self.name
    










