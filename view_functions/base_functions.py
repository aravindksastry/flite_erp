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
import ast
from decimal import *
import psycopg2, datetime
from db_links.database_connection import *
from nesting.nest_functions import *
from datetime import date, timedelta
from django.utils import timezone
import re
from django.db.models import Q

def get_coa(coa_grp_no):
    coa_grp = get_object_or_404(coa_group, coa_group_no = coa_grp_no)
    coa = coa_grp.coa_set.all().order_by('name')
    return(coa)

def select_boxes(sel_box_detail):
    ret = []
    if(sel_box_detail['name'] == 'vendor'):
        coa_grp_no = 2004
        ret = get_coa(coa_grp_no)
    elif(sel_box_detail['name'] == 'customer'):
        coa_grp_no = 1006
        ret = get_coa(coa_grp_no)
    elif(sel_box_detail['name'] == 'order_confirmation'):
        ttype_ref_no = 59
        ttype = get_object_or_404(transaction_type, transaction_type_ref_no = ttype_ref_no)
        ret = transaction_ref.objects.filter(transaction_type = ttype).order_by('name')
    elif(sel_box_detail['name'] == 'sale_invoice'):
        ttype_ref_no = 60
        ttype = get_object_or_404(transaction_type, transaction_type_ref_no = ttype_ref_no)
        ret = transaction_ref.objects.filter(transaction_type = ttype).order_by('name')
    elif(sel_box_detail['name'] == 'work_center'):
        ret = work_center.objects.all().order_by('name')
    elif(sel_box_detail['name'] == 'payment_terms'):
        ret = payment_terms.objects.all().order_by('name')
    elif(sel_box_detail['name'] == 'other_terms'):
        ret = other_terms.objects.all().order_by('name')
    elif(sel_box_detail['name'] == 'country'):
        ret = country.objects.all().order_by('name')
    elif(sel_box_detail['name'] == 'state'):
        ret = state.objects.all().order_by('name')
    elif(sel_box_detail['name'] == 'city'):
        ret = city.objects.all().order_by('name')
    elif(sel_box_detail['name'] == 'oc_item'):
        itm_grp = get_object_or_404(item_group, imported_unique = '102')
        ret = item_master.objects.filter(item_group = itm_grp).order_by('name')
    elif(sel_box_detail['name'] == 'tax_format'):
        ret = tax_format.objects.filter(active = True).order_by('name')
    elif(sel_box_detail['name'] == 'other_tax_format'):
        ret = tax_format.objects.filter(active = True, app_other_charges = True).order_by('name')
    elif(sel_box_detail['name'] == 'tpl_ref'):
        ttype_obj = get_object_or_404(transaction_type, transaction_type_ref_no = 2)
        ret = transaction_ref.objects.filter(transaction_type = ttype_obj, submit = True, active = True).order_by('name')
    elif(sel_box_detail['name'] == 'plant'):
        ret = plant.objects.all().order_by('name')
    else:
        ret = [('no select box definition')]
    return(ret)

def jour_index_add_param(inv_jour_id, param):
    inv_jour_obj = get_object_or_404(inventory_journal, id = inv_jour_id)
    if param == 'next_prod':
        '''output to be defined'''
    return()

def del_auto_pl(auto_pl_id):
    data = {}
    auto_pl_id = int(auto_pl_id)
    auto_pl_opt = auto_price_list.objects.filter(id = auto_pl_id)
    if len(auto_pl_opt) > 0:
        auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
        spec_code = auto_pl_obj.spec_code
        app_item_master = item_master.objects.filter(imported_item_code__startswith = spec_code)
        count = 0
        for cur_item_master in app_item_master:
            cur_item_master.delete()
            count += 1
        data['item_master_delete_count'] = count
        data['auto_pl_name'] = auto_pl_obj.name
        auto_pl_obj.delete()
    return(data)



def purge_pl(item_master_list):
    '''item_master_list = [(item_master_id1,qty1),(item_master_id1,qty2)....]'''
    item_dict = {}
    new_item_master_list = []
    for cur_item in item_master_list:
        item_id = cur_item[0]
        item_qty = cur_item[1]
        if item_id in item_dict:
            item_dict[item_id] += item_qty
        else:
            item_dict[item_id] = item_qty
    for item_id, item_qty in item_dict.items():
        new_item_master_list.append((item_id, item_qty))
    '''new_item_master_list = [(item_master_id1,qty1+qty2),(item_master_id1,qty3)....]'''
    return(new_item_master_list)

def conv_part_id_to_obj(list):
    '''
    list = [(id, qty), (part2_id, qty),......]
    '''
    obj_list = []
    for cur_part in list:
        part_obj = get_object_or_404(item_master, id = int(cur_part[0]))
        obj_list.append([part_obj, cur_part[1]])
    return(obj_list)
    
def cons_part_list(input_list):
    '''
    list = [(id, qty), (part2_id, qty),......]
    '''
    new_list = []
    for cur_part in list:
        index = [x for x, y in enumerate(input_list) if y[0] == cur_part.id]
        if len(index) == 0:
            new_list.append(list(cur_part))
        else:
            new_list[index[0]][1] += cur_part[1]
    return(new_list)

def bom_check(part_list):
    '''part_list = [(part1_id, qty), (part2_id, qty),......]'''
    ret = True
    for cur_part in part_list:
        cur_part_obj = item_master.objects.filter(id = cur_part[0])
        if len(cur_part_obj) == 0:
            ret = False
            break
        else:
            cur_part_obj = get_object_or_404(item_master, id=int(cur_part[0]))
            cur_bom_list = ast.literal_eval(cur_part_obj.bom)
            cur_imp_bom_list = ast.literal_eval(cur_part_obj.imported_bom)
            if not len(cur_bom_list) == len(cur_imp_bom_list):
                part_id_conversion([(cur_part_obj.imported_item_code, cur_part_obj.imported_item_finish, cur_part[1])])
                cur_part_obj = get_object_or_404(item_master, id=int(cur_part[0]))
                cur_bom_list = ast.literal_eval(cur_part_obj.bom)
            for cur_bom in cur_bom_list:
                cur_bom_obj = item_master.objects.filter(id = cur_bom[0])
                if len(cur_bom_obj) == 0:
                    part_id_conversion([(cur_part_obj.imported_item_code, cur_part_obj.imported_item_finish, cur_part[1])])
    return(ret)

def bom_multiplier(part_list, multi):
    '''part_list = [(part1_id, qty), (part2_id, qty),......]
    multi = float'''
    new_list = []
    for cur_part in part_list:
        new_app = list(cur_part)
        new_app[1] = round(cur_part[1] * float(multi), 2)
        new_list.append(new_app)
    return(new_list)

def collate_inf_bom(item_master_id):
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    dummy_list = ast.literal_eval(item_master_obj.bom)
    i = 0
    if bom_check(dummy_list) == False:
        infinite_update([[item_master_obj.imported_item_code, item_master_obj.imported_item_finish, 1.0]], True, {'auto_update':True})
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    dummy_list = ast.literal_eval(item_master_obj.bom)
    dummy_len = len(dummy_list)
    while i < dummy_len:
        #copy.deepcopy(
        cur_bom_id = dummy_list[i][0]
        cur_bom_qty = float(dummy_list[i][1])
        cur_item_obj = get_object_or_404(item_master, id = cur_bom_id)
        new_bom1 = ast.literal_eval(cur_item_obj.bom)
        if bom_check(new_bom1) == False:
            infinite_update([[item_master_obj.imported_item_code, item_master_obj.imported_item_finish, 1.0]], True, {'auto_update':True})
        cur_item_obj = get_object_or_404(item_master, id = cur_bom_id)
        new_bom1 = ast.literal_eval(cur_item_obj.bom)
        for cur_new_bom in new_bom1:
            new_bom_item_id = cur_new_bom[0]
            new_bom_qty = float(cur_new_bom[1]) * cur_bom_qty
            dummy_list.append([new_bom_item_id, new_bom_qty])
        dummy_len = len(dummy_list)
        i += 1
    new_list = purge_pl(dummy_list)
    return(new_list)

def composite_nest(input_list):
    '''
    input_list = [(id, qty), (part2_id, qty),......]
    '''
    feed_tare = []
    feed_boards = []
    new_rm_list = []
    new_ofct_list = []
    ret_dict = {}
    ret_dict['rm_list'] = new_rm_list
    if input_list == []:
        return(ret_dict)
    for cur_input in input_list:
        cur_part_obj = get_object_or_404(item_master, id=int(cur_input[0]))
        cur_part = (cur_part_obj.imported_item_code, cur_part_obj.imported_item_finish, cur_input[1])
        cur_part_unq = int(str(cur_part[0])[:3])
        print('cur_part_unq : ' + str(cur_part_unq))
        if cur_part_unq == 202 or cur_part_unq == 212 or cur_part_unq == 222:
            '''This Condition is not activated because the available raw material sizes are not added'''
            board_spec = cur_part[0][0:2] + '0' + cur_part[0][3:7] + '00' + cur_part[0][9:21]
            board_pl_obj = auto_price_list.objects.filter(spec_code = board_spec)
            if len(board_pl_obj) == 0:
                board_pl_obj = auto_price_list(spec_code = board_spec, name = description_gen(board_spec + '-0000-0000-0000-0000'))
                board_pl_obj.save()
            board_pl_obj = get_object_or_404(auto_price_list, spec_code = board_spec)
            """app_boards = board_pl_obj.available_rm_sizes_set.filter(exclude_size = False)
            
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
            """
            app_boards = board_pl_obj.available_rm_sizes_set.filter(exclude_size = False)
            for cur_board in app_boards:
                if board_pl_obj.spec_code[0:3] == '220':
                    place_h = divmod(cur_board.d1, int(str(cur_part[0])[22:26]))
                    place_v = divmod(cur_board.d1, int(str(cur_part[0])[27:31]))
                    '''Code has to be added to check if the fabric has grain direction for feeding
                    the right plate size - now assuming that grain doesn't matter'''
                    if place_h[1] < place_v[1]:
                        dim2 = int(str(cur_part[0])[27:31])
                    else:
                        dim2 = int(str(cur_part[0])[22:26])
                else:
                    dim2 = cur_board.d2
                board_pn = board_pl_obj.spec_code + '-' + str(10000 + cur_board.d1)[1:] + '-' + str(10000 + dim2)[1:] + '-' + \
                                        str(10000 + cur_board.d3)[1:] + '-' + str(10000 + cur_board.d4)[1:]
                board_fin = cur_part[1]
                feed_board_app = []
                board_pn_split = list(board_pn.split('-'))
                for cur_param in board_pn_split:
                    feed_board_app.append(int(cur_param))
                feed_board_app.append(str(board_fin))
                index = [i for i, v in enumerate(feed_boards) if v == tuple(feed_board_app)]
                if len(index) == 0:
                    feed_boards.append(tuple(feed_board_app))
            '''Eliminating the wastage value, hence making last 4 digits: 0000'''
            tare_pn = cur_part[0][:-4] + str('0000')
            tare_pn_split = list(tare_pn.split('-'))
            cur_feed_tare = []
            for cur_param in tare_pn_split:
                cur_feed_tare.append(int(cur_param))
            cur_feed_tare[2] = 0#get_grain_direction(tare_pn, str(cur_part[1]))
            cur_tare_fin = cur_part[1]
            cur_feed_tare.append(cur_tare_fin)
            cur_feed_tare.append(cur_part[2])
            feed_tare.append(tuple(cur_feed_tare))
        else:
            new_rm_list.append(cur_input)
    if len(feed_tare) > 0: 
        feed_board_qty = []
        for cur_board in feed_boards:
            cur_feed = list(cur_board)
            cur_feed.append(9999999)
            feed_board_qty.append(tuple(cur_feed))
        nest_result = comp_nest(feed_tare, feed_board_qty)
        for nest_key, nest_val in nest_result.items():
            if not nest_key == 'tare_summary':
                for cur_part in nest_val:
                    master_obj = item_master.objects.filter(imported_item_code = cur_part[0], imported_item_finish = cur_part[1])
                    if len(master_obj) == 0:
                        auto_update_item_master(cur_part[0], cur_part[1], cur_part[2])
                    master_obj = get_object_or_404(item_master, imported_item_code = cur_part[0], imported_item_finish = cur_part[1])
                    if nest_key == 'new_gen_offcut':
                        new_ofct_list.append((master_obj.id, cur_part[2]))
                    if nest_key == 'board_consumption':
                        new_rm_list.append((master_obj.id, cur_part[2]))
    ret_dict['rm_list'] = new_rm_list
    #ret_dict['new_ofct'] = new_ofct_list
    return(ret_dict)

def dict_search(dict, key, vals):
    '''dict = {}
    key = key in dictionary to hich value has to be searched
    vals = (param1, param2, param3....)
    '''
    available = False
    for cur_val in vals:
        if key in dict:
            if type(dict[key]) == tuple:
                '''If the data stored in tref_data is in the form of tuple, then it's a select box
                we cannot match closest string, we will have to match the exact ID
                '''
                if int(cur_val) == int(dict[key][0]):
                    available = True
                    break
            elif re.search(cur_val, dict[key], re.IGNORECASE):
                '''If the value of the given key is not tuple, it will be a string'''
                available = True
                break
    return(available)

def tref_field_search(tref, search_dict):
    '''search_dict = {'search_key1':('abc, 'rtf, 'asfv', ...), 'search_key2':('abc, 'rtf, 'asfv', ...), ....}'''
    tref_data = ast.literal_eval(tref.data)
    if not 'field_list' in tref_data:
        all_available = False
        return(all_available)
    tref_field_list = tref_data['field_list']
    all_available = True
    for search_key, search_vals in search_dict.items():
        if len(search_vals) > 0:
            available = dict_search(tref_field_list, search_key, search_vals)
            if available == False:
                all_available = False
                break
    return(all_available)

def tref_field_filter(tref_obj_list, search_dict):
    '''search_dict = {'search_key1':'search_val1','search_key2':'search_val2'....}'''
    new_tref_list = []
    for cur_key, cur_val in search_dict.items():
        if len(cur_val) > 0:
            search_dict[cur_key] = cur_val.split('!!')
        else:
            search_dict[cur_key] = ()
    for cur_key, cur_val in search_dict.items():
        for cur_str in cur_val:
            tref_obj_list = tref_obj_list.filter(data__icontains = cur_str)
    for cur_tref_obj in tref_obj_list:
        add_cur = tref_field_search(cur_tref_obj, search_dict)
        if add_cur == True:
            new_tref_list.append(cur_tref_obj)
    return(new_tref_list)

def filter_tref_with_item(tref_list, item_master_id):
    item_master_obj = get_object_or_404(item_master, id = int(item_master_id))
    new_tref_list = []
    for cur_tref in tref_list:
        cur_tref_obj = cur_tref[0]
        app_inv_jour_list = inventory_journal.objects.filter(transaction_ref = cur_tref_obj,\
                                                              item_master = item_master_obj, balance_qty__gt = 0)
        if len(app_inv_jour_list) > 0:
            new_tref_list.append(cur_tref)
    return(new_tref_list)

def filter_tref_with_tpl(tref_list, giv_tpl_ref_id):
    '''giv_tpl_ref_id must be equal to 0 if the mtrrefs pertaining to stock is to be filtered'''
    new_tref_list = []
    for cur_tref in tref_list:
        cur_tref_obj = cur_tref[0]
        app_inv_jour_list = inventory_journal.objects.filter(transaction_ref = cur_tref_obj, balance_qty__gt = 0)
        if giv_tpl_ref_id > 0:
            app_inv_jour_list = app_inv_jour_list.filter(tpl_ref_no = giv_tpl_ref_id)
        else:
            app_inv_jour_list = app_inv_jour_list.filter(Q(tpl_ref_no = 0) | Q(tpl_ref_no = None))
        if len(app_inv_jour_list) > 0:
            new_tref_list.append(cur_tref)
    return(new_tref_list)

def item_master_opt_name_filter(search_str):
    '''search_str = "abc!!def!!ghi~~jkl!!mno!!pqr....so on"'''
    main_tuple = search_str.split('~~')
    item_master_opt = []
    if len(main_tuple) > 0:
        filter_tuple = main_tuple[0].split('!!')
        item_master_opt = item_master.objects.all().order_by('name')
        for cur_filter_str in filter_tuple:
            item_master_opt = item_master_opt.filter(name__icontains = cur_filter_str)
        if len(main_tuple) == 2:
            exclude_tuple = main_tuple[1].split('!!')
            for cur_exclude_str in exclude_tuple:
                item_master_opt = item_master_opt.exclude(name__icontains = cur_exclude_str)
    return(item_master_opt)

def parent_tref_list(ttype_ids):
    debit_types = ast.literal_eval(str(ttype_ids))
    tref_list = []
    cur_tref_list = []
    inv_jour_list = []
    cur_inv_jour_list = []
    if(debit_types == (0,)):
        return(tref_list)
    for deb_type in debit_types:
        cur_ttype = transaction_type.objects.get(transaction_type_ref_no = deb_type)
        cur_tref_list = cur_ttype.transaction_ref_set.filter(active = True).order_by('-submit_date')
        for cur_debit_tref in cur_tref_list:
            tref_list.append((cur_debit_tref, ast.literal_eval(str(cur_debit_tref.data))))
            cur_inv_jour_list = cur_debit_tref.inventory_journal_set.exclude(balance_qty = 0)
    return(tref_list)#, inv_jour_list)

def real_parent_tref_list(tref):
    inv_jour_list = inventory_journal.objects.filter(transaction_ref = tref)
    act_tref_id_list = []
    act_tref_obj_list = []
    for cur_inv_jour in inv_jour_list:
        deb1_tref_id = 0
        deb2_tref_id = 0
        if cur_inv_jour.debit_journal1:
            deb1_tref_id = cur_inv_jour.debit_journal1.transaction_ref.id
        if cur_inv_jour.debit_journal2:
            deb2_tref_id = cur_inv_jour.debit_journal2.transaction_ref.id
        if deb1_tref_id > 0 and not deb1_tref_id in act_tref_id_list:
            act_tref_id_list.append(deb1_tref_id)
        if deb2_tref_id > 0 and not deb2_tref_id in act_tref_id_list:
            act_tref_id_list.append(deb2_tref_id)
    if tref.chain_tref > 0:
        act_tref_id_list.append(tref.chain_tref)
    act_tref_id_list.sort()
    for cur_tref_id in act_tref_id_list:
        act_tref_obj_list.append(get_object_or_404(transaction_ref, id = cur_tref_id))
    return(act_tref_obj_list)

def live_tpl_list():
    '''transaction_type ref no 37 refers to dispatch note'''
    disp_note_ttype = get_object_or_404(transaction_type, transaction_type_ref_no = 37)
    disp_note_tref_list = transaction_ref.objects.filter(transaction_type = disp_note_ttype, active = True)
    tpl_id_list = []
    for cur_disp_note in disp_note_tref_list:
        if not cur_disp_note.chain_tref in tpl_id_list:
            tpl_id_list.append(cur_disp_note.chain_tref)
    tpl_id_list.sort()
    tpl_obj_list = []
    for cur_tpl_id in tpl_id_list:
        cur_tpl_obj = get_object_or_404(transaction_ref, id = cur_tpl_id)
        tpl_obj_list.append((cur_tpl_obj, {'tpl_data':ast.literal_eval(cur_tpl_obj.data)}))
    return(tpl_obj_list)

def update_basic_rate_inv_jour(tref):
    print('Updating Inventory Journal Rate')
    ttype = tref.transaction_type
    trule = ttype.transaction_rule
    trule_data = ast.literal_eval(trule.data)
    fetch_type = 'automatic'
    if 'rate' in trule_data['attrib_list']:
        fetch_type = trule_data['attrib_list']['rate'][1]
    inv_jour_set = inventory_journal.objects.filter(transaction_ref = tref)
    tref_data = ast.literal_eval(str(tref.data))
    tax_calc = []
    '''
    [{'tax_head_no':'value','':'','':''....},{'':'','':'',...}....]
    9840037028 - kamesh
    7200005637 - tech pvt. ltd.
    '''
    tax_similar = 1
    if inv_jour_set:
        pre_tax = inv_jour_set[0].tax_format
        tax_consolidate = {}
        basic_total = float(0)
        for cur_inv_jour in inv_jour_set:
            if fetch_type == 'automatic':
                '''no modification from existing rate'''
            elif fetch_type == 'none':
                cur_inv_jour.rate = 0
            elif fetch_type == 'debit1_taxed_rate':
                cur_inv_jour.rate = cur_inv_jour.debit_journal1.taxed_rate
            elif fetch_type == 'debit1_stock_rate':
                deb1_tpl_ref_no = cur_inv_jour.debit_journal1.tpl_ref_no
                deb1_location_obj = get_object_or_404(location, id = int(cur_inv_jour.debit_journal1.location_ref_val))
                deb1_stk_obj = get_object_or_404(current_stock, location_ref = deb1_location_obj, tpl_ref_no = deb1_tpl_ref_no, \
                                                 item_master_ref = cur_inv_jour.item_master)
                cur_inv_jour.rate = deb1_stk_obj.cur_rate
            elif fetch_type == 'debit2_stock_rate':
                if cur_inv_jour.debit_journal2:
                    deb2_tpl_ref_no = cur_inv_jour.debit_journal2.tpl_ref_no
                    deb2_location_obj = get_object_or_404(location, id = int(cur_inv_jour.debit_journal2.location_ref_val))
                    deb2_stk_obj = get_object_or_404(current_stock, location_ref = deb2_location_obj, tpl_ref_no = deb2_tpl_ref_no, \
                                                     item_master_ref = cur_inv_jour.item_master)
                    cur_inv_jour.rate = deb2_stk_obj.cur_rate
                else:
                    cur_inv_jour.rate = Decimal(0)
            elif fetch_type == 'parent_special_rate':
                cur_inv_jour.rate = cur_inv_jour.debit_journal1.special_rate
            elif fetch_type == 'purchase_price':
                vendor_id = tref_data['field_list']['vendor'][0]
                vendor_obj = get_object_or_404(coa, id = vendor_id)
                app_vendor_pl = vendor_price.objects.filter(vendor = vendor_obj, item = cur_inv_jour.item_master)
                pur_rate = 0.0
                if len(app_vendor_pl) == 1:
                    vendor_pl_obj = app_vendor_pl[0]
                    pur_rate = vendor_pl_obj.purchase_rate
                cur_inv_jour.rate = pur_rate
            elif fetch_type == 'job_work_price':
                vendor_id = tref_data['field_list']['vendor'][0]
                vendor_obj = get_object_or_404(coa, id = vendor_id)
                jw_rate = 0.0
                app_vendor_pl = vendor_price.objects.filter(vendor = vendor_obj, item = cur_inv_jour.item_master)
                if len(app_vendor_pl) == 1:
                    vendor_pl_obj = app_vendor_pl[0]
                    jw_rate = vendor_pl_obj.job_work_rate
                cur_inv_jour.rate = jw_rate
            elif fetch_type == 'work_center_price':
                shop_order_id = tref_data['field_list']['work_center'][0]
                work_center_obj = get_object_or_404(work_center, id = shop_order_id)
                shop_order_rate = 0.0
                app_work_center_pl = work_center_price.objects.filter(work_center = work_center_obj, item = cur_inv_jour.item_master)
                if len(app_work_center_pl) == 1:
                    wc_pl_obj = app_work_center_pl[0]
                    shop_order_rate = wc_pl_obj.rate
                cur_inv_jour.rate = shop_order_rate
            elif fetch_type == 'sale_price':
                cur_inv_jour.rate = cur_inv_jour.item_master.bom_sale_price
            elif fetch_type == 'allocation_rate':
                cur_inv_jour.rate = 6
            cur_inv_jour_rate = float(cur_inv_jour.rate)
            cur_inv_jour_disc = float(cur_inv_jour.discount)
            cur_inv_jour_sur = float(cur_inv_jour.surcharge)
            cur_special_rate = cur_inv_jour_rate * (1 - cur_inv_jour_disc/100) + cur_inv_jour_sur
            cur_iss_qty = float(cur_inv_jour.issue_qty)
            cur_inv_jour.special_rate = cur_special_rate
            cur_inv_jour.value = cur_special_rate * cur_iss_qty
            cur_inv_jour.save()
            cur_tax_format_data = ast.literal_eval(str(cur_inv_jour.tax_format.data))
            cur_inv_jour_data = {}
            #cur_inv_jour.save()
            cur_inv_jour = get_object_or_404(inventory_journal, id = cur_inv_jour.id)
            basic_total += float(cur_inv_jour.value)
            cur_inv_jour_data['tax_format'] = cur_tax_format_data['apply']
            cur_inv_jour.data = cur_inv_jour_data
            cur_inv_jour.save()
    tref_data['basic_total'] = float(basic_total)
    tref.data = tref_data
    tref.save()
    return(float(basic_total))

def tax_apply(base_value, tax_format_data, tax_consolidate):
    '''
    base_value is the valule on which the taxes have to be applied
    tax_format_data = [(tax_head1,(tax_rate1, additional_value1),(parent_heads,...)), (tax_head2,(tax_rate2, additional_value2),(parent_heads,...))]
    tax_consolidate = {tax_head1:tot_val1, tax_head2:tot_val2...} - this can also be empty {}
    '''
    data = {}
    tax_calc = {}
    new_valuation = float(base_value)
    tax_total = float(0)
    for cur_tax in tax_format_data:
        parent_total = float(0)
        '''cur_tax = (tax_head,(tax_rate, additional_value),(parent_heads,...))'''
        for cur_parent in cur_tax[2]:
            if cur_parent == '':
                parent_total += float(base_value)
            else:
                '''abc'''
                parent_total += float(tax_calc[cur_parent])
        tax_calc[cur_tax[0]] = float(round(Decimal(parent_total)*Decimal(cur_tax[1][0])/100, 2) + round(Decimal(cur_tax[1][1]), 2))
        if(cur_tax[0] in tax_consolidate):
            tax_consolidate[cur_tax[0]] += tax_calc[cur_tax[0]]
        else:
            tax_consolidate[cur_tax[0]] = tax_calc[cur_tax[0]]
    for cur_tax_key, cur_tax_val in tax_calc.items():
        cur_tax_obj = get_object_or_404(tax_head, id = int(cur_tax_key))
        tax_total += float(cur_tax_val)
        if cur_tax_obj.add_to_valuation == True:
            new_valuation += float(cur_tax_val)
    data['new_valuation'] = float(round(new_valuation, 2))
    data['sum_total'] = base_value + round(tax_total, 2)
    data['tax_total'] = round(tax_total, 2)
    data['tax_split'] = tax_calc
    data['tax_consolidate'] = tax_consolidate
    return(data)

def update_inv_jour_rate(tref):
    print('Updating Inventory Journal Rate')
    ttype = tref.transaction_type
    trule = ttype.transaction_rule
    trule_data = ast.literal_eval(trule.data)
    fetch_type = 'none'
    if 'rate' in trule_data['attrib_list']:
        fetch_type = trule_data['attrib_list']['rate'][1]
    inv_jour_set = inventory_journal.objects.filter(transaction_ref = tref)
    tref_data = ast.literal_eval(str(tref.data))
    tax_calc = []
    '''
    [{'tax_head_no':'value','':'','':''....},{'':'','':'',...}....]
    9840037028 - kamesh
    7200005637 - tech pvt. ltd.
    '''
    tax_similar = 1
    if inv_jour_set:
        pre_tax = inv_jour_set[0].tax_format
        tax_consolidate = {}
        grand_total = Decimal(0)
        basic_total = update_basic_rate_inv_jour(tref)
        '''reseting inv++jour_set as rates & data may have got updated in the function update_basic_rate_inv_jour'''
        tref = get_object_or_404(transaction_ref, id=tref.id)
        tref_data = ast.literal_eval(str(tref.data))
        inv_jour_set = inventory_journal.objects.filter(transaction_ref = tref)
        base_with_osur = basic_total + float(tref.overall_surcharge)
        if basic_total == 0:
            osur_hike = float(0)
        else:
            osur_hike = float(round(base_with_osur / basic_total, 2))
        taxed_valuation_sum = float(0)
        '''all the inventory journal's values are to be hiked up before totaling
        for tax application, this ratio of hiking is the osur hike'''
        for cur_inv_jour in inv_jour_set:
            cur_inv_jour_data = ast.literal_eval(str(cur_inv_jour.data))
            cur_tax_format_data = cur_inv_jour_data['tax_format']
            if cur_inv_jour.tax_format != pre_tax:
                tax_similar = 0
            pre_tax = cur_inv_jour.tax_format
            cur_inv_jour_data = {}
            cur_inv_jour.save()
            cur_base_val = float(cur_inv_jour.value) * osur_hike
            cur_iss_qty = float(cur_inv_jour.issue_qty)
            tax_apply_data = tax_apply(cur_base_val, cur_tax_format_data, tax_consolidate)
            cur_inv_jour = get_object_or_404(inventory_journal, id = cur_inv_jour.id)
            cur_inv_jour_data['tax_format'] = cur_tax_format_data
            cur_inv_jour.tax_split = tax_apply_data['tax_split']
            tax_consolidate = tax_apply_data['tax_consolidate']
            cur_inv_jour.data = cur_inv_jour_data
            if cur_iss_qty == 0:
                cur_taxed_rate = float(0)
            else:
                cur_taxed_rate = float(round(tax_apply_data['new_valuation'] / cur_iss_qty, 2))
            cur_inv_jour.taxed_rate = cur_taxed_rate
            cur_inv_jour.taxed_value = tax_apply_data['new_valuation']
            taxed_valuation_sum += tax_apply_data['new_valuation']
            cur_inv_jour.save()
            tax_calc.append(tax_apply_data['tax_split'])
        tref_data['tax_summary'] = []
        print('Tax Consolidate : ' + str(tax_consolidate))
        if tax_similar == 1:
            for cur_tax in cur_inv_jour_data['tax_format']:
                tref_data['tax_summary'].append((cur_tax[0], \
                                                 get_object_or_404(tax_head, tax_head_no = cur_tax[0]).name, \
                                                 '@ ' + str(cur_tax[1][0]) + ' %',str(tax_consolidate[cur_tax[0]])))
        else:
            tax_head_ordered = tax_head.objects.order_by('tax_head_no')
            for cur_tax_head in tax_head_ordered:
                if cur_tax_head.tax_head_no in tax_consolidate:
                    tref_data['tax_summary'].append((cur_tax_head.tax_head_no, cur_tax_head.name,'@ ' + '*varies*' + ' % ', \
                                                     str(tax_consolidate[cur_tax_head.tax_head_no])))
        '''for val_sum in tref_data['value_summary']:
            grand_total += Decimal(val_sum[3])'''
        taxed_total = float(base_with_osur)
        for cur_tax_sum in tref_data['tax_summary']:
            taxed_total += float(cur_tax_sum[3])
        tref_data['taxed_total'] = taxed_total
        #taxed_with_other_tot = taxed_total + float(tref.other_charge)
        other_tax_data = ast.literal_eval(tref.other_charge_tax_ref.data)
        tref_data['other_tax_format'] = other_tax_data['apply']
        other_tax_apply_data = tax_apply(float(tref.other_charge), tref_data['other_tax_format'], {})
        tref_data['other_tot'] = other_tax_apply_data['sum_total']
        if taxed_valuation_sum == 0:
            ochar_hike = float(0)
        else:
            ochar_hike = float(round((other_tax_apply_data['new_valuation'] + taxed_valuation_sum) / taxed_valuation_sum, 2))
        grand_total = tref_data['taxed_total'] + tref_data['other_tot']
        tref_data['grand_total'] = float(round(grand_total, 2))
        inv_jour_set = inventory_journal.objects.filter(transaction_ref = tref)
        for cur_inv_jour in inv_jour_set:
            cur_iss_qty = float(cur_inv_jour.issue_qty)
            new_taxed_value = float(cur_inv_jour.taxed_value) * ochar_hike
            if cur_iss_qty == 0:
                new_taxed_rate = float(0)
            else:
                new_taxed_rate = new_taxed_value / cur_iss_qty
            cur_inv_jour.taxed_rate = new_taxed_rate
            cur_inv_jour.taxed_value = new_taxed_value
            cur_inv_jour.save()
    tref.data = tref_data
    tref.save()
    return()

def get_location_raw(sel_box_name, app_id):
    '''sel_box_name is one that's registered in the function select_boxes
    app_id is an id that is primary key of one of the rows in the table matching to the 
    short hand select_box_name in the select_boxex function'''
    loc_type_qset = select_boxes({'name':sel_box_name})
    loc_obj = loc_type_qset.filter(id = app_id)
    if len(loc_obj) == 0:
        return('error')
    loc_type_obj = location_type.objects.filter(short_hand = sel_box_name)
    if len(loc_type_obj) == 0:
        new_loc_type = location_type(short_hand = sel_box_name, name = sel_box_name)
        new_loc_type.save()
    loc_type_obj = get_object_or_404(location_type, short_hand = sel_box_name)
    app_location = location.objects.filter(location_type_ref = loc_type_obj, ref_no = app_id)
    if len(app_location) == 0:
        new_location = location(location_type_ref = loc_type_obj, ref_no = app_id)
        new_location.save()
    location_obj = get_object_or_404(location, location_type_ref = loc_type_obj, ref_no = app_id)
    return(location_obj)

def trace_location(tref_id):
    '''nothing yet'''
    tref_obj = get_object_or_404(transaction_ref, id = tref_id)
    ttype_obj = tref_obj.transaction_type
    trule_obj = ttype_obj.transaction_rule
    tref_data = ast.literal_eval(tref_obj.data)
    ttype_data = ast.literal_eval(tref_obj.transaction_type.data)
    trule_data = ast.literal_eval(trule_obj.data)
    if 'location_trace_type' in ttype_data:
        trace_type = ttype_data['location_trace_type']
    else:
        if trule_data['code'] == 3 or trule_data['code'] == 6:
            trace_type = 'debit1'
        else:
            trace_type = 'default_plant'
    '''in case the location_trace is plant_stock we consider ref_no as 1 - hejjala plant'''
    if trace_type == 'default_plant':
        location_ref_id = 1 #value of 1 corresponds to hejjala plant in plant table
        location_obj = get_location_raw('plant', location_ref_id)
    elif trace_type == 'debit1':
        location_obj = 'debit1'
    elif trace_type == 'debit2':
        location_obj = 'debit2'
    elif trace_type == 'job_order_nested_rm' or trace_type == 'job_order_components' or trace_type == 'job_order_dc':
        job_order_process_tref = get_object_or_404(transaction_ref, id = int(tref_obj.chain_tref))
        job_order_data = ast.literal_eval(job_order_process_tref.data)
        job_order_vendor_id = int(job_order_data['field_list']['vendor'][0])
        location_obj = get_location_raw('vendor', job_order_vendor_id)
    elif trace_type == 'shop_order_nested_rm' or trace_type == 'shop_order_components' or trace_type == 'shop_order_mo':
        shop_order_process_tref = get_object_or_404(transaction_ref, id = int(tref_obj.chain_tref))
        shop_order_data = ast.literal_eval(shop_order_process_tref.data)
        shop_order_wc_id = int(shop_order_data['field_list']['work_center'][0])
        location_obj = get_location_raw('work_center', shop_order_wc_id)
    elif trace_type == 'self_vendor':
        vendor_id = int(tref_data['field_list']['vendor'][0])
        location_obj = get_location_raw('vendor', vendor_id)
    elif trace_type == 'self_work_center':
        work_center_id = int(tref_data['field_list']['work_center'][0])
        location_obj = get_location_raw('work_center', work_center_id)
    else:
        return('error')
    return(location_obj)

def credit_location_tref(tref_id):
    tref_obj = get_object_or_404(transaction_ref, id=int(tref_id))
    tref_data = ast.literal_eval(tref_obj.data)
    ttype = tref_obj.transaction_type
    ttype_ref_no = ttype.transaction_type_ref_no
    ttype_data = ast.literal_eval(ttype.data)
    if 'stock_credit' in ttype_data:
        cr_location_obj = trace_location(tref_id)
        """loc_ref_trace_type = ttype_data['location_trace_type']
        if loc_ref_trace_type == 'self_inward_location':
            loc_short_hand = 'plant'
            location_ref_val = tref_data['field_list']['inward_location'][0]
        if loc_ref_trace_type == 'default_plant':
            '''all allocations from material inward will happen to default plant location only'''
            loc_short_hand
            location_ref_val = 1
        cr_location_obj = get_location_raw(loc_short_hand, location_ref_val)"""
        return(cr_location_obj)
    return()

def get_stock(item_master_id, tpl_ref_no, sel_box_name, app_id):
    '''sel_box_name is one that's registered in the function select_boxes
    app_id is an id that is primary key of one of the rows in the table matching to the 
    short hand select_box_name in the select_boxex function
    tpl_ref_no is another filtering parameter in calculating the applicable stock
    '''
    app_stk = []
    tot_stk = 0
    location_obj = get_location_raw(sel_box_name, app_id)
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    if location_obj == 'error':
        return('error')
    else:
        app_stk = current_stock.objects.filter(item_master_ref = item_master_obj, location_ref = location_obj, tpl_ref_no = tpl_ref_no)
    for cur_stk in app_stk:
        tot_stk += float(cur_stk.cur_stock)
    return(tot_stk)


def get_all_stock_data(item_master_id, tpl_ref_no):
    item_master_obj = get_object_or_404(item_master, id = item_master_id)
    data = {}
    '''
    plant_location_type = 1
    work_center_location_type = 2
    vendor_location_type = 3
    location_types = ['plant', 'work_center', 'vendor']
    '''
    
    all_loc_types = location_type.objects.all()
    for cur_loc_type in all_loc_types:
        cur_loc_type_stk = current_stock.objects.filter(item_master_ref = item_master_obj, \
                                                 tpl_ref_no = tpl_ref_no, location_ref__location_type_ref = cur_loc_type)
        tot_stk = 0
        for cur_stk in cur_loc_type_stk:
            tot_stk += cur_stk.cur_stock
        data[cur_loc_type.short_hand] = tot_stk
    '''data = {'plant':123, 'vendor':123, 'work_center':123}'''
    return(data)

def replace_item_master(old_item_master_id, new_item_master_id):
    '''Please note that this is an extremely risky function to call'''
    old_item_obj = get_object_or_404(item_master, id=old_item_master_id)
    new_item_obj = get_object_or_404(item_master, id=new_item_master_id)
    old_spec_code = old_item_obj.imported_item_code
    new_spec_code = new_item_obj.imported_item_code
    old_vendor_price = vendor_price.objects.filter(item = old_item_obj)
    new_vendor_price = vendor_price.objects.filter(item = new_item_obj)
    if len(new_vendor_price) == 0:
        for cur_vendor_price in old_vendor_price:
            cur_vendor_price.item = new_item_obj
            cur_vendor_price.save()
    else:
        for cur_vendor_price in old_vendor_price:
            cur_vendor_price.delete()
    old_work_center_price = work_center_price.objects.filter(item = old_item_obj)
    new_work_center_price = work_center_price.objects.filter(item = new_item_obj)
    if len(new_work_center_price) == 0:
        for cur_work_center_price in old_work_center_price:
            cur_work_center_price.item = new_item_obj
            cur_work_center_price.save()
    else:
        for cur_work_center_price in old_work_center_price:
            cur_work_center_price.delete()
    old_stock = current_stock.objects.filter(item_master_ref = old_item_obj)
    new_stock = current_stock.objects.filter(item_master_ref = new_item_obj)
    if len(new_vendor_price) == 0:
        for cur_stock in old_stock:
            cur_stock.item_master_ref = new_item_obj
            cur_stock.save()
    else:
        for cur_stock in old_stock:
            cur_stock.delete()
    old_inv_jour = inventory_journal.objects.filter(item_master = old_item_obj)
    new_inv_jour = inventory_journal.objects.filter(item_master = new_item_obj)
    if len(new_inv_jour) == 0:
        for cur_inv_jour in old_inv_jour:
            cur_inv_jour.item_master = new_item_obj
            cur_inv_jour.save()
    else:
        for cur_inv_jour in old_inv_jour:
            cur_inv_jour.delete()
    old_item_master = item_master.objects.filter(Q(bom__icontains=str(old_item_obj.id))|Q(imported_bom__icontains=str(old_spec_code)))
    for cur_item_master in old_item_master:
        bom = cur_item_master.bom
        new_bom = bom.replace(str(old_item_master_id), str(new_item_master_id))
        imported_bom = cur_item_master.imported_bom
        new_imported_bom = imported_bom.replace(str(old_spec_code), str(new_spec_code))
        cur_item_master.bom = new_bom
        cur_item_master.imported_bom = new_imported_bom
        cur_item_master.save()
    old_item_obj.delete()
    return()

def pagination_detail(data, result_list, entries):
    '''data is the dictionary going into the template
    resultlist is the overall result from view
    entries is the no. of entries to be shown in the template'''
    data['result_tot'] = len(result_list)
    i = 1
    data['page_range'] = []
    while i <= math.ceil(data['result_tot']/entries):
        data['page_range'].append(i)
        i += 1 
    return(data)

def vendor_jw_rate_update(loop_items, pl_obj, sel_vendor_obj):
    for cur_item_master in loop_items:
        vendor_pl_opt = vendor_price.objects.filter(item = cur_item_master, vendor = sel_vendor_obj)
        if len(vendor_pl_opt) > 0:
            cur_vendor_pl = get_object_or_404(vendor_price, item = cur_item_master, vendor = sel_vendor_obj)
        else:
            cur_vendor_pl = vendor_price(item = cur_item_master, vendor = sel_vendor_obj)
            cur_vendor_pl.save()
        cur_vendor_pl = get_object_or_404(vendor_price, item = cur_item_master, vendor = sel_vendor_obj)
        new_jw_rate = float(pl_obj.job_work_rate)
        rate_diff = float(cur_vendor_pl.job_work_rate) - new_jw_rate
        if rate_diff < 1 or rate_diff < -1:
            jw_rate_his = ast.literal_eval(cur_vendor_pl.jw_rate_history)
            jw_rate_his.append({'dt':str(timezone.now()), 'rate':float(new_jw_rate)})
            cur_vendor_pl.jw_rate_history = jw_rate_his
        cur_vendor_pl.job_work_rate = pl_obj.job_work_rate
        cur_vendor_pl.job_work_tax_format = pl_obj.job_work_tax_format
        cur_vendor_pl.last_updated = timezone.now()
        cur_vendor_pl.save()
    return()

def wc_rate_update(loop_items, pl_obj, sel_work_center_obj):
    for cur_item_master in loop_items:
        work_center_pl_opt = work_center_price.objects.filter(item = cur_item_master, work_center = sel_work_center_obj)
        if len(work_center_pl_opt) > 0:
            cur_work_center_pl = get_object_or_404(work_center_price, item = cur_item_master, work_center = sel_work_center_obj)
        else:
            cur_work_center_pl = work_center_price(item = cur_item_master, work_center = sel_work_center_obj)
            cur_work_center_pl.save()
        cur_work_center_pl = get_object_or_404(work_center_price, item = cur_item_master, work_center = sel_work_center_obj)
        new_jw_rate = float(pl_obj.rate)
        rate_diff = float(cur_work_center_pl.rate) - new_jw_rate
        if rate_diff < 1 or rate_diff < -1:
            wc_rate_his = ast.literal_eval(cur_work_center_pl.rate_history)
            wc_rate_his.append({'dt':str(timezone.now()), 'rate':new_jw_rate})
        cur_work_center_pl.rate_history = wc_rate_his
        cur_work_center_pl.rate = pl_obj.rate
        cur_work_center_pl.last_updated = timezone.now()
        cur_work_center_pl.save()
    return()

def html_to_excel_format(table_body, table_header):
    data = {}
    table_list = []
    table_header_list = []
    for cur_row in table_body:
        list_table = []
        for cur_row_val in cur_row:
            row_val = str(cur_row_val['val'])
            list_table.append(row_val)
        table_list.append(list_table)
    for cur_header_row in table_header:
        for cur_row_val in cur_header_row:
            row_val = str(cur_row_val['val'])
            table_header_list.append(row_val)
    data['table_body'] = table_list
    data['table_header'] = table_header_list
    return(data)

def gen_excel_export(data, work_sheet):#workbook):
    '''
    data = {
    'sheet_name':'string'
    'co_ordinate':(start_row, start_col)
    'header':[col1 name, col2 name.....]
    'body':[(r1c1_data, r1c2_data, r1c3_data...), (r2c1_data, r2c2_data, r2c3_data...),....]
    'col_width':[23, 52, 57, 74....]
    'conditional_format_type':'recognizable string'
    'merge_data':[(r1, c1, r2, c2), (r1, c1, r2, c2), .....(r1, c1, r2, c2)] all integer values - relative input
    'format_header':[1:col1_format, 2:col2_format, 3:col3_format,...]
    'format_body':[1:col1_format, 2:col2_format, 3:col3_format,...]
    'default_format':default_format
    }
    '''
    #east = workbook.add_worksheet(data['sheet_name'])
    col_head_format = {}
    col_body_format = {}
    east = work_sheet
    default_format = data['default_format']
    if not 'format_header' in data:
        data['format_header'] = {}
    if not 'format_body' in data:
        data['format_body'] = {}
    start_row = data['co_ordinate'][0]
    start_col = data['co_ordinate'][1]
    max_head_wid = max(map(len, data['header']))
    max_body_wid = max(map(len, data['body']))
    if max_head_wid > max_body_wid:
        tab_width = max_head_wid
    else:
        tab_width = max_body_wid
    i = 0
    while i < tab_width:
        
        if 'col_width' in data:
            try:
                data['col_width'][i]
            except:
                '''no column setting'''
            else:
                east.set_column(i, i, data['col_width'][i])
        if i in data['format_header']:
            col_head_format[i] = data['format_header'][i]
        else:
            col_head_format[i] = default_format
        if i in data['format_body']:
            col_body_format[i] = data['format_body'][i]
        else:
            col_body_format[i] = default_format
        i += 1
    #write(0, 0, 'Hello, world!')
    row = start_row
    col = start_col
    i = 0
    for cur_header in data['header']:
        east.write_string(row, col, cur_header, col_head_format[i])
        col += 1
        i += 1
    row = start_row + 1
    col = start_col
    for cur_row in data['body']:
        col = start_col
        for cur_cell in cur_row:
            east.write(row, col, cur_cell, col_body_format[i])
            col += 1
        row += 1
    if 'merge_data' in data:
        for cur_mer_data in data['merge_data']:
            rel_mer_st_row = cur_mer_data[0]
            rel_mer_st_col = cur_mer_data[1]
            rel_mer_end_row = cur_mer_data[2]
            rel_mer_end_col = cur_mer_data[3]
            mer_st_row = rel_mer_st_row + start_row
            mer_st_col = rel_mer_st_col + start_col
            mer_end_row = rel_mer_end_row + start_row
            mer_end_col = rel_mer_end_col + start_col
            if mer_st_row == start_row:
                merge_dat = data['header'][rel_mer_st_col]
            else:
                merge_dat = data['body'][rel_mer_st_row-1][rel_mer_st_col] 
                '''-1 is is added (subtracted) because the row data starts from row 1 while the array ccount starts from 0'''
            work_sheet.merge_range(mer_st_row, mer_st_col, mer_end_row, mer_end_col, merge_dat, default_format)
            #work_sheet.merge_range(1, 1, 1, 4, 'abcd', default_format)
    
    '''bg_green = workbook.add_format({'bg_color': '#00CC00', 'font_color': '#000000'})
    bg_yellow = workbook.add_format({'bg_color': '#FFFF00', 'font_color': '#000000'})
    bg_red = workbook.add_format({'bg_color': '#FF0000', 'font_color': '#000000'})
    bg_black = workbook.add_format({'bg_color': '#000000', 'font_color': '#FFFFFF'})
    if 'conditional_format_type' in data:
        if data['conditional_format_type'] == 'bpr':
            range = 'N2:N' + str(len(data['body'])+1)
            east.conditional_format(range, {'type': 'cell',
                                         'criteria': 'between',
                                         'minimum':-33.99,
                                         'maximum':0.0,
                                         'format': bg_green})
            east.conditional_format(range, {'type': 'cell',
                                         'criteria': 'between',
                                         'minimum':-66.99,
                                         'maximum':-33.99,
                                         'format': bg_yellow})
            east.conditional_format(range, {'type': 'cell',
                                         'criteria': 'between',
                                         'minimum':-99.0,
                                         'maximum':-67.99,
                                         'format': bg_red})
            east.conditional_format(range, {'type': 'cell',
                                         'criteria': '<=',
                                         'value':-100.0,
                                         'format': bg_black})
    #workbook.close()
    '''
    
    
    '''self.send_response(200)
    self.send_header('Content-Disposition', 'attachment; filename=test.xlsx')
    self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    self.end_headers()
    self.wfile.write(output.read())'''
    
    return()

def db_select_query_gen(data):
    query_type = data['query_type']
    table = data['table']
    filters = data['filters']
    exclusions = data['exclusions']
    ordering = data['ordering']
    
    if query_type == 'select':
        ret_query = 'select * from %s where %s and not %s'
    return()


