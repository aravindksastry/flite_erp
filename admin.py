from django.contrib import admin
from journal_mgmt.models import *
from django import forms

#from featherlite_erp import custom_admin_site

class transaction_rule_admin(admin.ModelAdmin):
    list_display = ('name', 'id', 'transaction_rule_code', 'data')

class inv_jour_inline(admin.TabularInline):
    model = inventory_journal
    extra = 4

class transaction_ref_admin(admin.ModelAdmin):
    list_display = ('name', 'id', 'created_date')

class ttype_department_admin(admin.ModelAdmin):
    list_display = ('name', 'report_data', 'data', 'data1')
        
class transaction_type_admin(admin.ModelAdmin):
    list_display = ('name', 'id', 'transaction_type_ref_no', 'transaction_rule', 'last_ref_no', 'debit_ttype1_ids', 'debit_ttype2_ids', 'data', 'data1')
    
class inventory_journal_admin(admin.ModelAdmin):
    list_display = ('name', 'id', 'item_master', 'transaction_ref', 'issue_qty', 'balance_qty', 'data', 'tax_format')
    
class coa_admin(admin.ModelAdmin):
    list_display = ('name', 'id', 'coa_no', 'coa_group')
    
class coa_group_admin(admin.ModelAdmin):
    list_display = ('name', 'id', 'coa_group_no', 'parent_coa_group')
    
class tax_head_admin(admin.ModelAdmin):
    list_display = ('name', 'tax_head_no', 'id', 'data')
    
class tax_format_admin(admin.ModelAdmin):
    list_display = ('name', 'id', 'data')
    
class item_master_admin(admin.ModelAdmin):
    list_display = ('id', 'created_date', 'last_updated', 'item_group', 'name', 'imported_item_code', 'imported_item_finish')
    list_filter = ['item_group']
    search_fields = ['name']

    
class auto_pl_admin(admin.ModelAdmin):
    list_display = ('id','name', 'created_date', 'last_updated', 'spec_code', 'item_department_ref')
    '''fieldsets = [
         ('RMP', {'fields' : ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9', 'p10', 'p11', 'p12', 'p13', 'p14', 'p15', 'p16', 'p17', 'p18', 'p19', 'p20'], 'classes':['collapse']}),
         #('Date Information', {'fields':['pub_date'], 'classes':['collapse']}),
         ]
    inlines = [ChoiceInline]'''
    search_fields = ['name']

class rmp_auto_admin(admin.ModelAdmin):
    list_display = ('id','name')
    search_fields = ['name']
    
class constants_admin(admin.ModelAdmin):
    list_display = ('id','name')
    search_fields = ['name']
    
class process_type_admin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ['name']
    
class vendor_price_admin(admin.ModelAdmin):
    list_display = ('id', 'item_name')
    search_fields = ['name']
    
class auto_pl_vendor_admin(admin.ModelAdmin):
    list_display = ('id', 'name', 'pl_auto_name', 'vendor')
    search_fields = ['name']
    
class auto_pl_work_center_admin(admin.ModelAdmin):
    list_display = ('id', 'name', 'pl_auto_name', 'work_center')
    search_fields = ['name']
    
class auto_rmp_vendor_admin(admin.ModelAdmin):
    list_display = ('id', 'name', 'rmp', 'vendor')
    search_fields = ['name']
    
class auto_rmp_work_center_admin(admin.ModelAdmin):
    list_display = ('id', 'name', 'rmp', 'work_center')
    search_fields = ['name']
    
class available_rm_sizes_admin(admin.ModelAdmin):
    list_display = ('id', 'name', 'auto_pl', 'spec_code', 'd1', 'd2', 'd3', 'd4')
    search_fields = ['name']

class plant_admin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ['name']
    
class packing_set(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ['name']

# Register your models here.

admin.site.register(coa_group, coa_group_admin)
admin.site.register(coa, coa_admin)
admin.site.register(inventory_journal, inventory_journal_admin)
admin.site.register(item_master, item_master_admin)
admin.site.register(item_group)
admin.site.register(vendor_price, vendor_price_admin)
admin.site.register(auto_price_list, auto_pl_admin)
admin.site.register(rmp_auto, rmp_auto_admin)
admin.site.register(constants, constants_admin)
admin.site.register(transaction_ref, transaction_ref_admin)
admin.site.register(transaction_rule, transaction_rule_admin)
admin.site.register(transaction_type, transaction_type_admin)
admin.site.register(ttype_department, ttype_department_admin)
admin.site.register(uom)
admin.site.register(other_terms)
admin.site.register(plant)
admin.site.register(payment_terms)
admin.site.register(country)
admin.site.register(state)
admin.site.register(city)
admin.site.register(work_center)
admin.site.register(tax_format)
admin.site.register(tax_head, tax_head_admin)
admin.site.register(imported_quotes)
admin.site.register(process_type, constants_admin)
admin.site.register(vendor_price_list_auto, auto_pl_vendor_admin)
admin.site.register(work_center_price_list_auto, auto_pl_work_center_admin)
admin.site.register(vendor_rmp_auto, auto_rmp_vendor_admin)
admin.site.register(work_center_rmp_auto, auto_rmp_work_center_admin)
admin.site.register(available_rm_sizes, available_rm_sizes_admin)




