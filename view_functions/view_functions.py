'''
Created on 01-Nov-2014

@author: aravind
'''
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect
from journal_mgmt.models import *
from django.template import RequestContext, loader
from django.views import generic
from django.core.urlresolvers import reverse
from journal_mgmt.view_functions.connect_functions import *
from journal_mgmt.view_functions.base_functions import *
from journal_mgmt.view_functions.report_functions import *
import ast
import xlsxwriter
import io
import decimal
from decimal import *
import psycopg2, datetime
from db_links.database_connection import *
from nesting.nest_functions import *
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Q
import re, copy


def inv_jour_create(tref, jour_detail, tpl_ref_no):
    ttype = tref.transaction_type
    trule = ttype.transaction_rule
    trule_data = ast.literal_eval(trule.data)
    tpl_ref_type = trule_data['attrib_list']['tpl_ref'][1]
    giv_discount = 0
    data_dict = {}
    print(str(tref.name) + str(jour_detail))
    if 'discount' in jour_detail[2]:
        giv_discount = jour_detail[2]['discount']
    if 'mod_qty' in jour_detail[2]:
        mod_qty = jour_detail[2]['mod_qty']
        data_dict['mod_qty'] = mod_qty
    error = []
    if float(jour_detail[1]) == 0:
        error.append(('No Qty Provided'))
        return(error)
    if tpl_ref_type == 'automatic' or tpl_ref_type == 'manual' or tpl_ref_type == 'tref_tpl':
        tpl_ref_no = tpl_ref_no
    elif tpl_ref_type == 'none' or tpl_ref_type == '':
        tpl_ref_no = 0
    elif tpl_ref_type == 'self':
        tpl_ref_no = tref.id
    location_ref = trace_location(tref.id)
    if trule_data['code'] == 1:
        location_ref_id = location_ref.id
        '''jour_detail = (<item_master or debit_journal1>_id, issue_qty, {'discount':20})'''
        '''tpl_ref_no is needed only when creating list'''
        item_master_obj = get_object_or_404(item_master, pk = jour_detail[0])
        inv_jour = tref.inventory_journal_set.create(item_master = item_master_obj, issue_qty = jour_detail[1], location_ref_val = location_ref_id, \
                                                     tpl_ref_no = int(tpl_ref_no), discount = giv_discount, data = data_dict)
    elif trule_data['code'] == 3 or trule_data['code'] == 6:
        '''jour_detail = (<parent_inv_journal>_id, issue_qty, {'discount':20})'''
        debit_jour1 = get_object_or_404(inventory_journal, pk = jour_detail[0])
        '''get all inventory journals of this transaction_ref where parent is the same as supplied in jour_detail[0]'''
        #all_issues = tref.inventory_journal_set.filter(debit_journal1 = debit_jour1)
        all_cur_issues = inventory_journal.objects.filter(transaction_ref = tref, debit_journal1 = debit_jour1)
        tot_cur_issue = 0.0
        for cur_issue in all_cur_issues:
            tot_cur_issue += float(cur_issue.issue_qty)
        tot_cur_issue += float(jour_detail[1])
        if float(tot_cur_issue) <= float(debit_jour1.balance_qty):
            if location_ref == 'debit1':
                location_ref_id = debit_jour1.location_ref_val
            else:
                location_ref_id = location_ref.id
            if tpl_ref_type == 'debit1':
                tpl_ref_no = debit_jour1.tpl_ref_no
            inv_jour = tref.inventory_journal_set.create(debit_journal1 = debit_jour1, item_master = debit_jour1.item_master, \
                                                         issue_qty = decimal.Decimal(jour_detail[1]), tpl_ref_no = int(tpl_ref_no), \
                                                         location_ref_val = location_ref_id, discount = giv_discount, data = data_dict)
        else:
            error.append((debit_jour1.name + 'Exceeding the available balance'))
    if (error == []):
        inv_jour.name = inv_jour.item_master.name
        inv_jour.save()
        return(inv_jour)
    return(error)


def inv_jour_bulk_save(post_data):
    prefix = "inventory_journal_set-"
    parent_bal1 = {}
    error = []
    test = 0
    tref = get_object_or_404(transaction_ref, pk=post_data['pk'])
    ttype = tref.transaction_type
    trule = ttype.transaction_rule
    trule_data = ast.literal_eval(trule.data)
    trule_code = trule_data['code']
    ttype_data = ast.literal_eval(str(ttype.data))
    trule_data = ast.literal_eval(ttype.transaction_rule.data)
    i = 1
    while (i < 1000):
        cur_jour_id = prefix + str(i) + "-id"
        if(cur_jour_id in post_data):
            cur_inv_jour = get_object_or_404(inventory_journal, pk=post_data[cur_jour_id])
            cur_inv_jour.issue_qty = Decimal(post_data[prefix + str(i) + "-issue_qty"])
            if(trule_code == 3 or trule_code == 6):
                parent_jour1 = cur_inv_jour.debit_journal1
                if(cur_inv_jour.debit_journal1 in parent_bal1):
                    parent_bal1[cur_inv_jour.debit_journal1] -= cur_inv_jour.issue_qty
                else:
                    parent_bal1[cur_inv_jour.debit_journal1] = parent_jour1.balance_qty - cur_inv_jour.issue_qty
                if(parent_bal1[cur_inv_jour.debit_journal1] < 0):
                    error.append((post_data[cur_jour_id],"ERROR! Balance Qty Available:" + str(parent_jour1.balance_qty) \
                                  + ", Posted:" + str(parent_bal1[cur_inv_jour.debit_journal1])))
            elif(trule_code == 1):
                #return(error)
                '''Error Conditions to be listed here for manual list'''
        else:
            break
        i += 1
    i = 1
    if (error == []):
        while (i < 1000):
            cur_jour_id = prefix + str(i) + "-id"
            if(cur_jour_id in post_data):
                cur_inv_jour = get_object_or_404(inventory_journal, pk=post_data[cur_jour_id])
                cur_inv_jour.issue_qty = Decimal(post_data[prefix + str(i) + "-issue_qty"])
                cur_inv_jour.discount = 0
                cur_inv_jour.surcharge = 0
                cur_inv_jour.tax_format = get_object_or_404(tax_format, id = 1)
                if 'discount' in trule_data['attrib_list']:
                    cur_inv_jour.discount = Decimal(post_data[prefix + str(i) + "-discount"])
                if 'surcharge' in trule_data['attrib_list']:
                    cur_inv_jour.surcharge = Decimal(post_data[prefix + str(i) + "-surcharge"])
                if 'tax' in trule_data['attrib_list']:
                    cur_inv_jour.tax_format = get_object_or_404(tax_format, id = int(post_data[prefix + str(i) + "-tax_format"]))
                cur_inv_jour.save()
            else:
                break
            i += 1
    update_inv_jour_rate(tref)
    return(error)

def inv_jour_list(tref):
    inv_jour_list = []
    ttype_obj = tref.transaction_type
    ttype_data = ast.literal_eval(ttype_obj.data)
    trule_data = ast.literal_eval(ttype_obj.transaction_rule.data)
    trule_code  = trule_data['code']
    tpl_match_type = None
    if trule_code == 6:
        #location_obj = fetch_allocation_location(tref.id)
        #location_obj = credit_location_tref(tref.id)
        tpl_match_type = ttype_data['allocation_type']
        if tpl_match_type == 'stock':
            cur_tpl_ref_no = 0
    cur_inv_jour_list = inventory_journal.objects.filter(transaction_ref = tref).order_by('name')
    if(cur_inv_jour_list == []):
        return(inv_jour_list)
    else:
        for cur_inv_jour in cur_inv_jour_list:
            add_data = {}
            add_data['tpl_info'] = {}
            add_data['oc_info'] = {}
            if not cur_inv_jour.tpl_ref_no == 0:
                tpl_obj = get_object_or_404(transaction_ref, id = int(cur_inv_jour.tpl_ref_no))
                add_data['tpl_info']['tpl_obj'] = tpl_obj
                add_data['tpl_info']['tpl_data'] = ast.literal_eval(tpl_obj.data)
            else:
                tpl_obj = None
            if trule_code == 6:
                add_data['stock_deb2'] = 0.0
                if tpl_match_type == 'tpl_match':
                    cur_tpl_ref_no = cur_inv_jour.tpl_ref_no
                location_obj = get_object_or_404(location, id = int(cur_inv_jour.location_ref_val))
                cur_available_stk_obj = current_stock.objects.filter(location_ref = location_obj, \
                                                  item_master_ref = cur_inv_jour.item_master, tpl_ref_no = cur_tpl_ref_no)
                if len(cur_available_stk_obj) > 0:
                    add_data['stock_deb2'] = cur_available_stk_obj[0].cur_stock
                else:
                    add_data['stock_deb2'] = 0.0
            print('Inventory Journal Data ' + cur_inv_jour.data)
            '''
            in case additional parameters are to be displayed in a particular tref_detail 
            page in inv_jour, this functionality is to be completed
            if 'add_jour_index' in ttype_data:
                add_param = ttype_data['add_jour_index']
                for cur_param in add_param:
                    jour_index_add_param(cur_inv_jour.id, cur_param['param'])'''
            inv_jour_list.append((cur_inv_jour, ast.literal_eval(str(cur_inv_jour.data)), add_data))
    return(inv_jour_list)

def inv_jour_load_list(cur_tref, parent_tref):
    load_inv_jour_list = []
    load_inv_jour_obj_list = []
    parent_inv_jour_list = inventory_journal.objects.filter(transaction_ref = parent_tref).order_by('name')
    parent_inv_jour_list = parent_inv_jour_list.exclude(balance_qty = 0)
    cur_tref_data = ast.literal_eval(cur_tref.data)
    cur_ttype_data = ast.literal_eval(cur_tref.transaction_type.data)
    inv_jour_config = {'filter_type':'none'}
    if 'load_filter' in cur_ttype_data:
        inv_jour_config = cur_ttype_data['load_filter']
    if inv_jour_config['filter_type'] == 'none':
        load_inv_jour_obj_list = parent_inv_jour_list
    elif inv_jour_config['filter_type'] == 'purchase_pl':
        '''purchase_pl filter type is used to give out inventory journals which 
        are present in the purchase_pl for selected vendor in transaction_type'''
        vendor_id = int(cur_tref_data['field_list'][inv_jour_config['key']][0])
        vendor_obj = get_object_or_404(coa, id=vendor_id)
        for cur_parent_inv_jour in parent_inv_jour_list:
            item_master_obj = cur_parent_inv_jour.item_master
            availability = vendor_price.objects.filter(vendor = vendor_obj, item = item_master_obj)
            if len(availability) > 0:
                load_inv_jour_obj_list.append(cur_parent_inv_jour)
    elif inv_jour_config['filter_type'] == 'wc_pl':
        '''wc_pl filter type is used to give out inventory journals which 
        are present in the work_center_pl for selected work_center in transaction_type'''
        wc_id = int(cur_tref_data['field_list'][inv_jour_config['key']][0])
        wc_obj = get_object_or_404(work_center, id=wc_id)
        for cur_parent_inv_jour in parent_inv_jour_list:
            item_master_obj = cur_parent_inv_jour.item_master
            availability = work_center_price.objects.filter(work_center = wc_obj, item = item_master_obj)
            if len(availability) > 0:
                load_inv_jour_obj_list.append(cur_parent_inv_jour)
    '''converting object list to array with tuples having parsed data'''
    for inv_jour in load_inv_jour_obj_list:
        load_inv_jour_list.append((inv_jour, ast.literal_eval(str(inv_jour.data))))
    return(load_inv_jour_list)

def debit1_jour_list(cur_tref_id, debit1_tref_id):
    debit1_tref = get_object_or_404(transaction_ref, pk=debit1_tref_id)
    cur_tref = get_object_or_404(transaction_ref, pk=cur_tref_id)
    cur_ttype = cur_tref.transaction_type
    cur_ttype_data = ast.literal_eval(str(cur_ttype.data))
    cur_trule = cur_ttype.transaction_rule
    cur_trule_data = ast.literal_eval(str(cur_trule.data))
    cur_tref_data = ast.literal_eval(str(cur_tref.data))
    inv_jour_list = []
    if cur_trule_data['debit_filter'] == 'none':
        inv_jour_qset = inventory_journal.objects.filter(transaction_ref = debit1_tref).order_by('name')
        for inv_jour in inv_jour_qset:
            inv_jour_list.append((inv_jour, ast.literal_eval(str(inv_jour.data))))
    elif cur_trule_data['debit_filter']['type'] == 'vendor_pl':
        vendor_id = int(cur_tref_data['field_list']['vendor'][0])
        vendor_obj = get_object_or_404(coa, id = vendor_id) 
        inv_jour_qset = inventory_journal.objects.filter(transaction_ref = debit1_tref).order_by('name')
        for inv_jour in inv_jour_qset:
            vendor_pl = vendor_price.objects.filter(item = inv_jour.item_master, vendor = vendor_obj)
            if len(vendor_pl) > 0:
                inv_jour_list.append((inv_jour, ast.literal_eval(str(inv_jour.data))))
        '''Incomplete code'''
    elif cur_trule_data['debit_filter']['type'] == 'work_center_pl':
        work_center_id = int(cur_tref_data['field_list']['work_center'][0])
        work_center_obj = get_object_or_404(work_center, id = work_center_id) 
        inv_jour_qset = inventory_journal.objects.filter(transaction_ref = debit1_tref).order_by('name')
        for inv_jour in inv_jour_qset:
            work_center_pl = work_center_price.objects.filter(item = inv_jour.item_master, work_center = work_center_obj)
            if len(work_center_pl) > 0:
                inv_jour_list.append((inv_jour, ast.literal_eval(str(inv_jour.data))))
    return(inv_jour_list)


def child_tref_list(tref):
    child_trefs = []
    all_ttypes = transaction_type.objects.all()
    ttype_ref_no = tref.transaction_type.transaction_type_ref_no
    inv_jour_set = inventory_journal.objects.filter(transaction_ref = tref)
    app_deb_list = {}
    trule_data = ast.literal_eval(tref.transaction_type.transaction_rule.data)
    child_ttypes = {}
    for cur_child_ttype in all_ttypes:
        cur_debit_ttypes = ast.literal_eval(str(cur_child_ttype.debit_ttype1_ids))
        if(ttype_ref_no in cur_debit_ttypes):
            child_ttypes[cur_child_ttype.id] = cur_child_ttype
        '''app_deb_list = {ttype_id:{'ttype_obj':ttype_obj, 'tref_list':{tref_id:tref_obj}, ....}'''
        if not cur_child_ttype.id in app_deb_list and ttype_ref_no in cur_debit_ttypes:
            app_deb_list[cur_child_ttype.id] = {'ttype_obj':cur_child_ttype, 'tref_list':{}}
    child_inv_jour_set = []
    for cur_inv_jour in inv_jour_set:
        cur_child_inv_jour_set = inventory_journal.objects.filter(debit_journal1 = cur_inv_jour)
        '''exclude all inventory journal whose transaction reference is scrapped / forced_close before submitting'''
        cur_child_inv_jour_set = cur_child_inv_jour_set.exclude(Q(transaction_ref__force_close = True) & Q(transaction_ref__submit = False))
        for cur_child in cur_child_inv_jour_set:
            child_inv_jour_set.append(cur_child)
            '''for cur_inv_jour in child_inv_jour_set:'''
            child_tref = cur_child.transaction_ref
            child_ttype = child_tref.transaction_type
            if not child_tref.id in app_deb_list[child_ttype.id]['tref_list']:
                app_deb_list[child_ttype.id]['tref_list'][child_tref.id] = child_tref
    for cur_ttype_id, cur_tref_list_dict in app_deb_list.items():
        ttype_obj = get_object_or_404(transaction_type, id = cur_ttype_id)
        tref_list = transaction_ref.objects.filter(transaction_type = ttype_obj)
        tref_list = tref_list.exclude(submit = True)
        tref_list = tref_list.exclude(force_close = True)
        for cur_tref in tref_list:
            inv_jour_list = inventory_journal.objects.filter(transaction_ref = cur_tref)
            if len(inv_jour_list) == 0:
                app_deb_list[cur_ttype_id]['tref_list'][cur_tref.id] = cur_tref
    for cur_child_ttype_key, cur_child_ttype_val in child_ttypes.items():
        cur_tref_list = app_deb_list[cur_child_ttype_key]['tref_list']
        tref_obj_list = []
        for cur_tref_id, cur_tref_obj in cur_tref_list.items():
            tref_obj_list.append(cur_tref_obj)
        app_child_tref = (cur_child_ttype_val, tref_obj_list)
        child_trefs.append(app_child_tref)
    '''child_trefs = [(transaction_type_obj, (transaction_ref1_obj, treansaction_ref2_obj,...)), ((), ())...]'''
    return(child_trefs)

def get_chain_tref(tref):
    child_trefs = transaction_ref.objects.filter(chain_tref = tref.id)
    return(child_trefs)

def field_list_collate_default(field_list):
    #ret = []
    ret = {}
    for cur_field in field_list:
        if(cur_field[1] == 'input'):
            #ret.append((cur_field[3]['name'], cur_field[2]))
            ret[cur_field[3]['name']] = cur_field[2]
        if(cur_field[1] == 'select'):
            '''No Default Selection by default - Do nothing'''
            '''This is for default selection [0] is the default selection - the first element in the drop box'''
            opt_list = select_boxes({'name':cur_field[2]})
            ret[cur_field[3]['name']] = [opt_list[0].id, opt_list[0].name]
    return(ret)

def prepare_children(coa_groups):
    ret = []
    for cur_coa_group in coa_groups:
        children_coa_group = cur_coa_group.coa_group_set.all()
        children_coa = cur_coa_group.coa_set.all()
        ret.append([cur_coa_group, children_coa_group, children_coa])
    return(ret)

def coa_list(coa_grp):
    ch_of_ac_list = coa_grp.coa_set.all()
    ret = []
    for cur_ch_of_ac in ch_of_ac_list:
        ret.append((cur_ch_of_ac, ast.literal_eval(str(cur_ch_of_ac.data))))
    return(ret)

def tref_links(tref):
    add_links = []
    ttype = tref.transaction_type
    ttype_data = ast.literal_eval(str(ttype.data))
    if 'add_links' in ttype_data:
        for cur_ttype_link in ttype_data['add_links']:
            link_disp_name = cur_ttype_link[0]
            link_det_dict = cur_ttype_link[1]
            link_recognizer_str = link_det_dict['name']
            if link_recognizer_str == 'child_tpl_index':
                '''child_tpl_index refers to all tpls that pertain to this Order Confirmation Transaction'''
                oc_tref = tref
                rcv_tpl_ref_no = 2
                rcv_tpl_ttype = get_object_or_404(transaction_type, transaction_type_ref_no = rcv_tpl_ref_no)
                cur_link = reverse('journal_mgmt:tref_index', args=(rcv_tpl_ttype.id,)) + '?ds_order_confirmation=' + str(oc_tref.id)
                #cur_link = {'url_name':'tref_index', 'args':(ttype.id,), 'get':'?q=&data_search=' +  str(tref.name)}
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'tpl_auto_plan':
                cur_link = reverse('journal_mgmt:tpl_auto_plan', args=(tref.id,))
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'mrs_preview_multi':
                cur_link = reverse('journal_mgmt:mrs_preview', args=(tref.id,)) + '?searched_name=&searched_data=' +  \
                            tref.name + '&index_filter=show_all' + '&multi_layer=True'
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'nes_mrs_preview_multi':
                cur_link = reverse('journal_mgmt:mrs_preview', args=(tref.id,)) + '?searched_name=&searched_data=' + \
                            tref.name + '&index_filter=show_all' + '&multi_layer=False' + '&nested=True'
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'mrs_preview_single':
                cur_link = reverse('journal_mgmt:mrs_preview', args=(tref.id,)) + '?searched_name=&searched_data=' + \
                            tref.name + '&index_filter=show_all' + '&multi_layer=False'
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'mrs_preview_single':
                cur_link = reverse('journal_mgmt:mrs_preview', args=(tref.id,)) + '?searched_name=&searched_data=' + \
                            tref.name + '&index_filter=show_all' + '&multi_layer=False' + '&nested=True'
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'vendor_pl':
                tref_data = ast.literal_eval(str(tref.data))
                vendor_id = int(tref_data['field_list']['vendor'][0])
                vendor_id = str(vendor_id)
                cur_link = reverse('journal_mgmt:vendor_pl_detail') + '?sel_vendor_id=' + vendor_id
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'vendor_pl_index':
                tref_data = ast.literal_eval(str(tref.data))
                if 'filter' in link_det_dict:
                    if link_det_dict['filter'] == 'tref_vendor':
                        vendor_id = int(tref_data['field_list']['vendor'][0])
                        vendor_id = str(vendor_id)
                        cur_link = reverse('journal_mgmt:vendor_pl_index') + '?sel_vendor_id=' + vendor_id
                else:
                    cur_link = reverse('journal_mgmt:vendor_pl_index')
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'wc_pl_index':
                tref_data = ast.literal_eval(str(tref.data))
                if 'filter' in link_det_dict:
                    if link_det_dict['filter'] == 'tref_work_center':
                        wc_id = int(tref_data['field_list']['work_center'][0])
                        wc_id = str(wc_id)
                        cur_link = reverse('journal_mgmt:wc_pl_index') + '?sel_wc_id=' + wc_id
                else:
                    cur_link = reverse('journal_mgmt:wc_pl_index')
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'job_shop_order':
                cur_link = reverse('journal_mgmt:job_shop_order_preview', args=(tref.id,))
                add_links.append((link_disp_name, cur_link))
            if link_recognizer_str == 'production_auto_plan':
                cur_link = reverse('journal_mgmt:production_auto_plan', args=(tref.id,))
                add_links.append((link_disp_name, cur_link))
    return(add_links)

def fetch_tref_data(ttype, tref, config):
    '''config = {'tpl_ref':tpl_no} - Needed when auto create list with no debit / custom debit'''
    data = {}
    data['test_working'] = 0
    trule = ttype.transaction_rule.transaction_rule_code
    data['trule'] = trule
    '''These are options for debit_transaction1/2/3 in transaction_ref table & parent transaction_type data'''
    data['debit_transaction1_opt'] = parent_tref_list(ttype.debit_ttype1_ids)
    data['debit_transaction2_opt'] = parent_tref_list(ttype.debit_ttype2_ids)
    data['debit_transaction3_opt'] = parent_tref_list(ttype.debit_ttype3_ids)
    ttype_data = ast.literal_eval(str(ttype.data))
    ttype_data1 = ast.literal_eval(str(ttype.data1))
    '''The Parsed data in transaction_type table for the given transaction_ref referenced key'''
    data['transaction_type'] = (ttype, ttype_data, {'ttype_data1':ttype_data1})
    '''format for carrying select_boxes -> {'labelname':[('option_id', 'option_name'),....]}'''
    data['select_boxes'] = []
    field_list = data['transaction_type'][1]['field_list']
    for cur_field in field_list:
        if(cur_field[1] == 'select'):
            data['select_boxes'].append((cur_field[3]['name'], select_boxes({'name':cur_field[2]})))
    data['tax_format_opt'] = []
    data['other_tax_format_opt'] = []
    data['live_tpl_opt'] = live_tpl_list()
    for cur_tax_format in select_boxes({'name':'tax_format'}):
        data['tax_format_opt'].append((cur_tax_format, ast.literal_eval(str(cur_tax_format.data))))
    for cur_tax_format in select_boxes({'name':'other_tax_format'}):
        data['other_tax_format_opt'].append((cur_tax_format, ast.literal_eval(str(cur_tax_format.data))))
    '''feed default tref_data from transaction_type -> data'''
    data['tref_data'] = {}
    data['tref_data']['field_list'] = field_list_collate_default(data['transaction_type'][1]['field_list'])
    if(tref != []):
        data['add_links'] = tref_links(tref)
        test_str = str(tref.data)
        data['tref_data'] = ast.literal_eval(str(test_str))
        data['child_trefs'] = child_tref_list(tref)
        data['chain_trefs'] = get_chain_tref(tref)
        if(trule == 1):
            data['item_group_opt'] = item_group.objects.all().order_by('name')
            #data['item_master_opt'] = item_master.objects.all()
        inv_jour = inv_jour_list(tref)
        if(inv_jour != []):
            data['inv_jour'] = inv_jour
    return(data)

def field_list_collate(post_data, field_list):
    ret = {}
    for cur_field in field_list:
        print('Cur Field : ' + str(cur_field))
        if (cur_field[3]['name'] in post_data):
            if(cur_field[1] == 'input'):
                ret[cur_field[3]['name']] = post_data[cur_field[3]['name']]
            elif(cur_field[1] == 'select'):
                print('Test - : ' + str(select_boxes({'name':cur_field[2]})))
                for opt in select_boxes({'name':cur_field[2]}):
                    print('OPT Checks ID : ' + str(opt.id) + ' post data' + post_data[cur_field[3]['name']])
                    if(opt.id == int(post_data[cur_field[3]['name']])):
                        ret[cur_field[3]['name']] = (opt.id, opt.name)
                        print('Ret 1 : ' + str(ret))
        else:
            if(cur_field[1] == 'input'):
                ret[cur_field[3]['name']] = cur_field[2]
            elif(cur_field[1] == 'select'):
                opt = select_boxes({'name':cur_field[2]})
                ret[cur_field[3]['name']] = (opt[0], opt[0].name)
        print('Ret 2 : ' + str(ret))
    return(ret)

def tref_submit(tref_id):
    tref_obj = get_object_or_404(transaction_ref, id=int(tref_id))
    if not tref_obj.submit == True:
        ttype_obj = tref_obj.transaction_type
        trule_obj = ttype_obj.transaction_rule
        ttype_data = ast.literal_eval(ttype_obj.data)
        trule_data = ast.literal_eval(trule_obj.data)
        tref_obj.name = str(ttype_data['short_hand']) + "_" + str(ttype_obj.last_ref_no + 1)
        tref_obj.ref_no = ttype_obj.last_ref_no + 1
        tref_obj.submit = True
        tref_obj.active = True
        ttype_obj.last_ref_no += 1
        ttype_code = trule_data['code']
        error = False
        clearence = pre_submit_activity(tref_id)
        if clearence == False:
            return(tref_obj)
        inv_jour_set = inventory_journal.objects.filter(transaction_ref = tref_obj)
        if ttype_code == 3 or ttype_code == 6:
            for cur_inv_jour in inv_jour_set:
                tot_cur_issue_deb1 = 0
                all_cur_issue_deb1 = inventory_journal.objects.filter(debit_journal1 = cur_inv_jour.debit_journal1,\
                                                                  transaction_ref = cur_inv_jour.transaction_ref)
                for cur_issue_deb1 in all_cur_issue_deb1:
                    tot_cur_issue_deb1 += cur_issue_deb1.issue_qty
                if tot_cur_issue_deb1 > cur_inv_jour.debit_journal1.balance_qty:
                    error = True
                    break
                if ttype_code == 6:
                    tot_cur_issue_deb2 = 0
                    all_cur_issue_deb2 = inventory_journal.objects.filter(debit_journal2 = cur_inv_jour.debit_journal2,\
                                                                  transaction_ref = cur_inv_jour.transaction_ref)
                    for cur_issue_deb2 in all_cur_issue_deb2:
                        tot_cur_issue_deb2 += cur_issue_deb2.issue_qty
                    if tot_cur_issue_deb2 > cur_inv_jour.debit_journal2.balance_qty:
                        error = True
                        break
            if error == False:
                for cur_inv_jour in inv_jour_set:
                    cur_item_master = cur_inv_jour.item_master
                    cur_issue_qty = float(cur_inv_jour.issue_qty)
                    cur_inv_jour.balance_qty = cur_issue_qty
                    parent_jour1 = cur_inv_jour.debit_journal1
                    deb1_ttype = parent_jour1.transaction_ref.transaction_type
                    deb1_ttype_data = ast.literal_eval(deb1_ttype.data)
                    if 'stock_credit' in ttype_data:
                        cur_location_obj = get_object_or_404(location, id = int(cur_inv_jour.location_ref_val))
                        stk_obj_avail = current_stock.objects.filter(location_ref = cur_location_obj, \
                                                                     tpl_ref_no = cur_inv_jour.tpl_ref_no, item_master_ref = cur_item_master)
                        if len(stk_obj_avail) == 0:
                            cur_stk_obj = current_stock(location_ref = cur_location_obj, tpl_ref_no = cur_inv_jour.tpl_ref_no, \
                                                        item_master_ref = cur_item_master)
                            cur_stk_obj.save()
                        cur_stk_obj = get_object_or_404(current_stock, location_ref = cur_location_obj, \
                                                        tpl_ref_no = cur_inv_jour.tpl_ref_no, item_master_ref = cur_item_master)
                        cur_stk_bal = float(cur_stk_obj.cur_stock)
                        new_stk_bal = cur_stk_bal + cur_issue_qty
                        cur_stk_obj.cur_stock = new_stk_bal
                        '''Modifying the stock rate'''
                        add_val = float(cur_inv_jour.taxed_value)
                        cur_stk_val = float(cur_stk_obj.tot_value)
                        new_stk_val = cur_stk_val + add_val
                        if new_stk_bal == 0:
                            new_stk_rate = 0
                        else:
                            new_stk_rate = new_stk_val / new_stk_bal
                        cur_stk_obj.cur_rate = new_stk_rate
                        cur_stk_obj.tot_value = new_stk_val
                        '''End of stock rate Modification'''
                        cur_stk_obj.save()
                    if 'stock_credit' in deb1_ttype_data:
                        deb1_location_obj = get_object_or_404(location, id = int(parent_jour1.location_ref_val))
                        deb1_stk_obj = get_object_or_404(current_stock, location_ref = deb1_location_obj, tpl_ref_no = parent_jour1.tpl_ref_no, \
                                                         item_master_ref = cur_item_master)
                        cur_deb1_stk_bal = float(deb1_stk_obj.cur_stock)
                        new_deb1_stk_bal = cur_deb1_stk_bal - cur_issue_qty
                        deb1_stk_obj.cur_stock = new_deb1_stk_bal
                        '''Modifying the stock rate'''
                        red_val = float(deb1_stk_obj.cur_rate) * cur_issue_qty
                        cur_stk_val = float(deb1_stk_obj.tot_value)
                        new_stk_val = cur_stk_val - red_val
                        if new_deb1_stk_bal == 0:
                            new_stk_rate = 0
                        else:
                            new_stk_rate = new_stk_val / new_deb1_stk_bal
                        deb1_stk_obj.cur_rate = new_stk_rate
                        deb1_stk_obj.tot_value = new_stk_val
                        '''End of stock rate Modification'''
                        deb1_stk_obj.save()
                    cur_parent_jour1_bal = float(parent_jour1.balance_qty)
                    new_parent_jour1_bal = cur_parent_jour1_bal - cur_issue_qty
                    parent_jour1.balance_qty = new_parent_jour1_bal
                    parent_jour1.save()
                    #jour1_tref = transaction_ref 
                    if ttype_code == 6:
                        parent_jour2 = cur_inv_jour.debit_journal2
                        deb2_ttype = parent_jour2.transaction_ref.transaction_type
                        deb2_ttype_data = ast.literal_eval(deb2_ttype.data)
                        if 'stock_credit' in deb2_ttype_data:
                            deb2_location_obj = get_object_or_404(location, id = int(parent_jour2.location_ref_val))
                            deb2_stk_obj = get_object_or_404(current_stock, location_ref = deb2_location_obj, tpl_ref_no = parent_jour2.tpl_ref_no, \
                                                             item_master_ref = cur_item_master)
                            cur_deb2_stk_bal = float(deb2_stk_obj.cur_stock)
                            new_deb2_stk_bal = cur_deb2_stk_bal - cur_issue_qty
                            deb2_stk_obj.cur_stock = new_deb2_stk_bal
                            '''Modifying the stock rate'''
                            red_val = float(deb2_stk_obj.cur_rate) * cur_issue_qty
                            cur_stk_val = float(deb2_stk_obj.tot_value)
                            new_stk_val = cur_stk_val - red_val
                            if new_deb2_stk_bal == 0:
                                new_stk_rate = 0
                            else:
                                new_stk_rate = new_stk_val / new_deb2_stk_bal
                            deb2_stk_obj.cur_rate = new_stk_rate
                            deb2_stk_obj.tot_value = new_stk_val
                            '''End of stock rate Modification'''
                            deb2_stk_obj.save()
                        cur_parent_jour2_bal = float(parent_jour2.balance_qty)
                        new_parent_jour2_bal = cur_parent_jour2_bal - cur_issue_qty
                        parent_jour2.balance_qty = new_parent_jour2_bal
                        parent_jour2.save()
                        '''new_bal = parent_jour2.balance_qty - cur_issue_qty
                        parent_jour2.balance_qty = new_bal
                        cur_inv_jour.save()
                        parent_jour2.save()'''
                    cur_inv_jour.save()
                '''this bit of code is written in order to make old transaction_ref - 
                which are closed (all bal qty emptied) as in active so that they don't appear in parent tref select box'''
                check_tref_obj_list = real_parent_tref_list(tref_obj)
                for cur_parent_tref in check_tref_obj_list:
                    inv_jour_list = inventory_journal.objects.filter(transaction_ref = cur_parent_tref, balance_qty__gt = 0)
                    if len(inv_jour_list) == 0:
                        cur_parent_tref.active = False
                        cur_parent_tref.save()
        elif ttype_code == 1:
            for cur_inv_jour in inv_jour_set:
                cur_inv_jour.balance_qty = cur_inv_jour.issue_qty
                cur_inv_jour.save()
        if error == False:
            ttype_obj.save()
            tref_obj.save()
            tref_obj = get_object_or_404(transaction_ref, id=int(tref_id))
            post_submit_activity(tref_obj.id)
    tref_obj = get_object_or_404(transaction_ref, id = int(tref_id))
    return(tref_obj)

def auto_create_tref(ttype_ref_id, tref_dict, inv_jour, submit_status, config):
    '''config is a dictionary, currently used to aqdd chain_tref, may be blank dictionary if not used'''
    ttype = get_object_or_404(transaction_type, transaction_type_ref_no = ttype_ref_id)
    ttype_data = ast.literal_eval(ttype.data)
    if len(inv_jour) > 0:
        inv_jour_qty_exists = False
        for cur_inv_jour in inv_jour:
            if cur_inv_jour[1] > 0:
                inv_jour_qty_exists = True
                break
        if inv_jour_qty_exists == False:
            return('no inv_jour')
    tref = transaction_ref()
    tref_data = {}
    tref_field_data = field_list_collate_default(ttype_data)
    tref.data = tref_dict
    tref.submit = False
    tref.active = False
    tref.transaction_type = ttype
    ch_tref = 0
    if 'chain_tref' in config:
        ch_tref = config['chain_tref']
    tref.chain_tref = ch_tref
    tref.name = ttype_data['short_hand'] + '_draft_' + str(tref.id)
    tref.save()
    tref = get_object_or_404(transaction_ref, id = tref.id)
    tref.name = ttype_data['short_hand'] + '_draft_' + str(tref.id)
    tref.save()
    tref = get_object_or_404(transaction_ref, id = tref.id)
    trule = ttype.transaction_rule
    trule_data = ast.literal_eval(trule.data)
    #tpl_ref_no = 0
    tpl_ref_data = trule_data['attrib_list']['tpl_ref']
    tpl_ref_type = tpl_ref_data[1]
    '''if tpl_ref_type == 'none':
        tpl_ref_no = 0
    elif tpl_ref_type == 'self':
        tpl_ref_no = tref.id
        
        tref.name = ttype_data['short_hand'] + '_' + str(ttype.last_ref_no + 1)
        tref.submit = True
        tref.active = True
        ttype.last_ref_no += 1
        ttype.save()
    tref.save()'''
    '''
    if ttype_data['code'] == 1
        inv_jour = [(pn, qty, det), (pn, qty, det)...]
    if ttype_data['code'] == 3 or ttype_data['code'] == 6
        inv_jour = [(inv_jour_id, qty, det), (inv_jour_id, qty, det)...]
    '''
    for cur_inv_jour in inv_jour:
        inv_jour_create(tref, cur_inv_jour, cur_inv_jour[2]['tpl_ref'])
    update_inv_jour_rate(tref)
    if submit_status == True:
        tref_submit(tref.id)
    tref = get_object_or_404(transaction_ref, id = tref.id)
    return(tref)


def auto_create_prod_ind(location_ref_id, giv_tpl_ref_no, bom_feed_list):
    '''pro_ind_list = [(item_master_id, qty), (item_master_id, qty), ....]
    giv_tpl_ref_no = tpl_id (transaction_ref's primary_key)'''
    bom_data = bom_collation(bom_feed_list, {'multi_layer':True})
    fin_proc_list = bom_data['final_process_list']
    sub_proc_list = bom_data['sub_process_list']
    pro_ind_list = fin_proc_list + sub_proc_list
    new_pro_ind_list = []
    for cur_pro_ind_jour in pro_ind_list:
        cur_pro_ind_jour = list(cur_pro_ind_jour)
        cur_pro_ind_jour.append({'tpl_ref':giv_tpl_ref_no})
        new_pro_ind_list.append(cur_pro_ind_jour)
    tpl_tref_obj = get_object_or_404(transaction_ref, id=int(giv_tpl_ref_no))
    tpl_inv_jour_set = inventory_journal.objects.filter(transaction_ref = tpl_tref_obj)
    fin_process_dict = {}
    pro_ttype_obj = get_object_or_404(transaction_type, transaction_type_ref_no = 8)
    pro_tref_dict = fetch_tref_data(pro_ttype_obj, [], {})['tref_data']['field_list']
    for cur_process in fin_proc_list:
        fin_process_dict[cur_process[0]] = float(cur_process[1])
    pro_ind_tref = auto_create_tref(8, pro_tref_dict, new_pro_ind_list, True, {'chain_tref':giv_tpl_ref_no})
    for cur_tpl_inv_jour in tpl_inv_jour_set:
        if cur_tpl_inv_jour.item_master.id in fin_process_dict:
            proc_qty = fin_process_dict[cur_tpl_inv_jour.item_master.id]
        else:
            proc_qty = 0.0
        new_tpl_bal_qty = float(cur_tpl_inv_jour.balance_qty) - proc_qty
        cur_tpl_inv_jour.balance_qty = new_tpl_bal_qty
        cur_tpl_inv_jour.save()
    return(pro_ind_tref)
    
def get_job_shop_ttype(tref_id):
    '''tref_id refers to the transaction_ref_id of job/shop order process'''
    ttype_dict = {}
    tref = get_object_or_404(transaction_ref, id = tref_id)
    ttype_ref_no = tref.transaction_type.transaction_type_ref_no
    tref_data = ast.literal_eval(tref.data)
    ttype_dict['material_inward'] = get_object_or_404(transaction_type, transaction_type_ref_no = 28)
    if ttype_ref_no == 12:
        '''
        --- JOB ORDER ---
        ttype_ref_no = 12 corresponds to job order process
        ttype_ref_no = 13 corresponds to job order receivable
        ttype_ref_no = 14 corresponds to job order pre nested raw material
        ttype_ref_no = 15 corresponds to job order offcut
        ttype_ref_no = 46 corresponds to job order nested rm req
        ttype_ref_no = 30 corresponds to Vendor RM Utilization
        ttype_ref_no = 29 corresponds to Delivery Challan
        '''
        ttype_dict['receivable'] = get_object_or_404(transaction_type, transaction_type_ref_no = 13)
        ttype_dict['pre_nested_rm'] = get_object_or_404(transaction_type, transaction_type_ref_no = 14)
        ttype_dict['offcut'] = get_object_or_404(transaction_type, transaction_type_ref_no = 15)
        ttype_dict['nested_rm'] = get_object_or_404(transaction_type, transaction_type_ref_no = 46)
        ttype_dict['rm_utilization'] = get_object_or_404(transaction_type, transaction_type_ref_no = 30)
        mov_rm_ttype = get_object_or_404(transaction_type, transaction_type_ref_no = 29)
        ttype_dict['move_rm'] = mov_rm_ttype
        vendor_id = tref_data['field_list']['vendor'][0]
        ttype_dict['nested_rm_location'] = get_location_raw('vendor', vendor_id)
        ttype_dict['ref_name'] = 'job_order'
        vendor_obj_list = select_boxes({'name':'vendor'})
        vendor_obj = vendor_obj_list.filter(id = int(vendor_id))[0]
        mov_rm_tref_field_list = fetch_tref_data(mov_rm_ttype, [], {})['tref_data']['field_list']
        mov_rm_tref_field_list['vendor'] = (vendor_obj.id, vendor_obj.name)
        ttype_dict['move_rm_field_list'] = mov_rm_tref_field_list
    elif ttype_ref_no == 16:
        '''
        --- SHOP ORDER ---
        ttype_ref_no = 16 corresponds to shop order process
        ttype_ref_no = 17 corresponds to shop order receivable
        ttype_ref_no = 18 corresponds to shop order pre nested raw material
        ttype_ref_no = 19 corresponds to shop order offcut
        ttype_ref_no = 50 corresponds to shop order nested rm req
        ttype_ref_no = 33 corresponds to WC RM utilization
        ttype_ref_no = 32 corresponds to Movement Order
        '''
        ttype_dict['receivable'] = get_object_or_404(transaction_type, transaction_type_ref_no = 17)
        ttype_dict['pre_nested_rm'] = get_object_or_404(transaction_type, transaction_type_ref_no = 18)
        ttype_dict['offcut'] = get_object_or_404(transaction_type, transaction_type_ref_no = 19)
        ttype_dict['nested_rm'] = get_object_or_404(transaction_type, transaction_type_ref_no = 50)
        ttype_dict['rm_utilization'] = get_object_or_404(transaction_type, transaction_type_ref_no = 33)
        mov_rm_ttype = get_object_or_404(transaction_type, transaction_type_ref_no = 32)
        ttype_dict['move_rm'] = mov_rm_ttype
        work_center_id = tref_data['field_list']['work_center'][0]
        ttype_dict['nested_rm_location'] = get_location_raw('work_center', work_center_id)
        ttype_dict['ref_name'] = 'shop_order'
        work_center_obj_list = select_boxes({'name':'work_center'})
        work_center_obj = work_center_obj_list.filter(id = int(work_center_id))[0]
        mov_rm_tref_field_list = fetch_tref_data(mov_rm_ttype, [], {})['tref_data']['field_list']
        mov_rm_tref_field_list['work_center'] = (work_center_obj.id, work_center_obj.name)
        ttype_dict['move_rm_field_list'] = mov_rm_tref_field_list
    return(ttype_dict)

def job_shop_rec_valuation(tref_id):
    '''tref_id received is the receivable components' tref_id'''
    rec_tref = get_object_or_404(transaction_ref, id=int(tref_id))
    rec_inv_jour = inventory_journal.objects.filter(transaction_ref = rec_tref)
    process_tref_id = int(rec_tref.chain_tref)
    ttype_dict = get_job_shop_ttype(process_tref_id)
    process_tref = get_object_or_404(transaction_ref, id=int(process_tref_id))
    process_inv_jour = inventory_journal.objects.filter(transaction_ref = process_tref)
    pre_nested_rm_tref = get_object_or_404(transaction_ref, transaction_type = ttype_dict['pre_nested_rm'], \
                                           chain_tref = process_tref_id)
    pre_nested_rm_jour_set = inventory_journal.objects.filter(transaction_ref = pre_nested_rm_tref)
    rm = {}
    proc = {}
    rec = {}
    '''
    rm = {item_master_id:{'qty':123, 'rate':123.45}, ....}
    proc = {item_master_id:{'qty':123, 'rate':123.45}, ....}
    rec = {item_master_id:{'qty':123, 'rate':???}, ....}
    off_com_item_rates = {item_master_id:{'qty':123, 'rate':123.45}, ....}
    avg_com_item_rates = {item_master_id:{'qty':123, 'rate':123.45}, ....}
    proc_out_item_rates = {item_master_id:{'qty':123, 'rate':123.45}, ....}
    satisfied_item_rates = {item_master_id:{'qty':123, 'rate':123.45}, ....}
    '''
    off_com_item_rates = {}
    avg_com_item_rates = {}
    for cur_proc_jour in process_inv_jour:
        proc[cur_proc_jour.item_master.id] = {'qty':float(cur_proc_jour.issue_qty), 'rate':float(cur_proc_jour.taxed_rate)}
    for cur_rm_jour in pre_nested_rm_jour_set:
        rm[cur_rm_jour.item_master.id] = {'qty':float(cur_rm_jour.issue_qty), 'rate':float(cur_rm_jour.taxed_rate)}
        if cur_rm_jour.item_master.id in process_inv_jour:
            com_item = get_object_or_404(item_master, id = cur_rm_jour.item_master.id)
            com_item_bom = ast.literal_eval(com_item.bom)
            cur_tot_rm_val = float(0)
            for cur_bom_item in com_item_bom:
                cur_tot_rm_val += rm[cur_bom_item[0]]['rate'] * float(cur_bom_item[1])
            off_rate = cur_tot_rm_val + process_inv_jour[com_item.id]['rate']
            off_com_item_rates[cur_rm_jour.item_master.id] = {'qty':proc[com_item.id]['qty'], 'rate':off_rate}
    for cur_off_item_id, cur_off_det in off_com_item_rates.items():
        tot_qty = cur_off_det['qty'] + rm[cur_off_item_id]['qty']
        off_val = cur_off_det['qty'] * cur_off_det['rate']
        rm_val = rm[cur_off_item_id]['qty'] * rm[cur_off_item_id]['rate']
        avg_rate = (rm_val + off_val) / tot_qty
        avg_com_item_rates[cur_off_item_id] = {'qty':tot_qty, 'rate':avg_rate}
    for cur_rec_jour in rec_inv_jour:
        cur_bom_set = ast.literal_eval(cur_rec_jour.item_master.bom)
        '''initializing rate calculation by adding final process rate'''
        tot_val = float(proc[cur_rec_jour.item_master.id]['rate'])
        for cur_bom in cur_bom_set:
            if cur_bom[0] in avg_com_item_rates:
                tot_val += avg_com_item_rates[cur_bom[0]]['rate'] * cur_bom[1]
            elif cur_bom[0] in rm:
                tot_val += rm[cur_bom[0]]['rate'] * cur_bom[1]
            elif cur_bom[0] in proc:
                '''adding process cost is sufficient when the bom item is not present in the raw material list'''
                tot_val += proc[cur_bom[0]]['rate'] * cur_bom[1]
            else:
                return('error')
        if not cur_rec_jour.item_master.id in rec:
            rec[cur_rec_jour.item_master.id] = {}
        rec[cur_rec_jour.item_master.id]['rate'] = tot_val
        cur_rec_jour.rate = tot_val
        cur_rec_jour.save()
    update_inv_jour_rate(rec_tref)
    return()

def job_shop_order_valuation(tref_id):
    '''tref_id received is the receivable components' tref_id'''
    rec_tref = get_object_or_404(transaction_ref, id=int(tref_id))
    process_tref_id = int(rec_tref.chain_tref)
    ttype_dict = get_job_shop_ttype(process_tref_id)
    nested_rm_tref = get_object_or_404(transaction_ref, transaction_type = ttype_dict['nested_rm'], \
                                           chain_tref = process_tref_id)
    nested_rm_inv_jour = inventory_journal.objects.filter(transaction_ref = nested_rm_tref)
    pre_nested_rm_tref = get_object_or_404(transaction_ref, transaction_type = ttype_dict['pre_nested_rm'], \
                                           chain_tref = process_tref_id)
    pre_nested_rm_jour_set = inventory_journal.objects.filter(transaction_ref = pre_nested_rm_tref)
    allocation_complete = True
    for cur_nested_rm_jour in nested_rm_inv_jour:
        if cur_nested_rm_jour.balance_qty > 0:
            allocation_complete = False
            break
    if allocation_complete == True:
        usf_dict = {}
        ''' usf_dict is meant to store data of nested raw material
        usf_dict = {(u, s, fin):{'parent_area':total_area_of_parent, 'tare_area':total_area_of_tares, 'wastage':parent_area/tare_area, \
                                           'total_value':total_value_of_goods_allocated, 'eff_tare_rate':total_value allocated / total tare area}}'''
        for cur_nested_rm_jour in nested_rm_inv_jour:
            cur_issue_qty = float(cur_nested_rm_jour.issue_qty)
            cur_imp_part_code = cur_nested_rm_jour.item_master.imported_item_code.split('-')
            '''cur_imp_part_code = (unq, sys, mat, s1, s2, s3, d1, d2, d3, d4)'''
            cur_unq = int(cur_imp_part_code[0])
            cur_sys = int(cur_imp_part_code[1])
            cur_fin = cur_nested_rm_jour.item_master.imported_item_finish
            usf_tuple = (cur_unq, cur_sys, cur_fin)
            app_allocation = inventory_journal.objects.filter(debit_journal1 = cur_nested_rm_jour)
            tot_alloc_val = float(0)
            for cur_allocation in app_allocation:
                tot_alloc_val += float(cur_allocation.taxed_value)
            if cur_issue_qty == 0:
                cur_nested_rm_jour.rate = 0
            else:
                cur_nested_rm_jour.rate = tot_alloc_val / cur_issue_qty
            cur_nested_rm_jour.save()
            if cur_unq == 200 or cur_unq == 210 or cur_unq == 220:
                if cur_unq == 200:
                    cur_area = float(cur_imp_part_code[6]) * float(cur_imp_part_code[7]) * cur_issue_qty
                elif cur_unq == 220:
                    cur_area = float(cur_imp_part_code[6]) * float(1000) * cur_issue_qty
                else:
                    cur_area = float(cur_imp_part_code[6]) * cur_issue_qty
                if usf_tuple in usf_dict:
                    new_area = float(usf_dict[usf_tuple]['parent_area']) + cur_area
                    usf_dict[usf_tuple]['parent_area'] = new_area
                else:
                    usf_dict[usf_tuple] = {'parent_area':cur_area, 'tare_area':float(0), 'wastage':float(0), \
                                           'total_value':float(0), 'eff_tare_rate':float(0)}
                new_tot_val = usf_dict[usf_tuple]['total_value'] + tot_alloc_val
                usf_dict[usf_tuple]['total_value'] = new_tot_val
        update_inv_jour_rate(nested_rm_tref)
        
        '''pre_nested_rm loop is done to fill in usf_dict with tare data'''
        
        '''the loop below is meant to populate usf_dict with tare data and effectively calculate the rate(in rs.) per unit area of tare'''
        for cur_pre_nested_rm_jour in pre_nested_rm_jour_set:
            cur_issue_qty = float(cur_pre_nested_rm_jour.issue_qty)
            cur_imp_part_code = cur_pre_nested_rm_jour.item_master.imported_item_code.split('-')
            '''cur_imp_part_code = (unq, sys, mat, s1, s2, s3, d1, d2, d3, d4)'''
            cur_unq = int(cur_imp_part_code[0])
            cur_sys = int(cur_imp_part_code[1])
            cur_fin = cur_pre_nested_rm_jour.item_master.imported_item_finish
            unq_str = str(cur_unq)
            search_unq = int(unq_str[:2] + '0')
            search_usf_tuple = (search_unq, cur_sys, cur_fin)
            if cur_unq == 202 or cur_unq == 212 or cur_unq == 222:
                if cur_unq == 202 or cur_unq == 222:
                    cur_area = float(cur_imp_part_code[6]) * float(cur_imp_part_code[7]) * cur_issue_qty
                else:
                    cur_area = float(cur_imp_part_code[6]) * cur_issue_qty
                new_area = float(usf_dict[search_usf_tuple]['tare_area'] + cur_area)
                usf_dict[search_usf_tuple]['tare_area'] = new_area
                usf_dict[search_usf_tuple]['wastage'] = float(usf_dict[search_usf_tuple]['parent_area'] / usf_dict[search_usf_tuple]['tare_area'])
                usf_dict[search_usf_tuple]['eff_tare_rate'] = float(usf_dict[search_usf_tuple]['total_value'] / usf_dict[search_usf_tuple]['tare_area'])
        
        '''the real loop over pre_nested_rm in order to calculate rate for each of the tare pieces'''
        for cur_pre_nested_rm_jour in pre_nested_rm_jour_set:
            cur_issue_qty = float(cur_pre_nested_rm_jour.issue_qty)
            cur_imp_part_code = cur_pre_nested_rm_jour.item_master.imported_item_code.split('-')
            '''cur_imp_part_code = (unq, sys, mat, s1, s2, s3, d1, d2, d3, d4)'''
            cur_unq = int(cur_imp_part_code[0])
            cur_sys = int(cur_imp_part_code[1])
            cur_fin = cur_pre_nested_rm_jour.item_master.imported_item_finish
            if cur_unq == 202 or cur_unq == 212 or cur_unq == 222:
                unq_str = str(cur_unq)
                search_unq = int(unq_str[:2] + '0')
                search_usf_tuple = (search_unq, cur_sys, cur_fin)
                cur_eff_rate = float(usf_dict[search_usf_tuple]['eff_tare_rate'])
                if cur_unq == 202 or cur_unq == 222:
                    cur_rate = float(cur_imp_part_code[6]) * float(cur_imp_part_code[7]) * cur_eff_rate
                else:
                    cur_rate = float(cur_imp_part_code[6]) * cur_eff_rate
            else:
                nested_rm_jour = get_object_or_404(inventory_journal, item_master = cur_pre_nested_rm_jour.item_master, \
                                                   transaction_ref = nested_rm_tref)
                cur_rate = nested_rm_jour.taxed_rate
            cur_pre_nested_rm_jour.rate = cur_rate
            cur_pre_nested_rm_jour.save()
        update_inv_jour_rate(pre_nested_rm_tref)
        job_shop_rec_valuation(rec_tref.id)
    return(allocation_complete)

    
def fetch_coa_data(coa_group_id, ch_of_ac):
    data = {}
    coa_grp = get_object_or_404(coa_group, id = coa_group_id)
    data['coa_group'] = (coa_grp, ast.literal_eval(str(coa_grp.data)))
    data['select_boxes'] = []
    for cur_field in data['coa_group'][1]['field_list']:
        if(cur_field[1] == 'select'):
            data['select_boxes'].append((cur_field[2], select_boxes({'name':cur_field[2]})))
    coa_data = {}
    coa_data['field_list'] = field_list_collate_default(data['coa_group'][1]['field_list'])
    data['coa'] = ([], coa_data)
    if ch_of_ac != []:
        data['coa'] = (ch_of_ac, ast.literal_eval(str(ch_of_ac.data)))
    return(data)


def update_work_center_rate(item_master_id, work_center_id):
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    work_center_obj = get_object_or_404(work_center, id = work_center_id)
    pl_obj = work_center_price.objects.filter(work_center = work_center_obj, item = item_master_obj)
    #return(item_master_obj.imported_item_code[:21])
    auto_pl_obj = get_object_or_404(auto_price_list, spec_code = item_master_obj.imported_item_code[:21])
    if len(pl_obj) > 0:
        pl_obj = pl_obj[0]
    else:
        pl_obj = work_center_price(work_center = work_center_obj, item = item_master_obj)
    pl_obj.name = work_center_obj.name
    rmp_con = get_rmp_con(auto_pl_obj.id, work_center_obj.id, 'work_center')
    broken_item = param_break(item_master_obj.imported_item_code, item_master_obj.imported_item_finish)
    pl_obj.rate = round(eval(dim_cost_port(broken_item['pn'], 0, rmp_con[0], rmp_con[1], auto_pl_obj.shop_order_price_calc_eqn, 1)), 2)
    pl_obj.save()
    return(item_master_obj)


def update_vendor_rate(item_master_id, vendor_id, rate_type):
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    vendor_obj = get_object_or_404(coa, id = vendor_id)
    pl_obj = vendor_price.objects.filter(vendor = vendor_obj, item = item_master_obj)
    
    auto_pl_obj = get_object_or_404(auto_price_list, spec_code = item_master_obj.imported_item_code[:21])
    
    if len(pl_obj) > 0:
        pl_obj = pl_obj[0]
    else:
        pl_obj = vendor_price(vendor = vendor_obj, item = item_master_obj)
    pl_obj.name = vendor_obj.name
    rmp_con = get_rmp_con(auto_pl_obj.id, vendor_obj.id, 'vendor')
    broken_item = param_break(item_master_obj.imported_item_code, item_master_obj.imported_item_finish)
    if rate_type == 'job_work':
        jw_rate =  round(Decimal(eval(dim_cost_port(broken_item['pn'], 0, rmp_con[0], rmp_con[1], auto_pl_obj.job_work_price_calc_eqn, 1))), 2)
        if len(str(jw_rate)) > 12:
            jw_rate = 999999999.99
        pl_obj.job_work_rate = jw_rate
    if rate_type == 'purchase' and auto_pl_obj.purchase_price_calc_eqn != 'sum':
        pur_rate = round(Decimal(eval(dim_cost_port(broken_item['pn'], 0, rmp_con[0], rmp_con[1], auto_pl_obj.purchase_price_calc_eqn, 1))), 2)
        if len(str(pur_rate)) > 12:
            pur_rate = 999999999.99
        pl_obj.purchase_rate = pur_rate
    if rate_type == 'purchase_factor':
        pur_factor = round(Decimal(eval(dim_cost_port(broken_item['pn'], 0, rmp_con[0], rmp_con[1], auto_pl_obj.purchase_factor_calc_eqn, 1))), 2)
        if len(str(pur_factor)) > 12:
            pur_factor = 999999999.99
        pl_obj.purchase_factor = pur_factor
    pl_obj.save()
    return(pl_obj)


def calc_pur_rate(item_master_id, vendor_id):
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    vendor_obj = get_object_or_404(coa, id = vendor_id)
    auto_pl_obj = get_object_or_404(auto_price_list, spec_code = item_master_obj.imported_item_code[:21])
    if auto_pl_obj.purchase_price_calc_eqn == 'sum':
        pur_price = update_vendor_rate(item_master_obj.id, vendor_obj.id, 'purchase_factor').purchase_factor * Decimal(1)
        for cur_bom in ast.literal_eval(str(item_master_obj.infinite_bom)):
            pur_price += update_vendor_rate(cur_bom[0], vendor_obj.id, 'purchase_factor').purchase_factor * Decimal(cur_bom[1])
    pl_obj = vendor_price.objects.filter(vendor = vendor_obj, item = item_master_obj)
    print('Purchase Sum : ' + str(pur_price))
    if len(pl_obj) > 0:
        pl_obj = pl_obj[0]
        pl_obj.purchase_rate = pur_price
        pl_obj.save()
    return(pl_obj)

def post_submit_activity(tref_id):
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    ttype = tref.transaction_type
    ttype_ref_no = ttype.transaction_type_ref_no
    ttype_data = ast.literal_eval(ttype.data)
    ttype_data1 = ast.literal_eval(ttype.data1)
    if 'post_submit_activity' in ttype_data1:
        if ttype_data1['post_submit_activity'] == 'order_confirmation':
            '''If order_confirmation
            OC Reference Names held in All TPLs pertaining to this OC has to be changed'''
            oc_obj = tref
            tpl_ttype = get_object_or_404(transaction_type, transaction_type_ref_no=2)
            app_tpl = transaction_ref.objects.filter(transaction_type = tpl_ttype, submit = False, active = False)
            search_dict = {'order_confirmation':str(oc_obj.id)}
            tpl_obj_set = tref_field_filter(app_tpl, search_dict)
            for cur_tpl in tpl_obj_set:
                tpl_data = ast.literal_eval(cur_tpl.data)
                tpl_data['field_list']['order_confirmation'] = (oc_obj.id, oc_obj.name)
                cur_tpl.data = tpl_data
                cur_tpl.save()
        elif ttype_data1['post_submit_activity'] == 'make_dispatch_note':
            '''Create a dispatch not when a tpl is submitted, qty & items will match the tpl items & issue qty'''
            tpl_obj = tref
            tpl_inv_jour = inventory_journal.objects.filter(transaction_ref = tref)
            ttype_disp_note = get_object_or_404(transaction_type, transaction_type_ref_no=37)
            ttype_disp_note_data = ast.literal_eval(ttype_disp_note.data)
            tref_disp_note_field_data = field_list_collate_default(ttype_disp_note_data['field_list'])
            disp_inv_jour = []
            for cur_tpl_inv_jour in tpl_inv_jour:
                tpl_inv_jour_det = {}
                tpl_inv_jour_det['discount'] = cur_tpl_inv_jour.discount
                tpl_inv_jour_det['tpl_ref'] = tpl_obj.id
                disp_inv_jour.append((cur_tpl_inv_jour.item_master_id, cur_tpl_inv_jour.issue_qty, tpl_inv_jour_det))
            cur_dispatch_note = auto_create_tref(ttype_disp_note.transaction_type_ref_no, tref_disp_note_field_data, \
                                                disp_inv_jour, True, {'chain_tref':tpl_obj.id})
        elif ttype_data1['post_submit_activity'] == 'make_dispatch_invoice':
            disp_tref_obj = tref
            oc_line_item_master_dict = {}
            '''oc_line_item_master_dict = {'oc_line_item_master_id':{'disp_tot_val':total_dispatch_value, 
            'oc_line_item_jour_obj':'oc_item_inv_jour_obj'}}'''
            tpl_dict = {}
            '''tpl_dict = {'tpl_tref_id':{'oc_line_item_master_id':oc_line_item_master_id}}'''
            disp_inv_jour_set = inventory_journal.objects.filter(transaction_ref = disp_tref_obj)
            oc_tref_dict = {}
            for cur_disp_inv_jour in disp_inv_jour_set:
                cur_tpl_ref_no = cur_disp_inv_jour.tpl_ref_no
                cur_oc_dict = None
                if cur_tpl_ref_no in tpl_dict:
                    cur_line_item_master_id = tpl_dict[cur_tpl_ref_no]['oc_item_item_master_id']
                    cur_oc_line_item_master_dict = oc_line_item_master_dict[cur_line_item_master_id]
                else:
                    tpl_tref_obj = get_object_or_404(transaction_ref, id = cur_tpl_ref_no)
                    tpl_tref_data = ast.literal_eval(tpl_tref_obj.data)
                    cur_oc_id = int(tpl_tref_data['field_list']['order_confirmation'][0])
                    cur_line_item_master_id = int(tpl_tref_data['field_list']['oc_item'][0])
                    cur_oc_obj = get_object_or_404(transaction_ref, id = cur_oc_id)
                    cur_line_item_master_obj = get_object_or_404(item_master, id = cur_line_item_master_id)
                    tpl_dict[cur_tpl_ref_no]  = {'oc_item_id':cur_line_item_master_obj.id}
                    if not cur_line_item_master_obj.id in oc_line_item_master_dict:
                        cur_line_item_jour_obj = get_object_or_404(inventory_journal, transaction_ref = cur_oc_obj, \
                                                        item_master = cur_line_item_master_obj)
                        oc_line_item_master_dict[cur_line_item_master_obj.id] = {'disp_tot_val':0, \
                                                         'oc_line_item_jour_obj':cur_line_item_jour_obj}
                cur_oc_line_item_master_dict = oc_line_item_master_dict[cur_line_item_master_id]
                cur_disptch_val = cur_disp_inv_jour.special_rate * cur_disp_inv_jour.balance_qty
                tot_dispatch = cur_oc_line_item_master_dict['disp_tot_val']
                tot_dispatch += cur_disptch_val
                oc_line_item_master_dict[cur_line_item_master_id]['disp_tot_val'] = tot_dispatch
            invoice_inv_jour = []
            oc_tref_dict = {}
            '''oc_tref_dict = {'oc_tref_id':[{'disp_tot_val':xx, 'oc_line_item_inv_jour':oc_item_inv_jour}]}'''
            if len(oc_line_item_master_dict) > 0:
                for oc_lin_key, oc_lin_val in oc_line_item_master_dict.items():
                    cur_oc_tref_id = oc_lin_val['oc_line_item_jour_obj'].transaction_ref.id
                    if not cur_oc_tref_id in oc_tref_dict:
                        oc_tref_dict[cur_oc_tref_id] = []
                    oc_tref_dict[cur_oc_tref_id].append(oc_lin_val)
                for cur_oc_tref_id, oc_inv_jour_list in oc_tref_dict.items():
                    invoice_inv_jour = []
                    for cur_oc_jour_dict in oc_inv_jour_list:
                        oc_qty  = cur_oc_jour_dict['oc_line_item_jour_obj'].issue_qty
                        oc_tot_val = cur_oc_jour_dict['oc_line_item_jour_obj'].special_rate
                        dispatch_tot_val = cur_oc_jour_dict['disp_tot_val']
                        dispatch_qty = oc_qty * (dispatch_tot_val / oc_tot_val)
                        invoice_inv_jour.append((cur_oc_jour_dict['oc_line_item_jour_obj'].id, dispatch_qty, {'tpl_ref':''}))
                    '''invoice transaction_type_ref_no = 60'''
                    invoice_ttype = get_object_or_404(transaction_type, transaction_type_ref_no = 60)
                    invoice_tref_dict = fetch_tref_data(invoice_ttype, [], {})['tref_data']['field_list']
                    invoice_tref = auto_create_tref(60, invoice_tref_dict, invoice_inv_jour, False, {'chain_tref':disp_tref_obj.id})
        elif ttype_data1['post_submit_activity'] == 'debit_pro_ind_ord_process':
            job_shop_process_tref = tref
            job_shop_ttype_dict = get_job_shop_ttype(job_shop_process_tref.id)
            nested_rm_ttype = job_shop_ttype_dict['nested_rm']
            tot_prod_ind_tref_id = []
            proc_inv_jour = inventory_journal.objects.filter(transaction_ref = job_shop_process_tref)
            for cur_proc_inv_jour in proc_inv_jour:
                if not cur_proc_inv_jour.transaction_ref.id in tot_prod_ind_tref_id:
                    tot_prod_ind_tref_id.append(cur_proc_inv_jour.transaction_ref.id)
            nested_rm_tref = get_object_or_404(transaction_type = nested_rm_ttype, chain_tref = job_shop_process_tref.id)
            nested_rm_inv_jour = inventory_journal.objects.filter(transaction_ref = nested_rm_tref).order_by('id')
            for cur_rm_inv_jour in nested_rm_inv_jour:
                cur_rm_balance = float(cur_rm_inv_jour.balance_qty)
                if len(ast.literal_eval(cur_rm_inv_jour.item_master.bom)) > 0:
                    for cur_prod_ind_tref_id in tot_prod_ind_tref_id:
                        prod_ind_tref = get_object_or_404(transaction_ref, id = cur_prod_ind_tref_id)
                        cur_prod_inv_jour_set = inventory_journal.objects.filter(transaction_ref = prod_ind_tref, \
                                                        item_master = cur_rm_inv_jour.item_master, balance__gt = 0)
                        for cur_prod_inv_jour in cur_prod_inv_jour_set:
                            cur_ind_jour_bal = cur_prod_inv_jour.balance_qty
                            if cur_rm_balance > cur_ind_jour_bal:
                                 cur_red = cur_ind_jour_bal
                            else:
                                cur_red = cur_rm_balance
                            cur_ind_jour_bal -= cur_red
                            cur_prod_inv_jour.balance_qty = cur_ind_jour_bal
                            cur_prod_inv_jour.save()
    return()

def allocate_list(tref_id):
    tref_obj = get_object_or_404(transaction_ref, id = tref_id)
    cur_ttype = tref_obj.transaction_type
    cur_ttype_data = ast.literal_eval(cur_ttype.data)
    deb2_ttype_ids = ast.literal_eval(cur_ttype.debit_ttype2_ids)
    tpl_match_type = cur_ttype_data['allocation_type']
    if tpl_match_type == 'stock':
        cur_tpl_ref_no = 0
    #location_obj = fetch_allocation_location(tref_id)
    app_bal_trace = {}
    stk_available = True
    inv_jour_set = inventory_journal.objects.filter(transaction_ref = tref_obj).order_by('id')
    i = 0
    while i < len(inv_jour_set):
        cur_inv_jour = inv_jour_set[i]
        '''getting all inventory journals applicable to debit type 2 & sorting it on submit date'''
        if tpl_match_type == 'tpl_match':
            cur_tpl_ref_no = cur_inv_jour.tpl_ref_no
        cur_item_master = cur_inv_jour.item_master
        location_deb1_id = cur_inv_jour.debit_journal1.location_ref_val
        location_deb1_obj = get_object_or_404(location, id = location_deb1_id)
        cur_available_stk_obj = current_stock.objects.filter(location_ref = location_deb1_obj, \
                                                  item_master_ref = cur_item_master, tpl_ref_no = cur_tpl_ref_no)
        if len(cur_available_stk_obj) > 0:
            cur_available_stk_obj = cur_available_stk_obj[0]
            if cur_available_stk_obj.cur_stock < cur_inv_jour.issue_qty:
                stk_available = False
                return('error')
            if stk_available == True:
                cur_issue_qty = float(cur_inv_jour.issue_qty)
                app_deb2_inv_jour = []
                for cur_deb2_ttype_id in deb2_ttype_ids:
                    cur_deb2_ttype_obj = get_object_or_404(transaction_type, transaction_type_ref_no = int(cur_deb2_ttype_id))
                    temp_app_deb2_inv_jour = inventory_journal.objects.filter(transaction_ref__transaction_type = cur_deb2_ttype_obj, \
                                                             transaction_ref__submit = True, transaction_ref__active = True, \
                                                             balance_qty__gt = 0, tpl_ref_no = cur_tpl_ref_no, item_master = cur_item_master, \
                                                             location_ref_val = location_deb1_id).order_by('transaction_ref__submit_date')
                    for cur_temp_app_deb2_inv_jour in temp_app_deb2_inv_jour:
                        app_deb2_inv_jour.append(cur_temp_app_deb2_inv_jour)
                if len(app_deb2_inv_jour) == 0:
                    return('error')
                else:
                    '''loop over all applicable stock inventory journals & start storing the balance qtys in dictionary app_bal_trace
                    as the qtys of stock are (imaginary) allocated we keep track of the prospective balance of each stock invjour in this dict'''
                    cur_deb2_inv_jour = None
                    for cur_stk_inv_jour in app_deb2_inv_jour:
                        if cur_stk_inv_jour.id in app_bal_trace:
                            if app_bal_trace[cur_stk_inv_jour.id] > 0.0:
                                cur_deb2_inv_jour = cur_stk_inv_jour
                                break
                        else:
                            app_bal_trace[cur_stk_inv_jour.id] = float(cur_stk_inv_jour.balance_qty)
                            cur_deb2_inv_jour = cur_stk_inv_jour
                            break
                    '''cur_deb2_inv_jour is the (First In) Stock inventory journal whose balance (prospective) is greater than 0'''
                    alloc_qty = float(0.0)
                    if not cur_deb2_inv_jour.id in app_bal_trace:
                        app_bal_trace[cur_deb2_inv_jour.id] = float(cur_deb2_inv_jour.balance_qty)
                    cur_deb2_bal_qty = app_bal_trace[cur_deb2_inv_jour.id]
                    if cur_issue_qty <= cur_deb2_bal_qty:
                        alloc_qty = cur_issue_qty
                    else:
                        alloc_qty = cur_deb2_bal_qty
                    cur_inv_jour.debit_journal2 = cur_deb2_inv_jour
                    new_issue_qty = cur_issue_qty - alloc_qty
                    cur_inv_jour.issue_qty = alloc_qty
                    cur_inv_jour.save()
                    deb1_inv_jour = cur_inv_jour.debit_journal1
                    if new_issue_qty > 0.0:
                        new_tpl_ref = cur_inv_jour.tpl_ref_no
                        new_location_ref = cur_inv_jour.location_ref_val
                        new_inv_jour = inv_jour_create(tref_obj, (deb1_inv_jour.id, new_issue_qty, {}), new_tpl_ref)
                        new_inv_jour.save()
                    new_deb2_bal = cur_deb2_bal_qty - alloc_qty
                    app_bal_trace[cur_deb2_inv_jour.id] = new_deb2_bal
        inv_jour_set = inventory_journal.objects.filter(transaction_ref = tref_obj).order_by('id')
        i += 1
    tref_obj = get_object_or_404(transaction_ref, id = int(tref_id))
    return(tref_obj)

def pre_submit_activity(tref_id):
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    ttype = tref.transaction_type
    ttype_ref_no = ttype.transaction_type_ref_no
    ttype_data = ast.literal_eval(ttype.data)
    ttype_data1 = ast.literal_eval(ttype.data1)
    submit = True
    if 'pre_submit_activity' in ttype_data1:
        if ttype_data1['pre_submit_activity'] == 'production_material_supply':
            submit = job_shop_order_valuation(tref_id)
    return(submit)

def bom_collation(part_list, config):
    '''part_list = [(part1_id, qty), (part2_id, qty),......]
    config = {'multi_layer':True}'''
    data = {}
    final_process_list = []
    sub_process_list = []
    rm_list = []
    boc_list = []
    dummy_process_list = []
    message = {}
    bom_status = bom_check(part_list)
    for cur_part in part_list:
        cur_part_obj = get_object_or_404(item_master, id = int(cur_part[0]))
        cur_tot_bom  = ast.literal_eval(cur_part_obj.bom)
        cur_tot_bom = bom_multiplier(cur_tot_bom, cur_part[1])
        if len(cur_tot_bom) > 0:
            index = [x for x, y in enumerate(final_process_list) if y[0] == cur_part_obj.id]
            if len(index) == 0:
                final_process_list.append(cur_part)
            else:
                final_process_list[index[0]][1] += cur_part[1]
            bom_status = bom_check(cur_tot_bom)
            for cur_bom in cur_tot_bom:
                cur_bom_obj = get_object_or_404(item_master, id = int(cur_bom[0]))
                sub_bom = ast.literal_eval(cur_bom_obj.bom)
                sub_bom = bom_multiplier(sub_bom, cur_bom[1])
                if len(sub_bom) > 0:
                    index = [x for x, y in enumerate(sub_process_list) if y[0] == cur_bom_obj.id]
                    if len(index) == 0:
                        sub_process_list.append(cur_bom)
                        #dummy_process_list.append(cur_bom)
                    else:
                        sub_process_list[index[0]][1] += cur_bom[1]
                        #dummy_process_list[index[0]][1] += cur_bom[1]
                else:
                    index = [x for x, y in enumerate(rm_list) if y[0] == cur_bom_obj.id]
                    if len(index) == 0:
                        rm_list.append(cur_bom)
                    else:
                        rm_list[index[0]][1] += cur_bom[1]
        else:
            index = [x for x, y in enumerate(boc_list) if y[0] == cur_part_obj.id]
            if len(index) == 0:
                boc_list.append(cur_part)
            else:
                boc_list[index[0]][1] += cur_part[1]
    
    if config['multi_layer'] == True or config['multi_layer'] == 'True':
        dummy_process_list = copy.deepcopy(sub_process_list)
        dummy_process_len = len(dummy_process_list)
        i = 0
        while i < dummy_process_len:
            cur_dummy_pro_obj = get_object_or_404(item_master, id = int(dummy_process_list[i][0]))
            cur_bom_list  = ast.literal_eval(cur_dummy_pro_obj.bom)
            cur_bom_list = bom_multiplier(cur_bom_list, dummy_process_list[i][1])
            bom_status = bom_check(cur_bom_list)
            for cur_bom in cur_bom_list:
                cur_bom_obj = get_object_or_404(item_master, id = int(cur_bom[0]))
                cur_sub_bom_list = ast.literal_eval(cur_bom_obj.bom)
                cur_sub_bom_list = bom_multiplier(cur_sub_bom_list, cur_bom[1])
                if len(cur_sub_bom_list) > 0:
                    dummy_process_list.append(list(cur_bom))
                    index = [x for x, y in enumerate(sub_process_list) if y[0] == cur_bom_obj.id]
                    if len(index) == 0:
                        sub_process_list.append(list(cur_bom))
                    else:
                        sub_process_list[index[0]][1] += cur_bom[1]
                else:
                    index = [x for x, y in enumerate(rm_list) if y[0] == cur_bom_obj.id]
                    if len(index) == 0:
                        rm_list.append(list(cur_bom))
                    else:
                        rm_list[index[0]][1] += cur_bom[1]
            dummy_process_len = len(dummy_process_list)
            i += 1
    data['final_process_list'] = final_process_list
    data['boc_list'] = boc_list
    data['sub_process_list'] = sub_process_list
    data['rm_list'] = rm_list
    return(data)

    
def dj_obj_list_sort(obj_list, config):
    '''obj_list = [(part_obj1, qty,...), (part_obj2, qty,...), ...]
    config = {'obj_index':1, 'obj_param':'name'}
    '''
    sorted_list = []
    if obj_list == []:
        return(sorted_list)
    temp_list = []
    obj_index = int(config['obj_index'])
    elem_len = len(obj_list[0])
    for cur_elem in obj_list:
        temp_elem = list(cur_elem)
        cur_obj = temp_elem[obj_index]
        if config['obj_param'] == 'name':
            temp_elem.append(cur_obj.name)
        temp_list.append(temp_elem)
    sorted_temp_list = sorted(temp_list, key=lambda x: x[elem_len])
    for cur_elem in sorted_temp_list:
        temp_elem = cur_elem[:elem_len]
        sorted_list.append(temp_elem)
    return(sorted_list)
         
def update_input_factor(item_master_id):
    item_master_obj = get_object_or_404(item_master, id=item_master_id)
    auto_pl_spec_code = item_master_obj.imported_item_code[:21]
    auto_pl_obj = get_object_or_404(auto_price_list, spec_code=auto_pl_spec_code)
    if len(item_master_obj.imported_item_code.split('-')) == 10 and len(auto_pl_obj.spec_code.split('-')) == 6:
        p_no_split = item_master_obj.imported_item_code.split('-')
        pn = {}
        pn['n'] = int(p_no_split[0])
        pn['s'] = int(p_no_split[1])
        pn['m'] = int(p_no_split[2])
        pn['s1'] = int(p_no_split[3])
        pn['s2'] = int(p_no_split[4])
        pn['s3'] = int(p_no_split[5])
        pn['d1'] = int(p_no_split[6])
        pn['d2'] = int(p_no_split[7])
        pn['d3'] = int(p_no_split[8])
        pn['d4'] = int(p_no_split[9])
        rmp_ext = get_rmp_con(auto_pl_obj.id, 0, 'sale')
        rmp_dict = rmp_ext[0]
        con_dict = rmp_ext[1]
        input_calc_eqn = dim_cost_port(pn, auto_pl_obj.input_rate_sale, rmp_dict, con_dict, auto_pl_obj.input_factor_calc_eqn, 1)
        sale_calc_eqn = dim_cost_port(pn, auto_pl_obj.input_rate_sale, rmp_dict, con_dict, auto_pl_obj.sale_price_calc_eqn, 1)
        input_val = round(eval(input_calc_eqn), 2)
        sale_val = round(eval(sale_calc_eqn), 2)
        item_master_obj.input_factor = input_val
        item_master_obj.process_valuation_sale = sale_val
        item_master_obj.save()
    return()
    
def bom_input_sum(item_master_id, type):
    '''type = {'update_ip_factor':True/False}'''
    update_factor = type['update_ip_factor']
    bom_index = []
    inf_bom = []
    dummy_list = [[item_master_id, 1.0]]
    i = 0
    while i < len(dummy_list):
        cur_set = dummy_list[i]
        bom_check([(cur_set[0], 1)])
        if len(item_master.objects.filter(id = cur_set[0])) == 0:
            return(True)
        cur_part = get_object_or_404(item_master, id = cur_set[0])
        parent_qty = cur_set[1]
        parent_bom = ast.literal_eval(cur_part.bom)
        redo = False
        for child_set in parent_bom:
            availability = item_master.objects.filter(id=int(child_set[0]))
            if len(availability) == 0:
                infinite_update([(cur_part.imported_item_code, cur_part.imported_item_finish, 1.0)], True, {'auto_update':True})
                redo = True
        if redo == False:
            for child_set in parent_bom:
                dummy_list.append([child_set[0], child_set[1]*parent_qty])
            i += 1
    for cur_set in dummy_list:
        if cur_set[0] in bom_index:
            pos = bom_index.index(cur_set[0])
            inf_bom[pos][1] += cur_set[1]
        else:
            inf_bom.append(cur_set)
    input_sum = 0.0
    sale_sum = 0.0
    for cur_set in inf_bom:
        if update_factor:
            update_input_factor(cur_set[0])
        if len(item_master.objects.filter(id = cur_set[0])) == 0:
            return(True)
        cur_obj = get_object_or_404(item_master, id=cur_set[0])
        input_sum += float(cur_obj.input_factor) * float(cur_set[1])
        sale_sum += float(cur_obj.process_valuation_sale) * float(cur_set[1])
    item_master_obj = get_object_or_404(item_master, id=item_master_id)
    item_master_obj = sale_price_update(item_master_obj.id, item_master_obj.input_factor, input_sum)
    '''item_master_obj.bom_input_price = input_sum
    item_master_obj.sale_price = sale_sum
    auto_pl_obj = auto_price_list.objects.filter(spec_code=item_master_obj.imported_item_code[:21])
    if len(auto_pl_obj) == 0:
        item_master_obj.delete()
        return()
    auto_pl_obj = get_object_or_404(auto_price_list, spec_code=item_master_obj.imported_item_code[:21])
    margin = float(auto_pl_obj.sale_margin)
    new_bom_sale_price = float(input_sum * margin)
    bom_sp_diff = new_bom_sale_price - float(item_master_obj.bom_sale_price)
    
    if bom_sp_diff > 2 or bom_sp_diff < -2:
        sp_history = ast.literal_eval(item_master_obj.bom_sp_his)
        cur_time_str = str(timezone.now())
        sp_history.append({'dt':cur_time_str,'rate':float(new_bom_sale_price)})
        item_master_obj.bom_sp_his = sp_history
        item_master_obj.save()
        item_master_obj = get_object_or_404(item_master, id=item_master_id)
    item_master_obj.bom_sale_price = new_bom_sale_price
    item_master_obj.price_last_updated = timezone.now()
    item_master_obj.save()
    item_master_obj = get_object_or_404(item_master, id=item_master_id)'''
    return(item_master_obj)

def get_actual_price_tpl(parts_array_360, action_type, settings):
    '''action type can be 'append' or 'over_write' depending on the requirement'''
    '''parts in quote_pl table
    sample --> {'items':{region name':'no. of segments'}, {'department name':[[part_no, 'part_name', 'part_size', 'fin_no', 'seg1 qty', 'seg2 qty',...'tot_seg qty', norms, rate, value]]}}
    {"B.Wood Department":[["038-02-02-003-000-003-2400-1200-1200-0450",
    "Standard Storage - 450D - PLB Body & Top (Openable Shutter)  Recessed Handles",
    "2400 H x 1200 W Top: 1200  W x 450 D","17-11-11-413-57-60-0-0-0-0-0-0-0",8,8,"6000.00",17280,138240]],
    "item":{"Region 1":1}}
    '''
    start_time = timezone.now()
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], \
                          password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    #normalize_pl_360()
    cursor.execute("""select item_id from quote_pl where id=%d""" % settings['quote_pl_id'])
    item_id = int(cursor.fetchall()[0][0])
    cursor.execute("""select name, type_id from item where id=%d""" % item_id)
    item_extract = cursor.fetchall()[0]
    item_type_id = item_extract[1]
    item_name = item_extract[0]
    cursor.execute("""select name, data from item_type where id=%d""" % item_type_id)
    item_type_extract = cursor.fetchall()[0]
    item_type_name = item_type_extract[0]
    item_type_data = ast.literal_eval(item_type_extract[1])
    '''default markup is needed to be multiplied with stored sale price  - 
    ONLY TO WRITE BACK INTO 360 DB as this is a requirment from featherlite'''
    def_markup = Decimal(item_type_data['default_markup'])
    tot_val = 0
    region_count = 0
    for key, val in parts_array_360['item'].items():
        region_count += val
    for cur_header, part_list in sorted(parts_array_360.items()):
        if not cur_header == 'item':
            for cur_part in part_list:
                skip_part = False
                part_code = cur_part[0]
                if len(part_code.split('-')[0]) == 2:
                    part_code = '0' + part_code
                part_finish = cur_part[3]
                if isinstance(part_finish, dict) or isinstance(part_finish, list):
                    #part_finish = '1-0-0-0-0-0-0-0-0-0-0-0-0'
                    part_finish = '1-1-1-1-1-1-1-1-1-1-1-1-1'
                elif part_finish == '-' or len(part_finish.split('-')) != 13:
                    #part_finish = '1-0-0-0-0-0-0-0-0-0-0-0-0'
                    part_finish = '1-1-1-1-1-1-1-1-1-1-1-1-1'
                '''Initially fin code used to be in the format x-x-0-0-0-0-0-0-0-0-0-0-0 where 0 is the default value
                later it was in the format x-x-543-543-543-543-543-543-543-543-543-543-543 where 543 is the default
                now we make the format as x-x-1-1-1-1-1-1-1-1-1-1-1 where 1 is the default
                the replacements are done to negate old formats of finish coming into the system due to stored up fininsh as string'''
                part_finish = part_finish.replace("-543-", "-1-")
                '''repeated purposefully as replacement is alternate initially'''
                part_finish = part_finish.replace("-543-", "-1-")
                part_finish = part_finish.replace("1-543", "1-1")
                part_finish = part_finish.replace("-0-", "-1-")
                '''repeated purposefully as replacement is alternate initially'''
                part_finish = part_finish.replace("-0-", "-1-")
                part_finish = part_finish.replace("-1-0", "-1-1")
                
                if int(part_finish.split('-')[0]) == 0:
                    part_finish = '1' + part_finish[1:]
                item_master_obj = item_master.objects.filter(imported_item_code = part_code, imported_item_finish = part_finish)
                if part_code[:6] == '078-01':
                    print('debug')
                if len(item_master_obj) == 0:
                    '''If item master doesn't exist'''
                    check_part = part_code.split('-')
                    for cur_check_part in check_part:
                        try:
                            int(cur_check_part)
                        except:
                            skip_part = True
                            break
                        else:
                            '''do nothing'''
                    if skip_part == True:
                        continue
                    print('Creating Item Master : ' + str(part_code) + ' | ' + str(part_finish))
                    infinite_update([(part_code, part_finish, 1.0)], True, {'auto_update':False})
                else:
                    item_master_obj = item_master_obj[0]
                    '''Other conditions on which infinite update has to be run'''
                    print('Importing Item Master : ' + str(item_master_obj))
                    par_br = param_break(item_master_obj.imported_item_code, item_master_obj.imported_item_finish)
                    check_new_pl = par_br['pn']
                    param = (par_br['pn']['n'], par_br['pn']['s'], par_br['pn']['m'], par_br['pn']['s1'], par_br['pn']['s2'], par_br['pn']['s3'])
                    cursor.execute("""select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d""" % param)
                    check_res = cursor.fetchall()
                    '''this code is written to consider pl items which are closest 
                    match  in cases where complete spec code doesn't match with entries in price_list'''
                    if len(check_res) == 0:
                        std_pl_query = get_std_pl_query(par_br['pn'], par_br['price_dep_arr'])
                        cursor.execute(std_pl_query[0] % std_pl_query[1])
                        check_res = cursor.fetchall()
                    if len(check_res) == 0:
                        print('Pricelist in 360 Not Available')
                        error_message = 'crm_auto_pl not found for Part No.:' + str(item_master_obj.imported_item_code) + '(' + str(par_br['unique_obj'][1]) + ')' + ' price dep arr :' + str(par_br['price_dep_arr'])
                        error_message += 'item : ' + item_name + ' type: ' + item_type_name
                        raise Exception(error_message) 
                        param = []
                        std_pl_query = get_std_pl_query(par_br['pn'], par_br['price_dep_arr'])
                        cursor.execute(std_pl_query[0] % std_pl_query[1])
                        std_pl_rslt = cursor.fetchall()[0]
                        rate = std_pl_rslt[35]
                        std_calc_eqn = std_pl_rslt[37]
                        qty = 1.0
                        item_master_obj.sale_price = eval(dim_cost_port(par_br['pn'], rate, {}, {}, std_calc_eqn, qty))
                        item_master_obj.bom_sale_price = eval(dim_cost_port(par_br['pn'], rate, {}, {}, std_calc_eqn, qty))
                        item_master_obj.save()
                        item_master_obj = get_object_or_404(item_master, imported_item_code = part_code, imported_item_finish = part_finish)
                    else:
                        pl_360_obj = check_res[0]
                        cursor.execute("""select * from b_o_m where pl_id=%d""" % (pl_360_obj[0],))
                        bom_360 = cursor.fetchall()
                        if item_master_obj.last_updated == None or item_master_obj.price_last_updated == None:
                            item_master_obj.last_updated = timezone.now() - timedelta(days=20)
                            item_master_obj.price_last_updated = timezone.now() - timedelta(days=20)
                            item_master_obj.save()
                            item_master_obj = get_object_or_404(item_master, imported_item_code = part_code, imported_item_finish = part_finish)
                        time_diff = timezone.now() - item_master_obj.price_last_updated
                        print('Last updated:' + str(item_master_obj.last_updated) + ' Time diff: '+ str(time_diff))
                        if len(bom_360) == len(ast.literal_eval(str(item_master_obj.bom))):
                            lprupd = item_master_obj.price_last_updated
                            print(lprupd)
                            issue2 = False
                            if item_master_obj.bom_sale_price < 0.01 or time_diff >= timedelta(days=1):
                                print('Sale Price Update Initiated due to 0 Price value or due to time lapse')
                                issue2 = bom_input_sum(item_master_obj.id, {'update_ip_factor':True})
                            if issue2 == True:
                                infinite_update([(part_code, part_finish, 1.0)], True, {'auto_update':False})
                                if item_master_obj.price_last_updated == None:
                                    print('Updating Sale Price Sum')
                                    bom_input_sum(item_master_obj.id, {'update_ip_factor':True})
                                elif timezone.now() - item_master_obj.price_last_updated > timedelta(hours=6):
                                    print('Updating Sale Price Sum')
                                    bom_input_sum(item_master_obj.id, {'update_ip_factor':True})
                        else:
                            print('Infinite Update Initiated due to irregular BOM Len')
                            infinite_update([(part_code, part_finish, 1.0)], True, {'auto_update':False})
                time_taken = timezone.now() - start_time
                if time_taken >= settings['time_left']:
                    return('Time Out')
                item_master_obj = get_object_or_404(item_master, imported_item_code = part_code, imported_item_finish = part_finish)
                #tot_val += round(item_master_obj.sale_price * cur_part[4 + region_count], 1)
                if item_master_obj.bom_sale_price > 0:
                    output_sale_price = item_master_obj.bom_sale_price
                else:
                    output_sale_price = item_master_obj.adhoc_sale_price
                tot_val += float(round(output_sale_price * def_markup * cur_part[4 + region_count], 1))
                if action_type == 'append':
                    '''cur_part.append(item_master_obj.sale_price)
                    cur_part.append(item_master_obj.sale_price * cur_part[4 + region_count])'''
                    cur_part.append(round(output_sale_price * def_markup, 2))
                    cur_part.append(round(output_sale_price * def_markup * cur_part[4 + region_count], 2))
                    auto_pl_obj = auto_price_list.objects.filter(spec_code = item_master_obj.imported_item_code[:21])[0]
                    cur_part.append({'item_master':item_master_obj, 'auto_pl':auto_pl_obj})
                elif action_type == 'over_write':
                    '''cur_part[6 + region_count] = int(round(item_master_obj.sale_price, 2))
                    cur_part[7 + region_count] = int(round(item_master_obj.sale_price * cur_part[4 + region_count], 2))'''
                    cur_part[6 + region_count] = float(round(output_sale_price * def_markup, 2))
                    cur_part[7 + region_count] = float(round(output_sale_price * def_markup * cur_part[4 + region_count], 2))
    cursor.close()
    db.close()
    '''parts array modified ---------- for append type
    sample --> {'items':{region name':'no. of segments'}, {'department name':[[part_no, 'part_name', 'part_size', 'fin_no', 'seg1 qty', 'seg2 qty',...'tot_seg qty', norms, rate, value]]}}
    {"B.Wood Department":[["038-02-02-003-000-003-2400-1200-1200-0450",
    "Standard Storage - 450D - PLB Body & Top (Openable Shutter)  Recessed Hanldles",
    "2400 H x 1200 W Top: 1200  W x 450 D","17-11-11-413-57-60-0-0-0-0-0-0-0",8,8,"6000.00",17280,138240, new_rate, new_val,
    {'item_master':item_master_obj,'auto_pl':auto_pl_obj}]],
    "item":{"Region 1":1}}
    
    --------------- for over_write type there is no change in out put array format
    '''
    return((parts_array_360, tot_val))


def production_order_list(item_master_list):
    '''item_master_list = [(item_master_id1,qty),(item_master_id2,qty)....]
    this list gives the list of processes to be undertaken in a job/shop order
    '''
    input_dict = {}
    data = {}
    for cur_tup in item_master_list:
        if cur_tup[0] in input_dict:
            new_qty = input_dict[cur_tup[0]] + cur_tup[1]
            input_dict[cur_tup[0]] = new_qty
        else:
            input_dict[cur_tup[0]] = cur_tup[1]
    item_master_list = purge_pl(item_master_list)
    bom_rec = bom_collation(item_master_list, {'multi_layer':False})
    init_rm_list = bom_rec['sub_process_list'] + bom_rec['rm_list']
    init_rm_list = purge_pl(init_rm_list)
    found_dict = {}
    act_rm_list = []
    act_rec_list = []
    #found_list = item_master_list.Keys.Intersect(init_rm_list.Keys)
    for cur_init_rm in init_rm_list:
        cur_item_id = cur_init_rm[0]
        cur_rm_qty = float(cur_init_rm[1])
        if cur_init_rm[0] in input_dict:
            app_input_qty = input_dict[cur_item_id]
            if app_input_qty > cur_rm_qty:
                common_qty = float(cur_rm_qty)
            elif app_input_qty <= cur_rm_qty:
                common_qty = float(app_input_qty)
            if cur_rm_qty - common_qty > 0.0:
                act_rm_list.append((cur_init_rm[0], cur_rm_qty - common_qty))
            '''Modifying / Reducing the quatity in input_dict so that it can be 
            converted to tuple with ease'''
            input_dict[cur_item_id] = float(input_dict[cur_item_id]) - common_qty
            #act_rec_list.append((cur_init_rm[0]), app_input_qty - common_qty)
        else:
            if cur_rm_qty > 0.0:
                act_rm_list.append((cur_item_id, cur_rm_qty))
    for ip_key, mod_val in input_dict.items():
        if mod_val > 0.0:
            act_rec_list.append((ip_key, mod_val))
    #if dict['item_master_id'] in init_rm_list['sub_process_list']:
    #    found_list['item_master_id']
    data['rm_req'] = act_rm_list
    data['receivable'] = act_rec_list
    return(data)


def job_shop_plan_inv_jour(jour_qty_list):
    '''jour_qty_list = [(jour1_id, qty), (jour2_id, qty), (jour3_id, qty), .....]'''
    data = {}
    nested_rm_list = []
    tpl_pro_dict = {}
    tpl_rec_item = {}
    tot_pre_nested_rm = []
    tot_rec_item = []
    cons_pre_nested_rm = []
    cons_no_bom_rm = []
    cons_semi_fin_rm = []
    rec_item = []
    rm_item_list = []
    for cur_jour_set in jour_qty_list:
        cur_inv_jour = get_object_or_404(inventory_journal, id = cur_jour_set[0])
        cur_qty = cur_jour_set[1]
        cur_tpl_ref_no = cur_inv_jour.tpl_ref_no
        if not cur_tpl_ref_no in tpl_pro_dict:
            tpl_pro_dict[cur_inv_jour.tpl_ref_no] = []
        tpl_pro_dict[cur_tpl_ref_no].append((cur_inv_jour.item_master.id, cur_qty))
    for cur_tpl_ref, cur_prod_list in tpl_pro_dict.items():
        cur_prod_res = production_order_list(cur_prod_list)
        tpl_rec_item[cur_tpl_ref] = cur_prod_res['receivable']
        for cur_rec_item in cur_prod_res['receivable']:
            cur_rec_item = list(cur_rec_item)
            cur_rec_item.append({'tpl_ref':cur_tpl_ref})
            tot_rec_item.append(cur_rec_item)
        for cur_rm_item in cur_prod_res['rm_req']:
            cur_rm_item = list(cur_rm_item)
            cur_rm_item.append({'tpl_ref':cur_tpl_ref})
            cur_rm_item = tuple(cur_rm_item)
            tot_pre_nested_rm.append(cur_rm_item)
            cur_rm_item_obj = get_object_or_404(item_master, id = int(cur_rm_item[0]))
            cur_rm_item_bom = ast.literal_eval(cur_rm_item_obj.bom)
            if len(cur_rm_item_bom) == 0:
                cons_no_bom_rm.append(cur_rm_item)
                cons_pre_nested_rm.append(cur_rm_item[:2])
            else:
                cons_semi_fin_rm.append(cur_rm_item)
    cons_pre_nested_rm = purge_pl(cons_pre_nested_rm)
    nest_res = composite_nest(cons_pre_nested_rm)
    '''
    location_stock_list = {item_master_id1:qty, item_master_id2:qty...}
    plant_stock_list = {item_master_id1:qty, item_master_id2:qty...}
    '''
    for cur_rec in tot_rec_item:
        rec_item_obj = get_object_or_404(item_master, id=cur_rec[0])
        rec_item.append((rec_item_obj, cur_rec[1], cur_rec[2]))
    for cur_pre_rm in tot_pre_nested_rm:
        '''['rm_req'] is removed'''
        rm_item_obj = get_object_or_404(item_master, id=cur_pre_rm[0])
        rm_item_list.append((rm_item_obj, cur_pre_rm[1], cur_pre_rm[2]))
    for cur_nested_rm in nest_res['rm_list']:
        nested_rm_item_obj = get_object_or_404(item_master, id=cur_nested_rm[0])
        nested_rm_list.append([nested_rm_item_obj, cur_nested_rm[1], {'mod_qty':0, 'tot_qty':cur_nested_rm[1], 'tpl_ref':0}])
    for cur_semi_fin_rm in cons_semi_fin_rm:
        semi_fin_item_obj = get_object_or_404(item_master, id=cur_semi_fin_rm[0])
        cur_semi_fin_dict = cur_semi_fin_rm[2]
        nested_rm_list.append([semi_fin_item_obj, cur_semi_fin_rm[1], {'mod_qty':0, 'tot_qty':cur_nested_rm[1], 'tpl_ref':cur_semi_fin_dict['tpl_ref']}])
    data['receivable'] = rec_item
    data['pre_nest_rm_req'] = rm_item_list
    data['nested_rm_req'] = nested_rm_list
    return(data)


def job_shop_plan(tref_id):
    data = {}
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    if tref.submit == True:
        return HttpResponseRedirect(reverse('journal_mgmt:job_shop_order', args=(tref_id,)))
    inv_jour_list = inventory_journal.objects.filter(transaction_ref=tref)
    jour_qty_list = []
    for cur_inv_jour in inv_jour_list:
        jour_qty_list.append((cur_inv_jour.id, cur_inv_jour.issue_qty))
    new_data = job_shop_plan_inv_jour(jour_qty_list)
    """
    nested_rm_list = []
    tpl_pro_dict = {}
    tpl_rec_item = {}
    tot_pre_nested_rm = []
    tot_rec_item = []
    cons_pre_nested_rm = []
    cons_no_bom_rm = []
    cons_semi_fin_rm = []
    rec_item = []
    rm_item_list = []
    for cur_inv_jour in inv_jour_list:
        cur_tpl_ref_no = cur_inv_jour.tpl_ref_no
        if not cur_tpl_ref_no in tpl_pro_dict:
            tpl_pro_dict[cur_inv_jour.tpl_ref_no] = []
        tpl_pro_dict[cur_tpl_ref_no].append((cur_inv_jour.item_master.id, cur_inv_jour.issue_qty))
    for cur_tpl_ref, cur_prod_list in tpl_pro_dict.items():
        cur_prod_res = production_order_list(cur_prod_list)
        tpl_rec_item[cur_tpl_ref] = cur_prod_res['receivable']
        for cur_rec_item in cur_prod_res['receivable']:
            cur_rec_item = list(cur_rec_item)
            cur_rec_item.append({'tpl_ref':cur_tpl_ref})
            tot_rec_item.append(cur_rec_item)
        for cur_rm_item in cur_prod_res['rm_req']:
            cur_rm_item = list(cur_rm_item)
            cur_rm_item.append({'tpl_ref':cur_tpl_ref})
            cur_rm_item = tuple(cur_rm_item)
            tot_pre_nested_rm.append(cur_rm_item)
            cur_rm_item_obj = get_object_or_404(item_master, id = int(cur_rm_item[0]))
            cur_rm_item_bom = ast.literal_eval(cur_rm_item_obj.bom)
            if len(cur_rm_item_bom) == 0:
                cons_no_bom_rm.append(cur_rm_item)
                cons_pre_nested_rm.append(cur_rm_item[:2])
            else:
                cons_semi_fin_rm.append(cur_rm_item)
    cons_pre_nested_rm = purge_pl(cons_pre_nested_rm)
    nest_res = composite_nest(cons_pre_nested_rm)
    '''
    location_stock_list = {item_master_id1:qty, item_master_id2:qty...}
    plant_stock_list = {item_master_id1:qty, item_master_id2:qty...}
    '''
    for cur_rec in tot_rec_item:
        rec_item_obj = get_object_or_404(item_master, id=cur_rec[0])
        rec_item.append((rec_item_obj, cur_rec[1], cur_rec[2]))
    for cur_pre_rm in tot_pre_nested_rm:
        '''['rm_req'] is removed'''
        rm_item_obj = get_object_or_404(item_master, id=cur_pre_rm[0])
        rm_item_list.append((rm_item_obj, cur_pre_rm[1], cur_pre_rm[2]))
    for cur_nested_rm in nest_res['rm_list']:
        nested_rm_item_obj = get_object_or_404(item_master, id=cur_nested_rm[0])
        nested_rm_list.append([nested_rm_item_obj, cur_nested_rm[1], {'mod_qty':0, 'tot_qty':cur_nested_rm[1], 'tpl_ref':0}])
    for cur_semi_fin_rm in cons_semi_fin_rm:
        semi_fin_item_obj = get_object_or_404(item_master, id=cur_semi_fin_rm[0])
        cur_semi_fin_dict = cur_semi_fin_rm[2]
        nested_rm_list.append([semi_fin_item_obj, cur_semi_fin_rm[1], {'mod_qty':0, 'tot_qty':cur_nested_rm[1], 'tpl_ref':cur_semi_fin_dict['tpl_ref']}])
    """
    data['process'] = inv_jour_list
    data['receivable'] = new_data['receivable']
    data['pre_nest_rm_req'] = new_data['pre_nest_rm_req']
    data['nested_rm_req'] = new_data['nested_rm_req']
    data['tref'] = tref
    return(data)

def feed_list_prep(obj_list):
    feed_list = []
    '''obj_list = [[item_master1_obj, qty, {'tpl_ref':123, 'mod_qty':...,...}], [item_master2_obj, qty, {'tpl_ref':123, 'mod_qty':...,...}]]'''
    for cur_obj in obj_list:
        feed_list.append([cur_obj[0].id, cur_obj[1], cur_obj[2]])
    '''feed_list = [[item_master1_id, qty, {'tpl_ref':123, 'mod_qty':...,...}], [item_master2_id, qty, {'tpl_ref':123, 'mod_qty':...,...}]]'''
    return(feed_list)

def job_shop_stk_validate(tref_id, nested_rm_obj_list):
    '''nested_rm_obj_list = [(item_master_obj, qty, {'tpl_ref':123, 'mod_qty':123}), (), ()...]'''
    data = {}
    ttype_obj_dict = get_job_shop_ttype(tref_id)
    foreign_location_obj = ttype_obj_dict['nested_rm_location']
    plant_location_obj = get_location_raw('plant', 1)
    foreign_stk_check = {}
    plant_stk_check = {}
    rm_util_item_obj_list = []
    mov_rm_item_obj_list = []
    tot_stk_available = True
    '''
    plant_stk_check = {rm_item_master1_id:{'available':123, 'balance':123},.....}
    foreign_stk_check = {rm_item_master1_id:{'available':123, 'balance':123},.....}
    rm_util_item_obj_list = [(item_master_obj, qty, {'tpl_ref':123, 'mod_qty':123}), (), ()...]
    mov_rm_item_obj_list = [(item_master_obj, qty, {'tpl_ref':123, 'mod_qty':123}), (), ()...]'''
    for cur_nested_rm in nested_rm_obj_list:
        cur_rm_obj = cur_nested_rm[0]
        cur_req_qty = cur_nested_rm[1]
        cur_tpl_ref = int(cur_nested_rm[2]['tpl_ref'])
        cur_foreign_util_qty = 0
        cur_plant_util_qty = 0
        if not cur_rm_obj.id in foreign_stk_check:
            foreign_stk = current_stock.objects.filter(item_master_ref = cur_rm_obj, location_ref = foreign_location_obj, tpl_ref_no = cur_tpl_ref)
            if len(foreign_stk) == 0:
                foreign_stk_check[cur_rm_obj.id] = {'available':0, 'balance':0}
            elif len(foreign_stk) > 1:
                return('error')
            else:
                foreign_stk = foreign_stk[0]
                foreign_stk_check[cur_rm_obj.id] = {'available':float(foreign_stk.cur_stock), 'balance':float(foreign_stk.cur_stock)}
        if not cur_rm_obj.id in plant_stk_check:
            plant_stk = current_stock.objects.filter(item_master_ref = cur_rm_obj, location_ref = plant_location_obj, tpl_ref_no = cur_tpl_ref)
            if len(plant_stk) == 0:
                plant_stk_check[cur_rm_obj.id] = {'available':0, 'balance':0}
            elif len(plant_stk) > 1:
                return('error')
            else:
                plant_stk = plant_stk[0]
                plant_stk_check[cur_rm_obj.id] = {'available':float(plant_stk.cur_stock), 'balance':float(plant_stk.cur_stock)}
        '''deducting balance in foreign location'''
        foreign_stk_bal = foreign_stk_check[cur_rm_obj.id]['balance']
        if cur_req_qty <= foreign_stk_bal:
            cur_foreign_util_qty = cur_req_qty
        else:
            cur_foreign_util_qty = foreign_stk_bal
        cur_bal_qty = cur_req_qty - cur_foreign_util_qty
        if cur_foreign_util_qty > 0:
            foreign_stk_check[cur_rm_obj.id]['balance'] = foreign_stk_bal - cur_foreign_util_qty
            rm_util_item_obj_list.append([cur_rm_obj, cur_foreign_util_qty, {'tpl_ref':cur_tpl_ref}])
        if cur_bal_qty > 0:
            '''deducting balance in plant location'''
            plant_stk_bal = plant_stk_check[cur_rm_obj.id]['balance']
            if cur_bal_qty <= plant_stk_bal:
                cur_plant_util_qty = cur_bal_qty
            else:
                cur_plant_util_qty = plant_stk_bal
            cur_bal_qty -= cur_plant_util_qty
            if cur_plant_util_qty > 0:
                plant_stk_check[cur_rm_obj.id]['balance'] = plant_stk_bal - cur_plant_util_qty
                mov_rm_item_obj_list.append([cur_rm_obj, cur_plant_util_qty, {'tpl_ref':cur_tpl_ref}])
        if not cur_bal_qty == 0:
            tot_stk_available = False
    data['valid'] = tot_stk_available
    data['foreign_stk'] = foreign_stk_check
    data['plant_stk'] = plant_stk_check
    data['rm_util_item_obj_list'] = rm_util_item_obj_list
    data['mov_rm_item_obj_list'] = mov_rm_item_obj_list
    return(data)

def job_shop_mov_feed_prepare(inward_ttype, mov_rm_item_obj_list):
    '''
    inward_ttype = transaction_type object which takes the material into the plant
    mov_rm_util_item_obj_list = [(item_master_obj, qty, {'tpl_ref':123, 'mod_qty':123}), (), ()...]
    mov_rm_util_feed_list = [(inward_jour1_id, qty_to_be_sent, {tpl_ref:123}), (), ()...]
    '''
    mov_rm_feed_list = []
    for cur_mov_rm in mov_rm_item_obj_list:
        cur_mov_rm_item_obj = cur_mov_rm[0]
        cur_mov_rm_qty = cur_mov_rm[1]
        cur_tpl_ref = cur_mov_rm[2]['tpl_ref']
        req_qty = cur_mov_rm_qty
        bal_req_qty = req_qty
        app_inw_jour_obj_list = inventory_journal.objects.filter(transaction_ref__transaction_type = inward_ttype, \
                                                                 transaction_ref__active = True, balance_qty__gt = 0, \
                                                                 item_master = cur_mov_rm_item_obj, tpl_ref_no = cur_tpl_ref).order_by('transaction_ref__submit_date')
        for cur_jour in app_inw_jour_obj_list:
            cur_avail_qty = cur_jour.balance_qty
            if bal_req_qty <= cur_avail_qty:
                cur_mov_qty = req_qty
            else:
                cur_mov_qty = cur_avail_qty
            mov_rm_feed_list.append([cur_jour.id, cur_mov_qty, {'tpl_ref':cur_tpl_ref}])
            bal_req_qty -= cur_mov_qty
            if bal_req_qty == 0:
                break
    return(mov_rm_feed_list)

def app_price_update(item_master_obj, config):
    '''config = {'fasttrack':True/False}'''
    item_master_id = item_master_obj.id
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], \
                          password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    par_br = param_break(item_master_obj.imported_item_code, item_master_obj.imported_item_finish)
    check_new_pl = par_br['pn']
    param = (par_br['pn']['n'], par_br['pn']['s'], par_br['pn']['m'], par_br['pn']['s1'], par_br['pn']['s2'], par_br['pn']['s3'])
    cursor.execute("""select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d""" % param)
    check_res = cursor.fetchall()
    '''this code is written to consider pl items which are closest 
    match  in cases where complete spec code doesn't match with entries in price_list'''
    if len(check_res) == 0:
        std_pl_query = get_std_pl_query(par_br['pn'], par_br['price_dep_arr'])
        cursor.execute(std_pl_query[0] % std_pl_query[1])
        check_res = cursor.fetchall()
    pl_360_obj = check_res[0]
    cursor.execute("""select * from b_o_m where pl_id=%d""" % (pl_360_obj[0],))
    bom_360 = cursor.fetchall()
    if item_master_obj.price_last_updated == None:
        item_master_obj.price_last_updated = timezone.now() - timedelta(days=20)
        item_master_obj.save()
        item_master_obj = get_object_or_404(item_master, id = item_master_id)
    time_diff = timezone.now() - item_master_obj.price_last_updated
    if not(time_diff <= timedelta(days=2) and config['fasttrack'] == True):
        if len(bom_360) == len(ast.literal_eval(item_master_obj.bom)):
            bom_input_sum(item_master_id, {'update_ip_factor':True})
        else:
            infinite_update([(item_master_obj.imported_item_code, item_master_obj.imported_item_finish, 1)], True, {'auto_update':True})
    cursor.close()
    db.close()
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    return(item_master_obj)

def price_matrix_opt_gen(auto_pl_id, rank_size):
    output_data = {}
    '''output needed is as follows:
    d1_opt = [val1, val2, val3...] 
    which lists all the d1 values available in the item master list corresponding
    to the given auto_pl_id
    similarly 
    d2_opt = [...], d3_opt = [...] & d4_opt = [...] will follow suite
    
    d1_ranking = [{'val':val1, 'count':count_val}, {}, {}...]
    d1_ranking lists the dictionaries containing the count of repeated d1 values in various
    item masters & ofcourse, with the value of D1
    similarly
    d2_ranking = [...], d3_ranking = [...] & d4_ranking = [...]
    finally the values of d1_ranking & d2_ranking are cut to the table size - rows & columns
    
    '''
    d1_opt = []
    d2_opt = []
    d3_opt = []
    d4_opt = []
    d1_ranking = []
    d2_ranking = []
    d3_ranking = []
    d4_ranking = []
    auto_pl_id = int(auto_pl_id)
    auto_pl_obj = get_object_or_404(auto_price_list, id=auto_pl_id)
    all_app_item_master = item_master.objects.filter(imported_item_code__startswith=auto_pl_obj.spec_code)
    for cur_item_master in all_app_item_master:
        imp_item_code = cur_item_master.imported_item_code
        master_d1 = int(imp_item_code[22:26])
        '''preparing ranks of D1 - sount of repetativeness'''
        if not master_d1 in d1_opt:
            d1_opt.append(master_d1)
            d1_ranking.append({'val':master_d1, 'count':1})
        else:
            for cur_d1_ranking_dict in d1_ranking:
                if cur_d1_ranking_dict['val'] == master_d1:
                    cur_index = d1_ranking.index(cur_d1_ranking_dict)
                    d1_ranking[cur_index]['count'] += 1
                    break
        master_d2 = int(imp_item_code[27:31])
        '''preparing ranks of D2 - sount of repetativeness'''
        if not master_d2 in d2_opt:
            d2_opt.append(master_d2)
            d2_ranking.append({'val':master_d2, 'count':1})
        else:
            for cur_d2_ranking_dict in d2_ranking:
                if cur_d2_ranking_dict['val'] == master_d2:
                    cur_index = d2_ranking.index(cur_d2_ranking_dict)
                    d2_ranking[cur_index]['count'] += 1
                    break
        master_d3 = int(imp_item_code[32:36])
        if not master_d3 in d3_opt:
            d3_opt.append(master_d3)
            d3_ranking.append({'val':master_d3, 'count':1})
        else:
            for cur_d3_ranking_dict in d3_ranking:
                if cur_d3_ranking_dict['val'] == master_d3:
                    cur_index = d3_ranking.index(cur_d3_ranking_dict)
                    d3_ranking[cur_index]['count'] += 1
                    break
        master_d4 = int(imp_item_code[37:41])
        if not master_d4 in d4_opt:
            d4_opt.append(master_d4)
            d4_ranking.append({'val':master_d4, 'count':1})
        else:
            for cur_d4_ranking_dict in d4_ranking:
                if cur_d4_ranking_dict['val'] == master_d4:
                    cur_index = d4_ranking.index(cur_d4_ranking_dict)
                    d4_ranking[cur_index]['count'] += 1
                    break
    d1_opt = sorted(d1_opt)
    d2_opt = sorted(d2_opt)
    d3_opt = sorted(d3_opt)
    d4_opt = sorted(d4_opt)
    '''sorting by rank first, taking top 5 values & then sorting by ascending value again for display purpose'''
    d1_ranking = sorted(sorted(d1_ranking, key=lambda x:-x['count'])[:rank_size], key=lambda x:x['val'])
    d2_ranking = sorted(sorted(d2_ranking, key=lambda x:-x['count'])[:rank_size], key=lambda x:x['val'])
    d3_ranking = sorted(sorted(d3_ranking, key=lambda x:-x['count'])[:rank_size], key=lambda x:x['val'])
    d4_ranking = sorted(sorted(d4_ranking, key=lambda x:-x['count'])[:rank_size], key=lambda x:x['val'])
    output_data['d1_opt'] = d1_opt
    output_data['d2_opt'] = d2_opt
    output_data['d3_opt'] = d3_opt
    output_data['d4_opt'] = d4_opt
    output_data['d1_ranking'] = d1_ranking
    output_data['d2_ranking'] = d2_ranking
    output_data['d3_ranking'] = d3_ranking
    output_data['d4_ranking'] = d4_ranking
    return(output_data)

def price_matrix_generator(auto_pl_id, d1_list, d2_list, d3_val, d4_val, hike):
    output_data = {}
    '''the needed output are 2 lists - 
    disp_tab_data = [[valr1c1, valr1c2, valr1c3...], [valr2c1, ...], []] - where values are actual sale values in the database
    disp_tab_rate_data = [[valr1c1, valr1c2, valr1c3...], [valr2c1, ...], []] - where values are sqmt/rmt rate for the items respectively'''
    disp_tab_sp_data = []
    disp_tab_ip_data = []
    disp_tab_rate_data = []
    auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
    d3_str = str(10000 + d3_val)[1:]
    d4_str = str(10000 + d4_val)[1:]
    for cur_d2 in d2_list:
        cur_d2_str = str(10000 + cur_d2)[1:]
        cur_row_sp_data = []
        cur_row_rate_data = []
        cur_row_ip_data = []
        for cur_d1 in d1_list:
            multd1 = 1
            multd2 = 1
            if cur_d1 > 0:
                multd1 = Decimal(cur_d1 / 1000)
            if cur_d2 > 0:
                multd2 = Decimal(cur_d2 / 1000)
            area = multd1 * multd2
            cur_d1_str = str(10000 + cur_d1)[1:]
            imp_item_code = auto_pl_obj.spec_code + '-' + cur_d1_str + '-' + cur_d2_str + '-' + d3_str + '-' + d4_str
            item_master_opt = item_master.objects.filter(imported_item_code=imp_item_code)
            all_match = True
            if len(item_master_opt) > 0:
                # init_bom_sale_price = item_master_opt[0].bom_sale_price
                init_item_master = app_price_update(item_master_opt[0], {'fasttrack':True})
                init_bom_sale_price = init_item_master.bom_sale_price
                for cur_item in item_master_opt:
                    diff = cur_item.bom_sale_price - init_bom_sale_price
                    if diff > 10 or diff < -10:
                        all_match = False
                        break
                if all_match == False:
                    for cur_item in item_master_opt:
                        app_price_update(cur_item, {'fasttrack':True})
                        # infinite_update([(cur_item.imported_item_code, cur_item.imported_item_finish, 1.0)], True, {'auto_update':True})
                cur_row_ip_data.append(item_master_opt[0].bom_input_price)
                cur_row_sp_data.append(float(item_master_opt[0].bom_sale_price) * float(hike))
                cur_row_rate_data.append(round(item_master_opt[0].bom_sale_price / area, 2))
            else:
                cur_row_ip_data.append('N/A')
                cur_row_sp_data.append('N/A')
                cur_row_rate_data.append('N/A')
        disp_tab_ip_data.append(cur_row_ip_data)
        disp_tab_sp_data.append(cur_row_sp_data)
        disp_tab_rate_data.append(cur_row_rate_data)
    output_data['disp_tab_sp_data'] = disp_tab_sp_data
    output_data['disp_tab_ip_data'] = disp_tab_ip_data
    output_data['disp_tab_rate_data'] = disp_tab_rate_data
    return(output_data)


def prod_kit_availability(item_master_id, qty, tpl_ref_no):
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    main_bom_arr = ast.literal_eval(item_master_obj.bom)
    data = {'plant':'NK', 'vendor':'NK', 'work_center':'NK'}
    redo = False
    for cur_bom_arr in main_bom_arr:
        cur_bom_item_id = cur_bom_arr[0]
        bom_item_obj = item_master.objects.filter(id = cur_bom_item_id)
        if len(bom_item_obj) == 0:
            infinite_update([(item_master_obj.imported_item_code, item_master_obj.imported_item_finish, 1)], True, {'auto_update':True})
            break
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    main_bom_arr = ast.literal_eval(item_master_obj.bom)
    for cur_bom_arr in main_bom_arr:
        cur_bom_item_id = int(cur_bom_arr[0])
        cur_req_qty = float(cur_bom_arr[1]) * qty
        bom_item_obj = get_object_or_404(item_master, id = cur_bom_item_id)
    return()


def job_shop_prepare(job_shop_dict, inv_jour_id, stock_loc_id_list, tref_add_data, inp_settings, tref_id):
    '''
    job_shop_dict = {vendor_id/work_center_id:[(jour_id, issue_qty, {'tpl_ref':tref.id}), (jour_id, qty, {'tpl_ref':tref.id})....], ...}, {}, {}...}
    stock_loc_id_list = [vendor_loc_ref_id1, vendor_loc_ref_id2, vendor_loc_ref_id3...]
    tref_add_data = {'vendor':True/'work_center':True, 'sel_id':vendor_id/work_center_id, mod_qty:float, 'jo_detail_list'/'so_detail_list':{'sel_city':, }}
    inv_jour_id = integer pk of inventory journal table
    inp_settings = {'save':True/False}
    '''
    data = {}
    sum_tot_qty = 0
    error = 0
    name = ''
    nested_rm_req_list = []
    dict_list = []
    nested_list = []
    pre_nest_rm_req_list = []
    receivable_list = []
    wc_nested_list = []
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    cur_inv_jour = get_object_or_404(inventory_journal, id=inv_jour_id)
    sel_id  = tref_add_data['sel_id']
    dict_list.append(job_shop_dict[sel_id])
    for cur_stock_loc_ref_id in stock_loc_id_list:
        for cur_list in dict_list:
            raw_material_dict = job_shop_plan_inv_jour(cur_list)
            rec_item_feed_list = feed_list_prep(raw_material_dict['receivable'])
            nested_rm_list = raw_material_dict['nested_rm_req']
            for cur_raw_material in raw_material_dict['nested_rm_req']:
                raw_material = cur_raw_material[2]
                req_qty = raw_material['tot_qty']
                data['req_qty'] = float(req_qty)
                req_item_id = cur_raw_material[0].id
                req_tare_id = cur_raw_material[0].id
                if 'vendor' in tref_add_data:
                    stk_qty_tpl = get_stock(req_tare_id, cur_inv_jour.tpl_ref_no, 'vendor', cur_stock_loc_ref_id)
                    stk_qty_no_tpl = get_stock(req_tare_id, 0, 'vendor', cur_stock_loc_ref_id)
                if 'work_center' in tref_add_data:
                    stk_qty_tpl = get_stock(req_tare_id, cur_inv_jour.tpl_ref_no, 'work_center', cur_stock_loc_ref_id)
                    stk_qty_no_tpl = get_stock(req_tare_id, 0, 'work_center', cur_stock_loc_ref_id)
                stk_qty_plant_tpl = get_stock(req_tare_id, cur_inv_jour.tpl_ref_no, 'plant', 1)
                stk_qty_plant_no_tpl = get_stock(req_tare_id, 0, 'plant', 1)
                tot_stk_qty = stk_qty_tpl + stk_qty_no_tpl + stk_qty_plant_tpl + stk_qty_plant_no_tpl
                sum_tot_qty = sum_tot_qty + req_qty
                if tot_stk_qty > req_qty:
                    #mod_qty_job = float(tref_add_data['mod_qty'])
                    mod_qty_job = 0
                    req_qty_job = req_qty
                    nested_mod_qty = mod_qty_job + req_qty_job
                    nested_rm_req_list.append((req_item_id, nested_mod_qty, {'mod_qty':mod_qty_job, 'tot_qty':nested_mod_qty, 'tpl_ref':0}))
                if len(raw_material_dict['nested_rm_req']) > 0:
                    nested_list.append((cur_raw_material[0].name ,tot_stk_qty, req_qty, inv_jour_id))
                data['nested_list'] = nested_list
                data['tot_stk_qty'] = tot_stk_qty
                data['nested_mod_qty'] = nested_mod_qty
            for cur_pre_nest_rm_req in raw_material_dict['pre_nest_rm_req']:
                pre_nest_rm_req_list.append((cur_pre_nest_rm_req[0].id, cur_pre_nest_rm_req[1], cur_pre_nest_rm_req[2]))
            for cur_receivable in raw_material_dict['receivable']:
                receivable_list.append((cur_receivable[0].id, cur_receivable[1], cur_receivable[2]))
            data['nested_rm_req_list'] = nested_rm_req_list
            data['receivable_list'] = receivable_list
            data['nested_list'] = nested_list
            data['pre_nest_rm_req_list'] = pre_nest_rm_req_list
            data['rec_item_feed_list'] = rec_item_feed_list
    if inp_settings['save'] == True and error == 0:
        ttype = tref.transaction_type
        if tot_stk_qty > nested_mod_qty :
            if 'vendor' in tref_add_data: 
                for cur_vendor_id, jour_det_list in job_shop_dict.items():
                    '''job_order_process ttype ref number is 12'''
                    pur_ord_ttype_obj = get_object_or_404(transaction_type, transaction_type_ref_no=12)
                    job_shop_pro_tref_dict = fetch_tref_data(pur_ord_ttype_obj, [], {})['tref_data']['field_list']
                    job_shop_pro_tref_dict['vendor'] = (cur_vendor_id, name)
                    jo_detail_dict = tref_add_data['jo_detail_dict']
                    job_shop_pro_tref_dict['ship_to'] = jo_detail_dict['ship_to']
                    job_shop_pro_tref_dict['shipping_addr1'] = jo_detail_dict['shipping_addr1']
                    job_shop_pro_tref_dict['shipping_addr2'] = jo_detail_dict['shipping_addr2']
                    job_shop_pro_tref_dict['city'] = jo_detail_dict['city']
                    job_shop_pro_tref_dict['state'] = jo_detail_dict['state']
                    job_shop_pro_tref_dict['date'] = jo_detail_dict['date']
                    job_shop_obj = auto_create_tref(12, {'field_list':job_shop_pro_tref_dict}, jour_det_list, False, {})
            if 'work_center' in tref_add_data: 
                for cur_work_center_id, jour_det_list in job_shop_dict.items():
                    '''shop_order_process ttype ref number is 16'''
                    pur_ord_ttype_obj = get_object_or_404(transaction_type, transaction_type_ref_no=16)
                    job_shop_pro_tref_dict = fetch_tref_data(pur_ord_ttype_obj, [], {})['tref_data']['field_list']
                    job_shop_pro_tref_dict['work_center'] = (cur_work_center_id, name)
                    so_detail_dict = tref_add_data['so_detail_dict']
                    job_shop_pro_tref_dict['delivery_dt'] = so_detail_dict['delivery_dt']
                    job_shop_obj = auto_create_tref(16, {'field_list':job_shop_pro_tref_dict}, jour_det_list, False, {})
            ttype_obj_dict = get_job_shop_ttype(job_shop_obj.id)
            rec_ttype = ttype_obj_dict['receivable']
            pre_nest_rm_ttype = ttype_obj_dict['pre_nested_rm']
            nested_rm_ttype = ttype_obj_dict['nested_rm']
            rm_util_ttype = ttype_obj_dict['rm_utilization']
            mov_rm_ttype = ttype_obj_dict['move_rm']
            mov_rm_field_list = ttype_obj_dict['move_rm_field_list']
            material_inward_ttype = ttype_obj_dict['material_inward']
            mov_feed_list = job_shop_mov_feed_prepare(material_inward_ttype, nested_rm_req_list)
            del_rm_tref = auto_create_tref(mov_rm_ttype.transaction_type_ref_no, \
                                       {'field_list':mov_rm_field_list}, mov_feed_list, True, {'chain_tref':job_shop_obj.id})
            comp_tref_dict = fetch_tref_data(nested_rm_ttype, [], {})['tref_data']['field_list']
            auto_create_tref(nested_rm_ttype.transaction_type_ref_no, comp_tref_dict, nested_rm_req_list, True, {'chain_tref':job_shop_obj.id})
            pre_nest_tref_dict = fetch_tref_data(pre_nest_rm_ttype, [], {})['tref_data']['field_list']
            auto_create_tref(pre_nest_rm_ttype.transaction_type_ref_no, comp_tref_dict, pre_nest_rm_req_list, True, {'chain_tref':job_shop_obj.id})
            nest_tref_dict = fetch_tref_data(rec_ttype, [], {})['tref_data']['field_list']
            component_tref = auto_create_tref(rec_ttype.transaction_type_ref_no, nest_tref_dict, rec_item_feed_list, False, {'chain_tref':job_shop_obj.id})
            job_shop_obj = tref_submit(job_shop_obj.id)
    return (data)    


def penetration_xls(fetched_data):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    xls_sheet = workbook.add_worksheet('bpr')
    export_data = {}
    export_data['co_ordinate'] = (0, 0)
    export_data['col_width'] = [5, 40, 15, 15]
    export_data['header'] = ['Sl No.', 'Project Name', 'Location', 'Revision', 'Revision Remarks', 'Qutation Date', 'Quote Name', 'Designer', 'Quote Value', 'WKS', 'FST0', 'ACC', 'Storage', 'P']
    #major_groups = auto_price_list.objects.order_by('name')
    export_data['body'] = []
    export_data['sheet_name'] = 'bpr'
    export_data['conditional_format_type'] = 'price_list'
    export_data['default_format'] = workbook.add_format()
    i = 0
    for cur_data in fetched_data:
        i += 1        
        export_row = [i, cur_data[0], cur_data[1], cur_data[2]]
        export_data['body'].append(export_row)
    gen_excel_export(export_data, xls_sheet)
    workbook.close()
    output.seek(0)
    response_obj = HttpResponse()
    response_obj['Content-Disposition'] = 'attachment; filename=Price List.xlsx'
    response_obj['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response_obj['Cache-Control'] = 'no-cache'
    response_obj.write(output.read())
    return response_obj

def rmp_export(fetched_data_1):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    xls_sheet = workbook.add_worksheet('price_list')
    export_data = {}
    export_data['co_ordinate'] = (0, 0)
    export_data['col_width'] = [5, 40, 15, 15]
    export_data['header'] = ['Sl No.', 'name', 'value', 'definition', 'constant']
    export_data['body'] = []
    export_data['sheet_name'] = 'price_list'
    export_data['conditional_format_type'] = 'price_list'
    export_data['default_format'] = workbook.add_format()
    i = 0
    for cur_data in fetched_data_1:
        i += 1        
        export_row = [i, cur_data[0], cur_data[1], cur_data[2], cur_data[3]]
        export_data['body'].append(export_row)
    gen_excel_export(export_data, xls_sheet)
    workbook.close()
    output.seek(0)
    response_obj = HttpResponse()
    response_obj['Content-Disposition'] = 'attachment; filename=Raw Material Prices.xlsx'
    response_obj['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response_obj['Cache-Control'] = 'no-cache'
    response_obj.write(output.read())
    return response_obj

def weight_vol_update(item_id, type):
    '''type = {'update_ip_factor':True/False}'''
    data = {}
    inf_bom_list = collate_inf_bom(item_id)
    item_master_obj = get_object_or_404(item_master, id = item_id)
    inf_bom_list.append((item_master_obj.id, 1))
    tot_volume = 0
    tot_weight= 0
    for cur_item_master_row in inf_bom_list:
        cur_item_master_id = cur_item_master_row[0]
        cur_item_qty = float(cur_item_master_row[1])
        cur_item_master_obj = get_object_or_404(item_master, id = cur_item_master_id)
        if type['update_ip_factor'] == True:
            item_spec_code = cur_item_master_obj.imported_item_code[0:21]
            auto_pl_obj = get_object_or_404(auto_price_list, spec_code = item_spec_code)
            broken_item = param_break(cur_item_master_obj.imported_item_code, cur_item_master_obj.imported_item_finish)
            rmp_con = get_rmp_con(auto_pl_obj.id, 0, 'sale')
            weight_cal_eqn = auto_pl_obj.weight_calc_eqn
            volume_cal_eqn = auto_pl_obj.volume_calc_eqn
            weight_eqn = dim_cost_port(broken_item['pn'], auto_pl_obj.input_rate_sale, rmp_con[0], rmp_con[1], weight_cal_eqn, 1)
            cur_weight = (round(eval(weight_eqn), 4)) * cur_item_qty
            volume_eqn = dim_cost_port(broken_item['pn'], auto_pl_obj.input_rate_sale, rmp_con[0], rmp_con[1], volume_cal_eqn, 1)
            cur_volume = (round(eval(volume_eqn), 4)) * cur_item_qty
            cur_item_master_obj.volume_factor = cur_volume
            cur_item_master_obj.weight_factor = cur_weight
            cur_item_master_obj.save()
            cur_item_master_obj = get_object_or_404(item_master, id = cur_item_master_id)
        tot_volume += float(cur_item_master_obj.volume_factor)
        tot_weight += float(cur_item_master_obj.weight_factor)
    tot_weight = (round(eval(str(tot_weight)), 4))
    tot_volume = (round(eval(str(tot_volume)), 6))
    item_master_obj.item_volume = tot_volume
    item_master_obj.item_weight = tot_weight
    item_master_obj.save()
    data['tot_weight'] = tot_weight
    data['tot_volume'] = tot_volume
    return (data) 

def quotation_xls(list):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    xls_sheet = workbook.add_worksheet('quotation')
    export_data = {}
    export_data['body'] = list['body']
    export_data['header'] = list['header']
    export_data['col_width'] = list['col_width']
    export_data['co_ordinate'] = list['co_ordinate']
    export_data['sheet_name'] = 'quotation'
    export_data['conditional_format_type'] = list['conditional_format_type']
    export_data['default_format'] = workbook.add_format()
    gen_excel_export(export_data, xls_sheet)
    workbook.close()
    output.seek(0)
    response_obj = HttpResponse()
    response_obj['Content-Disposition'] = 'attachment; filename='+ export_data['conditional_format_type'] +'.xlsx'
    response_obj['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response_obj['Cache-Control'] = 'no-cache'
    response_obj.write(output.read())
    return (response_obj)

def xls_matrix_prepare(auto_pl_id, hike, max_cols, settings):
    '''settings = {'gen_type':'auto_gen'}
    OR
    settings = {'gen_type':'stored_genre', 'd1':[12, 13, 24], 'd2':[13, 24, 32], 'd3':val, 'd4':val}'''
    output_data = {}
    ip_rate_table = []
    sp_rate_table = []
    auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
    matrix_opt_output = price_matrix_opt_gen(auto_pl_obj.id, max_cols)
    disp_tab_x_head = []
    disp_tab_y_head = []
    if (settings['gen_type'] == 'auto_gen'):
        for cur_d1_dict in matrix_opt_output['d1_ranking']:
            disp_tab_x_head.append(cur_d1_dict['val'])
        for cur_d2_dict in matrix_opt_output['d2_ranking']:
            disp_tab_y_head.append(cur_d2_dict['val'])
        d3_val = sorted(matrix_opt_output['d3_ranking'], key=lambda x:-x['count'])[0]['val']
        d4_val = sorted(matrix_opt_output['d4_ranking'], key=lambda x:-x['count'])[0]['val']
    elif (settings['gen_type'] == 'stored_genre'):
        for cur_d1_val in settings['d1']:
            disp_tab_x_head.append(cur_d1_val)
        for cur_d2_val in settings['d2']:
            disp_tab_y_head.append(cur_d2_val)
        d3_val = settings['d3']
        d4_val = settings['d4']
    data_output = price_matrix_generator(auto_pl_id, disp_tab_x_head, disp_tab_y_head, d3_val, d4_val, hike)
    '''header'''
    ip_rate_table.append([auto_pl_obj.name]) #row1
    time_stamp = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    ip_rate_table.append(['Input Price - ' + time_stamp]) #row2
    ip_rate_table.append(['Margin', float(auto_pl_obj.sale_margin), 'hike%', hike, 'D3=' + str(d3_val), 'D4=' + str(d4_val)])#row3
    ip_rate_table.append([''])
    ip_rate_table.append(['D1/D2'] + disp_tab_x_head) #row4
    i = 0
    for cur_val_row in data_output['disp_tab_ip_data']:
        row_data = [disp_tab_y_head[i]] + cur_val_row #1st column will be D2 header & the rest will be values
        ip_rate_table.append(row_data)
        i += 1
    
    sp_rate_table.append([auto_pl_obj.name]) #row1
    time_stamp = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    sp_rate_table.append(['Sale Price - ' + time_stamp]) #row2
    sp_rate_table.append(['Margin', auto_pl_obj.sale_margin, 'hike%', str(hike), 'D3=' + str(d3_val), 'D4=' + str(d4_val)])#row3
    sp_rate_table.append([''])
    sp_rate_table.append(['D1/D2'] + disp_tab_x_head) #row4
    i = 0
    for cur_rate_row in data_output['disp_tab_sp_data']:
        row_data = [disp_tab_y_head[i]] + cur_rate_row #1st column will be D2 header & the rest will be values
        sp_rate_table.append(row_data)
        i += 1
    
    output_data['ip_rate_table'] = ip_rate_table
    output_data['sp_rate_table'] = sp_rate_table
    return(output_data)

def price_matrix_xls(input_dict):
    '''auto_pl_id_list = [[p1id1, p1id2, p1id3], [p2id1, p2id2...], [...]]
    the input list contains many lists inside it, each of which will contain the auto_lp_ids of items to be tabulated
    each list inside the main list defines a different page & each id in the small list will give the tables listed in that page
    input_dict = {'input_type':'auto_gen', 'auto_pl_id_list':[[p1id1, p1id2, p1id3], [p2id1, p2id2...], [...]], 'max_cols':no. of cols in tabulation}
            OR
    input_dict = {'input_type':'stored_genre', 'auto_pl_id_list':[[p1id1, p1id2, p1id3], [p2id1, p2id2...], [...]], 'max_cols':no. of cols in tabulation}
    '''
    calc_type = input_dict['input_type']
    output = io.BytesIO()
    
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    i = 1
    for cur_auto_pl_id_list in input_dict['auto_pl_id_list']:
        xls_sheet = workbook.add_worksheet('tabulation'+str(i))
        start_point = {'x':1, 'y':1}
        current_point = copy.deepcopy(start_point)
        cur_height = 0
        for cur_auto_pl_id in cur_auto_pl_id_list:
            if cur_auto_pl_id == 3599:
                print('3599')
            '''resetting the x - coordinate'''
            if calc_type == 'auto_gen':
                all_matrix_ouput = []
                max_cols = input_dict['max_cols']
                matrix_output = xls_matrix_prepare(cur_auto_pl_id, 1.067, max_cols, {'gen_type':'auto_gen'})
                all_matrix_ouput.append(matrix_output)
            elif calc_type == 'stored_genre':
                all_matrix_ouput = []
                all_auto_pl_data = xls_price_matrix_data()
                for cur_d3_d4_dict in all_auto_pl_data[cur_auto_pl_id]:
                    max_cols = input_dict['max_cols']
                    matrix_output = xls_matrix_prepare(cur_auto_pl_id, 1.067, max_cols, {'gen_type':'stored_genre', 'd1':cur_d3_d4_dict['d1'], \
                                                            'd2':cur_d3_d4_dict['d2'], 'd3':cur_d3_d4_dict['d3'], 'd4':cur_d3_d4_dict['d4']})
                    all_matrix_ouput.append(matrix_output)
            for cur_matrix_output in all_matrix_ouput:
                current_point['x'] = start_point['x']
                ip_rate_table = cur_matrix_output['ip_rate_table']
                sp_rate_table = cur_matrix_output['sp_rate_table']
                cur_height = len(ip_rate_table)
                '''adding value table'''
                export_data = {}
                export_data['header'] = ip_rate_table[0]
                export_data['body'] = ip_rate_table[1:]
                export_data['col_width'] = [20, 6, 6, 6, 6, 6]
                export_data['co_ordinate'] = [current_point['y'], current_point['x']]
                export_data['conditional_format_type'] = 'test_file_name'
                tab_wid = max(map(len, export_data['body']))
                export_data['merge_data'] = [(0, 0, 0, tab_wid), (1, 0, 1, tab_wid)]
                export_data['default_format'] = workbook.add_format()
                export_data['default_format'].set_border(1)
                '''we're merging the header'''
                gen_excel_export(export_data, xls_sheet)
                '''adding rate table'''
                if max_cols + 3 < 10:
                    current_point['x'] += 10
                else:
                    current_point['x'] += max_cols + 3
                export_data = {}
                export_data['header'] = sp_rate_table[0]
                export_data['body'] = sp_rate_table[1:]
                export_data['col_width'] = [20, 6, 6, 6, 6, 6]
                export_data['co_ordinate'] = [current_point['y'], current_point['x']]
                export_data['conditional_format_type'] = 'test_file_name'
                export_data['merge_data'] = [(0, 0, 0, tab_wid), (1, 0, 1, tab_wid)]
                export_data['default_format'] = workbook.add_format()
                export_data['default_format'].set_border(1)
                gen_excel_export(export_data, xls_sheet)
                '''change cursor to go below'''
                current_point['y'] += cur_height + 3
            i += 1
    workbook.close()
    output.seek(0)
    response_obj = HttpResponse()
    response_obj['Content-Disposition'] = 'attachment; filename='+ export_data['conditional_format_type'] +'.xlsx'
    response_obj['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response_obj['Cache-Control'] = 'no-cache'
    response_obj.write(output.read())
    return (response_obj)

