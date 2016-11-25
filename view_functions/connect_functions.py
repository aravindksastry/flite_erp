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
import ast, copy
from decimal import *
import psycopg2, datetime
from db_links.database_connection import *
from journal_mgmt.view_functions import *
from nesting.nest_functions import *
from datetime import date, timedelta
from django.utils import timezone
#import pymssql
#import pyodbc

def get_rmp_con(auto_price_list_id, supplier_id, type):
    pl_obj = get_object_or_404(auto_price_list, id = auto_price_list_id)
    rmp_obj_set = [pl_obj.p1, pl_obj.p2, pl_obj.p3, pl_obj.p4, pl_obj.p5, pl_obj.p6, pl_obj.p7, pl_obj.p8, pl_obj.p9, pl_obj.p10,\
                   pl_obj.p11, pl_obj.p12, pl_obj.p13, pl_obj.p14, pl_obj.p15, pl_obj.p16, pl_obj.p17, pl_obj.p18, pl_obj.p19, pl_obj.p20]
    con_obj_set = [pl_obj.k1, pl_obj.k2, pl_obj.k3, pl_obj.k4, pl_obj.k5, pl_obj.k6, pl_obj.k7, pl_obj.k8, pl_obj.k9, pl_obj.k10,\
                   pl_obj.k11, pl_obj.k12, pl_obj.k13, pl_obj.k14, pl_obj.k15, pl_obj.k16, pl_obj.k17, pl_obj.k18, pl_obj.k19, pl_obj.k20]
    if type == 'vendor':
        supplier = get_object_or_404(coa, id = supplier_id)
    elif type == 'work_center':
        supplier = get_object_or_404(work_center, id = supplier_id)
    rmp_dict = {}
    con_dict = {}
    i = 0
    while i <= 19:
        '''i+1 is used as the keys for rmp & constants must be from 1 to 20'''
        rmp_key = 'p' + str(i+1)
        con_key = 'k' + str(i+1)
        if rmp_obj_set[i].constant_value == True or type == 'sale':
            rmp_dict[rmp_key] = rmp_obj_set[i].rmp_sale_rate
        else:
            if type == 'vendor':
                cur_rmp = vendor_rmp_auto.objects.filter(rmp = rmp_obj_set[i], vendor = supplier)
            elif type == 'work_center':
                cur_rmp = work_center_rmp_auto.objects.filter(rmp = rmp_obj_set[i], work_center = supplier)
            if len(cur_rmp) == 0:
                rmp_dict[rmp_key] = 0
            else:
                rmp_dict[rmp_key] = cur_rmp[0].rate
        con_dict[con_key] = con_obj_set[i].constant_value
        i += 1
    return(rmp_dict, con_dict)


def update_batch_input_factor(auto_pl_id):
    auto_pl_obj = get_object_or_404(auto_price_list, id=auto_pl_id)
    rmp_ext = get_rmp_con(auto_pl_obj.id, 0, 'sale')
    rmp_dict = rmp_ext[0]
    con_dict = rmp_ext[1]
    all_item_master = item_master.objects.filter(imported_item_code__startswith = auto_pl_obj.spec_code)
    for item_master_obj in all_item_master:
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
        input_calc_eqn = dim_cost_port(pn, auto_pl_obj.input_rate_sale, rmp_dict, con_dict, auto_pl_obj.input_factor_calc_eqn, 1)
        sale_calc_eqn = dim_cost_port(pn, auto_pl_obj.input_rate_sale, rmp_dict, con_dict, auto_pl_obj.sale_price_calc_eqn, 1)
        input_val = eval(input_calc_eqn)
        sale_val = round(eval(sale_calc_eqn), 2)
        item_master_obj.input_factor = input_val
        item_master_obj.process_valuation_sale = sale_val
        item_master_obj.save()
    return()

def quote_import_array(quotation_id):
    '''imported_item = (flite_360 part code, flite_360 finish code)'''
    line_items = []
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    #db = psycopg2.connect(database = 'featherlite', user='admin1', password='admin123', host='ferp.cv5o0gucwvmh.us-west-2.rds.amazonaws.com', port='5432')
    cursor = db.cursor()
    cursor.execute('select * from quotation where id=%d' % int(quotation_id))
    quotation_obj = cursor.fetchall()[0]
    quotation_data = quotation_obj[5]
    '''quotation_data sample is as shown below 2680 is the layout_id
    
    items array given above is represented in the format given below: - example shown
    {'items':{'item_id':{'sl_no':'', 'name':'', 'description':{'key1':'val1', 'key2':'val2'...}, 'layout_id':'', 'cost':''}}}
    
    This is one line of quotation table returned
    [(2316,
    'QUOTATION ',
     datetime.date(2014, 9, 22),
     1,
     2588, 
    '{  "items":{
                "16591":{"sl":"01","n":"750W x 450D x 1200HT","tid":8,"d":{"Depth & Material":"450D - PLB Body & Top","Configuration":"Openable Shutter","Size":"1200 H x 750 W Top: 750 W x 450 D"},"2680":25,"c":5400,"r":null},
                "16592":{"sl":"02","n":"Storage 1200W x 450D x 750HT","tid":8,"d":{"Depth & Material":"450D - PLB Body & Top","Configuration":"Openable Shutter + (2D+1F)","Size":"750 H x 1200 W Top: 1200 W x 450 D"},"2680":1,"c":7200,"r":null},
                "16593":{"sl":"03","n":"repro 1200W x 600D x 750HT","tid":8,"d":{"Depth & Material":"600D - PLB Body & Top","Configuration":"Openable Shutter","Size":"750 H x 1200 W Top: 1200 W x 600 D"},"2680":1,"c":7650,"r":null},
                "16594":{"sl":"04","n":"Storage 1200W x 450D x 750HT","tid":8,"d":{"Depth & Material":"450D - PLB Body & Top","Configuration":"Sliding Shutter","Size":"750 H x 1200 W Top: 1200 W x 450 D"},"2680":1,"c":5850,"r":null},
                "16597":{"sl":"05","n":"1200Dia","tid":11,"d":{"Table":"PLB 25mm Circular table of size: 1200 mm ","Understructure":"Perform Triangular Legs - Tube in Tube","Wire Management":"Cable Access: Dummy Flipup Box - 300 Cable Entry: Vertical Wire Entry Cover"},"2680":1,"c":8587,"r":null},
                "16601":{"sl":"06","n":"900Dia","tid":11,"d":{"Table":"PLB 25mm Circular table of size: 900 mm ","Understructure":"Prong Legs","Wire Management":"Cable Access: 65 Dia Wiremanager Cap"},"2680":1,"c":5953,"r":null},
                "16604":{"sl":"07","n":"1050Dia","tid":11,"d":{"Table":"PLB 25mm Circular table of size: 1050 mm ","Understructure":"Gable Ends","Wire Management":"Cable Access: Dummy Flipup Box - 300 Cable Entry: Vertical Wire Entry Cover"},"2680":1,"c":7341,"r":null},
                "16605":{"sl":"08","n":"2400W x 1050D x 750H","tid":14,"d":{"Table":"PLB 25mm Rectangular table of Size: 2400 L x 1050 D ","Understructure":" Supports: Gable Ends Modesty Panel: Type: PLT - 18 450 mm Height","Wire Management":"Cable Access: Dummy Flipup Box - 450 Qty:2 nos. Cable Entry: Vertical Wire Entry Cover"},"2680":1,"c":15086,"r":null},
                "16606":{"sl":"09","n":"1500L X 900D X 750HT ","tid":14,"d":{"Table":"PLB 25mm Rectangular table of Size: 1500 L x 900 D ","Understructure":" Supports: Perform Leg - Step Down","Wire Management":"Cable Access: Dummy Flipup Box - 450 Qty:1 nos. "},"2680":1,"c":10009,"r":null}
                },
        "lyt":{"2680":"exercise brijesh layout"},
        "lvy":{"3":{"VAT":"14.50"},"2":{"Freight and Insurance":"5.00"},"1":{"Excise Duty":"12.36"}},
        "oc":[],
        "pt":[],
        "ot":[]
    }',
    '1')]
    
    
    ------- Quote PL parts ------
    {'Department':[['part_no', part_desc, part_size, part_fin, Q1, Q2, ...Qn, Qtot, Norms, Rate, Value]]}
    "{
    "A.Metal Department":
    [["023-01-00-011-011-001-0590-0500-0700-0000","Perform Straight 50x50 Type - Left Side Leg; With RW hole - Non Sharing Type ; 1 Beam line(with levelers)","590 W x 500 Hl x 700 Hr","0-0-0-0-0-0-0-0-0-0-0-0-0",1,1,"750.00",1492.5,1492.5],
    ["023-01-00-011-011-002-0590-0500-0700-0000","Perform Straight 50x50 Type - Right  Side Leg; With RW hole - Non Sharing Type ; 1 Beam line(with levelers)","590 W x 500 Hl x 700 Hr","0-0-0-0-0-0-0-0-0-0-0-0-0",1,1,"750.00",1492.5,1492.5],
    ["023-01-00-021-011-003-0450-0500-0700-0000","Perform Straight 50x50 Type - Centre leg; With RW hole - Non Sharing Type ; 1 Beam line(with levelers)","450 W x 500 Hl x 700 Hr","0-0-0-0-0-0-0-0-0-0-0-0-0",1,1,"750.00",1387.5,1387.5],
    ["024-01-00-000-000-000-1380-0000-0000-0000","Perform Beam Leg to Leg","1380 L","0-0-0-0-0-0-0-0-0-0-0-0-0",1,1,"500.00",690,690],
    ["024-01-00-000-000-000-1450-0000-0000-0000","Perform Beam Leg to Leg","1450 L","0-0-0-0-0-0-0-0-0-0-0-0-0",1,1,"500.00",725,725]],
    "B.Wood Department":
    [["025-01-00-001-001-001-1426-0000-0000-0000","250 Ht Perform Raceway Facia:Laminate\/Laminate - Left Cutout","1426 L","0-0-0-0-0-0-0-0-0-0-0-0-0",1,1,"1080.00",1540.08,1540.08],["025-01-00-001-001-001-1496-0000-0000-0000",
    "250 Ht Perform Raceway Facia:Laminate\/Laminate - Left Cutout","1496 L","0-0-0-0-0-0-0-0-0-0-0-0-0",1,1,"1080.00",1615.68,1615.68]],
    "item":{"perfrom legs":1}
    }"
    '''
    quotation_data = ast.literal_eval(str(quotation_data.replace(":null", ":''")))
    
    cursor.execute('select * from quote_pl where quote_id=%d' % int(quotation_id))
    quote_pls = cursor.fetchall()
    
    cursor.execute('select * from project where id=%d' % int(quotation_obj[4]))
    project_obj = cursor.fetchall()[0]
    
    cursor.execute('select * from layout where enquiry_id=%d' % project_obj[0])
    layouts = cursor.fetchall()
    
    '''102 is the unique for workstations/storages etc., - imported line items'''
    for cur_quote_pl in quote_pls:
        cur_quote_pl_id = cur_quote_pl[0]
        oc_item_str = str(10000000 + cur_quote_pl_id)[1:]
        cur_new_line_item_pn = str('102' + '-' + oc_item_str[:2] + '-' + (oc_item_str[:4])[2:] + '-' + oc_item_str[4:] + '-' + '000' + '-' + '000' + '-' + '0000' + '-' + '0000' + '-' + '0000' + '-' + '0000')
        cursor.execute('select * from item where id=%d' % cur_quote_pl[3])
        f360_item_obj = cursor.fetchall()[0]
        cursor.execute('select * from item_type where id=%d' % f360_item_obj[2])
        f360_item_type_obj = cursor.fetchall()[0]
        cur_new_line_item_det = {'description':str('Imported Line Item ' + f360_item_obj[1] + ' - ' + \
                                                   f360_item_type_obj[1] + str(cur_quote_pl_id)), 'qty':0, \
                                                   'f360_item_row':f360_item_obj, 'value':cur_quote_pl[6]}
        '''Any Additional Parameter needed in detail can be added in cur_new_line_item_det dictionary'''
        discount = 0
        if cur_quote_pl[7]:
            discount =  cur_quote_pl[7]
        cur_new_line_item_det['discount'] = discount
        #return({'layouts':layouts, 'test':abc})
        for cur_layout in layouts:
            cur_new_line_item_det['qty'] += int(quotation_data['items'][str(cur_quote_pl[3])][str(cur_layout[0])])
        #cur_new_line_item_desc = str('Imported Line Item ' + f360_item_obj[1] + ' - ' + str(cur_quote_pl_id))
        #cur_new_line_item = [cur_new_line_item_pn, cur_new_line_item_desc, []]
        cur_new_line_item = [cur_new_line_item_pn, cur_new_line_item_det, []]
        cur_quote_pl_parts = ast.literal_eval(str(cur_quote_pl[8]))
        region_count = 0
        for key in cur_quote_pl_parts['item']:
            region_count += cur_quote_pl_parts['item'][key]
        
        i = 0
        while i < region_count:
            cur_new_seg_item_pn = str('103' + '-' + oc_item_str[:2] + '-' + oc_item_str[:4][2:] + '-' + oc_item_str[4:] + '-' + str(1000+i+1)[1:] + '-' + '000' + '-' + '0000' + '-' + '0000' + '-' + '0000' + '-' + '0000')
            #return({'Cur New Line Item':cur_new_line_item})
            cur_new_seg_item_det = {'description':str('Imported Segment ' + cur_new_line_item[1]['description'] + ' - ' + str(i+1)), 'qty':0}
            #cur_new_seg_item_desc = str('Imported Segment ' + cur_new_line_item[1] + ' - ' + str(i+1))
            cur_new_seg_item = [cur_new_seg_item_pn, cur_new_seg_item_det, ['the usual bom']]
            cur_new_line_item[2].append(cur_new_seg_item)
            i += 1
        tpl = []
        #return(cur_quote_pl_parts)
        for cur_header, part_list in cur_quote_pl_parts.items():
            if cur_header != 'item':
                for cur_part in part_list:
                    cur_part_no = cur_part[0]
                    cur_part_fin = cur_part[3]
                    '''Initially fin code used to be in the format x-x-0-0-0-0-0-0-0-0-0-0-0 where 0 is the default value
                    later it was in the format x-x-543-543-543-543-543-543-543-543-543-543-543 where 543 is the default
                    now we make the format as x-x-1-1-1-1-1-1-1-1-1-1-1 where 1 is the default
                    the replacements are done to negate old formats of finish coming into the system due to stored up fininsh as string'''
                    cur_part_fin = cur_part_fin.replace("-543-", "-1-")
                    '''repeated purposefully as replacement is alternate initially'''
                    cur_part_fin = cur_part_fin.replace("-543-", "-1-")
                    cur_part_fin = cur_part_fin.replace("1-543", "1-1")
                    cur_part_fin = cur_part_fin.replace("-0-", "-1-")
                    '''repeated purposefully as replacement is alternate initially'''
                    cur_part_fin = cur_part_fin.replace("-0-", "-1-")
                    cur_part_fin = cur_part_fin.replace("-1-0", "-1-1")
                    '''Enhancement code'''
                    cur_part_qty = []
                    if (cur_part_fin == '-' or cur_part_fin == '' or cur_part_fin == '0-0-0-0-0-0-0-0-0-0-0-0-0'):
                        #cur_part_fin = '1-0-0-0-0-0-0-0-0-0-0-0-0'
                        cur_part_fin = '1-1-1-1-1-1-1-1-1-1-1-1-1'
                    elif (len(cur_part_fin.split('-')) > 9):
                        '''do nothing'''
                    else:
                        return({'error':'irregular_finish - please update quotation in www.featherlite360.com before importing into ERP'})
                    qty_start = 4
                    i = 0
                    while i < region_count:
                        '''Enhancement code'''
                        if cur_part[qty_start + i] == '':
                            app_qty = 0
                        else:
                            app_qty = cur_part[qty_start + i]
                        cur_part_qty.append(app_qty)
                        '''cur_part_qty = cur_part[qty_start + i] 
                        cur_new_line_item[2][i][2].append([cur_part_no, cur_part_fin, cur_part_qty])'''
                        i += 1
                    tpl.append((cur_part_no, cur_part_fin, cur_part_qty))
        line_items.append((cur_new_line_item, tpl))
    
    cursor.execute('select * from project where id=%d' % int(quotation_obj[4]))
    project_obj = cursor.fetchall()[0]
    
    cursor.close()
    db.close()
    '''line_items = [([cur_new_line_item_pn, {'description':str('Imported Line Item ' + f360_item_obj[1] + ' - ' + \
                   f360_item_type_obj[1] + str(cur_quote_pl_id)), 'qty':0, 'f360_item_row':f360_item_obj, \
                   'value':cur_quote_pl[6], 'discount':123, 'qty':123}, [cur_new_seg_item_pn, cur_new_seg_item_det, \
                    ['the usual bom']]], [(cur_part_no, cur_part_fin, cur_part_qty), (cur_part_no, cur_part_fin, cur_part_qty), ....])]'''
    return(line_items, quotation_obj, project_obj)

def dim_cost_port(pn, rate, rmp, kon, calc_eqn, qty):
    '''pn = {'n':, 's':, 'm':, 's1':, 's2':, 's3':, 'd1':, 'd2':, 'd3':, 'd4':}'''
    i = 0
    eval_str = ''
    if not calc_eqn:
        calc_eqn = '0'
    print('(pn, Rate, rmp, calc_eqn, qty) : (' + str(pn) + ', ' + str(rate) + ', ' + str(rmp) + ', ' + str(calc_eqn) + ', ' + str(qty))
    print('calc_eqn : ' + str(calc_eqn))
    while i < len(calc_eqn):
        replace_char = calc_eqn[i]
        if calc_eqn[i] == 'c' or calc_eqn[i] == 'C':
            replace_char = rate
        elif calc_eqn[i] == 'q' or calc_eqn[i] == 'Q':
            replace_char = qty
        elif calc_eqn[i] == 'd' or calc_eqn[i] == 'D':
            replace_char = int(pn['d'+calc_eqn[i+1]])
            replace_char = str(replace_char)
            i += 1
            
        elif calc_eqn[i] == 'p' or calc_eqn[i] == 'P':
            if i < (len(calc_eqn) - 2):
                try:
                    int(calc_eqn[i+2])
                except:
                    inc = 1
                else:
                    inc = 2
            else:
                inc = 1
            print(str(i) + ' inc : ' + str(inc))
            replace_char = Decimal(rmp['p'+calc_eqn[i+1:i+1+inc]])
            replace_char = str(replace_char)
            i += inc
        elif calc_eqn[i] == 'k' or calc_eqn[i] == 'K':
            if i < (len(calc_eqn) - 2):
                try:
                    int(calc_eqn[i+2])
                except:
                    inc = 1
                else:
                    inc = 2
            else:
                inc = 1
            replace_char = Decimal(kon['k'+calc_eqn[i+1:i+1+inc]])
            replace_char = str(replace_char)
            i += inc
        i += 1
        eval_str += str(replace_char)
    if len(eval_str) == 0:
        eval_str = '0'
    return(eval_str)


def delete_duplicate_item_master(imp_part_no, imp_fin_no):
    repeated_items = item_master.objects.filter(imported_item_code = imp_part_no, imported_item_finish = imp_fin_no)
    if len(repeated_items) > 1:
        message = []
        i = len(repeated_items)
        x = [repeated_items[0], i]
        while i > 1:
            repeated_items[i-1].delete()
            i -= 1
    return(message)

def param_break(part_number, fin_number):
    data = {}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    p_no_split = part_number.split('-')
    print('Part Number : ' + str(part_number))
    print('Part Number Split : ' + str(p_no_split))
    cursor.execute('select * from pg_unique where id=%d' % int(p_no_split[0]))
    unique_obj = cursor.fetchall()[0]
    
    size_format_split = unique_obj[11].split(',')
    size_format = size_format_split[0]
    desc_format_split = unique_obj[13].split(',')
    desc_format = desc_format_split[0]
    price_dep_arr = ()
    '''If price dependence array is mentioned only'''
    if unique_obj[14]:
        price_dep_arr = (unique_obj[14].split('/')[0]).split(',')
    
    pg = {}
    pg['s'] = unique_obj[2]
    pg['m'] = unique_obj[3]
    pg['s1'] = unique_obj[4]
    pg['s2'] = unique_obj[5]
    pg['s3'] = unique_obj[6]
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
    
    if len(fin_number.split('-')) > 9:
        fin_no_split = fin_number.split('-')
        fin_type_id = int(fin_no_split[0])
        if fin_type_id == 0:
            fin_type_id = 1
        cursor.execute('select manage from finish_type where id=%d' % fin_type_id)
        
        fin_format = cursor.fetchall()[0][0]
        fin_format = fin_format.split(',')[0]
    else:
        #fin_no_split = ('1','0','0','0','0','0','0','0','0','0','0','0','0')
        fin_no_split = ('1','1','1','1','1','1','1','1','1','1','1','1','1')
        fin_format = '-'
    
    pfin = {}
    pfin_bom = {}
    i = 1
    while i <= 12:
        '''Since the first space is meant for format specification, i value will start from 1'''
        fin_base_id = int(fin_no_split[i])
        if fin_base_id == 0:
            fin_base_id = int(1)
        cursor.execute('select name from finish_base where id=%d' % fin_base_id)
        fin_base_obj = cursor.fetchall()[0]
        pfin[str('f'+str(i))] = fin_base_obj[0]
        pfin_bom[str('f'+str(i))] = fin_base_id
        i += 1
    #return(pfin)
    
    cursor.close()
    db.close()
    
    data['pn'] = pn
    data['pg'] = pg
    data['price_dep_arr'] = price_dep_arr
    data['size_format'] = size_format
    data['desc_format'] = desc_format
    data['fin_no_split'] = fin_no_split
    data['unique_obj'] = unique_obj
    data['p_no_split'] = p_no_split
    data['size_format_split'] = size_format_split
    data['desc_format_split'] = desc_format_split
    data['pfin'] = pfin
    data['pfin_bom'] = pfin_bom
    data['fin_format'] = fin_format
    return(data)


def part_id_conversion(imported_list):
    '''imported_list = [(imported_part_no, imported_part_fin, qty), (imported_part_no, imported_part_fin, qty) ....]'''
    real_list = []
    '''This loop is to convert immediate bom & infinite_bom'''
    for cur_item in imported_list:
        print('Start Part ID Conversion - ' + cur_item[0] + cur_item[1])
        item_master_obj = get_object_or_404(item_master, imported_item_code = cur_item[0], imported_item_finish = cur_item[1])
        imp_bom = ast.literal_eval(str(item_master_obj.imported_bom))
        imp_inf_bom = ast.literal_eval(str(item_master_obj.imported_infinite_bom))
        new_bom = []
        if len(str(imp_bom)) > 6:
        #if not imp_bom == {} or imp_bom == []:
            print('BOM ID Conversion - ' + str(imp_bom))
            for cur_bom in imp_bom:
                bom_obj = item_master.objects.filter(imported_item_code = cur_bom[0], imported_item_finish = cur_bom[1])
                if len(bom_obj) > 1:
                    delete_duplicate_item_master(cur_bom[0], cur_bom[1])
                print('Start BOM Conversion - ' + str(cur_bom))
                bom_obj = item_master.objects.filter(imported_item_code = cur_bom[0], imported_item_finish = cur_bom[1])
                if not len(cur_bom[0].split('-')) == 10 or not len(cur_bom[0]) == 41 or not len(bom_obj) > 0:
                    auto_update_item_master(cur_bom[0], cur_bom[1], 1)
                else:
                    bom_obj = get_object_or_404(item_master, imported_item_code = cur_bom[0], imported_item_finish = cur_bom[1])
                    new_bom.append((bom_obj.id, cur_bom[2]))
        item_master_obj.bom = new_bom
        item_master_obj.save()
        item_master_obj = get_object_or_404(item_master, imported_item_code = cur_item[0], imported_item_finish = cur_item[1])
        new_bom = []
        if len(str(imp_inf_bom)) > 6:
        #if not imp_inf_bom == {} or imp_inf_bom == []:
            for cur_inf_bom in imp_inf_bom:
                bom_obj = item_master.objects.filter(imported_item_code = cur_inf_bom[0], imported_item_finish = cur_inf_bom[1])
                if len(bom_obj) > 1:
                    print(bom_obj)
                    '''del duplicate item_master function call'''
                bom_obj = item_master.objects.filter(imported_item_code = cur_bom[0], imported_item_finish = cur_bom[1])
                if len(cur_inf_bom[0].split('-')) == 10 and len(cur_inf_bom[0]) == 41 and len(bom_obj) > 0:
                    bom_obj = get_object_or_404(item_master, imported_item_code = cur_inf_bom[0], imported_item_finish = cur_inf_bom[1])
                    new_bom.append((bom_obj.id, cur_inf_bom[2]))
                else:
                    infinite_update([[item_master_obj.imported_item_code, item_master_obj.imported_item_finish, 1.0]], True, {'auto_update':True})
        item_master_obj.infinite_bom = new_bom
        item_master_obj.save()
        real_list.append((item_master_obj.id, cur_item[2]))
        '''real_list = [(pn_id, qty), (pn_id, qty)....]'''
        print('Item Master Infinite imported BOM : ' + str(item_master_obj.imported_infinite_bom))
        print('Item Master Infinite BOM : ' + str(item_master_obj.infinite_bom))
    return(real_list)

def description_gen(part_number):
    '''This function does not save or update anything in the database, instead only reads the relevant data to provide description, size, finish in human readable format
    BOM generation is also called from here'''
    data = {}
    #fin_number = '1-0-0-0-0-0-0-0-0-0-0-0-0'
    fin_number = '1-1-1-1-1-1-1-1-1-1-1-1-1'
    pbreak = param_break(part_number, fin_number)
    unique_obj = pbreak['unique_obj']
    desc_format = pbreak['desc_format']
    desc_format_split = pbreak['desc_format_split']
    pn = pbreak['pn']
    pg = pbreak['pg']
    
    #cursor = db.cursor()
    
    new_desc_str = ''
    replace_char = ''
    test_str = ''
    
    '''This code is to convert description format to description string'''
    replacements = 0
    unique_detail = (unique_obj[0], unique_obj[1])
    for cur_char in desc_format:
        db_crm_dict = crm_connect_data()
        db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    
        cursor = db.cursor()
        replace_char = cur_char
        
        if(cur_char == '?'):
            '''the string entered in the database has the first value for format & the rest as replacement pointers, hence +1 before replacing'''
            replacements += 1
            replace_key = desc_format_split[replacements]
            if(replace_key == 'n'):
                cursor.execute('select name from pg_unique where id=%s' % int(pn['n']))
                replace_char = cursor.fetchall()[0][0]
            else:
                if int(pn[replace_key]) == 0:
                    replace_char = '?'
                else:
                    cursor.execute('select name from part_lookup where group_id=%d and param=%d' %(int(pg[replace_key]), int(pn[replace_key])))
                    replace_char = cursor.fetchall()
                    if len(replace_char) == 0:
                        cursor.execute('select lookup_format from part_group where id=%d' % int(pg[replace_key]))
                        lookup_table = cursor.fetchall()[0][0]
                        try:
                            len(lookup_table)
                        except:
                            replace_char = '?!'
                        else:
                            cursor.execute('select * from %s where id=%d' % (lookup_table, int(pn[replace_key])))
                            replace_char_row = cursor.fetchall()
                            if len(replace_char_row) > 0:
                                replace_char = replace_char_row[0]
                                '''if record exists where id = given split spec code''' 
                                if len(replace_char) > 1:
                                    '''if lookup table has more than one column replace_char = name of the row'''
                                    replace_char = replace_char[1]
                                else:
                                    '''else id of the row - usually used in dimension representation'''
                                    replace_char = replace_char[0]
                            else:
                                '''if no record exists for matching split spec code'''
                                replace_char = '???'
                    else:
                        replace_char = replace_char[0][0]
            
            if replace_char == []:
                replace_char = '-err!-'
            elif replace_char == 'None' or replace_char == '':
                replace_char = ''
        new_desc_str += str(replace_char)
        cursor.close()   
        db.close()
    print('Test Exit -------- ' + str(new_desc_str))
    return(new_desc_str)
    
def size_gen(part_number):
    #fin_number = '1-0-0-0-0-0-0-0-0-0-0-0-0'
    fin_number = '1-1-1-1-1-1-1-1-1-1-1-1-1'
    pbreak = param_break(part_number, fin_number)
    size_format = pbreak['size_format']
    size_format_split = pbreak['size_format_split']
    pn = pbreak['pn']
    pg = pbreak['pg']
    replacements = 0
    new_size_str = ''
    for cur_char in size_format:
        replace_char = cur_char
        if cur_char == '?':
            '''the string entered in the database has the first value for format & the rest as replacement pointers, hence +1 before replacing'''
            replacements += 1
            replace_key = 'd' + str(size_format_split[replacements])
            try:
                int(pn[replace_key])
            except:
                return({'error':{'error_description':'Size Computation Error', 'replace_ret':pn[replace_key], 'size_str':size_format_split, 'rep_key':replace_key, 'part_no':pn}})
            else:
                '''do nothing'''
            replace_char = int(pn[replace_key])
        new_size_str += str(replace_char)
    return(new_size_str)

def finish_gen(part_number, fin_number):
    pbreak = param_break(part_number, fin_number)
    fin_format = pbreak['fin_format']
    pfin = pbreak['pfin']
    replacements = 0
    new_fin_str = ''
    for cur_char in fin_format:
        replace_char = cur_char
        if cur_char == '?':
            '''the string entered in the database has the first value for format & the rest as replacement pointers, hence +1 before replacing'''
            replacements += 1
            
            replace_key = 'f' + str(replacements)
            #if not (replace_key == 'f1' or replace_key == 'f2' or replace_key == 'f3' or replace_key == 'f4' or replace_key == 'f5'):
            #    return({'error':{'error_description':'Finish Computation Error','fin_format':fin_format, 'part_number':pn, 'replace_key':replace_key, 'test_str':fin_no_split[replacements]}})
            replace_char = pfin[replace_key]
        new_fin_str += str(replace_char)
    return(new_fin_str)

def get_fin_grain_direction(part_no, fin_no):
    split_fin = fin_no.split("-")
    split_part = part_no.split("-")
    grain_direction = 0
    if int(split_fin[1]) <= 1:
        '''If finish is not given'''
        if int(split_part[0]) == 202:
            '''If the given part is a board/sheet tare'''
            if int(split_part[1]) == 1 or int(split_part[1]) == 2:
                '''If board/sheet material is PLB25mm (sys=1) or PLT18mm (sys=2) consider graqin by default'''
                grain_direction = 1  
        elif int(split_part[0]) == 222:
            '''If the given part is a Fabic tare'''
            '''We do not have the condition for assuming default grain direction'''
    else:
        '''If finish is given ( > 1)'''
        db_crm_dict = crm_connect_data()
        db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
        cursor = db.cursor()
        cursor.execute('select * from finish_base where id=%d' % (int(split_fin[1])))
        finish_base_obj = cursor.fetchall()[0]
        if not finish_base_obj[5] == None:
            '''Check Horizontal Grain Direction'''
            if int(finish_base_obj[5]) == 1:
                grain_direction = 1
        if not finish_base_obj[6] == None:
            '''Check Vertical Grain Direction'''
            if int(finish_base_obj[6]) == 1:
                grain_direction = 1
        cursor.close()
        db.close()
    return(grain_direction)

def get_type_grain_direction(part_no):
    grain_det = {}
    grain_direction = 0
    split_part = part_no.split("-")
    config = 'any'
    if int(split_part[0]) == 202:
        '''2 - PLT18mm - featherlite wants this item to be nested with grain direction - D1-D1 & D2-D2
        12 - Poly Carboate 6mm - featherlite wants this item to be nested with grain direction - D1-D2 & D2-D1
        19 - PLT25mm - featherlite wants this item to be nested with grain direction - D1-D1 & D2-D2
        '''
        grain_consideration = {2:2,12:1,19:2}
        if int(split_part[1]) in grain_consideration:
            grain_direction = grain_consideration[int(split_part[1])]
    grain_det = {'grain_direction':grain_direction}
    return(grain_det)

def get_part_lookup_opt(unique_id):
    data = {}
    data['param_order'] = ['system', 'material', 's1', 's2', 's3']
    data['param_detail'] = {'system':{'col_name':'ptr_system', 'opt':[], 'disp_name':'Sys', 'pl_col_name':'system_id'}, 
                            'material':{'col_name':'ptr_material', 'opt':[], 'disp_name':'Mat', 'pl_col_name':'material_id'},
                            's1':{'col_name':'ptr_s1', 'opt':[], 'disp_name':'S1', 'pl_col_name':'s1'},
                            's2':{'col_name':'ptr_s2', 'opt':[], 'disp_name':'S2', 'pl_col_name':'s2'},
                            's3':{'col_name':'ptr_s3', 'opt':[], 'disp_name':'S3', 'pl_col_name':'s3'}}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("select * from pg_unique where id=%d" % (unique_id,))
    unique_dict = cursor.fetchall()[0]
    for cur_param, cur_param_dict in data['param_detail'].items():
        cur_dict = copy.deepcopy(cur_param_dict)
        cur_col_name = cur_dict['col_name']
        cur_group_id = int(unique_dict[cur_col_name])
        cursor.execute("select * from part_group where id=%d" % (cur_group_id,)) 
        group_dict = cursor.fetchall()[0]
        lookup_table = 'part_lookup'
        if group_dict['lookup_format'] == None:
            cursor.execute("select * from part_lookup where group_id=%d" % (cur_group_id,))
        else:
            lookup_table = group_dict['lookup_format']
            cursor.execute("select * from %s" % (lookup_table,))
        app_lookup = cursor.fetchall()
        for cur_lookup in app_lookup:
            if lookup_table == 'part_lookup':
                cur_lookup_val = cur_lookup['param']
                cur_lookup_name = cur_lookup['name']
            else:
                cur_lookup_val = cur_lookup['id']
                if 'name' in cur_lookup:
                    cur_lookup_name = cur_lookup['name']
                else:
                    cur_lookup_name = cur_lookup_val
            cur_dict['opt'].append({'val':cur_lookup_val, 'name':cur_lookup_name})
        data['param_detail'][cur_param] = cur_dict
    cursor.close()
    db.close()
    return(data)

def clone_price_list_360(new_spec_code):
    data = {}
    master_part = item_master.objects.filter(imported_item_code = new_spec_code[0], imported_item_finish = new_spec_code[1])
    if not master_part:
        master_part = item_master(imported_item_code = new_spec_code[0], imported_item_finish = new_spec_code[1])
        master_part.created_date = timezone.now()
        print('Clone pl feed - ' + str(new_spec_code))
        print('Part description Feed - ' + str(new_spec_code))
        #part_details = part_description(new_spec_code + '-0000-0000-0000-0000', '1-0-0-0-0-0-0-0-0-0-0-0-0', 1.0)
        part_details = part_description(new_spec_code + '-0000-0000-0000-0000', '1-1-1-1-1-1-1-1-1-1-1-1-1', 1.0)
        availability = False
    else:
        master_part = master_part[0]
        part_details = part_description(master_part.imported_item_code, master_part.imported_item_finish, 1.0)
        availability = True
    spec_code_ori = new_spec_code
    new_spec_code = new_spec_code.split('-')
    #pbreak = param_break(spec_code_ori + '-0000-0000-0000-0000', '1-0-0-0-0-0-0-0-0-0-0-0-0')
    pbreak = param_break(spec_code_ori + '-0000-0000-0000-0000', '1-1-1-1-1-1-1-1-1-1-1-1-1')
    price_dep_arr = pbreak['price_dep_arr']
    new_pl = 0
    part_desc = description_gen(spec_code_ori + '-0000-0000-0000-0000')
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    pl_search_str_bom = "select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d"
    pl_search_param_bom = (int(new_spec_code[0]), int(new_spec_code[1]), int(new_spec_code[2]), int(new_spec_code[3]), int(new_spec_code[4]), int(new_spec_code[5]))
    cursor.execute(pl_search_str_bom % tuple(pl_search_param_bom))
    search_pl = cursor.fetchall()
    cursor.execute("select * from price_list where id=%d" % int(part_details['std_pl_obj'][0]))
    similar_pl_obj = cursor.fetchall()[0]
    if len(search_pl) == 0:
        #insert_str = """insert into price_list (name, unique_id, system_id, material_id, s1, s2, s3, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15,p16, p17, p18, p19, p20, price, calculation, calculation_bom) VALUES ('%s', %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, '%s','%s')"""
        insert_str = """insert into price_list VALUES """
        insert_param = list(similar_pl_obj)
        insert_param[0] = 'DEFAULT'
        insert_param[1] = part_desc
        insert_param[2] = new_spec_code[0]
        insert_param[3] = new_spec_code[1]
        insert_param[4] = new_spec_code[2]
        insert_param[5] = new_spec_code[3]
        insert_param[6] = new_spec_code[4]
        insert_param[7] = new_spec_code[5]
        i = 0
        for cur_param in insert_param:
            try:
                int(cur_param)
            except:
                insert_param[i] = cur_param
                if not cur_param:
                    insert_param[i] = 0
            else:
                insert_param[i] = int(cur_param)
            i += 1
        
        insert_str += str(tuple(insert_param))
        print(insert_str)
        insert_str = insert_str.replace("'DEFAULT'", "DEFAULT")
        insert_str = insert_str.replace("None", "DEFAULT")
        #insert_str.replace("Decimal('", "")
        #insert_str.replace("')", "")
        print(insert_str)
        cursor.execute(insert_str)
        db.commit()
    print('NEW SPEC CODE : ' + str(new_spec_code))
    cursor.execute("select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d" % \
                   (int(new_spec_code[0]), int(new_spec_code[1]), int(new_spec_code[2]), int(new_spec_code[3]), int(new_spec_code[4]), int(new_spec_code[5])))
    new_pl_obj = cursor.fetchall()[0]
    '''Cloning the BOM of similar PL to new PL'''
    cursor.execute("select * from b_o_m where pl_id=%d" % int(part_details['std_pl_obj'][0]))
    similar_bom = cursor.fetchall() 
    for cur_similar_bom in similar_bom:
        cur_bom_array = list(cur_similar_bom)
        cur_bom_array[0] = 'DEFAULT'
        cur_bom_array[1] = new_pl_obj[0]
        insert_str = """insert into b_o_m VALUES """
        insert_str += str(cur_bom_array)
        insert_str.replace("'DEFAULT'", "DEFAULT")
        cursor.execute(insert_str)
        db.commit()
    cursor.close()
    db.close()
    return(new_pl_obj)

def normalize_pl_360():
    data = {}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    #db = psycopg2.connect(database = 'featherlite', user='admin1', password='admin123', host='ferp.cv5o0gucwvmh.us-west-2.rds.amazonaws.com', port='5432')
    cursor = db.cursor()
    cursor.execute('select * from price_list')
    price_list_360 = cursor.fetchall()
    empty_list = []
    pl_column_names = {3:'system_id', 4:'material_id', 5:'s1', 6:'s2', 7:'s3'}
    for cur_pl_obj in price_list_360:
        '''In case system_id, material_id, s1, s2, s3 is None a value of "0" is added as default'''
        i = 3
        while i <= 7:
            '''In case system_id, material_id, s1, s2, s3 is None a value of "0" is added as default'''
            if cur_pl_obj[i] == None:
                cursor.execute('update price_list set %s=%d where id=%d' % (pl_column_names[i], 0, cur_pl_obj[0]))
                db.commit()
                empty_list.append(cur_pl_obj)
            i += 1
        i = 12
        j = 1
        while i <= 31:
            '''In case p1, p2, p3, ...., p20 is None a value of 1 is added as default'''
            if cur_pl_obj[i] == None:
                cursor.execute('update price_list set %s=%d where id=%d' % ('p'+str(j), 1, cur_pl_obj[0]))
                db.commit()
                empty_list.append(cur_pl_obj)
            i += 1
            j += 1
        cursor.execute('update price_list set comment_id=1 where comment_id IS NULL')
        db.commit()
        cursor.execute("""update price_list set calculation_bom=calculation where calculation_bom IS NULL or calculation_bom='DEFAULT' or calculation_bom='None'""")
        db.commit()
    data['quote_pl'] = {'objects': empty_list}
    cursor.close()
    db.close()
    return(data)

def normalize_derivative_360():
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    
    i = 1
    while i <= 12:
        if i <= 4:
            cursor.execute("""update derivative set %s=0 where %s IS NULL""" % ('d'+str(i), 'd'+str(i)))        
            db.commit()
        cursor.execute("""update derivative set %s='' where %s='0'""" % ('f'+str(i), 'f'+str(i)))        
        db.commit()
        #cursor.execute("""update derivative set %s='' where %s LIKE 'f%'""" % ('f'+str(i), 'f'+str(i)))
        #db.commit()
        print('Working On f' + str(i))
        i += 1
    cursor.close()
    db.close()
    """update price_list set system_id=0 where system_id IS NULL;
    update price_list set material_id=0 where material_id IS NULL;
    update price_list set s1=0 where s1 IS NULL;
    update price_list set s2=0 where s2 IS NULL;
    update price_list set s3=0 where s3 IS NULL;
    update pg_unique set size_format='-' where size_format IS NULL;"""
    return()

def get_std_pl_query(pn, price_dep_arr):
    pl_search_str = 'select * from price_list where unique_id=%d'
    pl_search_param = [int(pn['n'])]
    if 's' in price_dep_arr:
        pl_search_str += ' and system_id=%d'
        pl_search_param.append(int(pn['s']))
    if 'm' in price_dep_arr:
        pl_search_str += ' and material_id=%d'
        pl_search_param.append(int(pn['m']))
    if 's1' in price_dep_arr:
        pl_search_str += ' and s1=%d'
        pl_search_param.append(int(pn['s1']))
    if 's2' in price_dep_arr:
        pl_search_str += ' and s2=%d'
        pl_search_param.append(int(pn['s2']))
    if 's3' in price_dep_arr:
        pl_search_str += ' and s3=%d'
        pl_search_param.append(int(pn['s3']))
    return(pl_search_str, tuple(pl_search_param))

def bom_generation(part_number, fin_number, qty):
    data = {}
    #print('Part Number for BOM GEN : ' + str(part_number))
    pbreak = param_break(part_number, fin_number)
    fin_no_split = pbreak['fin_no_split']
    unique_obj = pbreak['unique_obj']
    desc_format = pbreak['desc_format']
    desc_format_split = pbreak['desc_format_split']
    pn = pbreak['pn']
    fin_format = pbreak['fin_format']
    price_dep_arr = pbreak['price_dep_arr']
    pfin = pbreak['pfin']
    pfin_bom = pbreak['pfin_bom']
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    #db = psycopg2.connect(database = 'featherlite', user='admin1', password='admin123', host='ferp.cv5o0gucwvmh.us-west-2.rds.amazonaws.com', port='5432')
    cursor = db.cursor()
    std_calc_eqn = '0'
    bom_calc_eqn = '0'
    input_factor_eqn = '0'
    std_calc = 0
    bom_calc = 0
    input_calc = 0
    bom = []
    bom_nested = []
    std_pl_query = get_std_pl_query(pn, price_dep_arr)
    '''pl_search_str = 'select * from price_list where unique_id=%d'
    pl_search_param = [int(pn['n'])]
    if 's' in price_dep_arr:
        pl_search_str += ' and system_id=%d'
        pl_search_param.append(int(pn['s']))
    if 'm' in price_dep_arr:
        pl_search_str += ' and material_id=%d'
        pl_search_param.append(int(pn['m']))
    if 's1' in price_dep_arr:
        pl_search_str += ' and s1=%d'
        pl_search_param.append(int(pn['s1']))
    if 's2' in price_dep_arr:
        pl_search_str += ' and s2=%d'
        pl_search_param.append(int(pn['s2']))
    if 's3' in price_dep_arr:
        pl_search_str += ' and s3=%d'
        pl_search_param.append(int(pn['s3']))
    '''
    cursor.execute(std_pl_query[0] % std_pl_query[1])
    price_list_obj_std = cursor.fetchall()
    if price_list_obj_std != []:
        std_calc_eqn = price_list_obj_std[0][37]
        std_rate = price_list_obj_std[0][35]
    else:
        error_message = 'crm_auto_pl not found for Part No.:' + str(part_number) + '(' + str(unique_obj[1]) + ')' + ' price dep arr :' + str(price_dep_arr)
        raise Exception(error_message) 
    #print('pn' + str(pn))
    pl_search_str_bom = 'select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d'
    pl_search_param_bom = (int(pn['n']), int(pn['s']), int(pn['m']), int(pn['s1']), int(pn['s2']), int(pn['s3']))
    sync_down_pl_360(part_number[:21])
    cursor.execute(pl_search_str_bom % tuple(pl_search_param_bom))
    price_list_obj_bom = cursor.fetchall()
    if len(price_list_obj_bom) == 0:
        '''this is done so that the software generates BOM for items which are not defined in pricelist with 
        complete match in spec code hence even match of specific codes / parameters - (price dep array) 
        is enough to generate BOM & get the right costing)'''
        price_list_obj_bom = price_list_obj_std
    std_eval_str = '0'
    bom_eval_str = '0'
    rmp = {}
    kon = {}
    
    '''Setting up raw material prices in dictionary rmp={1....20}'''
    if price_list_obj_bom != []:
        price_list_obj_bom = price_list_obj_bom[0]
        bom_calc_eqn = price_list_obj_bom[38]
        bom_rate = price_list_obj_bom[35]
        input_factor_eqn = price_list_obj_bom[41]
        '''get raw material prices of this item'''
        rmp = {}
        '''
        Read must start from column 13 because this is the coloumn where p1 value is available & goes upto 31 as 20 values are available
        as the cursor result will be an array of tuples price_list_obj_bom[12] to price_list_obj_bom[31] has to be captured
        '''
        i = 1
        start_col = 12 - i
        while i <= 20:
            rm_id = price_list_obj_bom[start_col + i]
            if not rm_id:
                rm_id = 1
            cursor.execute('select value from raw_material_price where id=%d' % rm_id)
            rmp['p' + str(i)] = cursor.fetchall()[0][0]
            i += 1
        
        '''get bom details of this item'''
        cursor.execute('select * from b_o_m where pl_id=%d' % price_list_obj_bom[0])
        bom_gen_fetch = cursor.fetchall()
        bom_gen_data = []
        for cur_bom_fetch in bom_gen_fetch:
            cur_bom_pl_id = cur_bom_fetch[2]
            cursor.execute('select * from price_list where id=%d' % cur_bom_pl_id)
            cur_bom_pl_obj = cursor.fetchall()[0]
            cur_bom_der_id = cur_bom_fetch[3]
            cursor.execute('select * from derivative where id=%d' % cur_bom_der_id)
            cur_bom_der_obj = cursor.fetchall()[0]
            new_part_no = ''
            #print('cur_bom_pl_obj : ' + str(cur_bom_pl_obj))
            skip_part = False
            i = 2
            while i < 8:
                try:
                    int(cur_bom_pl_obj[i])
                except:
                    skip_part = True
                i += 1
            if skip_part == True:
                continue
            new_part_no += str(1000 + cur_bom_pl_obj[2])[1:] + '-' + str(100 + cur_bom_pl_obj[3])[1:] + '-' + str(100 + cur_bom_pl_obj[4])[1:] + '-' \
                    + str(1000 + cur_bom_pl_obj[5])[1:] + '-' + str(1000 + cur_bom_pl_obj[6])[1:] + '-' + str(1000 + cur_bom_pl_obj[7])[1:]
            i = 0
            test = {}
            new_part_fin_no = str(cur_bom_pl_obj[33])
            for cur_der_col in cur_bom_der_obj:
                if i > 1 and i <= 5 :
                    dim_calc_eqn = cur_der_col
                    if dim_calc_eqn == 'None' or dim_calc_eqn == '':
                        dim_eval_str = '0'
                    else:
                        dim_eval_str = dim_cost_port(pn, std_rate, rmp, kon, dim_calc_eqn, qty)
                    '''from derivative table Cols 2, 3, 4, 5 give the dimension calculation equations of D1, D2, D3 & D4 for the given BOM'''
                    dim_no = eval(dim_eval_str)
                    if dim_no < 0.0:
                        dim_no = 0
                    elif dim_no > 9999.0:
                        dim_no = 9999
                    new_part_no += '-' + str(10000 + int(dim_no))[1:]
                    if int(str(1000 + cur_bom_pl_obj[2])[1:]) == 139:
                        print('Dim Calc Eqn : ' + str(dim_calc_eqn))
                        print('Dim Eval Str : ' + str(dim_eval_str))
                        print('New Part No.--------xxxxxxxxxxx------------xxxxxxxxxx-------- : ' + str(new_part_no))
                elif i == 6:
                    '''from derivative table Col 6 gives the quantity calculation equation for the given BOM'''
                    qty_calc_eqn = cur_der_col
                    qty_eval_str = dim_cost_port(pn, std_rate, rmp, kon, cur_der_col, qty)
                    #test[''] = qty_eval_str
                    bom_qty = round(eval(qty_eval_str), 2)
                    
                elif i > 6 and i <= 18:
                    try:
                        int(cur_der_col)
                    except:
                        new_part_fin_no += '-1'
                    else:
                        new_part_fin_no += '-' + str(pfin_bom[str('f' + str(cur_der_col))])
                    
                i += 1
            
            '''In case any BOM derivation seems to be wrong, the same can be printed during execution, however, with reference to the spec code'''
            bom_check = True
            if new_part_no[:3] == '127' and bom_check == True:
                print('Parent Input - ' + part_number)
                print('Parent Price List ID - ' + str(price_list_obj_bom[0]) + ' Parent Price List Name - ' + str(price_list_obj_bom[1]))
                print('Child Part No. - ' + new_part_no)
                print('Parent Raw Material Price - ' + str(rmp))
                print('Qty Calc Str - ' + qty_calc_eqn)
                print('Qty Eval Str - ' + qty_eval_str)
                #print(std_rate)
                #print('Qty Eval Eqn Input - ' + str(cur_bom_der_obj[6]) + ' Replaced Str - qty_eval_str' + str(qty_eval_str))
            if bom_qty > 0:
                bom.append((new_part_no, new_part_fin_no, bom_qty))
        '''This code is written to modify the wastage value in the BOM of an item'''
        bom_nested = []
        for cur_bom in bom:
            feed_boards = []
            cur_bom_unq = int(str(cur_bom[0])[:3])
            print('cur_bom_unq : ' + str(cur_bom_unq))
            if cur_bom_unq == 202 or cur_bom_unq == 212 or cur_bom_unq == 222:
                '''This Condition is not activated because the available raw material sizes are not added'''
                #print('Given BOM')
                #print(cur_bom)
                board_spec = cur_bom[0][0:2] + '0' + cur_bom[0][3:7] + '00' + cur_bom[0][9:21]
                #print('board_spec : ' + board_spec)
                board_pl_obj = auto_price_list.objects.filter(spec_code = board_spec)
                #board_pl_obj = get_object_or_404(auto_price_list, spec_code = board_spec)
                if len(board_pl_obj) == 0:
                    board_pl_obj = auto_price_list(spec_code = board_spec, name = description_gen(board_spec + '-0000-0000-0000-0000'))
                    board_pl_obj.save()
                board_pl_obj = get_object_or_404(auto_price_list, spec_code = board_spec)
                app_boards = board_pl_obj.available_rm_sizes_set.filter(exclude_size = False)
                if len(app_boards) == 0:
                    if board_spec[0:3] == '200':
                        '''The Default Board Size created will be 2430 x 1820 - in case no size is defined for the given plate - 200'''
                        new_board = available_rm_sizes(name = description_gen(board_spec + '-0000-0000-0000-0000') + '|' + size_gen(board_spec + '-2430-1820-0000-0000'),\
                                    auto_pl = board_pl_obj, d1 = 2430, d2 = 1820, d3 = 0, d4 = 0)
                    elif board_spec[0:3] == '210':
                        '''The Default Extrusion Size created will be 3660 - in case no size is defined for the given plate - 210'''
                        new_board = available_rm_sizes(name = description_gen(board_spec + '-0000-0000-0000-0000') + '|'+ size_gen(board_spec + '-3660-0000-0000-0000'),\
                                    auto_pl = board_pl_obj, d1 = 3660, d2 = 0, d3 = 0, d4 = 0)
                    elif board_spec[0:3] == '220':
                        '''The Default Extrusion Size created will be 5000x1370 - in case no size is defined for the given plate - 220'''
                        new_board = available_rm_sizes(name = description_gen(board_spec + '-0000-0000-0000-0000') + '|'+ size_gen(board_spec + '-5000-1370-0000-0000'),\
                                    auto_pl = board_pl_obj, d1 = 1370, d2 = 50000, d3 = 0, d4 = 0)
                    new_board.save()
                app_boards = board_pl_obj.available_rm_sizes_set.filter(exclude_size = False)
                for cur_board in app_boards:
                    if board_pl_obj.spec_code[0:3] == '220':
                        place_h = divmod(cur_board.d1, int(str(cur_bom[0])[22:26]))
                        place_v = divmod(cur_board.d1, int(str(cur_bom[0])[27:31]))
                        '''Code has to be added to check if the fabric has grain direction for feeding
                        the right plate size - now assuming that grain doesn't matter'''
                        if place_h[1] < place_v[1]:
                            dim2 = int(str(cur_bom[0])[27:31])
                        else:
                            dim2 = int(str(cur_bom[0])[22:26])
                    else:
                        dim2 = cur_board.d2
                    board_pn = board_pl_obj.spec_code + '-' + str(10000 + cur_board.d1)[1:] + '-' + str(10000 + dim2)[1:] + '-' + \
                                            str(10000 + cur_board.d3)[1:] + '-' + str(10000 + cur_board.d4)[1:]
                    board_fin = cur_bom[1]
                    feed_board_app = []
                    board_pn_split = list(board_pn.split('-'))
                    for cur_param in board_pn_split:
                        feed_board_app.append(int(cur_param))
                    feed_board_app.append(str(board_fin))
                    #feed_board_app.append(1.0)
                    #print('feed_board_app : ' + str(feed_board_app))
                    feed_boards.append(tuple(feed_board_app))
                #print('Applicable Boards:')
                #print(feed_boards)
                '''Eliminating the wastage value, hence making last 4 digits: 0000'''
                tare_pn = cur_bom[0][:-4] + str('0000')
                tare_pn_split = list(tare_pn.split('-'))
                feed_tare = []
                for cur_param in tare_pn_split:
                    feed_tare.append(int(cur_param))
                grain_det = get_type_grain_direction(tare_pn)
                feed_tare[2] = grain_det['grain_direction']
                feed_tare.append(str(cur_bom[1]))
                #print('feed_tare BOM : ')
                #print(tuple(feed_tare))
                #print('Applicable Rawmaterail sizes : ')
                #print(feed_boards)
                #print('Final Individual Nest Result : ')
                d1 = int(feed_tare[6])
                d2 = int(feed_tare[7])
                exec_update = True
                if (d2 == 0 and d1 > 3600) or d1 == 0:
                    exec_update = False
                elif d2 == 0 and ((d2 > 1800 and d1 > 2700) or (d2 > 2700 and d1 > 1800)):
                    exec_update = False
                if exec_update == True:
                    wastage = ind_nest(tuple(feed_tare), feed_boards)
                else:
                    wastage = 34
                #print(str(nest_result))
                #print('WASTAGE -------------- ' + str(nest_result['wastage']))
                tare_d4 = str(10000 + int(wastage))[1:]
                #print('Nest Wastage : ' + str(nest_result['wastage']) + ' Tare D4 : ' + tare_d4 + ' Cur Bom : ' + cur_bom[0])
                new_cur_bom_pn = cur_bom[0][:-4] + tare_d4
                new_cur_bom = (new_cur_bom_pn, cur_bom[1], round(cur_bom[2], 2))
            else:
                new_cur_bom = cur_bom
            bom_nested.append(new_cur_bom)
    #print('Standard Rate --------- : ' + str(std_rate))
    std_eval_str = dim_cost_port(pn, std_rate, rmp, kon, std_calc_eqn, qty)
    #print('BOM PL OBJ : ' + str(price_list_obj_bom))
    bom_eval_str = dim_cost_port(pn, std_rate, rmp, kon, bom_calc_eqn, qty)
    input_eval_str = dim_cost_port(pn, std_rate, rmp, kon, input_factor_eqn, qty)
    cursor.close()
    db.close()
    print_bom = False
    #if print_bom == True: 
        #print(' --------- Normal BOM : --------')
        #print(bom)
        #print(' --------- Nested BOM : --------')
        #print(bom_nested)
    data['bom'] = bom
    data['bom_nested'] = bom_nested
    data['std_calc_eqn'] = std_calc_eqn
    data['input_calc_eqn'] = input_factor_eqn
    if bom_calc_eqn == 'None' or bom_calc_eqn == 'DEFAULT' or bom_calc_eqn == None:
        bom_calc_eqn = std_calc_eqn
    data['bom_calc_eqn'] = bom_calc_eqn
    data['std_eval_str'] = std_eval_str
    data['bom_eval_str'] = bom_eval_str
    data['input_eval_str'] = input_eval_str
    data['std_pl_obj'] = price_list_obj_std[0]
    print('BOM Generation Output Data : ' + str(data))
    return(data)

def part_description(part_number, fin_number, qty):
    '''This function does not save or update anything in the database, instead only reads the relevant data to provide description, size, finish in human readable format
    BOM generation is also called from here'''
    #data = {}
    #print('param break feed - ' + str(part_number))
    pbreak = param_break(part_number, fin_number)
    unique_obj = pbreak['unique_obj']
    #print('TEST START2')
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.close()
    db.close()
    unique_detail = (unique_obj[0], unique_obj[1])
    if int(part_number[:3]) == 233:
        print('This is 233')
    '''This code is to convert description format to description string'''
    new_desc_str = description_gen(part_number)
    
    '''This Code is to convert Size format to size string'''
    new_size_str = size_gen(part_number)
    
    '''This code is to convert finish format to finish string'''
    new_fin_str = finish_gen(part_number, fin_number)
    
    bom_gen = bom_generation(part_number, fin_number, qty)
    print('TEST END')
    
    output = {}
    output['description'] = new_desc_str
    output['size'] = new_size_str
    output['finish'] = new_fin_str
    output['std_calc'] = bom_gen['std_calc_eqn']
    output['bom_calc'] = bom_gen['bom_calc_eqn']
    output['input_calc'] = bom_gen['input_calc_eqn']
    output['std_calc_val'] = round(eval(bom_gen['std_eval_str']), 2)
    output['bom_calc_val'] = round(eval(bom_gen['bom_eval_str']), 2)
    output['input_calc_val'] = round(eval(bom_gen['input_eval_str']), 2)
    output['bom'] = bom_gen['bom']
    output['bom_nested'] = bom_gen['bom_nested']
    output['unique'] = unique_detail
    output['adhoc_sale_price'] = round(eval(bom_gen['std_eval_str']), 2)
    output['test'] = False
    output['std_pl_obj'] = bom_gen['std_pl_obj']
    print('Part Description Output Data : ' + str(output))
    return(output)


def auto_update_item_master(imp_part_no, imp_fin_no, qty):
    print('Auto Update Item Master : ' + str(imp_part_no) + ' Fin : ' + str(imp_fin_no))
    print(imp_part_no[:3])
    if imp_part_no[:3] == '233':
        print(imp_part_no)
    '''This function Only Creates or Updates the given item in the input to the item master table only 1 level nom is updated in the same row - imported bom'''
    master_part = item_master.objects.filter(imported_item_code = imp_part_no, imported_item_finish = imp_fin_no)
    '''Do Not change the search string, only change the overwritten partnumber in case the no. of digits are less'''
    if len(master_part) == 0:
        master_part = item_master(imported_item_code = imp_part_no, imported_item_finish = imp_fin_no)
        master_part.created_date = timezone.now()
        part_details = part_description(imp_part_no, imp_fin_no, 1.0)
        availability = False
    else:
        master_part = master_part[0]
        print('TEST START1')
        part_details = part_description(master_part.imported_item_code, master_part.imported_item_finish, 1.0)
        availability = True
    
    if not 'description' in part_details:
        return({'error':'description_string unavailable', 'part_no':imp_part_no, 'fin_no':imp_fin_no})
    master_part.name = part_details['description'] + '|' + part_details['size'] + '|' + part_details['finish']
    if len(str(imp_part_no.split('-')[0])) == 2:
        imp_part_no = '0' + imp_part_no
    master_part.imported_item_code = imp_part_no
    master_part.imported_item_finish = imp_fin_no
    master_part.imported_bom = part_details['bom_nested']
    #master_part.imported_infinite_bom = infinite_update([(imp_part_no, imp_fin_no, 1)], False)
    master_part.process_valuation_sale =  part_details['bom_calc_val']
    master_part.adhoc_sale_price =  part_details['adhoc_sale_price']
    master_part.input_factor =  part_details['input_calc_val']
    master_part.last_updated = timezone.now()
    
    '''Item Group - i.e., Unique Storage in ERP'''
    item_gr = item_group.objects.filter(imported_unique = int(part_details['unique'][0]))
    if not item_gr:
        item_gr = item_group(imported_unique = int(part_details['unique'][0]))
    else:
        item_gr = item_gr[0]
    item_gr.name = part_details['unique'][1]
    item_gr.save()
    master_part.item_group = item_gr
    
    '''If the bom_pl is available in flite360
    if part_details['bom_pl']:
        bom_pl = part_details['bom_pl'][0][0]
    else:
        bom_pl = 0'''
    '''auto_pricelist - i.e., Pricelist Storage in ERP'''
    given_spec_code = imp_part_no[:21]
    
    auto_pl = auto_price_list.objects.filter(spec_code = given_spec_code)
    
    '''If the PL corresponding to search string is available'''
    if auto_pl:
        auto_pl = auto_pl[0]
    else:
        auto_pl = auto_price_list()
        auto_pl.created_date = timezone.now()
        auto_pl.auto_sync = True
        #clone_price_list_360(given_spec_code)
    if part_details['bom_calc'] == '0' or part_details['bom_calc'] == None:
        auto_pl.sale_price_calc_eqn = 0
    else:
        auto_pl.sale_price_calc_eqn = part_details['bom_calc']
        if auto_pl.allow_auto_sync == True:
            if len(part_details['bom_nested']) > 6:
                auto_pl.purchase_price_calc_eqn = 'sum'
            else:
                auto_pl.purchase_price_calc_eqn = part_details['bom_calc']
            auto_pl.purchase_factor_calc_eqn = part_details['bom_calc']
            auto_pl.job_work_price_calc_eqn = part_details['bom_calc']
            auto_pl.shop_order_price_calc_eqn = part_details['bom_calc']
            auto_pl.input_factor_calc_eqn = part_details['input_calc']
    auto_pl.last_updated = timezone.now()
    auto_pl.spec_code = given_spec_code
    auto_pl.item_group = item_gr
    auto_pl.name = part_details['description']
    auto_pl.save()
    if len(master_part.name) > 170:
        master_part.description = master_part.name
        master_part.name = master_part.name[:130] + (' *Truncated Please see description')
    master_part.save()
    bom_output = []
    for cur_master_bom in part_details['bom_nested']:
        add_bom = list(cur_master_bom)
        add_bom[2] = cur_master_bom[2] * qty
        bom_output.append(tuple(add_bom))
    return(bom_output)


def sale_price_update(item_master_id, new_input_factor, new_bom_input_sum):
    new_input_factor = float(new_input_factor)
    new_bom_input_sum = float(new_bom_input_sum)
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    auto_pl_obj = auto_price_list.objects.filter(spec_code=item_master_obj.imported_item_code[:21])
    if len(auto_pl_obj) == 0:
        item_master_obj.delete()
        return()
    auto_pl_obj = get_object_or_404(auto_price_list, spec_code=item_master_obj.imported_item_code[:21])
    new_margin = float(auto_pl_obj.sale_margin)
    new_bom_sale_price = float(new_bom_input_sum * new_margin)
    cur_bom_ip_rate = float(item_master_obj.bom_input_price)
    diff = cur_bom_ip_rate - new_bom_input_sum
    new_sp_his_data = ast.literal_eval(item_master_obj.bom_sp_his)
    if diff > 2.0 or diff < -2.0:
        old_bom_ip = round(float(item_master_obj.bom_input_price), 2)
        old_bom_sp = round(float(item_master_obj.bom_sale_price), 2)
        if old_bom_sp == 0:
            old_margin = 1
        else:
            old_margin = round(float(old_bom_sp/old_bom_sp), 2)
        new_sp_his_data.append({'bom_input_rate':old_bom_ip, 'bom_sale_price':old_bom_sp, \
                                'dt':str(item_master_obj.price_last_updated), 'margin':old_margin})
    item_master_obj.input_factor = new_input_factor
    item_master_obj.bom_input_price = new_bom_input_sum
    item_master_obj.bom_sale_price = new_bom_sale_price
    item_master_obj.bom_sp_his = new_sp_his_data
    item_master_obj.price_last_updated = timezone.now()
    item_master_obj.save()
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    return(item_master_obj)

def infinite_update(input_list, master_update, settings):
    '''
    input_list = [(imported_item_no, imported_item_fin, qty), (imported_item_no, imported_item_fin, qty)......]
    master_update = True/False
    settings = {'auto_update':True/False}
    '''
    test = {}
    parent_list = []
    parent_list_detail = []
    infinite_list = []
    infinite_list_detail = []
    dummy_list = []
    dummy_list_detail = []
    #normalize_pl_360()
    print('START -- ' + input_list[0][0] + input_list[0][1])
    for cur_input in input_list:
        cur_bom = auto_update_item_master(cur_input[0], cur_input[1], cur_input[2])
        for cur_bom_item in cur_bom:
            cur_search = (cur_bom_item[0], cur_bom_item[1])
            if not cur_search in parent_list:
                parent_list.append(cur_search)
                parent_list_detail.append([cur_bom_item[0], cur_bom_item[1], cur_bom_item[2]])
            else:
                pos = parent_list.index(cur_search)
                parent_list_detail[pos][2] += cur_bom_item[2]
    '''parent_list = [(bom_l1_item_no, bom_l1_item_fin, qty), (bom_l1_item_no, bom_l1_item_fin, qty)......]'''
    dummy_list = parent_list
    dummy_list_detail = parent_list_detail
    dummy_len = len(dummy_list_detail)
    test['inf_list'] = infinite_list
    i = 0
    while i < dummy_len:
        cur_bom_parent = []
        cur_search = (dummy_list_detail[i][0], dummy_list_detail[i][1])
        if not cur_search in infinite_list:
            infinite_list.append(cur_search)
            infinite_list_detail.append([parent_list_detail[i][0], parent_list_detail[i][1], parent_list_detail[i][2]])
        else:
            pos = infinite_list.index(cur_search)
            infinite_list_detail[pos][2] += parent_list_detail[i][2]
        '''We need to add a condition to avoid auto_update here as much as possible'''
        test_item = item_master.objects.filter(imported_item_code = input_list[0][0], imported_item_finish = input_list[0][1])
        if len(test_item) > 0:
            time_diff = timezone.now() - test_item[0].last_updated 
            if (time_diff >= timedelta(days=1) and settings['auto_update'] == False):
                print('Skipping auto item master update ' + str(test_item[0]))
                cur_bom_parent = test_item[0].imported_bom
                if len(str(cur_bom_parent)) > 6:
                    cur_bom_parent = ast.literal_eval(str(cur_bom_parent))
                else:
                    cur_bom_parent = []
            else:
                cur_bom_parent = auto_update_item_master(dummy_list_detail[i][0], dummy_list_detail[i][1], dummy_list_detail[i][2])
        else:
            cur_bom_parent = auto_update_item_master(dummy_list_detail[i][0], dummy_list_detail[i][1], dummy_list_detail[i][2])
        if 'error' in cur_bom_parent:
            return({'error':cur_bom_parent, 'parent':parent_list_detail[i]})
        for cur_bom_ln in cur_bom_parent:
            dummy_list_detail.append(list(cur_bom_ln))
        dummy_len = len(dummy_list_detail)
        i += 1
    test['count'] = i
    test['inf_list'] = infinite_list
    input_obj = item_master.objects.filter(imported_item_code = input_list[0][0], imported_item_finish = input_list[0][1])
    print('END -- ' + input_list[0][0] + 'xx' + input_list[0][1] + str(input_obj[0].name))
    if not input_obj:
        test['error'] = (input_list[0][0], input_list[0][1])
        return(test)
    if len(input_list) == 1 and master_update == True:
        item_check = item_master.objects.filter(imported_item_code = input_list[0][0], imported_item_finish = input_list[0][1])
        if len(item_check) > 1:
            for cur_item in item_check:
                repeated_items = item_master.objects.filter(imported_item_code = cur_item.imported_item_code, imported_item_finish = cur_item.imported_item_finish)
                if len(repeated_items) > 1:
                    message = []
                    message.append(cur_item)
                    i = len(repeated_items)
                    while i > 1:
                        repeated_items[i-1].delete()
                        i -= 1
            print('Repeated Item Master : '+ str(message))
        input_obj = get_object_or_404(item_master, imported_item_code = input_list[0][0], imported_item_finish = input_list[0][1])
        input_obj.imported_infinite_bom = infinite_list_detail
        input_obj.last_updated = timezone.now()
        input_obj.bom_last_updated = timezone.now()
        input_obj.save()
        print('Imported Infinite BOM : ' + str(input_obj.imported_infinite_bom))
        part_id_conversion([(input_list[0][0], input_list[0][1], input_list[0][2])])
        input_obj = get_object_or_404(item_master, imported_item_code = input_list[0][0], imported_item_finish = input_list[0][1])
        conv_feed_list = ast.literal_eval(input_obj.imported_bom)
        '''This code is added on 24 may - needed to store converted BOM data in sub-assemblies & not only in FGs '''
        i = 0
        while i < len(conv_feed_list):
            cur_bom_obj = get_object_or_404(item_master, imported_item_code=conv_feed_list[i][0], imported_item_finish=conv_feed_list[i][1])
            for cur_imp_bom in ast.literal_eval(cur_bom_obj.imported_bom):
                conv_feed_list.append(cur_imp_bom)
            i += 1
        part_id_conversion(conv_feed_list)
        calc_sale_price = Decimal(0)
        calc_bom_input_price = Decimal(0)
        print(str(input_obj.infinite_bom))
        inf_bom = ast.literal_eval(str(input_obj.infinite_bom))
        print('Updating Sale Price - ' + input_obj.name)
        print('Respective Infinite BOM - ' + str(inf_bom))
        if not inf_bom == [] and not inf_bom == '[]' and not inf_bom == {} and not inf_bom =='{}':
            '''Adding All BOM items processing cost'''
            for cur_inf_bom in inf_bom:
                cur_inf_item = get_object_or_404(item_master, id = cur_inf_bom[0])
                print(cur_inf_item.name + ' Process Val Sale:' + str(cur_inf_item.process_valuation_sale) + ' Adhoc Sale Price:' + str(cur_inf_item.adhoc_sale_price))
                calc_sale_price += Decimal(cur_inf_item.process_valuation_sale) * Decimal(cur_inf_bom[1])
                calc_bom_input_price += Decimal(cur_inf_item.input_factor) * Decimal(cur_inf_bom[1])
        '''Adding The Self Processing / BOM Calc Cost'''
        calc_sale_price += round(Decimal(input_obj.process_valuation_sale) * Decimal(input_list[0][2]), 2)
        calc_bom_input_price += round(Decimal(input_obj.input_factor) * Decimal(input_list[0][2]), 2)
        auto_pl_obj = get_object_or_404(auto_price_list, spec_code = input_obj.imported_item_code[:21])
        sale_margin = auto_pl_obj.sale_margin
        calc_bom_sale_price = round(calc_bom_input_price * sale_margin, 2)
        input_obj = sale_price_update(input_obj.id, input_obj.input_factor, calc_bom_input_price)
        print(calc_sale_price)
        '''
        input_obj.sale_price = calc_sale_price
        input_obj.bom_input_price = calc_bom_input_price
        input_obj.bom_sale_price = calc_bom_sale_price
        input_obj.price_last_updated = timezone.now()
        input_obj.save()
        '''
        #bom_input_sum(input_obj.id, {'update_ip_factor':True})
    return(infinite_list_detail)


def synchronize_rmp():
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select * from raw_material_price')
    rmp_set = cursor.fetchall()
    for cur_rmp in rmp_set:
        cur_auto_rmp = rmp_auto.objects.filter(rmp_pk_360=cur_rmp[0])
        if len(cur_auto_rmp) == 0:
            cur_auto_rmp = rmp_auto(rmp_pk_360=cur_rmp[0])
            cur_auto_rmp.created_date = timezone.now()
        else:
            cur_auto_rmp = get_object_or_404(rmp_auto, rmp_pk_360=cur_rmp[0])
        cur_auto_rmp.last_updated = timezone.now()
        cur_auto_rmp.name = cur_rmp[1]
        if not cur_rmp[2]:
            base_val = 0.0
        else:
            base_val = cur_rmp[2]
        if not cur_rmp[3]:
            uom = '-'
        else:
            uom = cur_rmp[3]
        cur_auto_rmp.rmp_sale_rate = base_val
        cur_auto_rmp.rate_uom = uom
        cur_auto_rmp.constant_value = cur_rmp[4]
        cur_auto_rmp.save()
    cursor.close()
    db.close()
    return()

def synchronize_item_group():
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select * from pg_unique')
    unique_set = cursor.fetchall()
    for cur_unique in unique_set:
        cur_item_group = item_group.objects.filter(imported_unique=cur_unique[0])
        if len(cur_item_group) == 0:
            cur_item_group = item_group(imported_unique=cur_unique[0])
        else:
            cur_item_group = get_object_or_404(item_group, imported_unique=cur_unique[0])
        cur_item_group.name = cur_unique[1]
        cur_item_group.save()
    cursor.close()
    db.close()
    return()

def synchronize_item_department():
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select * from department')
    department_set = cursor.fetchall()
    for cur_360_department in department_set:
        cur_department = item_department.objects.filter(flite_360_dep_id=cur_360_department[0])
        if len(cur_department) == 0:
            cur_department = item_department(flite_360_dep_id=cur_360_department[0])
        else:
            cur_department = get_object_or_404(item_department, flite_360_dep_id=cur_360_department[0])
        cur_department.name = cur_360_department[1]
        cur_department.save()
    cursor.close()
    db.close()
    return()


def rmp_con_upload(auto_pl_id, rmp_obj, con_obj):
    pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
    if 'p1' in rmp_obj:
        pl_obj.p1 = rmp_obj['p1']
    if 'p2' in rmp_obj:
        pl_obj.p2 = rmp_obj['p2']
    if 'p3' in rmp_obj:
        pl_obj.p3 = rmp_obj['p3']
    if 'p4' in rmp_obj:
        pl_obj.p4 = rmp_obj['p4']
    if 'p5' in rmp_obj:
        pl_obj.p5 = rmp_obj['p5']
    if 'p6' in rmp_obj:
        pl_obj.p6 = rmp_obj['p6']
    if 'p7' in rmp_obj:
        pl_obj.p7 = rmp_obj['p7']
    if 'p8' in rmp_obj:
        pl_obj.p8 = rmp_obj['p8']
    if 'p9' in rmp_obj:
        pl_obj.p9 = rmp_obj['p9']
    if 'p10' in rmp_obj:
        pl_obj.p10 = rmp_obj['p10']
    if 'p11' in rmp_obj:
        pl_obj.p11 = rmp_obj['p11']
    if 'p12' in rmp_obj:
        pl_obj.p12 = rmp_obj['p12']
    if 'p13' in rmp_obj:
        pl_obj.p13 = rmp_obj['p13']
    if 'p14' in rmp_obj:
        pl_obj.p14 = rmp_obj['p14']
    if 'p15' in rmp_obj:
        pl_obj.p15 = rmp_obj['p15']
    if 'p16' in rmp_obj:
        pl_obj.p16 = rmp_obj['p16']
    if 'p17' in rmp_obj:
        pl_obj.p17 = rmp_obj['p17']
    if 'p18' in rmp_obj:
        pl_obj.p18 = rmp_obj['p18']
    if 'p19' in rmp_obj:
        pl_obj.p19 = rmp_obj['p19']
    if 'p20' in rmp_obj:
        pl_obj.p20 = rmp_obj['p20']
    if len(con_obj) > 0:
        if 'k1' in con_obj:
            pl_obj.k1 = con_obj['k1']
        if 'k2' in con_obj:
            pl_obj.k2 = con_obj['k2']
        if 'k3' in con_obj:
            pl_obj.k3 = con_obj['k3']
        if 'k4' in con_obj:
            pl_obj.k4 = con_obj['k4']
        if 'k5' in con_obj:
            pl_obj.k5 = con_obj['k5']
        if 'k6' in con_obj:
            pl_obj.k6 = con_obj['k6']
        if 'k7' in con_obj:
            pl_obj.k7 = con_obj['k7']
        if 'k8' in con_obj:
            pl_obj.k8 = con_obj['k8']
        if 'k9' in con_obj:
            pl_obj.k9 = con_obj['k9']
        if 'k10' in con_obj:
            pl_obj.k10 = con_obj['k10']
        if 'k11' in con_obj:
            pl_obj.k11 = con_obj['k11']
        if 'k12' in con_obj:
            pl_obj.k12 = con_obj['k12']
        if 'k13' in con_obj:
            pl_obj.k13 = con_obj['k13']
        if 'k14' in con_obj:
            pl_obj.k14 = con_obj['k14']
        if 'k15' in con_obj:
            pl_obj.k15 = con_obj['k15']
        if 'k16' in con_obj:
            pl_obj.k16 = con_obj['k16']
        if 'k17' in con_obj:
            pl_obj.k17 = con_obj['k17']
        if 'k18' in con_obj:
            pl_obj.k18 = con_obj['k18']
        if 'k19' in con_obj:
            pl_obj.k19 = con_obj['k19']
        if 'k20' in con_obj:
            pl_obj.k20 = con_obj['k20']
    pl_obj.save()
    return(pl_obj)

def sync_down_pl_360(part_spec_code):
    if part_spec_code[:6] == '078-01':
        print('debug')
    
    split_spec = part_spec_code.split('-')
    split_spec = list(split_spec)
    i = 0
    while i < len(split_spec):
        split_spec[i] = int(split_spec[i])
        i += 1
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d' % tuple(split_spec))
    price_list_set = cursor.fetchall()
    if len(price_list_set) == 0:
        #pbreak = param_break(part_spec_code+'-0000-0000-0000-0000', '1-0-0-0-0-0-0-0-0-0-0-0-0')
        pbreak = param_break(part_spec_code+'-0000-0000-0000-0000', '1-1-1-1-1-1-1-1-1-1-1-1-1')
        fin_no_split = pbreak['fin_no_split']
        unique_obj = pbreak['unique_obj']
        desc_format = pbreak['desc_format']
        desc_format_split = pbreak['desc_format_split']
        pn = pbreak['pn']
        fin_format = pbreak['fin_format']
        price_dep_arr = pbreak['price_dep_arr']
        pfin = pbreak['pfin']
        pfin_bom = pbreak['pfin_bom']
        std_calc_eqn = '0'
        bom_calc_eqn = '0'
        std_calc = 0
        bom_calc = 0
        bom = []
        bom_nested = []
        std_pl_query = get_std_pl_query(pn, price_dep_arr)
        cursor.execute(std_pl_query[0] % std_pl_query[1])
        price_list_set = cursor.fetchall()
        if len(price_list_set) == 0:
            print(price_list_set)
            return(False)
    cur_price_list = price_list_set[0]
    cursor.execute('select * from b_o_m where pl_id = %d' % int(price_list_set[0][0]))
    cur_bom_set = cursor.fetchall()
    cursor.close()
    db.close()
    cur_auto_price_list = auto_price_list.objects.filter(spec_code=part_spec_code)
    if len(cur_auto_price_list) == 0:
        cur_auto_price_list = auto_price_list(spec_code=part_spec_code)
        cur_auto_price_list.created_date = timezone.now()
        cur_auto_price_list.last_updated = timezone.now()
        cur_auto_price_list.save()
    i = 12
    rmp_dict = {}
    con_dict = {}
    cur_auto_price_list = get_object_or_404(auto_price_list, spec_code=part_spec_code)
    while i <= 31:
        auto_rmp = get_object_or_404(rmp_auto, rmp_pk_360 = cur_price_list[i])
        '''i-11 is given because dictionary should have keys from p1, p2, p3...p20'''
        rmp_dict['p'+str(i-11)] = auto_rmp
        i += 1
    rmp_con_upload(cur_auto_price_list.id, rmp_dict, [])
    cur_auto_price_list = get_object_or_404(auto_price_list, spec_code=part_spec_code)
    cur_auto_price_list.flite_360_price_list_id=cur_price_list[0]
    cur_auto_price_list.last_updated = timezone.now()
    cur_auto_price_list.name = description_gen(part_spec_code + '-0000-0000-0000-0000')
    cur_item_group = get_object_or_404(item_group, imported_unique=cur_price_list[2])
    cur_item_department = get_object_or_404(item_department, flite_360_dep_id=cur_price_list[39])
    cur_auto_price_list.item_group = cur_item_group
    cur_auto_price_list.input_rate_sale = cur_price_list[35]
    cur_auto_price_list.adhoc_sale_price_calc_eqn = cur_price_list[37]
    cur_auto_price_list.sale_price_calc_eqn = cur_price_list[38]
    cur_auto_price_list.purchase_factor_calc_eqn = cur_price_list[38]
    cur_auto_price_list.job_work_price_calc_eqn = cur_price_list[41]#same as input factor calc eqn
    cur_auto_price_list.shop_order_price_calc_eqn = cur_price_list[38]#same as input factor calc eqn
    cur_auto_price_list.item_department_ref = cur_item_department
    cur_auto_price_list.input_factor_calc_eqn = cur_price_list[41]
    cur_auto_price_list.sale_margin = cur_price_list[42]
    cur_auto_price_list.weight_calc_eqn = cur_price_list[43]
    cur_auto_price_list.volume_calc_eqn = cur_price_list[44]
    print('End Price_list : ' + str(cur_price_list[0]) + ' '  + str(cur_price_list[1]) + ' BOM Items : ' + str(len(cur_bom_set)))
    if len(cur_bom_set) > 0:
        cur_auto_price_list.purchase_price_calc_eqn = 'sum'
    else:
        cur_auto_price_list.purchase_price_calc_eqn = cur_price_list[38]
    cur_auto_price_list.save()
    return(cur_price_list)

def sync_up_pl_360(part_spec_code):
    part_desc = description_gen(part_spec_code + '-0000-0000-0000-0000')
    if sync_down_pl_360(part_spec_code) == False:
        #part_details = part_description(part_spec_code + '-0000-0000-0000-0000', '1-0-0-0-0-0-0-0-0-0-0-0-0', 1.0)
        part_details = part_description(part_spec_code + '-0000-0000-0000-0000', '1-1-1-1-1-1-1-1-1-1-1-1-1', 1.0)
        split_spec_code = part_spec_code.split('-')
        print('TEST START2')
        part_desc = description_gen(part_spec_code + '-0000-0000-0000-0000')
        print('Test Exit2')
        feed_part_no = '015-06-04-003-000-000-0360-0900-0000-0000'
        #feed_part_fin = '1-0-0-0-0-0-0-0-0-0-0-0-0'
        feed_part_fin = '1-1-1-1-1-1-1-1-1-1-1-1-1'
        print('TEST --------- :' + str(description_gen(feed_part_no)))
        db_crm_dict = crm_connect_data()
        db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
        cursor = db.cursor()
        cursor.execute("select * from price_list where id=%d" % int(part_details['std_pl_obj'][0]))
        similar_pl_obj = cursor.fetchall()[0]
        insert_str = """insert into price_list VALUES """
        insert_param = list(similar_pl_obj)
        insert_param[0] = 'DEFAULT'
        insert_param[1] = part_desc
        insert_param[2] = int(split_spec_code[0])
        insert_param[3] = int(split_spec_code[1])
        insert_param[4] = int(split_spec_code[2])
        insert_param[5] = int(split_spec_code[3])
        insert_param[6] = int(split_spec_code[4])
        insert_param[7] = int(split_spec_code[5])
        i = 0
        for cur_param in insert_param:
            try:
                int(cur_param)
            except:
                insert_param[i] = cur_param
                if cur_param == None:
                    insert_param[i] = 0
            else:
                insert_param[i] = int(cur_param)
            i += 1
        if insert_param[28] == None or insert_param[28] == 'DEFAULT':
            insert_param[28] = insert_param[27]
        insert_str += str(tuple(insert_param))
        print(insert_str)
        insert_str = insert_str.replace("'DEFAULT'", "DEFAULT")
        insert_str = insert_str.replace("None", "DEFAULT")
        print(insert_str)
        cursor.execute(insert_str)
        db.commit()
        cursor.execute("select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d" % (int(split_spec_code[0]), int(split_spec_code[1]), int(split_spec_code[2]), int(split_spec_code[3]), int(split_spec_code[4]), int(split_spec_code[5])))
        new_pl_obj = cursor.fetchall()[0]
        '''Cloning the BOM of similar PL to new PL'''
        cursor.execute("select * from b_o_m where pl_id=%d" % int(part_details['std_pl_obj'][0]))
        similar_bom = cursor.fetchall() 
        for cur_similar_bom in similar_bom:
            cur_bom_array = list(cur_similar_bom)
            cur_bom_array[0] = 'DEFAULT'
            cur_bom_array[1] = new_pl_obj[0]
            insert_str = """insert into b_o_m VALUES """
            insert_str += str(tuple(cur_bom_array))
            insert_str.replace("'DEFAULT'", "DEFAULT")
            print(insert_str)
            cursor.execute(insert_str)
            db.commit()
        cursor.close()
        db.close()
    return()

def update_all_bom(all_item_master, respond):
    '''
    {type:start_end, start:val, end:val}
    {type:group, group:unique_id, start:val, end:val}
    
    ?update_all_bom=true&<group=012&>start=<0>&end=<50>&renew=<false/true>
    '''
    '''
    all_item_master = item_master.objects.exclude(imported_item_code__startswith = '102')
    all_item_master = all_item_master.exclude(imported_item_code__startswith = '103')
    if param['type'] == 'group':
        #grp_str = str(1000 + int(param['group']))[1:]
        grp_str = param['group']
        all_item_master = all_item_master.filter(imported_item_code__startswith = grp_str)
    #all_item_master = all_item_master.exclude(last_updated__gt = date(2015, 1, 27))
    all_item_master = all_item_master.order_by('id')
    if param['end'] == 0:
        param['end'] = len(all_item_master)
    all_item_master = all_item_master[param['start']:param['end']]'''
    tot_len = len(all_item_master)
    count = 0
    print('ALL Item Master -- :' + str(all_item_master))
    start_time = timezone.now()
    for cur_item in all_item_master:
        print('-------------' + str(cur_item))
        if len(cur_item.imported_item_code) == 41:
            split_part = cur_item.imported_item_code.split('-')
            unq = int(split_part[0])
            d1 = int(split_part[6])
            d2 = int(split_part[7])
            exec_update = True
            if d2 == 0 and d1 > 3000:
                exec_update = False
            elif d2 > 0 and not((d2 < 1800 and d1 < 2700) or (d2 < 2700 and d1 < 1800)):
                exec_update = False
            if exec_update == True:
                count += 1;
                exception_report = str(count) + ' / ' + str(tot_len) + ' - id : ' + str(cur_item.id) + str(' - ') + str(count/tot_len)
                print(exception_report)
                current_time = timezone.now()
                time_diff = current_time - start_time
                if time_diff >= timedelta(seconds=250) and respond == True:
                    raise Exception ('time Exceeded please continue from ' + exception_report)
                infinite_update([(cur_item.imported_item_code, cur_item.imported_item_finish, 1.0)], True, {'auto_update':True})
                
    return({'message':'Updated ' + str(count) + ' Items' + ' Total Len:' + str(tot_len)})

def get_finish_name(fin_no):
    fin_no_split = fin_no.split('-')
    sel_finish_set = []
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    i = 1
    while i <= 12:
        if int(fin_no_split[i]) == 0:
            cur_fin_name = ''
        else:
            cursor.execute('select name from finish_base where id=%d' % (int(fin_no_split[i]),))
            cur_fin_name = cursor.fetchall()[0][0]
        sel_finish_set.append((int(fin_no_split[i]), cur_fin_name))
        i += 1
    cursor.close()
    db.close()
    return(sel_finish_set)

def get_fin_type(spec_code):
    spec_split = spec_code.split('-')
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                          host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select ft1 from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d' % \
                   (int(spec_split[0]), int(spec_split[1]), int(spec_split[2]), int(spec_split[3]), int(spec_split[4]), int(spec_split[5])))
    fin_type_id = cursor.fetchall()
    pl_availability = True
    if len(fin_type_id) > 0:
        fin_type_id = fin_type_id[0]
    else:
        fin_type_id = 1
        pl_availability = False
    cursor.execute('select * from finish_type where id=%d' % (fin_type_id))
    fin_type_obj = cursor.fetchall()[0]
    cursor.close()
    db.close()
    return(fin_type_obj, pl_availability)

def get_fin_opt(fin_type_id):
    finish_opt = []
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                          host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select * from finish_type where id=%d' % (fin_type_id))
    finish_type_obj = cursor.fetchall()[0]
    i = 3
    print('Finish type obj - ' + str(finish_type_obj))
    while i <= 14:
        fin_type_base_id = int(finish_type_obj[i])
        cursor.execute('select * from finish_base where finish_type_base_id=%d' % (fin_type_base_id,))
        cur_fin_opt = cursor.fetchall()
        finish_opt.append(cur_fin_opt)
        print('Finish Type Base Id : ' + str(fin_type_base_id) + ' Finish Opt - ' + str(cur_fin_opt))
        i += 1
    cursor.close()
    db.close()
    return(finish_opt)
    
    
def test_auto_pl_create():
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                          host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    #cursor.execute("insert into approval_group (name) VALUES (%s)" % ("'xyz'",))
    y = 'Trio Base - Tube in Tube'
    cursor.execute("""insert into price_list 
        (name, unique_id, system_id, material_id, s1, s2, s3, price, calculation, calculation_bom)
         VALUES ('%s',%d,%d,%d,%d,%d,%d,%d,'%s','%s')""" % (y, 69, 4, 0, 0, 0, 0, 2580, 'C', 'C'))
    
    #x = "'Trio Base - Tube in Tube'" #Need X to be linked to Y
    #insert_param = (y, 69, 4, 0, 0, 0, 0, 2580, 'C', 'C')
    #cursor.execute(insert_str % insert_param)
    db.commit()
    cursor.close()
    db.close()
    return()

def del_auto_pl_360():
    auto_pl_list = auto_price_list.objects.all()
    auto_pl_list = auto_pl_list.exclude(spec_code__startswith = '102')
    auto_pl_list = auto_pl_list.exclude(spec_code__startswith = '103')
    for cur_auto_pl in auto_pl_list:
        item_master_list = item_master.objects.filter(imported_item_code__startswith = cur_auto_pl.spec_code)
        if len(item_master_list) == 0:
            db_crm_dict = crm_connect_data()
            db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                                  host=db_crm_dict['host'], port=db_crm_dict['port'])
            cursor = db.cursor()
            split_spec_code = []
            for cur_spec in cur_auto_pl.spec_code.split('-'):
                split_spec_code.append(int(cur_spec))
            cursor.execute("""select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d""" % tuple(split_spec_code))
            pl_360_obj = cursor.fetchall()
            if len(pl_360_obj) > 0:
                pl_360_obj = pl_360_obj[0]
                print(str(pl_360_obj[1]) + str(pl_360_obj[0]))
                cursor.execute("""select * from b_o_m where pl_id=%d""" % (int(pl_360_obj[0]),))
                print('BOM --- : ' + str(cursor.fetchall()))
                cursor.execute("""delete from b_o_m where pl_id=%d""" % (int(pl_360_obj[0]),))
                db.commit()
                cursor.execute("""select * from derivative where pl_id=%d""" % (int(pl_360_obj[0]),))
                derivative_set = cursor.fetchall()
                print('Derivative --- : ' + str(derivative_set))
                bom_2 = []
                for cur_der in derivative_set:
                    cursor.execute("""select * from b_o_m where derivative_id=%d""" % (int(cur_der[0]),))
                    bom_2 = cursor.fetchall()
                if len(bom_2) == 0:
                    cursor.execute("""delete from derivative where pl_id=%d""" % (int(pl_360_obj[0]),))
                    db.commit()
                    cursor.execute("""delete from price_list where id=%d""" % (int(pl_360_obj[0]),))
                    db.commit()
            cursor.close()
            db.close()
    return()

def auto_pl_match(auto_pl_id):
    auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
    spec_code = auto_pl_obj.spec_code
    split_spec_str = spec_code.split('-')
    split_spec_code = []
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                              host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    for cur_str in split_spec_str:
        split_spec_code.append(int(cur_str))
    cursor.execute("""select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d""" % tuple(split_spec_code))
    pl_360 = cursor.fetchall()
    match = True
    if len(pl_360) == 0:
        match = False
    cursor.close()
    db.close()
    return(match)

def del_crm_pl_bom_der(crm_pl_id):
    data = {}
    '''auto_pl_obj = get_object_or_404(auto_price_list, id = int(auto_pl_id))
    item_master_list = item_master.objects.filter(imported_item_code__startswith = auto_pl_obj.spec_code)
    
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                          host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    split_spec_code = []
    for cur_spec in auto_pl_obj.spec_code.split('-'):
        split_spec_code.append(int(cur_spec))
    cursor.execute("""select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d""" % tuple(split_spec_code))'''
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                          host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute("""select * from price_list where id=%d""" % (int(crm_pl_id),))
    crm_pl_obj = cursor.fetchall()
    data['del_status'] = False
    if len(crm_pl_obj) > 0:
        crm_pl_obj = crm_pl_obj[0]
        crm_pl_pk = int(crm_pl_obj[0])
        print(str(crm_pl_obj[1]) + str(crm_pl_obj[0]))
        cursor.execute("""select * from b_o_m where pl_id=%d""" % (crm_pl_pk,))
        print('BOM --- : ' + str(cursor.fetchall()))
        cursor.execute("""select * from derivative where pl_id=%d""" % (crm_pl_pk,))
        derivative_set = cursor.fetchall()
        print('Derivative --- : ' + str(derivative_set))
        bom_2 = []
        for cur_der in derivative_set:
            cursor.execute("""select * from b_o_m where derivative_id=%d""" % (int(cur_der[0]),))
            bom_2 = cursor.fetchall()
        if len(bom_2) == 0:
            cursor.execute("""delete from derivative where pl_id=%d""" % (crm_pl_pk,))
            db.commit()
            cursor.execute("""delete from b_o_m where pl_id=%d""" % (crm_pl_pk,))
            db.commit()
            cursor.execute("""delete from price_list where id=%d""" % (crm_pl_pk,))
            db.commit()
            data['del_status'] = True
    cursor.close()
    db.close()
    return(data)

def del_crm_pl_bom_der_erp(auto_pl_id):
    data = {}
    auto_pl_obj = get_object_or_404(auto_price_list, id = int(auto_pl_id))
    item_master_list = item_master.objects.filter(imported_item_code__startswith = auto_pl_obj.spec_code)
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                          host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    split_spec_code = []
    for cur_spec in auto_pl_obj.spec_code.split('-'):
        split_spec_code.append(int(cur_spec))
    cursor.execute("""select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d""" % tuple(split_spec_code))
    crm_pl_obj = cursor.fetchall()
    data['del_status'] = False
    if len(crm_pl_obj) > 0:
        data = del_crm_pl_bom_der(crm_pl_obj[0][0])
    cursor.close()
    db.close()
    return(data)


def redundant_auto_pl():
    auto_pl_set = auto_price_list.objects.all().order_by('spec_code')
    #auto_pl_set = auto_pl_set.filter(spec_code__startswith = '012')
    temp_auto_pl = auto_pl_set
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database = db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'],\
                              host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()    
    for cur_auto_pl in temp_auto_pl:
        if auto_pl_match(cur_auto_pl.id) == True:
            auto_pl_set = auto_pl_set.exclude(id = cur_auto_pl.id)
            print(str(cur_auto_pl.name) + ', ' + str(cur_auto_pl.flite_360_price_list_id) + ', ' + str(cur_auto_pl.spec_code))
    cursor.close()
    db.close()
    return(auto_pl_set)

def eval_test():
    str1 = '{"items":{"16573":{"2676":88,"sl":"01","n":"test part modifications","tid":9,"d":{"Name":"test"},"c":7616,"r":0}},"lyt":{"2676":"BOM PRICING TEST layout"},"lvy":{"1":{"Excise Duty":"12.36"},"2":{"Freight and Insurance":"5.00"},"3":{"VAT":"14.50"}},"oc":[],"pt":[],"ot":[]}'
    str2 = '{"items":{"16573":{"sl":"01","n":"test part modifications","tid":9,"d":{"Name":"test"},"2676":3,"c":19834,"r":null}},"lyt":{"2676":"BOM PRICING TEST layout"},"lvy":{"3":{"VAT":"14.50"},"2":{"Freight and Insurance":"5.00"},"1":{"Excise Duty":"12.36"}},"oc":[],"pt":[],"ot":[]}'
    x = ast.literal_eval(str1)
    y = ast.literal_eval(str2.replace(":null",":''"))
    return(x)

def name_filter_qry_builder(input_data):
    '''
    input_data = {'input_type':'!~', 'input':'abc!!xswfc~~vsdv!!cad'}
    other options of input type to be listed when needed and input to be fed accordingly
    '''
    data = {}
    filter_qry = "name ilike '%%'"
    exclude_qry = "name ilike ''"
    searched_str = input_data['input']
    name_filter_tup = searched_str.split('~~')
    name_filter_tup = name_filter_tup[0].split('!!')
    name_exclude_tup = ''
    name_exclude_tup = []
    if len(searched_str.split('~~')) > 1:
        name_exclude_tup = searched_str.split('~~')
        name_exclude_tup = name_exclude_tup[1].split('!!')
    for cur_name_filter in name_filter_tup:
        filter_qry += " and name ilike '%" + cur_name_filter + "%'"
    for cur_name_exclude in name_exclude_tup:
        exclude_qry += " and name ilike '%" + cur_name_exclude + "%'"
    data['filter_qry'] = filter_qry
    data['exclude_qry'] = exclude_qry
    return(data)
    
    
'''
planning module
ocn
style rate
buyer name
workorder
buyer rate
buyer date
ex-factory date
order qty
production qty
fabric type
'''