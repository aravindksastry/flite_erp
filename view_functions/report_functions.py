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
import ast
from decimal import *
import psycopg2, datetime
from db_links.database_connection import *
from nesting.nest_functions import *
from datetime import date, timedelta, datetime
from django.utils import timezone
import re
from django.db.models import Q
from time import strptime
from django.utils.datetime_safe import strftime


def unique_item_master_list(auto_pl_id):
    data = {}
    auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
    app_item_master = item_master.objects.filter(imported_item_code__startswith = auto_pl_obj.spec_code).order_by('imported_item_finish')
    red_master_list = app_item_master
    for cur_item_master in app_item_master:
        collate_inf_bom(cur_item_master.id)
        '''bom_stat = bom_check([[cur_item_master.id, 1],])
        if bom_stat == False:
            infinite_update([(cur_item_master.imported_item_code, cur_item_master.imported_item_finish, 1)], True, {'auto_update':True})
            cur_item_master = get_object_or_404(item_master, id = cur_item_master.id)'''
        cur_item_master = get_object_or_404(item_master, id = cur_item_master.id)
        similar_items = red_master_list.filter(imported_item_code = cur_item_master.imported_item_code)
        if len(similar_items) > 1:
            red_master_list = red_master_list.exclude(~Q(id = cur_item_master.id) & \
                                                  Q(imported_item_code = cur_item_master.imported_item_code))
    red_master_list = red_master_list.order_by('imported_item_code')
    data['master_list'] = red_master_list
    return(data)

def process_value_sum(item_master_id):
    '''This function sums up all input values of BOM items belonging to different processes separately'''
    data = {}
    process_value_dict = {}
    purchase_val = 0
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    tot_bom = collate_inf_bom(item_master_id)
    tot_bom.append([item_master_obj.id, 1])
    for cur_bom_item_set in tot_bom:
        cur_bom_qty = float(cur_bom_item_set[1])
        cur_bom_obj = get_object_or_404(item_master, id = cur_bom_item_set[0])
        auto_pl_obj = get_object_or_404(auto_price_list, spec_code = cur_bom_obj.imported_item_code[:21])
        new_bom = ast.literal_eval(cur_bom_obj.bom)
        if len(new_bom) > 0:
            if not auto_pl_obj.process.id in process_value_dict:
                process_value_dict[auto_pl_obj.process.id] = 0
            process_value_dict[auto_pl_obj.process.id] += float(cur_bom_obj.input_factor) * cur_bom_qty
        else:
            purchase_val += float(cur_bom_obj.input_factor) * cur_bom_qty
    data['process_value_dict'] = process_value_dict
    data['purchase_value'] = purchase_val
    return(data)

def process_wise_price_report(result_list):
    '''result_list = item_master object list'''
    data = {}
    process_wise_data = []
    proc_type_list = []
    tab_header = [[{'val':'Sl no.', 'col_span':1, 'row_span':1}, {'val':'Size', 'col_span':1, 'row_span':1}]]
    tab_body = []
    if len(result_list) > 0:
        sample_item = result_list[0]
        proc_val_data = process_value_sum(sample_item.id)
        auto_pl_obj = get_object_or_404(auto_price_list, spec_code = sample_item.imported_item_code[:21])
        tab_header[0].append({'val':'Purchase', 'col_span':1, 'row_span':1})
        for cur_proc_id, cur_proc_val in proc_val_data['process_value_dict'].items():
            '''take a sample BOM of the first item & list down all process types that appear - 
            for accessing objects in template'''
            cur_proc_obj = get_object_or_404(process_type, id = cur_proc_id)
            proc_type_list.append({'id':cur_proc_id, 'obj':cur_proc_obj})
            tab_header[0].append({'val':cur_proc_obj.name, 'col_span':1, 'row_span':1})
        tab_header[0] += [{'val':'Input Rate', 'col_span':1, 'row_span':1}, {'val':'Margin', 'col_span':1, 'row_span':1}, \
                          {'val':'Sale Rate', 'col_span':1, 'row_span':1}]
        i = 0
        for cur_item in result_list:
            i += 1
            proc_val_data = process_value_sum(cur_item.id)
            proc_val_dict = proc_val_data['process_value_dict']
            tot_purchase = proc_val_data['purchase_value']
            split_name = cur_item.name.split('|')
            size = cur_item.name
            if len(split_name) == 3:
                size = split_name[1]
            input_rate = float(cur_item.bom_input_price)
            db_margin = float(auto_pl_obj.sale_margin)
            sale_rate = input_rate * db_margin
            tab_row = [{'val':i, 'col_span':1}, {'val':size, 'col_span':1, 'row_span':1}, {'val':tot_purchase, 'col_span':1, 'row_span':1}]
            for cur_proc_type_dict in proc_type_list:
                cur_proc_val = proc_val_dict[cur_proc_type_dict['id']]
                tab_row.append({'val':cur_proc_val, 'col_span':1, 'row_span':1})
            tab_row += [{'val':input_rate, 'col_span':1, 'row_span':1}, {'val':db_margin, 'col_span':1, 'row_span':1}, \
                        {'val':sale_rate, 'col_span':1, 'row_span':1}]
            tab_body.append(tab_row)
            '''input_rate, db_margin, sale_rate'''
    data['tab_header'] = tab_header
    data['tab_body'] = tab_body
    return(data)

def all_item_price_report(result_list):
    '''result_list = item_master object list'''
    data = {}
    process_wise_data = []
    proc_type_list = []
    tab_header = [({'val':'Sl no.', 'col_span':1}, {'val':'Size', 'col_span':1, 'row_span':1}, \
                   {'val':'Input Price', 'col_span':1, 'row_span':1}, {'val':'Margin', 'col_span':1, 'row_span':1}, \
                   {'val':'Sale Price', 'col_span':1, 'row_span':1}, {'val':'price_last_update', 'col_span':1, 'row_span':1})]
    tab_body = []
    if len(result_list) > 0:
        sample_item = result_list[0]
        auto_pl_obj = get_object_or_404(auto_price_list, spec_code = sample_item.imported_item_code[:21])
        i = 0
        for cur_item in result_list:
            i += 1
            proc_val_data = process_value_sum(cur_item.id)
            split_name = cur_item.name.split('|')
            size = cur_item.name
            if len(split_name) == 3:
                size = split_name[1]
            input_rate = float(cur_item.bom_input_price)
            db_margin = float(auto_pl_obj.sale_margin)
            sale_rate = input_rate * db_margin
            tab_body.append([{'val':i, 'col_span':1, 'row_span':1}, {'val':size, 'col_span':1, 'row_span':1}, \
                             {'val':input_rate, 'col_span':1, 'row_span':1}, {'val':db_margin, 'col_span':1, 'row_span':1}, \
                             {'val':sale_rate, 'col_span':1, 'row_span':1}, {'val':cur_item.price_last_updated, 'col_span':1, 'row_span':1}])
    data['tab_header'] = tab_header
    data['tab_body'] = tab_body
    return(data)

def price_history_data(result_list):
    data = {}
    tab_header = [[{'val':'Sl no.', 'col_span':1, 'row_span':2}, {'val':'Specification', 'col_span':1, 'row_span':2}, \
                   {'val':'Size', 'col_span':1, 'row_span':2}, {'val':'finish', 'col_span':1, 'row_span':2}], []]
    i = 0
    while i < 3:
        main_str = 'last_updated - ' + str(i)
        tab_header[0].append({'val':main_str, 'col_span':4, 'row_span':1})
        tab_header[1] += [{'val':'Input', 'col_span':1, 'row_span':1}, {'val':'Margin', 'col_span':1, 'row_span':1}, \
                             {'val':'Sale Price', 'col_span':1, 'row_span':1}, {'val':'Updated', 'col_span':1, 'row_span':1}]
        i += 1
    j = 0
    tab_body = []
    for cur_item_obj in result_list:
        j += 1
        new_row = []
        split_name = cur_item_obj.name.split('|')
        size = cur_item_obj.name
        if len(split_name) == 3:
            size = split_name[1]
            spec = split_name[0]
            fin = split_name[2]
        new_row = [{'val':j, 'col_span':1, 'row_span':1}, {'val':spec, 'col_span':1, 'row_span':1}, \
                   {'val':size, 'col_span':1, 'row_span':1}, {'val':fin, 'col_span':1, 'row_span':1}]
        cur_bom_sp_his = ast.literal_eval(cur_item_obj.bom_sp_his)
        history_index = len(cur_bom_sp_his) - 1
        i = 0
        while i < 3:
            if i == 0:
                cur_ip = float(cur_item_obj.bom_input_price)
                cur_sp = float(cur_item_obj.bom_sale_price)
                if cur_sp == 0 or cur_ip == 0:
                    cur_mar = 1
                else:
                    cur_mar = float(round(cur_sp / cur_ip, 2))
                cur_dt = cur_item_obj.price_last_updated
                new_row += [{'val':cur_ip, 'col_span':1, 'row_span':1}, \
                            {'val':cur_mar, 'col_span':1, 'row_span':1}, \
                            {'val':cur_sp, 'col_span':1, 'row_span':1}, \
                            {'val':cur_dt, 'col_span':1, 'row_span':1}]
            else:
                if history_index >= 0:
                    spec_his_data = cur_bom_sp_his[history_index]
                    cur_ip = spec_his_data['bom_input_rate']
                    cur_sp = spec_his_data['bom_sale_price']
                    if cur_sp == 0 or cur_ip == 0:
                        cur_mar = 1
                    else:
                        cur_mar = float(round(cur_sp / cur_ip, 2))
                    #datetime.datetime.strptime(new_date_format, '%b. %d, %Y')
                    cur_dt = spec_his_data['dt'].split('.')[0]
                    if cur_dt == 'None':
                        cur_dt = '-'
                    else:
                        cur_dt = datetime.strptime(cur_dt, '%Y-%m-%d %H:%M:%S').strftime('%b. %d, %Y %H:%M %p')
                    new_row += [{'val':cur_ip, 'col_span':1, 'row_span':1}, {'val':cur_mar, 'col_span':1, 'row_span':1}, \
                                     {'val':cur_sp, 'col_span':1, 'row_span':1}, {'val':cur_dt, 'col_span':1, 'row_span':1}]
                else:
                    new_row += [{'val':'-', 'col_span':1, 'row_span':1}, {'val':'-', 'col_span':1, 'row_span':1}, \
                                {'val':'-', 'col_span':1, 'row_span':1}, {'val':'-', 'col_span':1, 'row_span':1}]
                history_index -= 1
            i += 1
        tab_body.append(new_row)
    data['tab_header'] = tab_header
    data['tab_body'] = tab_body
    return(data)

def quotation_report(param_dict):
    data = {}
    icategory = ('WKS', 'FST', 'ACC', 'Storage', 'Ped')
    item_type_category = {1:icategory[0], 2:icategory[0], 3:icategory[1], 4:icategory[1], \
                          5:icategory[1], 6:icategory[1], 7:icategory[2], 8:icategory[3], \
                          9:icategory[1], 10:icategory[4], 11:icategory[1], 12:icategory[1], \
                          13:icategory[3], 14:icategory[1]}
    """each item types from 1-14 is categorized into icategory - for displaying in the report"""
    tab_header = [[{'val':'Sl no.', 'col_span':1, 'row_span':1}, \
                   {'val':'Project Name', 'col_span':1, 'row_span':1},\
                   {'val':'Location', 'col_span':1, 'row_span':1},\
                   {'val':'Revision', 'col_span':1, 'row_span':1},\
                   {'val':'Revision Remarks', 'col_span':1, 'row_span':1},\
                   {'val':'Quotation Date', 'col_span':1, 'row_span':1},\
                   {'val':'Quote Name', 'col_span':1, 'row_span':1},
                   {'val':'Designer', 'col_span':1, 'row_span':1},
                   {'val':'Sales Mgr', 'col_span':1, 'row_span':1},
                   {'val':'Quote Value (AIP)', 'col_span':1, 'row_span':1},]]
    for cur_icat in icategory:
        tab_header[0].append({'val':cur_icat, 'col_span':1, 'row_span':1})
    tab_body = []
    start_date = param_dict['start_date']
    end_date = param_dict['end_date']
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                          host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute("""select * from quotation where date>'%s' and date<'%s' and mod_price='1' order by date""" % \
                   (start_date, end_date))
    quotation_total = cursor.fetchall()
    sl_no = 1
    for cur_quote in quotation_total:
        item_type_det = {}
        quote_id = int(cur_quote[0])
        quote_name = cur_quote[1]
        quote_date = cur_quote[2]
        rev_count = int(cur_quote[3])
        project_id = int(cur_quote[4])
        site_city_id = int(cur_quote[4])
        cursor.execute("""select * from quote_pl where quote_id=%d""" % (quote_id,))
        app_quote_pl = cursor.fetchall()
        tot_basic_aip = 0
        for cur_quote_pl in app_quote_pl:
            cur_qpl_id = int(cur_quote_pl[0])
            cur_quote_spec = ast.literal_eval(cur_quote_pl[4].replace(":null", ":''"))
            if len(cur_quote_spec) < 8:
                continue
            cur_qpl_qty = float(cur_quote_spec['Quantity'])
            cur_qpl_tot_cost = float(cur_quote_pl[6])
            tot_basic_aip += cur_qpl_tot_cost
            item_id = int(cur_quote_pl[3])
            cursor.execute("""select * from item where id=%d""" % (item_id,))
            cur_item = cursor.fetchall()[0]
            cur_item_type_id = cur_item[2]
            cur_item_type_str = item_type_category[cur_item_type_id]
            if not cur_item_type_str in item_type_det:
                item_type_det[cur_item_type_str] = 0
            item_type_det[cur_item_type_str] += cur_qpl_qty
        cursor.execute("""select * from project where id=%d""" % (project_id,))
        project_row = cursor.fetchall()[0]
        project_name = project_row[1]
        site_city_id = int(project_row[7])
        design_mgr_id = int(project_row[24])
        sales_mgr_id = int(project_row[23])
        cursor.execute("""select name from city where id=%d""" % (site_city_id,))
        site_city_name = cursor.fetchall()[0][0]
        cursor.execute("""select name from db_user where id=%d""" % (design_mgr_id,))
        designer_name = cursor.fetchall()[0][0]
        cursor.execute("""select name from db_user where id=%d""" % (sales_mgr_id,))
        sales_mgr_name = cursor.fetchall()[0][0]
        new_row = [{'val':sl_no, 'col_span':1, 'row_span':1},
                   {'val':project_name, 'col_span':1, 'row_span':1},
                   {'val':site_city_name, 'col_span':1, 'row_span':1},
                   {'val':rev_count, 'col_span':1, 'row_span':1},
                   {'val':'', 'col_span':1, 'row_span':1},
                   {'val':quote_date, 'col_span':1, 'row_span':1},
                   {'val':quote_name, 'col_span':1, 'row_span':1},
                   {'val':designer_name, 'col_span':1, 'row_span':1},
                   {'val':sales_mgr_name, 'col_span':1, 'row_span':1},
                   {'val':tot_basic_aip, 'col_span':1, 'row_span':1}]
        for cur_icat in icategory:
            if cur_icat in item_type_det:
                new_row.append({'val':item_type_det[cur_icat], 'col_span':1, 'row_span':1})
            else:
                new_row.append({'val':0, 'col_span':1, 'row_span':1})
        tab_body.append(new_row)
        sl_no += 1
    cursor.close()
    db.close()
    data['tab_header'] = tab_header
    data['tab_body'] = tab_body
    return(data)

def pending_reports(param_dict):
    data = {}
    start_date = param_dict['start_date']
    end_date = param_dict['end_date']
    ttype_id = param_dict['ttype_ref_no']
    sl_no = 1
    tab_body = []
    tab_header = [[{'val':'Sl no.', 'col_span':1, 'row_span':1}, \
                   {'val':'Transaction Ref Id', 'col_span':1, 'row_span':1},\
                   {'val':'Transaction Ref Name', 'col_span':1, 'row_span':1},\
                   {'val':'Vendor Name', 'col_span':1, 'row_span':1},\
                   {'val':'Submited Date', 'col_span':1, 'row_span':1},\
                   {'val':'Ref Name', 'col_span':1, 'row_span':1},\
                   {'val':'Grand Total', 'col_span':1, 'row_span':1}]]
    tref_list = transaction_ref.objects.filter(created_date__gte = start_date, submit_date__lte = end_date, transaction_type_id = ttype_id, active = True)
    for cur_tref in tref_list:
        item_type_det = {}
        tref_id = cur_tref.id
        tref_name = cur_tref.name
        tref_submited_date = cur_tref.submit_date
        ref_name = cur_tref.ref_name
        ttype_data = ast.literal_eval(cur_tref.data)
        if ttype_id == 63 or ttype_id == 68:
            vendor_name = ttype_data['field_list']['vendor'][1]
        if ttype_id == 72:
            vendor_name = ttype_data['field_list']['work_center'][1]
        grand_total = ttype_data['grand_total']
        new_row = [{'val':sl_no, 'col_span':1, 'row_span':1}, \
                   {'val':tref_id, 'col_span':1, 'row_span':1},\
                   {'val':tref_name, 'col_span':1, 'row_span':1},\
                   {'val':vendor_name, 'col_span':1, 'row_span':1},\
                   {'val':tref_submited_date, 'col_span':1, 'row_span':1},\
                   {'val':ref_name, 'col_span':1, 'row_span':1},\
                   {'val':grand_total, 'col_span':1, 'row_span':1}]
        
        tab_body.append(new_row)
        sl_no += 1
    data['tab_header'] = tab_header
    data['tab_body'] = tab_body
    return(data)


def xls_price_matrix_data():
    dim_data = {}

    '''stored_data = {'auto_pl_id':[{d1:[1, 2, 3, 4...], d2:[12, 23, 12, 35,23 5], d3:[2354,11,531], d4:[32, 436, 1325]}, {}, {}]}'''
    '''linear table tope left hand - perform - PLB 25mm Left hand!!Linear!!perform'''
    dim_data[3599] = [{'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[450],'d3':450, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[525],'d3':525, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[600],'d3':600, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[675],'d3':675, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[700],'d3':700, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[750],'d3':750, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[900],'d3':900, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[1050],'d3':1050, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[1200],'d3':1200, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[1350],'d3':1350, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[1500],'d3':1500, 'd4':0},
                    {'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950], 'd2':[1650],'d3':1650, 'd4':0}]
    
    '''L Shaped Table top left hand perform - '''
    dim_data[3596] = [{'sheet':'table_top','d1':[1200, 1350, 1500, 1650, 1800, 1950,2100], 
                          'd2':[1200, 1350, 1500, 1650, 1800],'d3':600, 'd4':600}]
    
    '''PLB 25mm 120 degree table top perform'''
    dim_data[4639] = [{'sheet':'table_top','d1':[1050, 1200, 1350], 
                          'd2':[1050, 1200, 1350],'d3':600, 'd4':600}]
    
    '''PLB 25mm Meeting Table PLB 25mm'''
    dim_data[350] = [{'sheet':'table_top','d1':[1200, 1350, 1500, 1650, 1800, 1950,2100], 
                          'd2':[1200, 1350, 1500, 1650, 1800],'d3':0, 'd4':0}]
    
    '''PLB 25mm V Generator / D shaped Generator'''
    dim_data[5093] = [{'sheet':'table_top','d1':[1500, 1650, 1800, 1950, 2100, 2250], 
                          'd2':[600, 750, 900],'d3':0, 'd4':0}]
    
    '''PLB 25mm Left hand Cabin Linear Table profile Straight tip'''
    dim_data[167] = [{'sheet':'table_top','d1':[900, 1050, 1200, 1350, 1500, 1650, 1800, 1950, 2100], 
                          'd2':[450, 600, 750, 900], 'd3':0, 'd4':0}]
    
    ''''''

    '''Perform Collaborate (Beta) Type - Left Side Leg - Non Sharing Type ; 1 Beam line(with levelers)'''
    dim_data[2897] = [{'sheet':'desking_leg','d1':[430, 505, 580, 655, 575, 680, 730],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Collaborate (Beta) Type - Left Side Leg - Non Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[3112] = [{'sheet':'desking_leg','d1':[430, 505, 580, 655, 575, 680, 730],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Collaborate (Beta) Type - None Side Leg - Sharing 2 beam line'''
    dim_data[2899] = [{'sheet':'desking_leg','d1':[1030, 1180, 1330, 1380, 1480, 1630, 1780],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Collaborate (Beta) Type - None Side Leg - Sharing 4 beam line'''
    dim_data[3166] = [{'sheet':'desking_leg','d1':[1030, 1180, 1330, 1380, 1480, 1630, 1780],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Connect (Alpha) Type - Left Side Leg - Non Sharing Type ; 1 Beam line(with levelers)'''
    dim_data[2833] = [{'sheet':'desking_leg','d1':[275, 350, 425, 500, 525, 575],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Connect (Alpha) Type - Left Side Leg - Non Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[2834] = [{'sheet':'desking_leg','d1':[275, 350, 425, 500, 525, 575],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Connect (Alpha) Type - None Side Leg - Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[2829] = [{'sheet':'desking_leg','d1':[750, 900, 1050, 1100, 1200, 1350, 1500],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Connect (Alpha) Type - None Side Leg - Sharing Type ; 4 Beam Line(with levelers)'''
    dim_data[2828] = [{'sheet':'desking_leg','d1':[750, 900, 1050, 1100, 1200, 1350, 1500],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Cantilever 60x40 Leg Type - None Centre leg - Non Sharing Type ; 1 Beam line(with levelers)'''
    dim_data[2893] = [{'sheet':'desking_leg','d1':[300, 400, 425, 450, 475, 500, 550, 625],
                               'd2':[690], 'd3':690, 'd4':0}]
    '''Perform Cantilever 60x40 Leg Type - None Centre leg - Non Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[3114] = [{'sheet':'desking_leg','d1':[525, 550, 575, 600, 625, 650, 725, 730],
                               'd2':[690], 'd3':690, 'd4':0}]
    '''Perform Cantilever 60x40 Leg Type - None Centre leg - Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[2888] = [{'sheet':'desking_leg','d1':[750, 900, 1050, 1100, 1200, 1350, 1500],
                               'd2':[690], 'd3':690, 'd4':0}]
    '''Perform Cantilever 60x40 Leg Type - None Centre leg - Sharing Type ; 4 Beam Line(with levelers)'''
    dim_data[2888] = [{'sheet':'desking_leg','d1':[900, 1050, 1100, 1200, 1350, 1500],
                               'd2':[690], 'd3':690, 'd4':0}]
    '''Perform Colors Type - Left Side Leg - Non Sharing Type ; 1 Beam line(with levelers)'''
    dim_data[4326] = [{'sheet':'desking_leg','d1':[275, 350, 425, 500, 525, 575],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Colors Type - Left Side Leg - Non Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[4353] = [{'sheet':'desking_leg','d1':[275, 350, 425, 500, 525, 575],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Colors Type - None Side Leg - Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[4620] = [{'sheet':'desking_leg','d1':[750, 900, 1050, 1100, 1200, 1350, 1500],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Colors Type - None Side Leg - Sharing Type ; 4 Beam Line(with levelers)'''
    dim_data[4621] = [{'sheet':'desking_leg','d1':[750, 900, 1050, 1100, 1200, 1350, 1500],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Plus Type - Left Side Leg - Non Sharing Type ; 1 Beam line(with levelers)'''
    dim_data[4463] = [{'sheet':'desking_leg','d1':[430, 505, 580, 655, 575, 680, 730],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Plus Type - Left Side Leg - Non Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[4550] = [{'sheet':'desking_leg','d1':[430, 505, 580, 655, 575, 680, 730],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Plus Type - None Side Leg - Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[4467] = [{'sheet':'desking_leg','d1':[1030, 1180, 1330, 1380, 1480, 1630, 1780],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Plus Type - None Side Leg - Sharing Type ; 4 Beam Line(with levelers)'''
    dim_data[4528] = [{'sheet':'desking_leg','d1':[1030, 1180, 1330, 1380, 1480, 1630, 1780],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Synergy Type - Left Side Leg - Non Sharing Type ; 1 Beam line(with levelers)'''
    dim_data[5002] = [{'sheet':'desking_leg','d1':[275, 350, 425, 500, 525, 575],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Synergy Type - Left Side Leg - Non Sharing Type ; 2 Beam line(with levelers)'''
    dim_data[5014] = [{'sheet':'desking_leg','d1':[275, 350, 425, 500, 525, 575],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Synergy Type - None Side Leg - Sharing Type ; 2 Beam Line(with levelers)'''
    dim_data[5015] = [{'sheet':'desking_leg','d1':[750, 900, 1050, 1100, 1200, 1350, 1500],
                               'd2':[710], 'd3':710, 'd4':0}]
    '''Perform Synergy Type - None Side Leg - Sharing Type ; 4 Beam Line(with levelers)'''
    dim_data[5015] = [{'sheet':'desking_leg','d1':[750, 900, 1050, 1100, 1200, 1350, 1500],
                               'd2':[710], 'd3':710, 'd4':0}]
    
    ''''''

    '''Perform Raceway Facia:Laminate/Laminate - Sharing Cutout'''
    dim_data[143] = [{'sheet':'desking_raceway','d1':[890, 935, 980, 1040, 1085, 1130, 1190, 1235, 1280, 1340, 1385, 1430],
                                 'd2':[0], 'd3':0, 'd4':0}]
    dim_data[2745] = [{'sheet':'desking_raceway','d1':[890, 935, 980, 1040, 1085, 1130, 1190, 1235, 1280, 1340, 1385, 1430],
                                 'd2':[0], 'd3':0, 'd4':0}]
    dim_data[252] = [{'sheet':'desking_raceway','d1':[890, 935, 980, 1040, 1085, 1130, 1190, 1235, 1280, 1340, 1385, 1430],
                                 'd2':[0], 'd3':0, 'd4':0}]
    dim_data[2721] = [{'sheet':'desking_raceway','d1':[890, 935, 980, 1040, 1085, 1130, 1190, 1235, 1280, 1340, 1385, 1430],
                                 'd2':[0], 'd3':0, 'd4':0}]
    

    '''12mm Screen - Fabric Magnetic (on Al Extrusion)'''
    dim_data[2824] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':12, 'd4':50, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''12mm Screen - Fabric Magnetic (on Studs)'''
    dim_data[140] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':12, 'd4':50, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''12mm Screen - Fabric (on Al Extrusion)'''
    dim_data[3217] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':12, 'd4':50, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''12mm Screen - Fabric (on Studs)'''
    dim_data[389] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':12, 'd4':50, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''18mm Screen (Al Trims) - Fabric Magnetic (on Studs)'''
    dim_data[4186] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':18, 'd4':0, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''18mm Screen (Al Trims) - Fabric Magnetic strip With Acc Rail (on Studs)'''
    dim_data[4417] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':18, 'd4':0, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''18mm Screen (Al Trims) - Fabric Magnetic strip with Al beeding (on Studs)'''
    dim_data[4589] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':18, 'd4':0, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''18mm Screen (Al Trims) - Fabric (on Studs)'''
    dim_data[4218] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':18, 'd4':0, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''18mm Screen - Fabric Magnetic (on Studs)'''
    dim_data[2879] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':18, 'd4':50, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''18mm Screen - Fabric (on Studs)'''
    dim_data[2878] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':18, 'd4':50, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''8mm screen - Coloured glass (on Al Extrusion)'''
    dim_data[206] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':8, 'd4':25, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''8mm screen - Coloured glass (on Studs)'''
    dim_data[218] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':8, 'd4':25, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''8mm screen - Glass Marker (on Studs)'''
    dim_data[2238] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':8, 'd4':25, 
                          'd2':[450, 750, 1050, 1200, 1350]}]
    '''Al Screen Assy'''
    dim_data[4599] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':0, 'd4':0, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''Neo - 33 Screen (None; 1 Middle C)'''
    dim_data[197] = [{'sheet':'screen','d1':[300, 350, 400, 450], 'd3':0, 'd4':0, 
                          'd2':[450, 525, 600, 675, 750, 900, 1050, 1200, 1350, 1500]}]
    '''6mm Screen - Acrylic (on Detachable studs)'''
    dim_data[5039] = [{'sheet':'screen','d1':[250, 300, 350, 400], 'd3':0, 'd4':0, 
                          'd2':[450, 525, 600, 675, 750, 900]}]
    '''Gable end - 18 mm No Cutout - Straight Profile'''
    gable_end_data = {}
    dim_data[87] = [{'sheet':'gable_end','d1':[710], 'd3':0, 'd4':0, 
                          'd2':[300, 325, 350, 375, 400, 425, 450, 475, 500, 525, 550, 575, 600, 625, 650 ,675, 700, 725, 750]}]
    dim_data[115] = [{'sheet':'gable_end','d1':[710], 'd3':0, 'd4':0, 
                          'd2':[300, 325, 350, 375, 400, 425, 450, 475, 500, 525, 550, 575, 600, 625, 650 ,675, 700, 725, 750]}]

    '''PLT - 18mm Rectangular Modesty Panel'''
    dim_data[4645] = [{'sheet':'modesty_panel','d1':[435, 450, 500], 'd3':0, 'd4':0, 
                                'd2':[600, 700, 850, 1150, 1200, 1300, 1450, 1600]}]
    '''Sqr Embossed Metal Rectangular Modesty Panel'''
    dim_data[363] = [{'sheet':'modesty_panel','d1':[435, 450, 500], 'd3':0, 'd4':0, 
                                'd2':[600, 700, 850, 1150, 1200, 1300, 1450, 1600]}]
    '''PLT - 12mm Rectangular Modesty Panel'''
    dim_data[4691] = [{'sheet':'modesty_panel','d1':[435, 450, 500], 'd3':0, 'd4':0, 
                                'd2':[320, 420, 470, 545, 570, 620, 823, 898, 923, 920, 973, 1070, 1170, 1220, 1370, 1520]}]
    
    '''Plain Metal Rectangular Modesty Panel'''
    dim_data[4653] = [{'sheet':'modesty_panel','d1':[435, 450, 500], 'd3':0, 'd4':0, 
                                'd2':[320, 420, 470, 545, 570, 620, 823, 898, 923, 920, 973, 1070, 1170, 1220, 1370, 1520]}]
    

    '''Neo - 33 Frame (1 face sloting; 1 Middle C)'''
    dim_data[319] = [{'sheet':'frame_neo_30','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    '''Neo - 33 Frame (2 face sloting; 1 Middle C)'''
    dim_data[557] = [{'sheet':'frame_neo_30','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    
    '''Frame Neo 50'''
    '''Neo - 50 Frame (1 face sloting; 1 Middle C)'''
    dim_data[68] = [{'sheet':'frame_neo_50','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    '''Neo - 50 Frame (1 face sloting; 2 Middle C ATT)'''
    dim_data[69] = [{'sheet':'frame_neo_50','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    '''Neo - 50 Frame (1 face sloting; 2 Middle C BTT)'''
    dim_data[238] = [{'sheet':'frame_neo_50','d1':[1050, 1200, 1350, 1500, 1800], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    '''Neo - 50 Frame (2 face slotting; 1 Middle C)'''
    dim_data[70] = [{'sheet':'frame_neo_50','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    '''Neo - 50 frame_neo_50 (2 face slotting; 2 Middle C ATT)'''
    dim_data[71] = [{'sheet':'frame_neo_50','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    '''Neo - 50 frame_neo_50 (2 face slotting; 2 Middle C BTT)'''
    dim_data[239] = [{'sheet':'frame_neo_50','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    '''Neo - 50 frame_neo_50 with Bottom Rib (1 face sloting; 1 Middle C)'''
    dim_data[2215] = [{'sheet':'frame_neo_50','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    '''Neo - 50 frame_neo_50 with Bottom Rib (1 face sloting; 2 Middle C BTT)'''
    dim_data[970] = [{'sheet':'frame_neo_50','d1':[1050, 1200], 'd3':0, 'd4':0, 
                        'd2':[1050, 1200, 1350, 1500]}]
    '''Neo - 50 frame_neo_50 with Bottom Rib (2 face slotting; 1 Middle C)'''
    dim_data[2219] = [{'sheet':'frame_neo_50','d1':[1050, 1200], 'd3':0, 'd4':0, 
                        'd2':[1050, 1200, 1350, 1500]}]
    '''Neo - 50 frame_neo_50 with Bottom Rib (2 face slotting; 2 Middle C BTT)'''
    dim_data[1433] = [{'sheet':'frame_neo_50','d1':[1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[1050, 1200, 1350, 1500]}]
    
    
    '''Frame Neo 70'''
    '''Neo - 70 Frame (1 face sloting; 1 Middle C)'''
    dim_data[5024] = [{'sheet':'frame_neo_70','d1':[1050, 1200], 'd3':0, 'd4':0, 
                        'd2':[1050, 1200, 1350, 1500]}]
    '''Neo - 70 Frame (1 face sloting; 2 Middle C ATT)'''
    dim_data[533] = [{'sheet':'frame_neo_70','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600,675, 750, 900, 1200]}]
    '''Neo - 70 Frame (1 face sloting; 2 Middle C BTT)'''
    dim_data[538] = [{'sheet':'frame_neo_70','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600,675, 750, 900, 1200]}]
    '''Neo - 70 Frame (2 face slotting; 1 Middle C)'''
    dim_data[534] = [{'sheet':'frame_neo_70','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600,675, 750, 900, 1200]}]
    '''Neo - 70 Frame (2 face slotting; 2 Middle C ATT)'''
    dim_data[536] = [{'sheet':'frame_neo_70','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 900, 1200]}]
    '''Neo - 70 Frame (2 face slotting; 2 Middle C BTT)'''
    dim_data[537] = [{'sheet':'frame_neo_70','d1':[900, 1050, 1200, 1350], 'd3':0, 'd4':0, 
                        'd2':[600, 750, 900, 1050, 1200]}]
    
    
    '''Acrylic Tile (6 mm) - STD'''
    dim_data[578] = [{'sheet':'tiles','d1':[150, 300, 450, 600], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Clear Glass Tile (6 mm) - STD '''
    dim_data[415] = [{'sheet':'tiles','d1':[150, 300, 450, 600], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Glass With Colour Vinyl Tile (6 mm) - STD'''
    dim_data[600] = [{'sheet':'tiles','d1':[300, 450, 600], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Fabric Magnetic Tile (6 mm) - STD'''
    dim_data[84] = [{'sheet':'tiles','d1':[300, 450, 600], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Fabric Tile (6 mm) - STD'''
    dim_data[83] = [{'sheet':'tiles','d1':[300, 450, 600], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Glass With Frosty Vinyl Tile (6 mm) - STD'''
    dim_data[271] = [{'sheet':'tiles','d1':[300, 450, 600], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Glass Marker Tile (6 mm) - STD'''
    dim_data[91] = [{'sheet':'tiles','d1':[300, 350, 400, 450, 570, 600, 750], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Laminate Graph Marker Tile (6 mm) - STD'''
    dim_data[2207] = [{'sheet':'tiles','d1':[300, 350, 400, 450, 570, 600, 750], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Laminate Tile (6 mm) - STD'''
    dim_data[85] = [{'sheet':'tiles','d1':[300, 350, 400, 450, 570, 600, 750], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    
    '''Soft Board Tile (6 mm) - STD'''
    dim_data[631] = [{'sheet':'tiles','d1':[300, 350, 400, 450, 570, 600, 750], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Toughened Clear Glass Tile (6 mm) - STD'''
    dim_data[599] = [{'sheet':'tiles','d1':[300, 350, 400, 450, 570, 600, 750], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    '''Poly carbonate Tile (6 mm) - STD'''
    dim_data[618] = [{'sheet':'tiles','d1':[300, 350, 400, 450, 570, 600, 750], 'd3':0, 'd4':0, 
                        'd2':[450, 600, 750, 800, 900, 1050, 1200]}]
    
    '''Extra Items'''
    '''H Channel (Horizontal)'''
    dim_data[108] = [{'sheet':'extra_items','d1':[450, 600, 750, 900, 1050, 1200, 1350, 1500], 'd3':0, 'd4':0, 
                        'd2':[0]}]
    '''H Channel (Vertical)'''
    dim_data[195] = [{'sheet':'extra_items','d1':[150, 300, 450, 600, 750, 900, 1050], 'd3':0, 'd4':0, 
                        'd2':[0]}]
    '''Desking Beam Leg to lEG 40x20 Type 2'''
    dim_data[2900] = [{'sheet':'extra_items','d1':[580, 630, 730, 880, 930, 1030, 1180, 1180, 1330, 1480, 1630], 'd3':0, 'd4':0, 
                        'd2':[0]}]
    '''Desking Beam Leg to Beam 40x20 Type 2'''
    dim_data[2901] = [{'sheet':'extra_items','d1':[580, 630, 730, 880, 930, 1030, 1180, 1180, 1330, 1480, 1630], 'd3':0, 'd4':0, 
                        'd2':[0]}]

    return(dim_data)










