from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpRequest
from journal_mgmt.models import *
from django.template import RequestContext, loader
from django.views import generic
from django.core.urlresolvers import reverse
import ast, copy
from decimal import *
from journal_mgmt.view_functions.view_functions import *
from journal_mgmt.view_functions.connect_functions import *
from journal_mgmt.view_functions.report_functions import *
from journal_mgmt.view_functions.base_functions import *
from journal_mgmt.view_functions.file_location import *
from journal_mgmt.forms import *
from report_export.main import *
import psycopg2, datetime
from psycopg2 import extras
from django.utils import timezone
from db_links.database_connection import *
import math, os
from datetime import datetime, timedelta
import json
from django.db.models import Q
from django.shortcuts import render_to_response
from reportlab.pdfgen import canvas
import reportlab
from encodings.utf_8 import encode
from django.utils.encoding import smart_str
from json.encoder import JSONEncoder
from django.core.context_processors import media
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout 



# from journal_mgmt.models import project

# need to try with mongo db
# Create your views here.

def test_http(request):
    # return HttpResponse("test")
    data = {}
    output = {}
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    data = {}
    if x_forwarded_for:
        data['ip'] = x_forwarded_for.split(',')[0]
    else:
        data['ip'] = request.META.get('REMOTE_ADDR')
    if(request.POST):
        '''xyz'''
        data = 'POSTED'
        data = request.POST
    else:
        data['test_data'] = 1 / 47
        output = data
    # data = quote_pl.objects.all()
    return render(request, 'journal_mgmt/test_response.html', {'data': data})
    # return HttpResponse("abcd")
def login_page(request):
    data = {}
    data['referer'] = request.META.get('HTTP_REFERER')
    if request.POST:
        post_data = request.POST
    return render(request, 'journal_mgmt/login.html', {'data': data})

def login_authenticate(request):
    data = {}
    post_data = request.POST
    user = authenticate(username=post_data['username'], password=post_data['password'])
    if user is not None:
        # the password verified for the user
        if user.is_active:
            print("User is valid, active and authenticated")
            login(request, user)
            return HttpResponseRedirect(reverse('journal_mgmt:home'))
        else:
            print("The password is valid, but the account has been disabled!")
            return HttpResponseRedirect(reverse('core:login'))
    else:
        # the authentication system was unable to verify the username and password
        print("The username and password were incorrect.")
        return HttpResponseRedirect(reverse('journal_mgmt:login'))
	
'''def home_generic(request):
    data = {}
    data['ttype'] = transaction_type.objects.all().order_by('name')
    data['coa_group'] = coa_group.objects.all().order_by('name')
    data['coa'] = coa.objects.all().order_by('name')
    return render(request, 'journal_mgmt/home.html', {'data': data})'''
	
def home(request):
    data = {}
    dept = ttype_department.objects.all().order_by('name')
    dept = dept.exclude(id=1)
    dept_data = []
    for cur_dept in dept:
        dept_data.append((cur_dept, ast.literal_eval(cur_dept.data)))
    data['dept_data'] = dept_data
    return render(request, 'journal_mgmt/home.html', {'data': data})

def home_view(request, dept_id):
    data = {}
    ttype_all = transaction_type.objects.all().order_by('name')
    ttype_data_all = []
    for cur_ttype_all in ttype_all:
        ttype_data_all.append((cur_ttype_all,))
    data['ttype_data_all'] = ttype_data_all
    ttype = transaction_type.objects.filter(ttype_department_ref=dept_id).order_by('name')
    ttype_data = []
    ttype_data_grouped = []
    cur_group = []
    prev_alpha = ''
    for cur_ttype in ttype:
        print('transactionType : ' + str(cur_ttype.name) + ' data : ' + str(cur_ttype.data))
        ttype_data.append((cur_ttype, ast.literal_eval(cur_ttype.data)))
        if not prev_alpha == cur_ttype.name[0]:
            prev_alpha = cur_ttype.name[0]
            if not cur_group == []:
                ttype_data_grouped.append(cur_group)
            cur_group = []
            cur_group.append(prev_alpha)
        cur_group.append((cur_ttype, ast.literal_eval(cur_ttype.data)))
    if len(ttype) > 0:
        ttype_data_grouped.append(cur_group)
    data['ttype_data'] = ttype_data
    data['ttype_data_grouped'] = ttype_data_grouped
    dept = ttype_department.objects.all().order_by('name')
    dept = dept.exclude(id=1)
    data['chosen_dept'] = get_object_or_404(ttype_department, id=int(dept_id))
    dept_data = []
    for cur_dept in dept:
        dept_data.append((cur_dept, ast.literal_eval(cur_dept.data)))
    data['dept_data'] = dept_data
    return render(request, 'journal_mgmt/home_view.html', {'data': data})

def tref_index(request, ttype_id):
    data = {}
    data['status_filter'] = ''
    data['searched_name'] = ''
    data['searched_data'] = ''
    data['select_boxes'] = []
    data['index_params'] = []
    ttype = get_object_or_404(transaction_type, id=int(ttype_id))
    data['ttype'] = ttype
    ttype_data = ast.literal_eval(ttype.data)
    data['ttype_data'] = ttype_data
    for cur_field in ttype_data['field_list']:
        if 'search' in cur_field[3] and cur_field[1] == 'select':
            data['select_boxes'].append((cur_field[2], select_boxes({'name':cur_field[2]})))
        if 'index' in cur_field[3]:
            data['index_params'].append(cur_field[3]['name'])
    tref_list = transaction_ref.objects.filter(transaction_type=ttype_id).order_by('-submit_date')
    tref_list = tref_list.exclude(force_close=True)
    tref_list = tref_list.exclude(submit=True, active=False)
    if request.GET or request.POST:
        dsearch = {}
        if request.GET:
            source_data = request.GET
            get_data = source_data
        else:
            source_data = request.POST
            post_data = source_data
        
        if 'searched_name' in source_data:
            searched_name = source_data['searched_name']
            data['searched_name'] = searched_name
            searched_name_split = searched_name.split('!!')
            for cur_str in searched_name_split:
                tref_list = tref_list.filter(name__icontains=cur_str)
                
        if 'status_filter' in source_data:
            status_filter = source_data['status_filter']
            data['status_filter'] = status_filter
            if data['status_filter'] == 'show_all':
                '''do nothing - no filter'''
            else:
                data['active'] = False
                data['submit'] = False
                data['force_close'] = False
                if data['status_filter'] == 'show_draft':
                    data['active'] = False
                    data['submit'] = False
                    data['force_close'] = False
                elif data['status_filter'] == 'show_active':
                    data['active'] = True
                    data['submit'] = True
                    data['force_close'] = False
                tref_list = transaction_ref.objects.filter(transaction_type=ttype_id, name__icontains=source_data['searched_name'], active=data['active'], \
                                                    submit=data['submit'], force_close=data['force_close'])
        '''Searching for data search parameters in source data'''
        for cur_field in ttype_data['field_list']:
            cur_ds_key = 'ds_' + cur_field[3]['name']
            if 'search' in cur_field[3] and cur_ds_key in source_data:
                dsearch[cur_field[3]['name']] = source_data[cur_ds_key]
        data['dsearch'] = dsearch
        feed_search = {}
        '''But before actually executing the search - we remove parameters whihc have '*All*' as search value'''
        for search_key, search_val in dsearch.items():
            if not search_val == '*All*':
                feed_search[search_key] = search_val
        tref_list = tref_field_filter(tref_list, feed_search)
    tref_obj_list = []
    for cur_tref in tref_list:
        tref_obj_list.append((cur_tref, ast.literal_eval(cur_tref.data)))
    data['object_list'] = tref_obj_list
    ttype = get_object_or_404(transaction_type, pk=ttype_id)
    data['pre_filter_param'] = {'ttype':ttype}
    '''for charms''' 
    ttype_shrt_cut = transaction_type.objects.filter(ttype_department_ref=ttype.ttype_department_ref).order_by('name')
    ttype_charm = []
    for cur_ttype in ttype_shrt_cut:
        ttype_charm.append((cur_ttype, ast.literal_eval(cur_ttype.data)))
    data['ttype_charm'] = ttype_charm
    dept = get_object_or_404(ttype_department, id=int(ttype.ttype_department_ref.id))
    data['dept_data'] = dept
    data['dept_logo'] = ast.literal_eval(dept.data)
    if request.GET:
        get_data = request.GET
        response_obj = HttpResponse()
        response_obj['Content-Disposition'] = 'attachment; filename=shipment_bom.xlsx'
        response_obj['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response_obj['Cache-Control'] = 'no-cache'
        '''response_obj.write(output.read())'''
        return response_obj
    return render(request, 'journal_mgmt/tref_index.html', {'data': data})

def tref_detail(request, tref_id):
    tref = get_object_or_404(transaction_ref, pk=tref_id)
    data = {}
    data['object'] = tref
    data['id'] = data['object'].id
    data['name'] = data['object'].name
    data['ref_no'] = data['object'].ref_no
    data['active'] = data['object'].active
    data['submit'] = data['object'].submit
    data['force_close'] = data['object'].force_close
    data['debit_transaction1'] = (data['object'].debit_transaction1)
    sel_debit_tref1 = data['debit_transaction1']
    data['debit_transaction2'] = (data['object'].debit_transaction2)
    data['debit_transaction3'] = (data['object'].debit_transaction3)
    data['inv_jour'] = inv_jour_list(tref)
    data['trule_data'] = ast.literal_eval(tref.transaction_type.transaction_rule.data)
    data['trule_data1'] = ast.literal_eval(tref.transaction_type.transaction_rule.data1)
    data['trule_data2'] = ast.literal_eval(tref.transaction_type.transaction_rule.data2)
    tpl_ref_type = data['trule_data']['attrib_list']['tpl_ref'][1]
    data['item_master_opt'] = []
    data['debit_item_master_opt'] = []
    sel_debit_tpl_ref = '*All*'
    app_data = fetch_tref_data(data['object'].transaction_type, tref, {})
    for cur_app in app_data:
        data[cur_app] = app_data[cur_app]
    if(request.POST):
        post_data = request.POST
        if 'load' in post_data:
            data['load_inv_jour'] = True  # post_data['load']
            sel_debit_tref_id = post_data['sel_debit_tref1']
            try:
                int(sel_debit_tref_id)
            except:
                '''do nothing'''
            else:
                debit_tref1 = get_object_or_404(transaction_ref, id=sel_debit_tref_id)
                inv_jour_config = {'filter_type':'none'}
                if 'load_filter' in post_data:
                    inv_jour_config = post_data['load_filter']
                data['inv_jour_debit1_opt'] = inv_jour_load_list(tref, debit_tref1)
                data['inv_jour_load_list'] = data['inv_jour_debit1_opt']
                # data['inv_jour_debit2_opt'] = inv_jour_load_list(tref, tref.debit_transaction2)
        data['redirect_name'] = ''
        data['redirect_data'] = ''
        data['redirect_status'] = ''
        if 'redirect_name' in post_data:
            data['redirect_name'] = post_data['redirect_name']
        if 'redirect_data' in post_data:
            data['redirect_data'] = post_data['redirect_data']
        if 'redirect_status' in post_data:
            data['redirect_status'] = post_data['redirect_status']
        detail_redirect_str = '?redirect_name=' + str(post_data['redirect_name']) + \
                     '&redirect_data=' + str(post_data['redirect_data']) + '&redirect_status=' + str(post_data['redirect_status'])
        '''This code gets active when ttype code is 1'''
        if 'item_search_str' in post_data:
            raw_search_str = post_data['item_search_str']
            data['item_search_str'] = raw_search_str
            split_search_str = raw_search_str.split('!!')
            data['item_master_opt'] = item_master.objects.filter(name__icontains=split_search_str[0])
            if len(split_search_str) == 0:
                data['item_master_opt'] = []
            else:
                for cur_str in split_search_str:
                    data['item_master_opt'] = data['item_master_opt'].filter(name__icontains=cur_str)
                data['item_master_opt'] = data['item_master_opt'].order_by('name')
        '''This code gets active when ttype code is 3 or 6'''
        if 'debit_item_search_str' in post_data:
            if len(post_data['debit_item_search_str']) > 3:
                data['debit_item_search_str'] = post_data['debit_item_search_str']
                data['debit_item_master_opt'] = item_master_opt_name_filter(data['debit_item_search_str'])
        if 'debit_item_master' in post_data:
            try:
                int(post_data['debit_item_master'])
            except:
                data['sel_debit_item_master'] = post_data['debit_item_master']
            else:
                sel_deb_im_id = int(post_data['debit_item_master'])
                data['sel_debit_item_master'] = get_object_or_404(item_master, id=sel_deb_im_id)
                '''debit transaction options can be filtered only if a selected 
                item still exists in the drop down after changing the search string'''
                item_available = data['debit_item_master_opt'].filter(id=data['sel_debit_item_master'].id)
                if len(item_available) > 0:
                    data['debit_transaction1_opt'] = filter_tref_with_item(data['debit_transaction1_opt'], sel_deb_im_id)
        if 'sel_debit_tpl_ref' in post_data:
            sel_debit_tpl_ref = post_data['sel_debit_tpl_ref']
            try:
                int(sel_debit_tpl_ref)
            except:
                data['sel_debit_tpl_ref'] = sel_debit_tpl_ref
            else:
                sel_debit_tpl_ref = int(sel_debit_tpl_ref)
                data['sel_debit_tpl_ref'] = sel_debit_tpl_ref
                data['debit_transaction1_opt'] = filter_tref_with_tpl(data['debit_transaction1_opt'], sel_debit_tpl_ref)
        if 'sel_tpl_ref' in post_data:
            data['sel_tpl_ref'] = int(post_data['sel_tpl_ref'])
        if 'sel_debit_tref1' in post_data:
            try:
                int(post_data['sel_debit_tref1'])
            except:
                '''do nothing'''
            else:
                sel_debit_tref1 = get_object_or_404(transaction_ref, id=int(post_data['sel_debit_tref1']))
                data['sel_debit_tref1'] = sel_debit_tref1
                data['inv_jour_debit1_opt'] = inv_jour_load_list(tref, sel_debit_tref1)
                data['debit_item_search_str'] = post_data['debit_item_search_str']
                if len(post_data['debit_item_search_str']) > 3:
                    data['debit_item_master_opt'] = item_master_opt_name_filter(data['debit_item_search_str'])
                # data['inv_jour_debit1_opt'] = debit1_jour_list(tref.id, sel_debit_tref1.id)
        if('_add_inv_jour' in post_data):
            if(post_data['inventory_journal_set-add-issue_qty']):
                if(float(post_data['inventory_journal_set-add-issue_qty']) > 0):
                    if(('inventory_journal_set-add-item_master' in post_data) and (post_data['inventory_journal_set-add-item_master'] != '-')):
                        tpl_ref_no = int(post_data['sel_tpl_ref'])
                        add_item_master_id = int(post_data['inventory_journal_set-add-item_master'])
                        add_item_master_qty = float(post_data['inventory_journal_set-add-issue_qty'])
                        inv_jour_create(tref, (add_item_master_id, add_item_master_qty, {}), tpl_ref_no)
                    elif(('inventory_journal_set-add-debit_journal1' in post_data) and (post_data['inventory_journal_set-add-debit_journal1'] != '-')):
                        add_inv_jour_id = int(post_data['inventory_journal_set-add-debit_journal1'])
                        add_inv_jour_qty = float(post_data['inventory_journal_set-add-issue_qty'])
                        inv_jour_create(tref, (add_inv_jour_id, add_inv_jour_qty, {}), tpl_ref_type)
                update_inv_jour_rate(tref)
            inv_jour_config = {'filter_type':'none'}
            data['inv_jour'] = inv_jour_list(tref)
    return render(request, 'journal_mgmt/tref_detail.html', {'data': data})
    

def tref_detail_popup(request, tref_id):
    tref = get_object_or_404(transaction_ref, pk=tref_id)
    data = {}
    data['object'] = tref
    data['id'] = data['object'].id
    data['name'] = data['object'].name
    data['ref_no'] = data['object'].ref_no
    data['active'] = data['object'].active
    data['submit'] = data['object'].submit
    data['force_close'] = data['object'].force_close
    data['debit_transaction1'] = (data['object'].debit_transaction1)
    sel_debit_tref1 = data['debit_transaction1']
    data['debit_transaction2'] = (data['object'].debit_transaction2)
    data['debit_transaction3'] = (data['object'].debit_transaction3)
    data['inv_jour'] = inventory_journal.objects.filter(transaction_ref=tref).order_by('name')
    data['trule_data'] = ast.literal_eval(tref.transaction_type.transaction_rule.data)
    data['trule_data1'] = ast.literal_eval(tref.transaction_type.transaction_rule.data1)
    data['trule_data2'] = ast.literal_eval(tref.transaction_type.transaction_rule.data2)
    tpl_ref_type = data['trule_data']['attrib_list']['tpl_ref'][1]
    # data['inv_jour'] = inventory_journal.objects.filter(transaction_ref = 4)
    app_data = fetch_tref_data(data['object'].transaction_type, tref, {})
    for cur_app in app_data:
        data[cur_app] = app_data[cur_app]
    if(request.GET):
        get_data = request.GET
        if 'load' in get_data:
            data['load_inv_jour'] = get_data['load']
            sel_debit_tref_id = get_data['sel_debit_tref1']
            try:
                int(sel_debit_tref_id)
            except:
                '''do nothing'''
            else:
                debit_tref1 = get_object_or_404(transaction_ref, id=sel_debit_tref_id)
                inv_jour_config = {'filter_type':'none'}
                if 'load_filter' in get_data:
                    inv_jour_config = get_data['load_filter']
                data['inv_jour_debit1_opt'] = inv_jour_load_list(tref, debit_tref1)
                data['inv_jour_load_list'] = data['inv_jour_debit1_opt']
                # data['inv_jour_debit2_opt'] = inv_jour_load_list(tref, tref.debit_transaction2)
        data['redirect_name'] = ''
        data['redirect_data'] = ''
        data['redirect_status'] = ''
        if 'redirect_name' in get_data:
            data['redirect_name'] = get_data['redirect_name']
        if 'redirect_data' in get_data:
            data['redirect_data'] = get_data['redirect_data']
        if 'redirect_status' in get_data:
            data['redirect_status'] = get_data['redirect_status']
        detail_redirect_str = '?redirect_name=' + str(get_data['redirect_name']) + \
                     '&redirect_data=' + str(get_data['redirect_data']) + '&redirect_status=' + str(get_data['redirect_status'])
        if 'item_search_str' in get_data:
            raw_search_str = get_data['item_search_str']
            data['item_search_str'] = raw_search_str
            split_search_str = raw_search_str.split('!!')
            data['item_master_opt'] = item_master.objects.filter(name__icontains=split_search_str[0])
            for cur_str in split_search_str:
                data['item_master_opt'] = data['item_master_opt'].filter(name__icontains=cur_str)
            data['item_master_opt'] = data['item_master_opt'].order_by('name')
        if 'sel_debit_tref1' in get_data:
            sel_debit_tref1 = get_object_or_404(transaction_ref, id=int(get_data['sel_debit_tref1']))
            data['sel_debit_tref1'] = sel_debit_tref1
            data['inv_jour_debit1_opt'] = inv_jour_load_list(tref, sel_debit_tref1)
            # data['inv_jour_debit1_opt'] = debit1_jour_list(tref.id, sel_debit_tref1.id)
        if('_add_inv_jour' in get_data):
            if(get_data['inventory_journal_set-add-issue_qty']):
                if(int(get_data['inventory_journal_set-add-issue_qty']) > 0):
                    if(('inventory_journal_set-add-item_master' in get_data) and (get_data['inventory_journal_set-add-item_master'] != '-')):
                        tpl_ref_no = 0
                        if tpl_ref_type == 'manual':
                            tpl_ref_no = int(get_data['inventory_journal_set-add-tpl_ref_no'])
                        add_item_master_id = int(get_data['inventory_journal_set-add-item_master'])
                        add_item_master_qty = float(get_data['inventory_journal_set-add-issue_qty'])
                        inv_jour_create(tref, (add_item_master_id, add_item_master_qty, {}), tpl_ref_no)
                    elif(('inventory_journal_set-add-debit_journal1' in get_data) and (get_data['inventory_journal_set-add-debit_journal1'] != '-')):
                        add_inv_jour_id = int(get_data['inventory_journal_set-add-debit_journal1'])
                        add_inv_jour_qty = float(get_data['inventory_journal_set-add-issue_qty'])
                        inv_jour_create(tref, (add_inv_jour_id, add_inv_jour_qty, {}), 'debit1')
                update_inv_jour_rate(tref)
            inv_jour_config = {'filter_type':'none'}
            data['inv_jour'] = inv_jour_list(tref)
    return render(request, 'journal_mgmt/tref_detail_popup.html', {'data': data})

def tref_create(request, ttype_id):
    ttype = get_object_or_404(transaction_type, pk=ttype_id)
    data = {}
    data['ttype_data'] = ast.literal_eval(ttype.data)
    data['id'] = ''
    # data['transaction_type'] = ttype
    '''Old Method - not to be used'''
    data['name'] = str(data['ttype_data']['short_hand']) + "_draft"
    data['ref_no'] = ttype.last_ref_no + 1
    data['active'] = False
    data['submit'] = False
    data['force_close'] = False
    app_data = fetch_tref_data(ttype, [], {})
    if(request.GET):
        get_data = request.GET 
        if 'deb1' in get_data:
            data['deb1'] = int(get_data['deb1'])
        if 'redirect_name' in get_data:
            data['redirect_name'] = get_data['redirect_name']
        if 'redirect_data' in get_data:
            data['redirect_data'] = get_data['redirect_data']
        if 'redirect_status' in get_data:
            data['redirect_status'] = get_data['redirect_status']
    for cur_app in app_data:
        data[cur_app] = app_data[cur_app]
    # return render(request, 'journal_mgmt/test_response.html', {'data': data})
    return render(request, 'journal_mgmt/tref_detail.html', {'data': data})

def inv_jour_delete(request, inv_jour_id):
    inv_jour = get_object_or_404(inventory_journal, pk=inv_jour_id)
    if not inv_jour.transaction_ref.submit == True:
        inv_jour.delete()
    return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(inv_jour.transaction_ref.id,)))

def inv_jour_bulk_create(request):
    post_data = request.POST
    prefix = "add_inventory_journal_set-"
    parent_bal1 = {}
    error = []
    test = 0
    tref = get_object_or_404(transaction_ref, pk=int(post_data['pk']))
    if 'no_load' in post_data:
        return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(tref.id,)))
    ttype = tref.transaction_type
    trule = ttype.transaction_rule
    trule_data = ast.literal_eval(trule.data)
    cur_inv_jour = inventory_journal.objects.filter(transaction_ref=tref)
    if(len(cur_inv_jour) != 0):
        error.append(('Items already exist for the selected Transaction Reference'))
    if (error == []):
        i = 1
        while (i < 1000):
            cur_jour_id = prefix + str(i) + "-debit_journal1"
            if(cur_jour_id in post_data):
                if(trule_data['code'] == 3 or trule_data['code'] == 6):
                    add_iss_qty = float(post_data[prefix + str(i) + "-issue_qty"])
                    add_bal_qty = float(post_data[prefix + str(i) + "-balance_qty"])
                    if(add_iss_qty > add_bal_qty):
                        parent_inv_jour_id = post_data[prefix + str(i) + "-debit_journal1"]
                        parent_inv_jour = get_object_or_404(inventory_journal, id=parent_inv_jour_id)
                        error.append((parent_inv_jour.name, "Available Balance:", parent_inv_jour.balance_qty, \
                                      "Issued Qty:", post_data[prefix + str(i) + "-issue_qty"]))
                elif(trule_data['code'] == 1):
                    '''Error Conditions to be listed here for manual list'''
                    continue
            else:
                break
            i += 1
    # return render(request, 'journal_mgmt/test_response.html', {'data': error})
    i = 1
    if (error == []):
        while (i < 1000):
            cur_jour_id = prefix + str(i) + "-id"
            if(cur_jour_id in post_data):
                if(trule_data['code'] == 3 or trule_data['code'] == 6):
                    parent_jour_id = int(post_data[prefix + str(i) + "-debit_journal1"])
                    parent_inv_jour = get_object_or_404(inventory_journal, id=parent_jour_id)
                    issue_qty = float(post_data[prefix + str(i) + "-issue_qty"])
                    # cur_inv_jour = inventory_journal(name=parent_inv_jour.name, item_master=parent_inv_jour.item_master, issue_qty=post_data[prefix + str(i) + "-issue_qty"], debit_journal1=parent_inv_jour, transaction_ref=tref)
                    inv_jour_create(tref, (parent_inv_jour.id, issue_qty, {}), 'debit1')
                elif(trule_data['code'] == 1):
                    '''Save method for auto load - creation list to be worked out - work includes template modification accordingly'''
                    add_item_master_id = post_data['inventory_journal_set-add-item_master']
                    add_issue_qty = post_data['inventory_journal_set-add-issue_qty']
                    inv_jour_create(tref, (add_item_master_id, add_issue_qty, {}), 0)
            else:
                break
            i += 1
        update_inv_jour_rate(tref)
    return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(tref.id,)))
    
def inv_jour_add(request):
    if (request.POST):
        post_data = request.POST
        data = {}
        data['debit_transaction1'] = (data['object'].debit_transaction1)
        sel_debit_tref1 = data['debit_transaction1']
        tref = get_object_or_404(transaction_ref, pk=int(post_data['pk']))
        detail_redirect_str = '?redirect_name=' + str(post_data['redirect_name']) + \
                         '&redirect_data=' + str(post_data['redirect_data']) + '&redirect_status=' + str(post_data['redirect_status'])
        if('_add_inv_jour' in post_data):
            if(post_data['inventory_journal_set-add-issue_qty']):
                if(int(post_data['inventory_journal_set-add-issue_qty']) > 0):
                    if(('inventory_journal_set-add-item_master' in post_data) and \
                       (post_data['inventory_journal_set-add-item_master'] != '-')):
                        posted_item_id = int(post_data['inventory_journal_set-add-item_master'])
                        posted_qty = post_data['inventory_journal_set-add-issue_qty']
                        inv_jour_create(tref, (posted_item_id, posted_qty, {}), 0)
                    elif(('inventory_journal_set-add-debit_journal1' in post_data) and \
                         (post_data['inventory_journal_set-add-debit_journal1'] != '-')):
                        posted_jour_id = int(post_data['inventory_journal_set-add-debit_journal1'])
                        posted_qty = post_data['inventory_journal_set-add-issue_qty']
                        inv_jour_create(tref, (posted_jour_id, posted_qty), 'debit1')
                update_inv_jour_rate(tref)
            return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(tref.id,)) + detail_redirect_str)
    
def tref_save(request):
    if(request.POST):
        post_data = request.POST
        ttype = get_object_or_404(transaction_type, pk=post_data['transaction_type'])
        ttype_data = ast.literal_eval(str(ttype.data))
        trule = ttype.transaction_rule
        trule_data = ast.literal_eval(trule.data)
        trule = ttype.transaction_rule.transaction_rule_code
        tref_data = {}
        redirect_name = ''
        redirect_data = ''
        redirect_status = ''
        if 'redirect_name' in post_data:
            redirect_name = post_data['redirect_name']
        if 'redirect_data' in post_data:
            redirect_data = post_data['redirect_data']
        if 'redirect_status' in post_data:
            redirect_status = post_data['redirect_status']
        print('Collating Field List data - Post Data : ' + str(post_data) + ' ttype_data : ' + str(ttype_data['field_list']))
        tref_data['field_list'] = field_list_collate(post_data, ttype_data['field_list'])
        # return render(request, 'journal_mgmt/test_response.html', {'data': tref_data})
        index_redirect_str = '?searched_name=' + redirect_name + '&searched_data=' + redirect_data + '&index_filter=' + redirect_status
        detail_redirect_str = '?searched_name=' + redirect_name + '&searched_data=' + redirect_data + '&index_filter=' + redirect_status        
        if(post_data['pk'].isdigit()):
            tref = get_object_or_404(transaction_ref, pk=int(post_data['pk']))
            # return render(request, 'journal_mgmt/test_response.html', {'data': tref_data})
            if 'force_close' in post_data:
                tref.force_close = True
                tref.active = False
                tref.save()
                return HttpResponseRedirect(reverse('journal_mgmt:tref_index', args=(ttype.id,)) + index_redirect_str)
            if tref.submit == False:
                tref.name = post_data['name']
                tref.transaction_type = ttype
                tref.ref_no = post_data['ref_no']
                tref.ref_name = post_data['ref_name']
                if 'overall_surcharge_remark' in post_data:
                    tref.overall_surcharge_remark = post_data['overall_surcharge_remark']
                    tref.overall_surcharge = post_data['overall_surcharge']
                if 'other_charge_remark' in post_data:
                    tref.other_charge_remark = post_data['other_charge_remark']
                    tref.other_charge = post_data['other_charge']
                    other_charge_tax_obj = get_object_or_404(tax_format, id=int(post_data['other_charge_tax']))
                    tref.other_charge_tax_ref = other_charge_tax_obj
                tref.data = tref_data
                error = inv_jour_bulk_save(post_data)
                # return HttpResponse("abcd")
                '''check if current transaction_ref has inventory journal, else save debit_transaction1'''
                cur_inv_jour = tref.inventory_journal_set.all()
                if(len(cur_inv_jour) == 0):
                    if('debit_transaction1' in post_data):
                        debit_tref1 = get_object_or_404(transaction_ref, pk=post_data['debit_transaction1'])
                        tref.debit_transaction1 = debit_tref1
                tref.save()
                # return(render(request, 'journal_mgmt/test_response.html', {'data': tref_data}))
                if(error == []):
                    update_inv_jour_rate(tref)
                    if 'allocate' in post_data:
                        allocate_list(tref.id)
                        return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(tref.id,)) + detail_redirect_str)
                    if('submit' in post_data and len(cur_inv_jour) > 0):
                        tref = tref_submit(tref.id)
                else:
                    return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(tref.id,)) + detail_redirect_str)
                
            if('_continue' in post_data):
                return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(tref.id,)) + detail_redirect_str)
            elif('_addanother' in post_data):
                return HttpResponseRedirect(reverse('journal_mgmt:tref_create', args=(ttype.id,)) + detail_redirect_str)
            else:
                return HttpResponseRedirect(reverse('journal_mgmt:tref_index', args=(ttype.id,)) + index_redirect_str)
        else:
            tref = auto_create_tref(ttype.transaction_type_ref_no, tref_data, [], False, {})
            tref_id = tref.id
            tref.name = post_data['name'] + '_' + str(tref_id)
            tref.ref_no = post_data['ref_no']
            if('debit_transaction1' in post_data):
                debit_tref1 = get_object_or_404(transaction_ref, pk=post_data['debit_transaction1'])
                tref.debit_transaction1 = debit_tref1
            tref.save()
            '''Need to increase the last_ref_no in the transaction_type table after saving transaction_ref
                because we had added the ref no while rendering the create form'''
            if('_continue' in post_data):
                # return HttpResponseRedirect(reverse('journal_mgmt:test_response', args=()))
                return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(tref_id,)))
            else:
                return HttpResponseRedirect(reverse('journal_mgmt:tref_index', args=(ttype.id,)))
    return HttpResponseRedirect(reverse('journal_mgmt:test_response', args=()))
def tree_test(request):
    data = 0
    return render(request, 'journal_mgmt/tree_test.html', {'data': data})


def coa_group_create(request, parent_coa_group_id):
    data = {}
    data['parent_coa_group'] = get_object_or_404(coa_group, id=parent_coa_group_id)
    return render(request, 'journal_mgmt/coa_group_detail.html', {'data': data})


def coa_group_detail(request, coa_group_id):
    data = {}
    data['coa_group'] = get_object_or_404(coa_group, id=coa_group_id)
    return render(request, 'journal_mgmt/coa_group_detail.html', {'data': data})


def coa_create(request, coa_group_id):
    data = {}
    data = fetch_coa_data(int(coa_group_id), [])
    return render(request, 'journal_mgmt/coa_detail.html', {'data': data})

def coa_detail(request, coa_id):
    data = {}
    ch_of_ac = get_object_or_404(coa, id=coa_id)
    data = fetch_coa_data(ch_of_ac.coa_group.id, ch_of_ac)
    return render(request, 'journal_mgmt/coa_detail.html', {'data': data})

def coa_index(request, coa_group_id):
    data = {}
    coa_grp = get_object_or_404(coa_group, id=coa_group_id)
    data['coa_group'] = (coa_grp, ast.literal_eval(coa_grp.data))
    data['coa_list'] = coa_list(coa_grp)
    return render(request, 'journal_mgmt/coa_index.html', {'data': data})

def coa_save(request):
    post_data = request.POST
    coa_grp = get_object_or_404(coa_group, pk=int(post_data['coa_group']))
    coa_grp_data = ast.literal_eval(coa_grp.data)
    coa_data = {}
    coa_data['field_list'] = field_list_collate(post_data, coa_grp_data['field_list'])
    if(post_data['pk'].isdigit()):
        ch_of_ac = get_object_or_404(coa, pk=post_data['pk'])
    else:
        max_coa_no = int(str(coa_grp.coa_set.all().order_by('-coa_no')[0].coa_no)[4:])
        new_coa_no = int(str(coa_grp.coa_group_no) + str(max_coa_no + 1))
        print('New COA No. - ' + str(new_coa_no))
        ch_of_ac = coa(coa_group=coa_grp)
        ch_of_ac.coa_no = new_coa_no
    ch_of_ac.name = post_data['name']
    ch_of_ac.data = coa_data
    ch_of_ac.save()
    return HttpResponseRedirect(reverse('journal_mgmt:coa_index', args=(coa_grp.id,)))

def coa_and_group_index(request):
    data = {}
    data['tree'] = []
    return render(request, 'journal_mgmt/coa_and_group_index.html', {'data': data})

def pdf_view(request):
    data = {}
    site_path = get_site_path()
    if(request.GET):
        get_data = request.GET
        if('tref_id' in get_data):
            tref_id = int(get_data['tref_id'])
            tref_obj = get_object_or_404(transaction_ref, id=tref_id)
            django_integrate(tref_id)
            file_location = site_path + 'media/documents/auto_pl/preview/view_pdf.pdf'
            data['location'] = file_location
            return HttpResponseRedirect('///media/documents/auto_pl/preview/view_pdf.pdf')

def pdf_response(request):
    # Create the HttpResponse object with the appropriate PDF headers.
    '''site_path = get_site_path()
    if(request.GET):
        get_data = request.GET
        if('tref_id' in get_data):
            tref_id = int(get_data['tref_id'])
            tref_obj = get_object_or_404(transaction_ref, id = tref_id)
            django_integrate(tref_id)
            file_location = site_path + 'report_export/view_pdf.pdf'
            file_name = tref_obj.name
            course = Courses.objects.get(pk = id)
            path_to_file = get_path_to_course_download(course)
        
            response = HttpResponse(mimetype='application/force-download')
            response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(file_name)
            response['X-Sendfile'] = smart_str(path_to_file)
            return response
            return shipment_export_xls(result_list)
    '''
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="somefilename.pdf"'
    
    # Create the PDF object, using the response object as its "file."
    p = canvas.Canvas(response)

    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    p.drawString(100, 100, "Hello world.")

    # Close the PDF object cleanly, and we're done.
    p.showPage()
    p.save()
    return response



def quote_import(request):
    data = {}
    data['message'] = 'Price Update Under Progress Please Access Quotations on 06 July 15'
    # return render(request, 'journal_mgmt/test_response.html', {'data': data})
    # data['project_opt'] = project.objects.order_by('name')
    data['project_opt'] = []
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    # db = psycopg2.connect(database = 'featherlite', user='admin1', password='admin123', host='ferp.cv5o0gucwvmh.us-west-2.rds.amazonaws.com', port='5432')
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("select * from project where EXISTS (select * from quotation where project_id=project.id);")
    all_project_rows = cursor.fetchall()
    data['project_opt'] = all_project_rows
    quotation_opt = []
    project_selected = False
    quote_selected = False
    redirect = False
    project_row = ''
    if(request.GET):
        get_data = request.GET
        project_id = int(get_data['project'])
        project_selected = True
        if('referer' in get_data):
            data['redirect_url'] = get_data['referer'] + '&brdcrmbs[0][0]=' + get_data['brdcrmbs[0][0]'] + '&brdcrmbs[0][1]=' + get_data['brdcrmbs[0][1]'] + \
                                    '&brdcrmbs[0][2][0]=' + get_data['brdcrmbs[0][2][0]'] + '&brdcrmbs[1][0]=' + get_data['brdcrmbs[1][0]'] + '&brdcrmbs[1][1]=' + \
                                    get_data['brdcrmbs[1][1]'] + '&brdcrmbs[1][2][Status]=' + get_data['brdcrmbs[1][2][Status]']
            if 'filter[Project]' in get_data:
                data['redirect_url'] += '&filter[Project]=' + get_data['filter[Project]']
            elif 'brdcrmbs[2][2][Project]' in get_data:
                data['redirect_url'] += '&brdcrmbs[2][0]=Quotation&brdcrmbs[2][1]=Quotation/Index&brdcrmbs[2][2][Project]=' + get_data['brdcrmbs[2][2][Project]']
            redirect = True
        if('quotation' in get_data):
            # return(render(request, 'journal_mgmt/test_response.html', {'data': int(get_data['quotation'])}))
            quote_id = int(get_data['quotation'])
            quote_selected = True
    if request.POST:
        post_data = request.POST
        if 'project' in post_data:
            project_id = int(post_data['project'])
            project_selected = True
        if('quotation' in post_data):
            # return(render(request, 'journal_mgmt/test_response.html', {'data': int(get_data['quotation'])}))
            quote_id = int(post_data['quotation'])
            quote_selected = True
    if project_selected == True:
        cursor.execute('select * from project where id=%d' % (project_id,))
        project_row = cursor.fetchall()[0]  # project_obj
        cursor.execute('select * from quotation where project_id=%s' % (project_id,))
        quotation_opt = cursor.fetchall()
        city_id = int(project_row['site_city_id'])
        cursor.execute('select name from city where id=%d' % (city_id,))
        city_row = cursor.fetchall()[0]
    if quote_selected == True:
        cursor.execute('select * from quotation where id=%d' % (quote_id,))
        quotation_row = cursor.fetchall()[0]
        '''
        Sample -> data colomn in quotation
        {"items":
        {"23464":
        {"sl":"01","n":"Linear 1200x600","tid":1,
        "d":{"Table Top":"PLB 25mm Shape:Linear (Left + Right) Profile:Rectangular (L+R) Size:1200 X 600 with 65 Dia Wiremanager Cap",
        "Main Inside":"Frame | Neo - 50 Corner:1200 H x 600 W Tiles : BTT-Laminate, ATT-Fabric Magnetic (Raceways:1 Skirting, 1 BTT) | Adjacent Frame:1200 H x 600 W Tiles : BTT-Laminate, ATT-Laminate Graph Marker (Raceways:1 Skirting, 1 BTT)",
        "Main Passage Side":"Frame | Neo - 50 Corner:1200 H x 600 W Tiles : BTT-Laminate, ATT-Fabric (Raceways:1 Skirting) | Adjacent Frame:1200 H x 600 W Tiles : BTT-Laminate, ATT-Fabric (Raceways:1 Skirting)",
        "Return Inside":"Supports | Non Sharing:Gable End (Straight) - 710H x 500W x 18t Sharing:Gable End (Straight) - 710H x 500W x 18t",
        "Return Passage Side":"Supports | Gable End (Straight) - 710H x 500W x 18t","Intermediate Inside":"Supports | Non Sharing:Gable End (Straight) - 710H x 500W x 18t Sharing:Gable End (Straight) - 710H x 500W x 18t",
        "Intermediate Passage Side":"Supports | Gable End (Straight) - 710H x 500W x 18t","Accessory":"(1) ABS Keyboard Tray without Mouse Pad(2) CPU Trolley",
        "Pedestal":"(1) Depth & Material:450D - PLB Body & Top, Configuration:2D + 1F, Size:640H X 400W"},
        "3666":8,"c":12826,"r":null}},"lyt":{"3666":"Marvel project layout"},"lvy":{"3":{"VAT":"14.50"},"2":{"Freight and Insurance":"5.00"},
        "1":{"Excise Duty":"12.36"}},"oc":[],"pt":[],"ot":[]}'''
        
        '''{"items":{"16573":{"sl":"01","n":"test part modifications","tid":9,"d":{"Name":"test"},"2676":93,"c":7971,"r":null}},
        "lyt":{"2676":"BOM PRICING TEST layout"},"lvy":{"3":{"VAT":"14.50"},
        "2":{"Freight and Insurance":"5.00"},"1":{"Excise Duty":"12.36"}},"oc":[],"pt":[],"ot":[]}'''
                
        data['quotation'] = quotation_row
        data['quotation']['data'] = ast.literal_eval(str(quotation_row['data'].replace(":null", ":''")))
        cursor.execute('select * from quote_pl where quote_id=%s' % int(quotation_row['id']))
        data['quote_pls'] = cursor.fetchall()
        data['quote_pl_index'] = []
        start_time = timezone.now()
        xl_export_data = []
        
        export_data = {}
        export_header = ['OC No.', 'Project Name', 'Location', 'Product Name', 'Department', 'Part Name', 'Size', 
                                 'Finish', 'Code Desc', 'Qty', 'Date of Manufacture', 'Pack Size']
        export_body = []
        for cur_quote_pl in data['quote_pls']:
            print('Current Quote PL : ' + str(cur_quote_pl))
            cur_quote_pl['spec'] = cur_quote_pl['spec'].replace(":null", ":''")
            cur_quote_pl['spec'] = ast.literal_eval(str(cur_quote_pl['spec'].replace(",null", ",''")))
            cur_quote_pl['parts'] = cur_quote_pl[8].replace(":null", ":''")
            cur_quote_pl['parts'] = ast.literal_eval(str(cur_quote_pl['parts'].replace(",null", ",''")))
            time_left = timedelta(minutes=4) - (timezone.now() - start_time)
            appended_quote_pl = get_actual_price_tpl(cur_quote_pl['parts'], 'append', \
                                                     {'time_left':time_left, 'quote_pl_id':int(cur_quote_pl['id'])})
            time_taken = timezone.now() - start_time
            if time_taken > timedelta(minutes=4):
                message = {}
                message['Update Status'] = 'Partially updated masters - too many new items found, please try again for complete update'
                message['halt point'] = cur_quote_pl['spec']
                return(render(request, 'journal_mgmt/test_response.html', {'data': message}))
            cursor.execute('select * from item where id=%s' % int(cur_quote_pl['item_id']))
            cur_item = cursor.fetchall()[0]
            test_append = (cur_quote_pl, cur_item, appended_quote_pl[1])
            for cur_department, cur_tpl_item_list in appended_quote_pl[0].items():
                if cur_department == 'item':
                    continue
                else:
                    for cur_tpl_item in cur_tpl_item_list:
                        tpl_item_spec = cur_tpl_item[1]
                        tpl_item_size = cur_tpl_item[2]
                        tpl_item_finish = cur_tpl_item[3]
                        tpl_item_tot_qty = cur_tpl_item[4]
                        region_count = len(cur_tpl_item) - 11
                        erp_data_dict = cur_tpl_item[region_count + 10]
                        item_master_obj = erp_data_dict['item_master']
                        item_master_split_name = item_master_obj.name.split('|')
                        if len(item_master_split_name) == 3:
                            tpl_item_finish = item_master_split_name[2]
                        xl_export_row = (project_row['id'], project_row['name'], city_row['name'], cur_item['name'], cur_department,
                                         tpl_item_spec, tpl_item_size, tpl_item_finish, '' , tpl_item_tot_qty, '', '')
                        export_body.append(xl_export_row)
            data['quote_pl_index'].append(test_append)
            data['export_header'] = []
        if request.POST:
            if 'export' in post_data:
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                xls_sheet = workbook.add_worksheet('sheet_all_export')
                export_data['sheet_name'] = 'all_tpl'
                export_data['header'] = export_header
                export_data['body'] = export_body
                export_data['col_width'] = [30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30]
                export_data['co_ordinate'] = [0, 0]
                export_data['conditional_format_type'] = 'test_file_name'
                export_data['merge_data'] = []
                export_data['default_format'] = workbook.add_format()
                export_data['default_format'].set_border(1)
                export_data['sheet_name'] = 'all_tpl_export'
                gen_excel_export(export_data, xls_sheet)
                workbook.close()
                output.seek(0)
                response_obj = HttpResponse()
                response_obj['Content-Disposition'] = 'attachment; filename='+ export_data['conditional_format_type'] +'.xlsx'
                response_obj['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                response_obj['Cache-Control'] = 'no-cache'
                response_obj.write(output.read())
                return (response_obj)
        data['quote_selected'] = quote_selected
    data['project_selected'] = project_selected
    data['project'] = project_row
    data['quotation_opt'] = quotation_opt
    cursor.close()
    db.close()
    return(render(request, 'journal_mgmt/quote_import.html', {'data': data}))


def new_quote_pl_detail(request, quote_pl_id):
    '''parts in quote_pl table
    sample --> {'items':{region name':'no. of segments'}, {'department name':[[part_no, 'part_name', 'part_size', 'fin_no', 'seg1 qty', 'seg2 qty',...'tot_seg qty', norms, rate, value]]}}
    {"B.Wood Department":[["038-02-02-003-000-003-2400-1200-1200-0450","Standard Storage - 450D - PLB Body & Top (Openable Shutter)  Recessed Hanldles","2400 H x 1200 W Top: 1200  W x 450 D","17-11-11-413-57-60-0-0-0-0-0-0-0",8,8,"6000.00",17280,138240]],
    "item":{"Region 1":1}}
    '''
    data = {}
    item_list = []
    image_list = []
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select * from quote_pl where id=%s' % quote_pl_id)
    quote_pl_obj = cursor.fetchall()[0]
    new_spec = quote_pl_obj[4].replace(":null", ":''")
    new_spec = new_spec.replace(",null", ",''")
    new_parts = quote_pl_obj[8].replace(":null", ":''")
    new_parts = new_parts.replace(",null", ",''")
    item_id = quote_pl_obj[1]
    data['quote_pl'] = {'obj': quote_pl_obj, 'spec':ast.literal_eval(new_spec), 'parts':ast.literal_eval(new_parts)}
    data['region_count'] = 0
    for key in data['quote_pl']['parts']['item']:
        data['region_count'] += data['quote_pl']['parts']['item'][key]
    cursor.execute('select * from item where id=%s' % int(quote_pl_obj[3]))
    data['quote_pl']['item_obj'] = cursor.fetchall()[0]
    cursor.execute('select * from quotation where id=%s' % data['quote_pl']['obj'][2])
    data['quotation_obj'] = list(cursor.fetchall()[0])
    data['quotation_obj'][5] = ast.literal_eval(data['quotation_obj'][5].replace(":null", ":''"))
    cursor.close()
    db.close()
    time_left = timedelta(minutes=2)
    appended_quote_pl = get_actual_price_tpl(data['quote_pl']['parts'], 'append', \
                                             {'time_left':time_left, 'quote_pl_id':int(quote_pl_obj[0])})
    data['quote_pl']['parts'] = appended_quote_pl[0]
    new_quote_pl = {}
    region_count = data['region_count']
    for cur_department, cur_part_list in data['quote_pl']['parts'].items():
        if cur_department == 'item':
            new_quote_pl['item'] = cur_part_list
        else:
            for cur_part in cur_part_list:
                part_dict = cur_part[10 + region_count]
                cur_sel_pl_id = part_dict['auto_pl'].id
                cur_item_id = part_dict['item_master'].id
                document_obj = document.objects.filter(tab_id=cur_sel_pl_id, tab_name='auto_pl', doctype=1).order_by('-id')
                if not cur_department in new_quote_pl:
                    new_quote_pl[cur_department] = {}
                if len(document_obj) > 0:
                    if len(document_obj) > 1:
                        document_obj = document_obj[0]
                    else:
                        document_obj = get_object_or_404(document, tab_id=cur_sel_pl_id, tab_name='auto_pl', doctype=1)
                    #document_obj = get_object_or_404(document, id = 1)
                    docfile = document_obj.docfile
                    if not docfile in new_quote_pl[cur_department]:
                        new_quote_pl[cur_department][docfile] = []
                    new_cur_part = cur_part
                    new_cur_part[10 + region_count]['doc_obj'] = document_obj
                    new_quote_pl[cur_department][docfile].append(new_cur_part)
                else:
                    if not cur_sel_pl_id in new_quote_pl[cur_department]:
                        new_quote_pl[cur_department][cur_sel_pl_id] = []
                    '''doctype = 1( preview )'''
                    new_cur_part = cur_part
                    new_cur_part[10 + region_count]['doc_obj'] = document_obj
                    new_quote_pl[cur_department][cur_sel_pl_id].append(new_cur_part)
    data['new_quote_pl'] = new_quote_pl
    if request.GET:
        get_data = request.GET
        item_id_list = []
        i = 1
        while i < 1000:
            id_key = 'item_id_' + str(i)
            if id_key in get_data:
                item_id = int(get_data[id_key])
            data['item_id'] = item_id
            i += 1
        item_id_list.append(item_id)                
        if 'nested' in get_data:
            mrs_feed = []
            for cur_header, part_list in data['quote_pl']['parts'].items():
                if not cur_header == 'item':
                    for cur_part in part_list:
                        # print(str(len(cur_part)) + ' - ' + str(11 + data['region_count']) + ' : ' + str(cur_part))
                        cur_part_obj = cur_part[10 + data['region_count']]['item_master']
                        tot_qty = cur_part[4 + data['region_count']]
                        mrs_feed.append((cur_part_obj.id, float(tot_qty)))
            data = {}
            bom_data = []
            config = {'multi_layer':'True'}
            bom_data = bom_collation(mrs_feed, config)
            bom_data['nested_rm_list'] = []
            nest_res = composite_nest(bom_data['rm_list'])
            for cur_part in nest_res['rm_list']:
                bom_data['nested_rm_list'].append(cur_part)
            nest_res['new_ofct'] = []
            for cur_part in nest_res['new_ofct']:
                bom_data['new_ofct'].append(cur_part)
            new_bom_data = {}
            for cur_bom_key, cur_bom_val in bom_data.items():
                obj_list = conv_part_id_to_obj(cur_bom_val)
                new_bom_data[cur_bom_key] = dj_obj_list_sort(obj_list, {'obj_index':0, 'obj_param':'name'})  # obj_list.sort(key=lambda obj: obj[0].name)
            data['bom_data'] = new_bom_data
            return(render(request, 'journal_mgmt/mrs_preview.html', {'data': data}))
    return(render(request, 'journal_mgmt/new_quote_pl.html', {'data': data}))




def cluster_pl_detail(request, quote_pl_id):
    '''cluster_parts in quote_pl table
    sample --> {"28529":{"2594":[[[70,1,1,1,0,0,1200,600,0,0,"tbl",1],[23,"1",0,10,32,3,300,690,690,0,"sgf",2],
                [24,1,0,0,0,0,630,0,0,0,"sgf",2],[78,1,0,0,0,0,0,0,0,0,"sf,",8],[78,4,0,0,0,0,0,0,0,0,"sf",8],
                [78,1,0,0,0,0,0,0,0,0,"sf",4],[78,3,0,0,0,0,0,0,0,0,"sf",4],[78,6,0,0,0,0,0,0,0,0,"sf",16]], 1,"1"]}}
                
    {'Region ID':{'Cluster ID':['Tot Qty', 'Units Per Cluster', [[uid, sys, mat, s1, s2, s3, d1, d2, d3, d4, finstr, qty],[...]....]]}}
                '''
    data = {}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    
    '''the 8 lines below is meant to get markup value of the respective item_type'''
    cursor.execute("""select item_id from quote_pl where id=%s""" % quote_pl_id)
    item_id = int(cursor.fetchall()[0][0])
    cursor.execute("""select type_id from item where id=%d""" % item_id)
    item_type_id = int(cursor.fetchall()[0][0])
    cursor.execute("""select data from item_type where id=%d""" % item_type_id)
    item_data = str(cursor.fetchall()[0][0])
    item_data = ast.literal_eval(item_data)
    '''default markup is needed to be multiplied with stored sale price  - 
    ONLY TO WRITE BACK INTO 360 DB as this is a requirment from featherlite'''
    def_markup = Decimal(item_data['default_markup'])
    '''markup arrived'''
    
    cursor.execute('select * from quote_pl where id=%s' % quote_pl_id)
    quote_pl_obj = cursor.fetchall()[0]
    cursor.close()
    db.close()
    cluster_parts = quote_pl_obj[9].replace(":null", ":''")
    cluster_parts = cluster_parts.replace(",null", ",''")
    cluster_parts = ast.literal_eval(cluster_parts)
    qpl_parts = ast.literal_eval(quote_pl_obj[8])
    disp_part = {}
    disp_spec_code = {}
    disp_cluster = {}
    '''disp_part = {'part_id':['part_obj', 'tot_qty', {'region_id':{'cluster_id':'part_qty', ....}]}}
    disp_cluster = {'region_id':{'cluster_id':['cluster_name', 'tot_seg_qty', 'units_per_cluster', 'cluster_rate']}}
    disp_spec_code = {'spec_code':['part_obj(any 1 matching to spec code)', 'tot_qty', {'region_id':{'cluster_id':'part_qty', ....}]}}
    '''
    cons_parts = []
    cons_spec_code = []
    cons_imp_parts = []
    err_display = ''
    cluster_count = 0
    sorted_region_keys = []
    sorted_cluster_keys = {}
    '''
    sorted_cluster_keys = {region1id:[cluster_id1, cluster_id2,....], 'region2id':[].... }
    '''
    tot_units = 0
    tot_val = 0
    start_time = timezone.now()
    time_out = False
    for cur_dep_key, cur_dep_parts in qpl_parts.items():
        if cur_dep_key == 'item':
            continue
        else:
            total_index = len(cur_dep_parts[0]) - 4
            for cur_part_det in cur_dep_parts:
                cur_tot_qty = cur_part_det[total_index]
                cur_spec_code = cur_part_det[0]
                app_part_obj_list = item_master.objects.filter(imported_item_code=cur_spec_code).order_by('imported_item_finish')
                if len(app_part_obj_list) == 0:
                    continue
                cur_part_obj = app_part_obj_list[0]
                # cur_sale_price = app_part_obj[0].sale_price
                '''this condition is brought in to ensure that we don't loop over checking of parts for every cluster'''
                cur_app_sale_price = app_part_obj_list[0].bom_sale_price
                check_all = False
                for cur_part_obj in app_part_obj_list:
                    # if not cur_sale_price == cur_part_obj.sale_price:
                    cur_diff = cur_app_sale_price - cur_part_obj.bom_sale_price
                    if cur_diff > 1 or cur_diff < -1:
                        check_all = True
                if check_all == True:
                    # ref_part_obj = bom_input_sum(app_part_obj_list[0].id, {'update_ip_factor':True})
                    ref_part_obj = app_part_obj_list[0]
                    test = infinite_update([(ref_part_obj.imported_item_code, ref_part_obj.imported_item_finish, 1.0)], True, {'auto_update':True})
                    app_part_obj_list = item_master.objects.filter(imported_item_code=cur_spec_code).order_by('imported_item_finish')
                    ref_part_obj = get_object_or_404(item_master, id=ref_part_obj.id)
                    # ref_part_obj = app_price_update(ref_part_obj)
                    ref_bom_len = len(ast.literal_eval(ref_part_obj.bom))
                    for cur_part_obj in app_part_obj_list:
                        cur_diff = cur_part_obj.bom_sale_price - ref_part_obj.bom_sale_price
                        cur_bom_len = len(ast.literal_eval(cur_part_obj.bom))
                        if cur_diff > 1 or cur_diff < -1 and ref_bom_len == cur_bom_len:
                            cur_part_obj = bom_input_sum(cur_part_obj.id, {'update_ip_factor':True})
                            cur_diff = cur_app_sale_price - cur_part_obj.bom_sale_price
                        if cur_diff > 1 or cur_diff < -1 or (not ref_bom_len == cur_bom_len):
                            test = infinite_update([(cur_part_obj.imported_item_code, cur_part_obj.imported_item_finish, 1.0)], True, {'auto_update':True})
                            cur_part_obj = get_object_or_404(item_master, id=cur_part_obj.id)
                app_part_obj_list = item_master.objects.filter(imported_item_code=cur_spec_code).order_by('imported_item_finish')
                cur_part_obj = app_part_obj_list[0]
                cons_parts.append(cur_part_obj)
                if not cur_part_obj.imported_item_code in disp_spec_code:
                    disp_spec_code[cur_part_obj.imported_item_code] = [cur_part_obj, cur_tot_qty, {}, {'markup_rate':round(cur_part_obj.bom_sale_price * def_markup, 2)}]
                if not cur_part_obj.id in disp_part:
                    disp_part[cur_part_obj.id] = [cur_part_obj, cur_tot_qty, {}, {'markup_rate':round(cur_part_obj.bom_sale_price * def_markup, 2)}]
    """for cur_cons_part in cons_parts:
        disp_part[cur_cons_part.id] = [cur_cons_part, 0, {}, {'markup_rate':round(cur_cons_part.bom_sale_price * def_markup, 2)}]
        cur_part_obj = cur_cons_part
        '''
        [0]cur_cons_part is the part_object
        [1]2nd value in the array is an integer it is the total quantity
        [2]3rd value in the array is a dictionary meant for carrying the region-wise & segment-wise quantities
        [3]4th value in the array is a dictionary meant for other details - currently {'markup_rate':def_markup}
        '''"""
    cluster_count = 0
    for cur_region_id, region_val in cluster_parts.items():
        cur_region_id = int(cur_region_id)
        disp_cluster[cur_region_id] = {}
        if not cur_region_id in sorted_region_keys:
            sorted_region_keys.append(cur_region_id)
            sorted_cluster_keys[cur_region_id] = []
        cur_cluster_keys = sorted_cluster_keys[cur_region_id]
        for clusterset_id, cluster_set_val in region_val.items():
            clusterset_id = int(clusterset_id)
            sorted_cluster_keys[cur_region_id].append(clusterset_id)
            cluster_rate = 0
            cluster_val = 0
            part_detail = cluster_set_val[0]
            tot_seg_qty = cluster_set_val[1]
            cluster_name = cluster_set_val[3]
            cur_cluster_keys
            try:
                int(cluster_set_val[2])
            except:
                units_per_cluster = 1
            else:
                units_per_cluster = int(cluster_set_val[2])
            disp_cluster[cur_region_id][clusterset_id] = [cluster_name, tot_seg_qty, units_per_cluster, cluster_rate]
            for cur_part in part_detail:
                error = False
                try:
                    cur_spec_code = str(1000 + int(cur_part[0]))[1:] + '-' + str(100 + int(cur_part[1]))[1:] + '-' + str(100 + int(cur_part[2]))[1:] + '-' + \
                                str(1000 + int(cur_part[3]))[1:] + '-' + str(1000 + int(cur_part[4]))[1:] + '-' + str(1000 + int(cur_part[5]))[1:] + '-' + \
                                str(10000 + int(cur_part[6]))[1:] + '-' + str(10000 + int(cur_part[7]))[1:] + '-' + str(10000 + int(cur_part[8]))[1:] + '-' + str(10000 + int(cur_part[9]))[1:]
                except:
                    cur_spec_code = ''
                    i = 1
                    if int(cur_part[0]) == 18:
                        print(cur_part)
                    for cur_spec in cur_part[:10]:
                        if i == 2 or i == 3:
                            multi = 100
                        elif i < 7:
                            multi = 1000
                        else:
                            multi = 10000
                        if cur_spec == '':
                            cur_spec = 0
                        else:
                            try:
                                int(cur_spec)
                            except:
                                error = True
                                break
                            else:
                                cur_spec = int(cur_spec)
                        if not cur_spec_code == '':
                            cur_spec_code += '-'
                        cur_spec_code += str(multi + int(cur_spec))[1:]
                        i += 1
                try:
                    int(cur_part[11])
                except:
                    error = True
                print(cur_spec_code)
                if error == True:
                    continue
                else:
                    if cur_spec_code in disp_spec_code:
                        cur_part_obj = disp_spec_code[cur_spec_code][0]
                        new_ind_qty = int(cur_part[11])
                        if not cur_region_id in disp_part[cur_part_obj.id][2]:
                            disp_part[cur_part_obj.id][2][cur_region_id] = {}
                        if not clusterset_id in disp_part[cur_part_obj.id][2][cur_region_id]:
                            disp_part[cur_part_obj.id][2][cur_region_id][clusterset_id] = 0
                        disp_part[cur_part_obj.id][2][cur_region_id][clusterset_id] += new_ind_qty
                        cluster_val += round(float(cur_part[11]) * float(cur_part_obj.bom_sale_price) * float(def_markup), 2)
            if float(units_per_cluster) < 1:
                cluster_rate = cluster_val
            else:
                cluster_rate = cluster_val / float(units_per_cluster)
            disp_cluster[cur_region_id][clusterset_id] = [cluster_name, tot_seg_qty, units_per_cluster, cluster_rate]
            tot_units += float(units_per_cluster) * float(tot_seg_qty)
            tot_val += float(cluster_val) * float(tot_seg_qty)
            cluster_count += 1
    sorted_region_keys.sort()      
    for cur_region_id, cur_cluster_list in sorted_cluster_keys.items():
        cur_cluster_list.sort()
        sorted_cluster_keys[cur_region_id] = cur_cluster_list
    sorted_parts = []
    for cur_part_id, cur_part_det in disp_part.items():
        sorted_parts.append(cur_part_det)
    sorted_parts.sort(key=lambda x: x[0].imported_item_code, reverse=False)
    data['segregated_parts'] = {}
    for cur_sorted_part in sorted_parts:
        cur_spec_code = cur_sorted_part[0].imported_item_code[:21]
        cur_auto_pl = get_object_or_404(auto_price_list, spec_code=cur_spec_code)
        cur_item_dep_name = cur_auto_pl.item_department_ref.name
        if not cur_item_dep_name in data['segregated_parts']:
            data['segregated_parts'][cur_item_dep_name] = []
        data['segregated_parts'][cur_item_dep_name].append(cur_sorted_part)
    data['def_markup'] = def_markup
    data['sorted_parts'] = sorted_parts
    data['disp_part'] = disp_part
    data['disp_cluster'] = disp_cluster
    data['cluster_count'] = cluster_count
    data['tot_val'] = tot_val
    data['tot_units'] = tot_units
    data['error_message'] = err_display
    data['sorted_region_keys'] = sorted_region_keys
    data['sorted_cluster_keys'] = sorted_cluster_keys
    return(render(request, 'journal_mgmt/cluster_pl.html', {'data': data}))

def quote_write_back(request, quotation_id):
    quotation_id = int(quotation_id)
    data = {}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select * from quotation where id=%s' % quotation_id)
    quotation_obj = list(cursor.fetchall()[0])
    quotation_obj[5] = ast.literal_eval(quotation_obj[5].replace(":null", ":''"))
    cursor.execute('select * from quote_pl where quote_id=%d' % quotation_id)
    quote_pl_index = cursor.fetchall()
    start_time = timezone.now()
    for cur_quote_pl in quote_pl_index:
        cur_quote_pl = list(cur_quote_pl)
        cur_quote_pl[4] = cur_quote_pl[4].replace(",null", ",''")
        cur_quote_pl[4] = ast.literal_eval(cur_quote_pl[4].replace(":null", ":''"))
        cur_quote_pl[8] = cur_quote_pl[8].replace(",null", ",''")
        cur_quote_pl[8] = ast.literal_eval(cur_quote_pl[8].replace(":null", ":''"))
        time_left = timedelta(minutes=4) - (timezone.now() - start_time)
        mod_result = get_actual_price_tpl(cur_quote_pl[8], 'over_write', \
                                          {'time_left':time_left, 'quote_pl_id':int(cur_quote_pl[0])})
        time_taken = timezone.now() - start_time
        if time_taken > timedelta(minutes=4):
            message = {}
            message['Update Status'] = 'Partially updated masters - too many new items found, please try again for complete update'
            message['halt point'] = cur_quote_pl[4]
            return(render(request, 'journal_mgmt/test_response.html', {'data': message}))
        print('MOD RESULT : ' + str(mod_result))
        cur_quote_pl[8] = mod_result[0]
        cursor.execute("""update quote_pl set cost='%d' where id=%d""" % (int(mod_result[1]), int(cur_quote_pl[0])))
        db.commit()
        quotation_obj[5]['items'][str(cur_quote_pl[3])]['c'] = int(round(mod_result[1] / cur_quote_pl[4]['Quantity'], 2))
        cur_quote_pl[8] = json.dumps(cur_quote_pl[8]).replace(":''", ":null")
        cur_quote_pl[8] = cur_quote_pl[8].replace(",''", ",null")
        cursor.execute("""update quote_pl set parts='%s' where id=%d""" % (cur_quote_pl[8], int(cur_quote_pl[0])))
        db.commit()
        '''Update rate in item table'''
        cur_item_pk = cur_quote_pl[3]
        cursor.execute("""select * from item where id=%d""" % (cur_item_pk,))
        cur_item_obj = cursor.fetchall()[0]
        item_rate = float(round(mod_result[1] / cur_quote_pl[4]['Quantity'], 2))
        discount = 0.0
        if cur_item_obj[11]:
            discount = cur_item_obj[11]
        cursor.execute("""update item set quote_value='%s' where id=%d""" % (item_rate, cur_item_pk))
        db.commit()
        cursor.execute("""update item set offered_unit_price='%s' where id=%d""" % \
                       (int(round((item_rate * float((1 - discount / 100))), 2)), cur_item_pk))
        db.commit()
    cursor.execute("""update quotation set data='%s' where id=%d""" % \
                   (json.dumps(quotation_obj[5]).replace(":''", ":null"), int(quotation_id)))
    db.commit()
    cursor.execute("""update quotation set mod_price='1' where id=%d""" % (int(quotation_id),))
    db.commit()
    cursor.close()
    db.close()
    post_data = []
    if (request.POST):
        post_data = request.POST
    return HttpResponseRedirect(post_data['redirect_url'])

def quotation_save(request, quotation_id):
    data = {}
    message = {}
    '''Create OC here transaction_type_ref_no for OC is 59'''
    imported_array = quote_import_array(quotation_id)
    '''This is a test code to check the array received'''
    # return(render(request, 'journal_mgmt/test_response.html', {'data': imported_array}))
    if 'error' in imported_array:
        return(render(request, 'journal_mgmt/test_response.html', {'data': imported_array}))
    ttype_oc = get_object_or_404(transaction_type, transaction_type_ref_no=59)
    ttype_oc_data = ast.literal_eval(ttype_oc.data)
    tref_oc_field_data = field_list_collate_default(ttype_oc_data['field_list'])
    tref_oc_field_data['project'] = imported_array[2][1]
    tref_oc_field_data['quotation'] = imported_array[1][1]
    tref_oc_data = {}
    tref_oc_data['field_list'] = tref_oc_field_data
    oc_inv_jour = []
    data['line_items'] = imported_array[0]
    for cur_arr_line in data['line_items']:
        item_real_value = Decimal(0)
        item_offered_rate = Decimal(cur_arr_line[0][1]['f360_item_row'][10])
        cur_line_item_qty = int(cur_arr_line[0][1]['qty'])
        '''
        db_crm_dict = crm_connect_data()
        db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
        cursor = db.cursor()
        cursor.execute('select * from quote_pl where id=%s' % quote_pl_id)
        quote_pl_obj = cursor.fetchall()[0]
        
        cursor.close()
        db.close()
        '''
        item_rate = round(cur_arr_line[0][1]['value'] / cur_arr_line[0][1]['qty'], 2)
        item_discount = cur_arr_line[0][1]['discount']
        # master_line = item_master.objects.filter(imported_item_code=cur_arr_line[0][0], imported_item_finish='1-0-0-0-0-0-0-0-0-0-0-0-0')
        master_line = item_master.objects.filter(imported_item_code=cur_arr_line[0][0], imported_item_finish='1-1-1-1-1-1-1-1-1-1-1-1-1')
        if not master_line:
            master_line = item_master(imported_item_code=cur_arr_line[0][0])
            master_line.created_date = timezone.now()
        else:
            master_line = master_line[0]
        master_line.name = cur_arr_line[0][1]['description']
        
        # master_line.imported_item_finish = '1-0-0-0-0-0-0-0-0-0-0-0-0'
        master_line.imported_item_finish = '1-1-1-1-1-1-1-1-1-1-1-1-1'
        seg_bom_collate = {}
        '''This is where you create tpls'''
        for cur_arr_bom in cur_arr_line[1]:
            tot_qty = Decimal(cur_arr_bom[2][0])
            tpl_item_obj = item_master.objects.filter(imported_item_code=cur_arr_bom[0], \
                                                      imported_item_finish=cur_arr_bom[1])
            if len(tpl_item_obj) == 0:
                inf_bom = infinite_update([(cur_arr_bom[0], cur_arr_bom[1], 1.0)], True, {'auto_update':False})
                print('Infinite BOM Completed')
                if 'error' in inf_bom:
                    return(render(request, 'journal_mgmt/test_response.html', {'data': inf_bom}))
            else:
                time_diff = tpl_item_obj[0].price_last_updated - timezone.now()
                if (tpl_item_obj[0].sale_price == 0.0 or tpl_item_obj[0].sale_price == None or time_diff >= timedelta(days=4)):
                    inf_bom = infinite_update([(cur_arr_bom[0], cur_arr_bom[1], 1.0)], True, {'auto_update':False})
            tpl_item_obj = get_object_or_404(item_master, imported_item_code=cur_arr_bom[0], imported_item_finish=cur_arr_bom[1])
            item_real_value += tpl_item_obj.bom_sale_price * tot_qty
            # return(render(request, 'journal_mgmt/test_response.html', {'data' : message})) 
            # auto_update_item_master(cur_arr_bom[0], cur_arr_bom[1], 1)
            i = 0
            for cur_seg_qty in cur_arr_bom[2]:
                '''cur_arr_bom[2] has segment-wise quantities [q1, q2, q3, q4...., q-tot]'''
                if int(cur_seg_qty) < 0:
                    '''in case any of the quantities is found to be zero, exception is thrown'''
                    message = {1:'negative quantities found in TPL - item:' + str(tpl_item_obj.name)}
                    return(render(request, 'journal_mgmt/test_response.html', {'data': {'status':'Negative Quantities found for TPL', 'message':message}}))
                if not i in seg_bom_collate:
                    seg_bom_collate[i] = [(cur_arr_bom[0], cur_arr_bom[1], int(cur_seg_qty))]
                else:
                    seg_bom_collate[i].append((cur_arr_bom[0], cur_arr_bom[1], int(cur_seg_qty)))
                i += 1
        item_real_rate = item_real_value / cur_line_item_qty
        actual_discount = 100 * (item_real_rate - item_offered_rate) / item_real_rate
        master_line_bom = []
        print('---------All TPL Items Updated in masters---------')
        i = 0
        for cur_arr_seg in cur_arr_line[0][2]:
            print('START -- cur_arr_seg - ' + cur_arr_seg[1]['description'])
            # master_line_bom.append((cur_arr_seg[0], '1-0-0-0-0-0-0-0-0-0-0-0-0', 1))
            master_line_bom.append((cur_arr_seg[0], '1-1-1-1-1-1-1-1-1-1-1-1-1', 1))
            # master_seg = item_master.objects.filter(imported_item_code=cur_arr_seg[0], imported_item_finish='1-0-0-0-0-0-0-0-0-0-0-0-0')
            master_seg = item_master.objects.filter(imported_item_code=cur_arr_seg[0], imported_item_finish='1-1-1-1-1-1-1-1-1-1-1-1-1')
            if not master_seg:
                master_seg = item_master(imported_item_code=cur_arr_seg[0])
                master_seg.created_date = timezone.now()
            else:
                master_seg = master_seg[0]
            master_seg.name = cur_arr_seg[1]['description']
            master_seg.imported_bom = seg_bom_collate[i]
            item_gr = item_group.objects.filter(imported_unique=103)[0]
            master_seg.item_group = item_gr
            master_seg.sale_price = item_real_rate
            master_seg.bom_sale_price = item_real_rate
            master_seg.adhoc_sale_price = item_real_rate
            master_seg.last_updated = timezone.now()
            master_seg.imported_item_code = cur_arr_seg[0]
            # master_seg.imported_item_finish = '1-0-0-0-0-0-0-0-0-0-0-0-0'
            master_seg.imported_item_finish = '1-1-1-1-1-1-1-1-1-1-1-1-1'
            master_seg.save()
            print('END -- cur_arr_seg - ' + cur_arr_seg[1]['description'])
            print('Part ID Conversion for ' + master_seg.name + ' Under Progress - Code ' + master_seg.imported_item_code + ' Finish Code ' + master_seg.imported_item_finish)
            print(part_id_conversion([(master_seg.imported_item_code, master_seg.imported_item_finish, 1)]))
            i += 1
        print('---------All Segment TPLs Updated in masters---------')
        master_line.sale_price = item_real_rate
        master_line.adhoc_sale_price = item_real_rate
        master_line.bom_sale_price = item_real_rate
        master_line.imported_bom = master_line_bom
        item_gr = item_group.objects.filter(imported_unique=102)[0]
        master_line.item_group = item_gr
        master_line.last_updated = timezone.now()
        master_line.save()
        '''Preparing the inventory journal for auto tref create'''
        plant_location = get_location_raw('plant', 1)
        oc_inv_jour_det = {'tpl_ref':0}
        oc_inv_jour_det['discount'] = actual_discount
        oc_inv_jour.append((master_line.id, cur_arr_line[0][1]['qty'], oc_inv_jour_det))
        print('Part ID Conversion for ' + master_line.name + ' Under Progress')
        print((master_line.imported_item_code, master_line.imported_item_finish, 1))
        print(part_id_conversion([(master_line.imported_item_code, master_line.imported_item_finish, 1.0)]))
        # infinite_update(master_seg.imported_bom, True)
    message['Item Master'] = 'Complete Synchronization'
    message['OC Creation'] = 'New OC Created'
    print('All Line Items Updated in masters')
    quote_availability = imported_quotes.objects.filter(quote=imported_array[1][0], project=imported_array[2][0])
    if len(quote_availability) > 0:
        message['OC Creation'] = 'OC Already Available please refer to ' + quote_availability[0].name
        return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(quote_availability[0].ord_con,)))
        return(render(request, 'journal_mgmt/test_response.html', {'data': {'status':'Successfully Imported', 'message':message}}))
    if not quote_availability:
        tref_oc = auto_create_tref(ttype_oc.transaction_type_ref_no, tref_oc_data, oc_inv_jour, False, {})
        '''Receive TLP Has transaction ref no. as 2'''
        ttype_rec_tpl = get_object_or_404(transaction_type, transaction_type_ref_no=2)
        
        plant_location = get_location_raw('plant', 1)
        for cur_oc_inv_jour in oc_inv_jour:
            cur_oc_item_obj = get_object_or_404(item_master, id=cur_oc_inv_jour[0])
            for cur_tpl_seg in ast.literal_eval(str(cur_oc_item_obj.bom)):
                cur_tpl_seg_obj = get_object_or_404(item_master, id=cur_tpl_seg[0])
                
                cur_tpl_data = {'field_list':{'segment': cur_tpl_seg_obj.name, 'order_confirmation': (tref_oc.id, tref_oc.name), \
                                              'oc_item': (cur_oc_item_obj.id, cur_oc_item_obj.name)}}
                '''Preparing the inventory journal for auto tref create'''
                seg_inv_jour = []
                seg_bom = ast.literal_eval(str(cur_tpl_seg_obj.bom))
                for cur_seg_inv_jour in seg_bom:
                    seg_inv_jour_det = {}
                    seg_inv_jour_det['discount'] = actual_discount
                    seg_inv_jour_det['tpl_ref'] = 0
                    seg_inv_jour.append((cur_seg_inv_jour[0], cur_seg_inv_jour[1], seg_inv_jour_det))
                cur_tpl = auto_create_tref(ttype_rec_tpl.transaction_type_ref_no, cur_tpl_data, seg_inv_jour, False, {'chain_tref':tref_oc.id})
        new_quote = imported_quotes(name=tref_oc.name)
        new_quote.quote = imported_array[1][0]
        new_quote.quote_name = imported_array[1][1]
        new_quote.project = imported_array[2][0]
        new_quote.project_name = imported_array[2][1]
        tref_oc.ref_name = new_quote.project_name
        new_quote.ord_con = tref_oc.id
        new_quote.ord_con_name = tref_oc.name
        new_quote.save()
        message['OC Creation'] = 'New OC Created please refer to ' + tref_oc.name
        return HttpResponseRedirect(reverse('journal_mgmt:tref_detail', args=(tref_oc.id,)))


def quote_redirect(request, quotation_id):
    data = {}
    referer = request.META.get('HTTP_REFERER')
    #quotation_id = get_data['quotation_id']
    db_crm_dict = crm_connect_data()
    crm_domain_name = db_crm_dict['domain_name']
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    cursor.execute('select * from quotation where id=%s' % quotation_id)
    quotation_obj = list(cursor.fetchall()[0])
    quotation_obj[5] = ast.literal_eval(quotation_obj[5].replace(":null", ":'null'"))
    project_id = int(quotation_obj[4])
    cursor.execute('select * from project where id=%s' % project_id)
    project_obj = list(cursor.fetchall()[0])
    status_id = project_obj[12]
    cursor.execute('select * from status where id=%s' % status_id)
    status_obj = list(cursor.fetchall()[0])
    status_id = status_obj[0]
    status_name = status_obj[1]
    cursor.close()
    db.close()
    if referer == None:
        referer = crm_domain_name + '/index.php?r=Quotation/Index&brdcrmbs[0][0]=' + status_name + \
        '&brdcrmbs[0][1]=Status/Index&brdcrmbs[0][2][0]=&brdcrmbs[1][0]=Project&brdcrmbs[1][1]=Project/Index&brdcrmbs[1][2][Status]=' \
         + str(status_id) + '&filter[Project]=' + str(project_id)
    data['referer'] = referer
    if request.GET:
        get_data = request.GET
        if 'action_type' in get_data:
            if get_data['action_type'] == 'write_back':
                '''return HttpResponseRedirect(reverse('journal_mgmt:quote_import', args=()))'''
            elif get_data['action_type'] == 'view_quote':
                '''return HttpResponseRedirect(reverse('journal_mgmt:quote_import', args=()) + '?project=' + str(quotation_obj[4]) + '&quotation=' + str(quotation_id) + '&referer=' + data['referer'])'''
    #return HttpResponseRedirect(reverse('journal_mgmt:test_rig', args=()) + '?project=' + str(quotation_obj[4]) + '&quotation=' + str(quotation_id) + '&referer=' + data['referer'])
    return HttpResponseRedirect(reverse('journal_mgmt:quote_import', args=()) + '?project=' + str(quotation_obj[4]) + '&quotation=' + str(quotation_id) + '&referer=' + data['referer'])
    # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
    # return HttpResponseRedirect('http://127.0.0.1/')
    # return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    return HttpResponseRedirect('http://www.google.com/')

def auto_pl_supplier_addition(request, auto_pl_id):
    data = {}
    auto_pl_obj = get_object_or_404(auto_price_list, id=auto_pl_id)
    data['auto_pl'] = auto_pl_obj
    data['supplier_opt'] = []
    get_data = request.GET
    data['type'] = get_data['type']
    if get_data:
        if get_data['type'] == 'vendor':
            '''get all vendors - job work & purchase'''
            data['supplier_opt'] = select_boxes({'name':'vendor'})
            # data['supplier_opt'] = select_boxes('purchases')
        elif get_data['type'] == 'work_center':
            data['supplier_opt'] = select_boxes({'name':'work_center'})
    # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
    # return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_sup_create', args=(int(auto_pl_id),)))
    return(render(request, 'journal_mgmt/auto_pl_supplier.html', {'data': data}))
    # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))

def auto_pl_supplier_save(request, auto_pl_id):
    data = {}
    mdl = []
    post_data = request.POST
    auto_pl_obj = get_object_or_404(auto_price_list, id=int(auto_pl_id))
    if post_data:
        if post_data['type'] == 'vendor':
            new_sup = get_object_or_404(coa, id=int(post_data['supplier']))
            if len(vendor_price_list_auto.objects.filter(auto_pl=auto_pl_obj, vendor=new_sup)) > 0:
                return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_detail', args=(int(auto_pl_id),)))
            else:
                new_pl_sup = vendor_price_list_auto(auto_pl=auto_pl_obj, vendor=new_sup)
        elif post_data['type'] == 'work_center':
            new_sup = get_object_or_404(work_center, id=int(post_data['supplier']))
            if len(work_center_price_list_auto.objects.filter(auto_pl=auto_pl_obj, work_center=new_sup)) > 0:
                return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_detail', args=(int(auto_pl_id),)))
            else:
                new_pl_sup = work_center_price_list_auto(auto_pl=auto_pl_obj, work_center=new_sup)
        new_pl_sup.name = new_sup.name
        new_pl_sup.save()
        data['message'] = 'New Supplier Added Successfully'
        # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
    data['message'] = 'No Data'
    return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_detail', args=(int(auto_pl_id),)))
    # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
    
    
def auto_price_list_update(request, auto_pl_id):
    data = {}
    auto_pl_obj = get_object_or_404(auto_price_list, id=auto_pl_id)
    data['price_list'] = auto_pl_obj
    all_variants = item_master.objects.filter(imported_item_code__startswith=auto_pl_obj.spec_code)
    get_data = request.GET
    if 'item_master' in get_data:
        selected_item = get_object_or_404(item_master, id=int(get_data['item_master']))
        if 'update_infinite_bom' in get_data:
            sync_down_pl_360(auto_pl_obj.spec_code)
            print('TEST START : ' + str(selected_item.imported_item_code))
            test = infinite_update([(selected_item.imported_item_code, selected_item.imported_item_finish, 1.0)], True, {'auto_update':True})
        if 'update_bom_sale_price' in get_data:
            print('TEST START : ' + str(selected_item.imported_item_code))
            bom_input_sum(selected_item.id, {'update_ip_factor':True})
        if 'update_weight_vol' in get_data:
            print('TEST START : ' + str(selected_item.imported_item_code))
            weight_vol_update(selected_item.id, {'update_ip_factor':True})
        if 'update_all_infinite_bom' in get_data:
            sync_down_pl_360(auto_pl_obj.spec_code)
            for cur_item in all_variants:
                test = infinite_update([(cur_item.imported_item_code, cur_item.imported_item_finish, 1.0)], True, {'auto_update':True})
        if 'update_bom_sale_price_for_all_variants' in get_data:
            for cur_item in all_variants:
                bom_input_sum(cur_item.id, {'update_ip_factor':True})
        if 'update_weight_vol_for_all_variants' in get_data:
            for cur_item in all_variants:
                weight_vol_update(cur_item.id, {'update_ip_factor':True})
        if 'update_vendor_price' in get_data:
            print('Updating Vendor Price for ' + selected_item.name)
            sel_pl_vendor_id = get_data['vendor']
            sel_pl_vendor = get_object_or_404(vendor_price_list_auto, id=int(sel_pl_vendor_id))
            update_vendor_rate(selected_item.id, sel_pl_vendor.vendor.id, 'job_work')
            update_vendor_rate(selected_item.id, sel_pl_vendor.vendor.id, 'purchase_format')
            if auto_pl_obj.purchase_price_calc_eqn == 'sum':
                calc_pur_rate(selected_item.id, sel_pl_vendor.vendor.id)
            else:
                update_vendor_rate(selected_item.id, sel_pl_vendor.vendor.id, 'purchase')
            print(selected_item.name + ' Vendor Price Updated')
        
        if 'update_all_vendor_price' in get_data:
            sel_pl_vendor_id = get_data['vendor']
            sel_pl_vendor = get_object_or_404(vendor_price_list_auto, id=int(sel_pl_vendor_id))
            for cur_item in all_variants:
                print('Updating Vendor Price for ' + cur_item.name)
                update_vendor_rate(cur_item.id, sel_pl_vendor.vendor.id, 'job_work')
                update_vendor_rate(cur_item.id, sel_pl_vendor.vendor.id, 'purchase_factor')
                if auto_pl_obj.purchase_price_calc_eqn == 'sum':
                    calc_pur_rate(cur_item.id, sel_pl_vendor.vendor.id)
                else:
                    update_vendor_rate(cur_item.id, sel_pl_vendor.vendor.id, 'purchase')
                print(cur_item.name + ' Vendor Price Updated')
                    
        if 'update_work_center_price' in get_data:
            print('Updating Work Center Price for ' + selected_item.name)
            sel_pl_work_center_id = get_data['work_center']
            sel_pl_work_center = get_object_or_404(work_center_price_list_auto, id=int(sel_pl_work_center_id))
            update_work_center_rate(selected_item.id, sel_pl_work_center.work_center.id)
            print(selected_item.name + ' Work Center Price Updated')
        
        if 'update_all_work_center_price' in get_data:
            sel_pl_work_center_id = get_data['work_center']
            sel_pl_work_center = get_object_or_404(work_center_price_list_auto, id=int(sel_pl_work_center_id))
            for cur_item in all_variants:
                print('Updating Work Center Price for ' + cur_item.name)
                update_work_center_rate(cur_item.id, sel_pl_work_center.work_center.id)
                print(cur_item.name + ' Work Center Price Updated')
        return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_detail', args=(auto_pl_id,)) + '?item_master=' + str(selected_item.id)\
                                             + '&vendor=' + get_data['vendor'] + '&work_center=' + get_data['work_center'])


def auto_price_list_del_index(request):
    data = {}
    get_data = request.GET
    result_list = auto_price_list.objects.all().order_by('spec_code')
    index_url = reverse('journal_mgmt:auto_pl_del_index')
    filter_type = 'show_all'
    page_no = 1
    searched_param = ''
    if get_data:
        if 'show_all' in get_data:
            result_list = auto_price_list.objects.all().order_by('spec_code')
            filter_type = 'show_all'
        elif 'show_redundant' in get_data:
            result_list = redundant_auto_pl()
            filter_type = 'show_redundant'
        if 'searched_param' in get_data:
            searched_name_set = get_data['searched_param'].split('!!')
            for cur_name_search in searched_name_set:
                result_list = result_list.filter(name__icontains=cur_name_search).order_by('spec_code')
            # result_list = result_list.filter(name__icontains=get_data['searched_param']).order_by('spec_code')
            searched_param = get_data['searched_param']
        if 'page_no' in get_data:
            page_no = int(get_data['page_no'])
    else:
        result_list = redundant_auto_pl()
    data['searched_param'] = searched_param
    index_url += '?searched_param=' + searched_param + '&' + filter_type + '=True'
    data['index_url'] = index_url
    '''data['result_tot'] = len(result_list)
    i = 1
    data['page_tot'] = []
    while i <= math.ceil(data['result_tot']/100):
        data['page_tot'].append(i)
        i += 1
    '''
    data = pagination_detail(data, result_list, 100)
    disp_result_list = result_list[(page_no - 1) * 100:page_no * 100]
    data['index_result'] = []
    for cur_disp_res in disp_result_list:
        cur_match = auto_pl_match(cur_disp_res.id)
        item_master_count = len(item_master.objects.filter(imported_item_code__startswith=cur_disp_res.spec_code))
        remarks = ''
        if cur_match == True:
            remarks = 'PN Match'
        else:
            remarks = 'ERROR'
        data['index_result'].append((cur_disp_res, {'remarks':remarks, 'master_count':int(item_master_count)}))
    # data['index_result'] = result_list[(page_no - 1) * 100:page_no * 100]
    
    data['page_no'] = page_no
    return render(request, 'journal_mgmt/auto_price_list_del_index.html', {'data': data})

def auto_price_list_delete(request, auto_pl_id):
    data = {}
    if request.GET:
        get_data = request.GET
        if 'confirmed' in get_data:
            get_data = request.GET
            if 'del_crm' in get_data:
                data['crm_pl'] = del_crm_pl_bom_der_erp(auto_pl_id)
            data['erp_pl'] = del_auto_pl(auto_pl_id)
        return render(request, 'journal_mgmt/test_response.html', {'data': data})

def confirmation_page(request):
    referer_url = request.META.get('HTTP_REFERER')
    if request.GET:
        get_data = request.GET
        data = {}
        yes_url = ''
        no_url = referer_url
        reason = str(get_data['reason'])
        remarks = []
        '''remark = ['remark line 1', 'remark line 2', 'remark line 3']'''
        yes_url = ''
        all_param = {}
        i = 1
        while i < 6:
            search_str = 'param' + str(i)
            if search_str in get_data:
                all_param[i] = get_data[search_str]
            else:
                break
            i += 1
        if reason == 'auto_pl_del':
            auto_pl_id = int(all_param[1])
            auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
            remarks.append('Sure you want to delete ' + auto_pl_obj.name + '?')
            app_item_master = item_master.objects.filter(imported_item_code__startswith = auto_pl_obj.spec_code)
            remarks.append('The Item master count is ' + str(len(app_item_master)))
            remarks.append('')
            yes_url = reverse('journal_mgmt:auto_price_list_delete', args=(int(auto_pl_id),)) + '?confirmed=true'
        if reason == 'auto_pl_crm_pl_del':
            auto_pl_id = int(all_param[1])
            auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
            remarks.append('Sure you want to delete ' + auto_pl_obj.name + '?')
            app_item_master = item_master.objects.filter(imported_item_code__startswith = auto_pl_obj.spec_code)
            remarks.append('The Item master count is ' + str(len(app_item_master)))
            remarks.append('')
            yes_url = reverse('journal_mgmt:auto_price_list_delete', args=(int(auto_pl_id),)) + '?confirmed=true&del_crm=true'
        data['reason'] = reason
        data['remarks'] = remarks
        data['yes_url'] = yes_url
        data['no_url'] = no_url
        return render(request, 'journal_mgmt/confirmation_page.html', {'data': data})
    return HttpResponseRedirect(referer_url)


def crm_pl_delete(request, crm_pl_id):
    data = {}
    data['crm_pl'] = del_crm_pl_bom_der(crm_pl_id)
    return render(request, 'journal_mgmt/test_response.html', {'data': data})

def auto_price_list_index(request):
    data = {}
    result_list = []
    get_data = request.GET
    result_list = auto_price_list.objects.all().order_by('spec_code')
    index_url = reverse('journal_mgmt:auto_pl_index')
    page_no = 1
    searched_param = ''
    if get_data:
        if 'searched_param' in get_data:
            searched_name_set = get_data['searched_param'].split('!!')
            for cur_name_search in searched_name_set:
                result_list = result_list.filter(name__icontains=cur_name_search).order_by('spec_code')
            # result_list = result_list.filter(name__icontains=get_data['searched_param']).order_by('spec_code')
            searched_param = get_data['searched_param']
        if 'page_no' in get_data:
            page_no = int(get_data['page_no'])
    data['searched_param'] = searched_param
    index_url += '?searched_param=' + searched_param
    data['index_url'] = index_url
    '''data['result_tot'] = len(result_list)
    i = 1
    data['page_tot'] = []
    while i <= math.ceil(data['result_tot']/100):
        data['page_tot'].append(i)
        i += 1
    '''
    data = pagination_detail(data, result_list, 100)
    data['index_result'] = result_list[(page_no - 1) * 100:page_no * 100]
    data['disp_result'] = []
    
    for cur_pl in data['index_result']:
        add_data  = {}
        img_objs = []
        master_count = len(item_master.objects.filter(imported_item_code__startswith=cur_pl.spec_code))
        doc_type_obj = get_object_or_404(doctype, id = 1)
        app_img_objs = document.objects.filter(tab_name = 'auto_pl', tab_id = cur_pl.id, doctype = doc_type_obj).order_by('id')
        for cur_img_obj in app_img_objs:
            file_name = str(cur_img_obj.docfile)
            file_name = file_name.split('/')
            file_name = file_name[len(file_name)-1]#get the last element
            img_objs.append({'img_obj':cur_img_obj, 'name':file_name})
        add_data['master_count'] = master_count
        add_data['img_objects'] = img_objs
        data['disp_result'].append((cur_pl, add_data))
    data['page_no'] = page_no
    return(render(request, 'journal_mgmt/auto_price_list_index.html', {'data': data}))
    # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))


def auto_price_list_detail(request, auto_pl_id):
    data = {}
    auto_pl_obj = get_object_or_404(auto_price_list, id=auto_pl_id)
    data['price_list'] = auto_pl_obj
    all_variants = item_master.objects.filter(imported_item_code__startswith=auto_pl_obj.spec_code).order_by('name')
    data['item_master_opt'] = all_variants
    data['compiled_infinite_bom'] = []
    data['infinite_bom_raw'] = []
    get_data = request.GET
    data['raw_material_prices'] = rmp_auto.objects.all()
    data['constants'] = constants.objects.all()
    data['auto_pl_obj'] = auto_pl_obj
    data['vendor_opt'] = auto_pl_obj.vendor_price_list_auto_set.all()
    data['work_center_opt'] = auto_pl_obj.work_center_price_list_auto_set.all()
    pl_obj = auto_pl_obj
    data['rmp_obj_set'] = [pl_obj.p1, pl_obj.p2, pl_obj.p3, pl_obj.p4, pl_obj.p5, pl_obj.p6, pl_obj.p7, pl_obj.p8, pl_obj.p9, pl_obj.p10, \
                           pl_obj.p11, pl_obj.p12, pl_obj.p13, pl_obj.p14, pl_obj.p15, pl_obj.p16, pl_obj.p17, pl_obj.p18, pl_obj.p19, pl_obj.p20]
    data['con_obj_set'] = [pl_obj.k1, pl_obj.k2, pl_obj.k3, pl_obj.k4, pl_obj.k5, pl_obj.k6, pl_obj.k7, pl_obj.k8, pl_obj.k9, pl_obj.k10, \
                           pl_obj.k11, pl_obj.k12, pl_obj.k13, pl_obj.k14, pl_obj.k15, pl_obj.k16, pl_obj.k17, pl_obj.k18, pl_obj.k19, pl_obj.k20]
    if get_data:
        if 'item_master' in get_data:
            selected_item = get_object_or_404(item_master, id=int(get_data['item_master']))
            auto_pl_obj = get_object_or_404(auto_price_list, id=auto_pl_id)
            broken_item = param_break(selected_item.imported_item_code, selected_item.imported_item_finish)
            selected_vendor_auto = 0
            selected_work_center_auto = 0
            item_summary = []
            item_summary.append([selected_item.id, 1])
            purchase_sum = 0
            data['new_sale_price'] = 0
            # print('NEW SALE VALUE - ' + str(data['new_sale_price']))
            for cur_tot_bom_raw in collate_inf_bom(selected_item.id):
                item_summary.append([cur_tot_bom_raw[0], cur_tot_bom_raw[1]])
            data['compiled_infinite_bom'] = []
            for cur_tot_item in item_summary:
                cur_item = get_object_or_404(item_master, id=cur_tot_item[0])
                cur_pl_obj = auto_price_list.objects.filter(spec_code=cur_item.imported_item_code[:21])
                selected_spec_code = cur_item.imported_item_code[0:21]
                auto_pl_process_obj = get_object_or_404(auto_price_list, spec_code=selected_spec_code)
                selected_process_id = auto_pl_process_obj.process.id
                process_obj = get_object_or_404(process_type, id=selected_process_id)
                if len(ast.literal_eval(str(cur_item.bom))) > 0:
                    has_bom = True 
                else:
                    has_bom = False
                # print('compare code :' + str(cur_item.imported_item_code))
                if len(cur_pl_obj) > 0:
                    cur_pl_obj = cur_pl_obj[0]
                cur_rmp_con = get_rmp_con(cur_pl_obj.id, 0, 'sale')
                cur_broken_item = param_break(cur_item.imported_item_code, cur_item.imported_item_finish)
                cur_sp_interpret = dim_cost_port(cur_broken_item['pn'], cur_pl_obj.input_rate_sale, cur_rmp_con[0], \
                                                 cur_rmp_con[1], cur_pl_obj.input_factor_calc_eqn, 1)
                data['compiled_infinite_bom'].append([cur_item, cur_tot_item[1], {'auto_pl_obj':cur_pl_obj, \
                                                            'has_bom':has_bom, 'sp_interpret':cur_sp_interpret}])
                print('NEW SALE VALUE - ' + str(data['new_sale_price']) + ' (' + str(Decimal(cur_item.process_valuation_sale)) + ')')
            '''data['compiled_infinite_bom'] = [[item_object, item_qty, item_sale_value(qty*rate), auto_pl_obj]]'''            
            rmp_con = get_rmp_con(auto_pl_obj.id, 0, 'sale')
            data['adhoc_sale_interpret'] = dim_cost_port(broken_item['pn'], auto_pl_obj.input_rate_sale, rmp_con[0], \
                                                         rmp_con[1], auto_pl_obj.adhoc_sale_price_calc_eqn, 1)
            data['new_adhoc_sale_rate'] = round(eval(data['adhoc_sale_interpret']), 2)
            print(auto_pl_obj.sale_price_calc_eqn)
            data['bom_sale_interpret'] = dim_cost_port(broken_item['pn'], auto_pl_obj.input_rate_sale, rmp_con[0], rmp_con[1], \
                                                       auto_pl_obj.sale_price_calc_eqn, 1)
            data['new_bom_sale_rate'] = round(eval(data['bom_sale_interpret']), 2)
            if (int(get_data['vendor']) > 0):
                selected_vendor_auto = get_object_or_404(vendor_price_list_auto, id=int(get_data['vendor']))
                rmp_con = get_rmp_con(auto_pl_obj.id, selected_vendor_auto.vendor.id, 'vendor')
                data['jw_interpret'] = dim_cost_port(broken_item['pn'], 0, rmp_con[0], rmp_con[1], \
                                                     auto_pl_obj.job_work_price_calc_eqn, 1)
                data['jw_rate'] = round(eval(data['jw_interpret']), 2)
                data['pur_interpret'] = dim_cost_port(broken_item['pn'], 0, rmp_con[0], rmp_con[1], \
                                                      auto_pl_obj.purchase_price_calc_eqn, 1)
                data['pur_rate'] = 0
                data['pur_factor_interpret'] = dim_cost_port(broken_item['pn'], 0, rmp_con[0], rmp_con[1], \
                                                             auto_pl_obj.purchase_factor_calc_eqn, 1)
                data['pur_factor_rate'] = round(eval(data['pur_factor_interpret']), 2)
                data['vendor_rmp_con'] = rmp_con
                real_vendor = get_object_or_404(coa, id=selected_vendor_auto.vendor.id)
                data['vendor_pl'] = 0
                if auto_pl_obj.purchase_price_calc_eqn != 'sum':
                    data['pur_rate'] = round(eval(data['pur_interpret']), 2)
                i = 0
                while i < len(data['compiled_infinite_bom']):
                    cur_compiled_item = data['compiled_infinite_bom'][i]
                    vendor_pl = vendor_price.objects.filter(item=cur_compiled_item[0], vendor=real_vendor)
                    if len(vendor_pl) > 0:
                        vendor_pl = vendor_pl[0]
                        cur_pur_factor_val = round(Decimal(vendor_pl.purchase_factor) * Decimal(cur_compiled_item[1]), 2)
                        data['compiled_infinite_bom'][i].append(vendor_pl)
                        data['compiled_infinite_bom'][i].append(cur_pur_factor_val)
                        data['pur_rate'] += float(cur_pur_factor_val)
                        if vendor_pl.item.id == selected_item.id:
                            data['vendor_pl'] = vendor_pl
                    else:
                        vendor_pl = []
                        cur_pur_factor_val = 0
                    i += 1
            if (int(get_data['work_center']) > 0):
                selected_work_center_auto = get_object_or_404(work_center_price_list_auto, id=int(get_data['work_center']))
                rmp_con = get_rmp_con(auto_pl_obj.id, selected_work_center_auto.work_center.id, 'work_center')
                data['so_interpret'] = dim_cost_port(broken_item['pn'], 0, rmp_con[0], rmp_con[1], auto_pl_obj.shop_order_price_calc_eqn, 1)
                data['so_rate'] = round(eval(data['so_interpret']), 2)
                data['work_center_rmp_con'] = rmp_con
                real_work_center = get_object_or_404(work_center, id=selected_work_center_auto.work_center.id)
                data['work_center_pl'] = 0
                work_center_pl = work_center_price.objects.filter(item=selected_item, work_center=real_work_center)
                if len(work_center_pl) > 0:
                    data['work_center_pl'] = work_center_pl[0]
            data['infinite_bom_raw'] = collate_inf_bom(selected_item.id)
            data['sel_item_master'] = selected_item
            data['price_list'] = auto_pl_obj
            data['sel_vendor'] = selected_vendor_auto
            data['sel_work_center'] = selected_work_center_auto
    return(render(request, 'journal_mgmt/auto_price_list_detail.html', {'data': data}))


def auto_price_list_save(request, auto_pl_id):
    data = {}
    post_data = request.POST
    pl_obj = get_object_or_404(auto_price_list, id=auto_pl_id)
    if post_data:
        pl_obj.job_work_price_calc_eqn = post_data['job_work_calc']
        pl_obj.purchase_price_calc_eqn = post_data['purchase_calc']
        pl_obj.shop_order_price_calc_eqn = post_data['shop_order_calc']
        pl_obj.purchase_factor_calc_eqn = post_data['format_calc']
        pl_obj.save()
        i = 1
        rmp_obj = {}
        con_obj = {}
        while i <= 20:
            rmp_key = 'rmp' + str(i)
            con_key = 'con' + str(i)
            if rmp_key in post_data:
                rmp_obj['p' + str(i)] = get_object_or_404(rmp_auto, id=post_data[rmp_key])
            if con_key in post_data:
                con_obj['k' + str(i)] = get_object_or_404(constants, id=post_data[con_key])
            i += 1
        pl_obj = rmp_con_upload(pl_obj.id, rmp_obj, con_obj)        
    # return(render(request, 'journal_mgmt/test_response.html', {'data': post_data}))
    if '_save' in post_data:
        return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_index', args=()))
    elif '_continue' in post_data:
        return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_detail', args=(int(auto_pl_id),)) + \
                                    '?item_master=' + post_data['re_item_master_id'] + '&vendor=' + post_data['re_pl_vendor_id'] \
                                     + '&work_center=' + post_data['re_pl_work_center_id'])
        
def auto_pl_matrix(request):
    data = {}
    auto_pl_opt = []
    searched_str = ''
    disp_tab_x_head = [] 
    disp_tab_y_head = []
    matrix_output = {}
    matrix_output['disp_tab_ip_data'] = []
    matrix_output['disp_tab_sp_data'] = []
    matrix_output['disp_tab_rate_data'] = []
    disp_tab_rate_data = []
    d3_val = 0
    d4_val = 0
    d1_start = 0
    d1_inc = 0
    d1_end = 0
    d2_start = 0
    d2_inc = 0
    d2_end = 0
    min_count = 0
    sel_pl_id = '-None-'
    pl_opt_ids = []
    d1_opt = []
    d1_ranking = []
    d2_opt = []
    d2_ranking = []
    d3_ranking = []
    d4_ranking = []
    d3_opt = []
    d4_opt = []
    if request.POST:
        post_data = request.POST
        '''name_str = abc!!def!!ghi!!jkl
        names having strings 'abc' & 'def' will be retained
         & names having strings 'ghi' & 'jkl' will be excluded 
        '''
        searched_str = post_data['searched_str']
        searched_arr = searched_str.split('~~')
        if len(searched_arr) > 0:
            filter_arr = searched_arr[0].split('!!')
            auto_pl_opt = auto_price_list.objects.all().order_by('name')
            for cur_str in filter_arr:
                auto_pl_opt = auto_pl_opt.filter(name__icontains=cur_str)
        if len(searched_arr) > 1:
            exclude_arr = searched_arr[1].split('!!')
            for cur_str in exclude_arr:
                auto_pl_opt = auto_pl_opt.exclude(name__icontains=cur_str)
        min_count = int(post_data['min_count'])
        if min_count > 0:
            temp_auto_pl_opt = copy.deepcopy(auto_pl_opt)
            for cur_auto_pl in temp_auto_pl_opt:
                app_item_master = item_master.objects.filter(imported_item_code__startswith = cur_auto_pl.spec_code)
                if len(app_item_master) < min_count:
                    auto_pl_opt = auto_pl_opt.exclude(id = cur_auto_pl.id)
                else:
                    pl_opt_ids.append(cur_auto_pl.id)
        d3_val = int(post_data['d3_val'])
        d4_val = int(post_data['d4_val'])
        cur_d1 = d1_start
        cur_d2 = d2_start
        d1_start = int(post_data['d1_start'])
        d1_inc = int(post_data['d1_inc'])
        d1_end = int(post_data['d1_end'])
        d2_start = int(post_data['d2_start'])
        d2_inc = int(post_data['d2_inc'])
        d2_end = int(post_data['d2_end'])
        cur_d1 = d1_start
        cur_d2 = d2_start
        sel_pl_id = post_data['auto_pl_id']
        try:
            int(sel_pl_id)
        except:
            '''do nothing'''
        else:
            sel_pl_id = int(sel_pl_id)
            auto_pl_obj = get_object_or_404(auto_price_list, id=sel_pl_id)
            '''taking top 5 values'''
            matrix_opt_output = price_matrix_opt_gen(sel_pl_id, 5)
            d1_opt = matrix_opt_output['d1_opt']
            d2_opt = matrix_opt_output['d2_opt']
            d3_opt = matrix_opt_output['d3_opt']
            d4_opt = matrix_opt_output['d4_opt']
            d1_ranking = matrix_opt_output['d1_ranking']
            d2_ranking = matrix_opt_output['d2_ranking']
            d3_ranking = matrix_opt_output['d3_ranking']
            d4_ranking = matrix_opt_output['d4_ranking']
        if 'super_fill' in post_data:
            i = 0
            for cur_d1_dict in d1_ranking:
                disp_tab_x_head.append(cur_d1_dict['val'])
            for cur_d2_dict in d2_ranking:
                disp_tab_y_head.append(cur_d2_dict['val'])
            d3_val = sorted(d3_ranking, key=lambda x:-x['count'])[0]['val']
            d4_val = sorted(d4_ranking, key=lambda x:-x['count'])[0]['val']
        if 'auto_fill' in post_data:
            i = 1
            while cur_d1 <= d1_end and i <= 10:
                disp_tab_x_head.append(cur_d1)
                cur_d1 += d1_inc
                i += 1
            i = 1
            while cur_d2 <= d2_end and i <= 10:
                disp_tab_y_head.append(cur_d2)
                cur_d2 += d2_inc
                i += 1
        if 'get_price' in post_data:
            i = 1
            while i <= 10:
                x_search_str = 'd1-' + str(i)
                if not x_search_str in post_data:
                    break
                x_val = int(post_data[x_search_str])
                disp_tab_x_head.append(int(x_val))
                i += 1
            i = 1
            while i <= 10:
                y_search_str = 'd2-' + str(i)
                if not y_search_str in post_data:
                    break
                y_val = int(post_data[y_search_str])
                disp_tab_y_head.append(int(y_val))
                i += 1
            matrix_output = price_matrix_generator(auto_pl_obj.id, disp_tab_x_head, disp_tab_y_head, d3_val, d4_val, 1)
            data['sel_pl_obj'] = auto_pl_obj
            sel_pl_id = auto_pl_obj.id
        if 'spread_sheet' in post_data:
            export_id_list = ast.literal_eval(post_data['export_ids'])
            if len(export_id_list) == 0:
                export_id_list = [auto_pl_obj.id]
            '''only the first variable is checked if it's an integer - if it is, the whole list is closed inside another array to standardize'''
            if isinstance(export_id_list[0], int ):
                export_id_list = [export_id_list]
            return price_matrix_xls({'input_type':'auto_gen', 'auto_pl_id_list':export_id_list, 'max_cols':5})
    data['auto_pl_opt'] = auto_pl_opt
    data['pl_opt_ids'] = pl_opt_ids
    data['pl_count'] = len(auto_pl_opt)
    data['min_count'] = min_count
    data['d1_start'] = d1_start
    data['d1_inc'] = d1_inc
    data['d1_end'] = d1_end
    data['d1_opt'] = sorted(d1_opt)
    data['d2_start'] = d2_start
    data['d2_inc'] = d2_inc
    data['d2_end'] = d2_end
    data['d2_opt'] = sorted(d2_opt)
    data['d3_val'] = d3_val
    data['d3_opt'] = sorted(d3_opt)
    data['d4_val'] = d4_val
    data['d4_opt'] = sorted(d4_opt)
    data['disp_tab_x_head'] = disp_tab_x_head
    data['disp_tab_y_head'] = disp_tab_y_head
    data['disp_tab_ip_data'] = matrix_output['disp_tab_ip_data']
    data['disp_tab_sp_data'] = matrix_output['disp_tab_sp_data']
    data['disp_tab_rate_data'] = matrix_output['disp_tab_rate_data']
    data['sel_pl_id'] = sel_pl_id
    data['searched_str'] = searched_str
    return(render(request, 'journal_mgmt/auto_pl_matrix.html', {'data': data}))

def price_report(request):
    data = {}
    page_no = 1
    name_search = ''
    sel_report_type = ''
    auto_pl_id = 0
    report_opt = ['all_size_price', 'historical_price_data', 'process_wise_price']
    table_header = []
    table_body = []
    auto_pl_opt = []
    if request.POST:
        post_data = request.POST
        name_search = post_data['name_search']
        auto_pl_opt = auto_price_list.objects.all().order_by('spec_code')
        result_list = item_master.objects.all().order_by('name')
        include_str = name_search.split('~~')[0]
        include_str = include_str.split('!!')
        exclude_str = ''
        if len(name_search.split('~~')) > 1:
            exclude_str = name_search.split('~~')[1]
            exclude_str = exclude_str.split('!!')
        for cur_str_search in include_str:
            result_list = result_list.filter(name__icontains=cur_str_search)
        for cur_str_search in exclude_str:
            result_list = result_list.exclude(name__icontains=cur_str_search)
        result_list = result_list[0:1000]
        sel_report_type = post_data['sel_report_type']
        #if not 'auto_pl_filter' in post_data:
            #sel_report_type = post_data['sel_report_type']
            #auto_pl_id = int(post_data['sel_auto_pl'])
            #if auto_pl_id > 0:
                #auto_pl_obj = get_object_or_404(auto_price_list, id=auto_pl_id)
                #result_list = unique_item_master_list(auto_pl_id)['master_list']
        data = pagination_detail(data, result_list, 100)
        if 'page_no' in post_data:
            page_no = int(post_data['page_no'])
        result_list = result_list[(page_no - 1) * 100:page_no * 100]
        if sel_report_type == 'historical_price_data':
            sel_report_type = 'historical_price_data'
            his_price_data = price_history_data(result_list)
            table_header = his_price_data['tab_header']
            table_body = his_price_data['tab_body']
        elif sel_report_type == 'process_wise_price':
            sel_report_type = 'process_wise_price'
            proc_wise_data = process_wise_price_report(result_list)
            table_header = proc_wise_data['tab_header']
            table_body = proc_wise_data['tab_body']
        elif sel_report_type == 'all_size_price':
            sel_report_type = 'all_size_price'
            all_size_data = []
            for cur_item in result_list:
                all_size_data.append({'item_obj':cur_item})
            all_item_data = all_item_price_report(result_list)
            table_header = all_item_data['tab_header']
            table_body = all_item_data['tab_body']
    data['page_no'] = page_no
    data['name_search'] = name_search
    data['sel_report_type'] = sel_report_type
    data['report_opt'] = report_opt
    data['auto_pl_opt'] = auto_pl_opt
    data['sel_auto_pl_id'] = auto_pl_id
    data['table_header'] = table_header
    data['table_body'] = table_body
    return(render(request, 'journal_mgmt/auto_pl_item_report.html', {'data': data}))

def transaction_report(request):
    data = {}
    export_data = {}
    i = 0
    page_no = 1
    name_search = ''
    sel_report_type = ''
    report_opt = ['Quotation History','Pending PO', 'Pending Job Order', 'Pending Shop Order']
    table_header = []
    table_body = []
    start_date = datetime.today() - timedelta(days=10)
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = datetime.today().strftime('%Y-%m-%d')
    export_data['body'] = []
    export_data['header'] = []
    export_data['col_width'] = [5, 40, 20, 5, 5, 10, 10, 15, 10, 5, 5, 5, 5, 5]
    export_data['co_ordinate'] = (0, 0)
    if request.POST:
        post_data = request.POST
        sel_report_type = post_data['sel_report_type']
        if 'sel_start_date' in post_data:
            start_date = post_data['sel_start_date']
            start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        if 'sel_end_date' in post_data:
            end_date = post_data['sel_end_date']
            end_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        if sel_report_type ==  'Quotation History':
            param_dict = {'start_date':start_date, 'end_date':end_date}
            quote_data = quotation_report(param_dict)
            result_list = quote_data['tab_body']
            table_header = quote_data['tab_header']
            for cur_data in table_header:
                for cur_header in cur_data:
                    export_header = cur_header['val']
                    export_data['header'].append(export_header)
            table_body = quote_data['tab_body']
            export_data['conditional_format_type'] = 'Quotation Report'
            for cur_data in table_body:
                i += 1
                if cur_data[5]['val'] == 'None':
                    month_name = ''
                else:
                    date = datetime.strptime(str(cur_data[5]['val']), '%Y-%m-%d')
                    month_name = date.strftime("%d %b, %Y")
                export_row = [i, cur_data[1]['val'], cur_data[2]['val'], cur_data[3]['val'], cur_data[4]['val'], month_name,\
                              cur_data[6]['val'], cur_data[7]['val'], cur_data[8]['val'], cur_data[9]['val'], cur_data[10]['val'],\
                              cur_data[11]['val'], cur_data[12]['val'], cur_data[13]['val']]
                export_data['body'].append(export_row)
            sel_report_type = 'Quotation History'
        if sel_report_type ==  'Pending PO':
            """ ttype_ref_no 63 is For Purchase Order"""
            export_data['conditional_format_type'] = 'Purchase Order Report'
            param_dict = {'start_date':start_date, 'end_date':end_date, 'ttype_ref_no':63}
            quote_data = pending_reports(param_dict)
            result_list = quote_data['tab_body']
            table_header = quote_data['tab_header']
            for cur_data in table_header:
                for cur_header in cur_data:
                    export_header = cur_header['val']
                    export_data['header'].append(export_header)
            table_body = quote_data['tab_body']
            for cur_data in table_body:
                i += 1
                if cur_data[4]['val'] == 'None':
                    month_name = ''
                else:
                    cur_date = str(cur_data[4]['val'])
                    date = datetime.strptime(cur_date[0:10], '%Y-%m-%d')
                    month_name = date.strftime("%d %b, %Y")
                export_row = [i, cur_data[1]['val'], cur_data[2]['val'], cur_data[3]['val'], month_name, cur_data[5]['val'],\
                              cur_data[6]['val']]
                export_data['body'].append(export_row)
            sel_report_type = 'Pending PO'
        if sel_report_type ==  'Pending Job Order':
            """ ttype_ref_no 68 is For Job Order Process"""
            export_data['conditional_format_type'] = 'Job Order Report'
            param_dict = {'start_date':start_date, 'end_date':end_date, 'ttype_ref_no':68}
            quote_data = pending_reports(param_dict)
            result_list = quote_data['tab_body']
            table_header = quote_data['tab_header']
            for cur_data in table_header:
                for cur_header in cur_data:
                    export_header = cur_header['val']
                    export_data['header'].append(export_header)
            table_body = quote_data['tab_body']
            for cur_data in table_body:
                i += 1        
                if cur_data[4]['val'] == 'None':
                    manth_name = ''
                else:
                    cur_date = str(cur_data[4]['val'])
                    date = datetime.strptime(cur_date[0:10], '%Y-%m-%d')
                    month_name = date.strftime("%d %b, %Y")
                export_row = [i, cur_data[1]['val'], cur_data[2]['val'], cur_data[3]['val'], month_name, cur_data[5]['val'],\
                              cur_data[6]['val']]
                export_data['body'].append(export_row)
            sel_report_type = 'Pending Job Order'
        if sel_report_type ==  'Pending Shop Order':
            """ ttype_ref_no 72 is For Shop Order Process"""
            export_data['conditional_format_type'] = 'Shop Order Report'
            param_dict = {'start_date':start_date, 'end_date':end_date, 'ttype_ref_no':72}
            quote_data = pending_reports(param_dict)
            result_list = quote_data['tab_body']
            table_header = quote_data['tab_header']
            for cur_data in table_header:
                for cur_header in cur_data:
                    export_header = cur_header['val']
                    export_data['header'].append(export_header)
            table_body = quote_data['tab_body']
            for cur_data in table_body:
                i += 1
                if cur_data[4]['val'] == 'None':
                    month_name = ''
                else:
                    cur_date = str(cur_data[4]['val'])
                    date = datetime.strptime(cur_date[0:10], '%Y-%m-%d')
                    month_name = date.strftime("%d %b, %Y")
                export_row = [i, cur_data[1]['val'], cur_data[2]['val'], cur_data[3]['val'], month_name, cur_data[5]['val'],\
                              cur_data[6]['val']]
                export_data['body'].append(export_row)
            sel_report_type = 'Pending Shop Order'
        data = pagination_detail(data, table_body, 1000)
        if 'page_no' in post_data:
            page_no = int(post_data['page_no'])
        result_list = result_list[(page_no - 1) * 100:page_no * 100]
        table_body = result_list
        data['table_header'] = table_header
        data['table_body'] = table_body
        #list = html_to_excel_format(table_body, table_header)
        if 'export' in post_data:
            if post_data['export'] == 'spread_sheet':
                return quotation_xls(export_data)
    data['table_header'] = table_header
    data['table_body'] = table_body
    data['page_no'] = page_no
    data['name_search'] = name_search
    data['sel_start_date'] = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
    data['sel_end_date'] = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
    data['sel_report_type'] = sel_report_type
    data['report_opt'] = report_opt
    return(render(request, 'journal_mgmt/transaction_report.html', {'data': data}))

def crm_pl_index(request):
    data = {}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    page_no = 1
    result_list = []
    ilike_param = ''
    query_str = ''
    get_data = request.GET
    if get_data:
        if 'searched_param' in get_data:
            searched_name_set = get_data['searched_param'].split('!!')
            query_str = """select id, name, unique_id, system_id, material_id, s1, s2, s3 from price_list where """
            i = 1
            for cur_name_search in searched_name_set:
                new_str = "name ILIKE '%" + cur_name_search + "%'"
                ilike_param += new_str
                if i > 1 and 1 < len(searched_name_set):
                    ilike_param += ' and '
            # result_list = result_list.filter(name__icontains=get_data['searched_param']).order_by('spec_code')
            searched_param = get_data['searched_param']
            data['searched_param'] = searched_param
        if 'page_no' in get_data:
            page_no = int(get_data['page_no'])
    if len(ilike_param) > 5:
        query_str += ilike_param
        query_str += " order by unique_id, system_id, material_id, s1, s2, s3"
        cursor.execute(query_str)
    else:
        cursor.execute("""select id, name, unique_id, system_id, material_id, s1, s2, s3  from price_list order by unique_id, system_id, material_id, s1, s2, s3""")
    result_list = cursor.fetchall()
    cursor.close()
    db.close()
    data = pagination_detail(data, result_list, 100)
    disp_result_list = []
    result_list = result_list[(page_no - 1) * 100:page_no * 100]
    for cur_result in result_list:
        crm_spec_code = str(cur_result[2])
        i = 3
        while i <= 7:
            add_str = '-' + str(cur_result[i])
            crm_spec_code += add_str
            i += 1
        item_group_obj = get_object_or_404(item_group, imported_unique=int(cur_result[2]))
        auto_pl_match = auto_price_list.objects.filter(flite_360_price_list_id=int(cur_result[0]))
        if len(auto_pl_match) > 0:
            auto_pl_match = auto_pl_match[0]
        else:
            auto_pl_match = ''
        disp_result_list.append((cur_result[0], {'item_group':item_group_obj, 'name':cur_result[1], 'crm_spec_code':crm_spec_code, 'auto_pl_obj':auto_pl_match}))
    data['disp_result_list'] = disp_result_list
    data['index_result'] = disp_result_list[(page_no - 1) * 100:page_no * 100]
    data['page_no'] = page_no
    return(render(request, 'journal_mgmt/crm_pl_index.html', {'data': data}))
    

def item_master_create(request):
    data = {}
    data['item_group_opt'] = item_group.objects.all()
    data['item_group_opt'] = data['item_group_opt'].order_by('name')
    get_group_id = ''
    get_auto_pl = ''
    # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
    if request.GET:
        get_data = request.GET
        if 'group_id' in get_data:
            item_group_obj = get_object_or_404(item_group, id=int(get_data['group_id']))
            data['sel_item_group'] = item_group_obj
            get_group_id = item_group_obj.id
            data['auto_pl_opt'] = auto_price_list.objects.filter(item_group=item_group_obj).order_by('name')
            data['auto_pl_opt'] = data['auto_pl_opt'].exclude(flite_360_price_list_id=None)
            data['auto_pl_opt'] = data['auto_pl_opt'].exclude(flite_360_price_list_id=0)
            if 'preview' in get_data or 'apply_auto_pl' in get_data or 'text_search' in get_data:
                if 'text_search' in get_data:
                    data['filter_text'] = get_data['filter_text']
                else:
                    data['filter_text'] = get_data['sel_filter_text']
                filter_array = data['filter_text'].split('!!')
                print('Filter Text - ' + str(data['filter_text']) + ' filter array - ' + str(filter_array))
                for cur_filter in filter_array:
                    data['auto_pl_opt'] = data['auto_pl_opt'].filter(name__icontains=cur_filter)
                if 'apply_auto_pl' in get_data:
                    auto_pl_obj = get_object_or_404(auto_price_list, id=int(get_data['auto_pl_id']))
                    data['sel_dim'] = [0, 0, 0, 0]
                elif 'preview' in get_data:
                    auto_pl_obj = get_object_or_404(auto_price_list, id=int(get_data['sel_auto_pl_id']))
                if 'preview' in get_data:
                    i = 1
                    data['sel_finish'] = []
                    data['sel_dim'] = []
                    while i <= 12:
                        if i <= 4:
                            if int(get_data['d' + str(i)]) == 0 or int(get_data['d' + str(i)]) < 0:
                                get_dim = 0
                            else:
                                get_dim = int(get_data['d' + str(i)])
                            data['sel_dim'].append(get_dim)
                        cur_get_fin = 0
                        if len(get_data['f' + str(i)]) == 0:
                            cur_get_fin = 0
                        elif int(get_data['f' + str(i)]) == 1:
                            cur_get_fin = 0
                        else:
                            cur_get_fin = int(get_data['f' + str(i)])
                        data['sel_finish'].append(cur_get_fin)
                        i += 1
                if 'apply_auto_pl' in get_data or 'preview' in get_data:
                    data['sel_auto_pl'] = auto_pl_obj
                    fin_type = get_fin_type(auto_pl_obj.spec_code)
                    if fin_type[1] == True:
                        data['fin_type'] = fin_type[0]
                        data['pl_availability'] = fin_type[1]
                    else:
                        data['fin_type'] = 1
                    '''fin_opt is a dictionary carrying selected finish & finish options together fin_opt = {f1:{'sel':'id', 'opt':fin_opt}, fin2:.....12:}'''
                    fin_opt = []
                    fin_opt_rec = get_fin_opt(int(data['fin_type'][0]))
                    for cur_fin_opt_rec in fin_opt_rec:
                        fin_app = {}
                        if 'preview' in get_data:
                            fin_app['sel'] = data['sel_finish']
                        else:
                            ''' As Finish is not selected yet 'sel' = 1 '''
                            fin_app['sel'] = 1
                        fin_app['opt'] = cur_fin_opt_rec
                        fin_opt.append(fin_app)
                    data['finish_opt'] = fin_opt
                    if 'preview' in get_data:
                        part_no = auto_pl_obj.spec_code
                        for cur_dim in data['sel_dim']:
                            if len(str(cur_dim)) > 0:
                                part_no += '-' + str(10000 + int(cur_dim))[1:]
                            else:
                                part_no += '-0000'
                        data['part_no'] = part_no
                        fin_type = get_fin_type(auto_pl_obj.spec_code)
                        if fin_type[1] == True:
                            data['fin_type'] = fin_type[0]
                            data['pl_availability'] = fin_type[1]
                        else:
                            data['fin_type'] = 1
                        fin_no = str(data['fin_type'][0])
                        for cur_fin in data['sel_finish']:
                            fin_no += '-' + str(cur_fin)
                        data['fin_no'] = fin_no
                        data['part_description'] = description_gen(part_no) + '|' + size_gen(part_no)
                        data['finish_description'] = finish_gen(part_no, fin_no)
                        item_master_obj = item_master.objects.filter(imported_item_code=data['part_no'], imported_item_finish=data['fin_no'])
                        data['item_availability'] = {}
                        if len(item_master_obj) == 0:
                            data['item_availability']['status'] = False
                        else:
                            data['item_availability']['status'] = True
                            data['item_availability']['obj'] = item_master_obj[0]
    return(render(request, 'journal_mgmt/item_master_create.html', {'data': data}))

def item_master_detail(request, item_master_id):
    data = {}
    item_master_obj = get_object_or_404(item_master, id=item_master_id)
    data['item_master'] = item_master_obj
    data['sel_item_group'] = item_master_obj.item_group
    data['sel_auto_pl'] = get_object_or_404(auto_price_list, spec_code=item_master_obj.imported_item_code[:21])
    data['sel_finish'] = get_finish_name(item_master_obj.imported_item_finish)
    inf_bom_array = collate_inf_bom(item_master_obj.id)
    data['inf_bom'] = []
    for cur_inf_bom in inf_bom_array:
        cur_inf_bom_obj = get_object_or_404(item_master, id=cur_inf_bom[0])
        data['inf_bom'].append((cur_inf_bom_obj, cur_inf_bom[1]))
    imm_bom_array = ast.literal_eval(item_master_obj.bom)
    data['imm_bom'] = []
    for cur_imm_bom in imm_bom_array:
        cur_imm_bom_obj = get_object_or_404(item_master, id=cur_imm_bom[0])
        data['imm_bom'].append((cur_imm_bom_obj, cur_imm_bom[1]))
    fin_type = get_fin_type(item_master_obj.imported_item_code[:21])
    data['fin_type'] = fin_type[0]
    data['pl_availability'] = fin_type[1]
    return(render(request, 'journal_mgmt/item_master_detail.html', {'data': data}))

def item_master_index(request):
    data = {}
    result_list = []
    data['item_group_opt'] = item_group.objects.all().order_by('name')
    index_url = reverse('journal_mgmt:item_master_index')
    page_no = 1
    searched_str = ''
    group_str = '*All*'
    data['sel_item_group'] = '*All*'
    if request.GET:
        get_data = request.GET
        if 'group_id' in get_data:
            try:
                int(get_data['group_id'])
            except:
                result_list = item_master.objects.all().order_by('name')
            else:
                item_group_obj = get_object_or_404(item_group, id=int(get_data['group_id']))
                data['sel_item_group'] = item_group_obj
                group_str = str(item_group_obj.id)
                result_list = item_group_obj.item_master_set.all().order_by('name')
            searched_str = get_data['name_search']
            data['searched_name'] = searched_str
            searched_name_set = searched_str.split('!!')
            for cur_name_search in searched_name_set:
                result_list = result_list.filter(name__icontains=cur_name_search)
            data['result_list'] = result_list
        if 'page_no' in get_data:
            page_no = int(get_data['page_no'])
    index_url += '?name_search=' + searched_str + '&group_id=' + group_str
    data['index_url'] = index_url
    data = pagination_detail(data, result_list, 100)
    data['result_list'] = result_list[(page_no - 1) * 100:page_no * 100]
    data['page_no'] = page_no
    return(render(request, 'journal_mgmt/item_master_index.html', {'data': data}))

def item_master_save(request):
    if request.POST:
        post_data = request.POST 
        inf_bom = infinite_update([(post_data['part_no'], post_data['fin_no'], 1.0)], True, {'auto_update':False})
        item_master_obj = get_object_or_404(item_master, imported_item_code=post_data['part_no'], imported_item_finish=post_data['fin_no'])
        if '_save' in post_data:
            return HttpResponseRedirect(reverse('journal_mgmt:item_master_index', args=()))
        elif '_addanother' in post_data:
            return HttpResponseRedirect(reverse('journal_mgmt:item_master_create', args=()))
        elif '_continue' in post_data: 
            return HttpResponseRedirect(reverse('journal_mgmt:item_master_detail', args=(item_master_obj.id,)))
        return HttpResponseRedirect(reverse('journal_mgmt:item_master_index', args=()))

def auto_rmp_supplier_detail(request, auto_rmp_id, sup_type, pl_sup_id):
    data = {}
    auto_rmp_obj = get_object_or_404(rmp_auto, id=auto_rmp_id)
    data['auto_rmp'] = auto_rmp_obj
    data['supplier_opt'] = []
    get_data = request.GET
    data['type'] = sup_type
    data['pl_vendor_id'] = 0
    data['pl_work_center_id'] = 0
    if get_data:
        if data['type'] == 'vendor':
            '''get all vendors - job work & purchase'''
            data['pl_vendor_id'] = pl_sup_id
            pl_sup_obj = get_object_or_404(vendor_price_list_auto, id=pl_sup_id)
            vendor_rmp_set = vendor_rmp_auto.objects.filter(rmp=auto_rmp_obj, vendor=pl_sup_obj.vendor)
            if len(vendor_rmp_set) > 0:
                rmp_sup = vendor_rmp_set[0]
            else:
                rmp_sup = vendor_rmp_auto(rmp=auto_rmp_obj, vendor=pl_sup_obj.vendor, name=pl_sup_obj.name)
        
        elif data['type'] == 'work_center':
            data['pl_work_center_id'] = pl_sup_id
            pl_sup_obj = get_object_or_404(work_center_price_list_auto, id=pl_sup_id)
            work_center_rmp_set = work_center_rmp_auto.objects.filter(rmp=auto_rmp_obj, work_center=pl_sup_obj.work_center)
            if len(work_center_rmp_set) > 0:
                rmp_sup = work_center_rmp_set[0]
            else:
                rmp_sup = work_center_rmp_auto(rmp=auto_rmp_obj, work_center=pl_sup_obj.work_center, name=pl_sup_obj.name)
        
        rmp_sup.name = pl_sup_obj.name
        rmp_sup.save()
        data['rmp_supply'] = rmp_sup
        data['auto_pl_id'] = get_data['auto_pl_id']
        data['item_master_id'] = get_data['item_master_id']
    return(render(request, 'journal_mgmt/auto_rmp_supplier.html', {'data': data}))
    
def auto_rmp_supplier_save(request, rmp_supply_id):
    data = {}
    mdl = []
    post_data = request.POST
    pl_vendor_id = 0
    pl_work_center_id = 0
    if post_data:
        # return(render(request, 'journal_mgmt/test_response.html', {'data': post_data}))
        auto_pl_id = int(post_data['auto_pl_id'])
        item_master_id = int(post_data['item_master_id'])
        if post_data['type'] == 'vendor':
            rmp_supply = get_object_or_404(vendor_rmp_auto, id=int(post_data['rmp_supply_id']))
            pl_vendor_id = post_data['pl_vendor_id']
        elif post_data['type'] == 'work_center':
            rmp_supply = get_object_or_404(work_center_rmp_auto, id=int(post_data['rmp_supply_id']))
            pl_work_center_id = post_data['pl_work_center_id']
        # return(render(request, 'journal_mgmt/test_response.html', {'data': rmp_supply.name}))
        rmp_supply.rate = Decimal(post_data['rmp_supply_value'])
        rmp_supply.save()
        data['message'] = 'New Supplier Added Successfully'
        # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
    data['message'] = 'No Data'
    return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_detail', args=(auto_pl_id,)) + '?item_master=' + str(item_master_id)\
                                             + '&vendor=' + str(pl_vendor_id) + '&work_center=' + str(pl_work_center_id))
    # return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
        
def auto_rmp_create(request):
    data = {}
    data['type'] = 'rmp'
    return(render(request, 'journal_mgmt/auto_rmp_con_detail.html', {'data': data}))

def auto_rmp_detail(request, auto_rmp_id):
    data = {}
    data['model'] = get_object_or_404(rmp_auto, id=auto_rmp_id)
    data['type'] = 'rmp'
    if request.GET:
        get_data = request.GET
        data['model_id'] = get_data['model_id']
    return(render(request, 'journal_mgmt/auto_rmp_con_detail.html', {'data': data}))
    

def auto_rmp_save(request):
    post_data = request.POST
    if post_data:
        post_id = post_data['model_id'] 
        try:
            int(post_id)
        except:
            # return(render(request, 'journal_mgmt/test_response.html', {'data': 'exception'}))
            auto_rmp_obj = rmp_auto()
            auto_rmp_obj.created_date = timezone.now()
        else:
            # return(render(request, 'journal_mgmt/test_response.html', {'data': 'No exception'}))
            auto_rmp_obj = get_object_or_404(rmp_auto, id=int(post_data['model_id']))
        auto_rmp_obj.name = post_data['model_name']
        auto_rmp_obj.rmp_sale_rate = post_data['rmp_sale_rate']
        auto_rmp_obj.last_updated = timezone.now()
        auto_rmp_obj.save()
        data = {'message':'item ' + post_data['model_name'] + ' saved successfully'}
        return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
        
def constants_create(request):
    data = {}
    data['type'] = 'con'
    return(render(request, 'journal_mgmt/auto_rmp_con_detail.html', {'data': data}))

def constants_detail(request, constants_id):
    data = {}
    data['model'] = get_object_or_404(constants, id=constants_id)
    data['type'] = 'con'
    if request.GET:
        get_data = request.GET
        data['model_id'] = get_data['model_id']
    return(render(request, 'journal_mgmt/auto_rmp_con_detail.html', {'data': data}))
    

def constants_save(request):
    post_data = request.POST
    if post_data:
        post_id = post_data['model_id']
        try:
            int(post_id)
        except:
            # return(render(request, 'journal_mgmt/test_response.html', {'data': 'exception'}))
            auto_con_obj = constants()
            auto_con_obj.created_date = timezone.now()
        else:
            # return(render(request, 'journal_mgmt/test_response.html', {'data': 'No exception'}))
            auto_con_obj = get_object_or_404(constants, id=int(post_data['model_id']))
        auto_con_obj.name = post_data['model_name']
        auto_con_obj.constant_value = post_data['constant_value']
        auto_con_obj.last_updated = timezone.now()
        auto_con_obj.save()
        data = {'message':'item ' + post_data['model_name'] + ' saved successfully'}
        return(render(request, 'journal_mgmt/test_response.html', {'data': data}))


def shipment_create(request):
    data = {}
    if request.POST:
        post_data = request.POST
        oc_ttype = get_object_or_404(transaction_type, transaction_type_ref_no=59)
        oc_opt = transaction_ref.objects.filter(transaction_type=oc_ttype, submit=True, active=True)
        tpl_obj_set = []
        if 'oc_name' in post_data:
            data['oc_name'] = post_data['oc_name']
            searched_name = post_data['oc_name'].split('!!')
            for cur_name_search in searched_name:
                oc_opt = oc_opt.filter(name__icontains=cur_name_search)
        if 'project_name' in post_data:
            data['project_name'] = post_data['project_name']
            search_dict = {'project':post_data['project_name']}
            oc_opt = tref_field_filter(oc_opt, search_dict)
        if 'order_confirmation' in post_data:
            oc_obj = get_object_or_404(transaction_ref, id=int(post_data['order_confirmation']))
            data['sel_oc'] = oc_obj
            tpl_ttype = get_object_or_404(transaction_type, transaction_type_ref_no=2)
            app_tpl = transaction_ref.objects.filter(transaction_type=tpl_ttype, submit=True, active=True)
            search_dict = {'order_confirmation':str(oc_obj.id)}
            tpl_obj_set = tref_field_filter(app_tpl, search_dict)
        data['oc_opt'] = []
        for cur_oc in oc_opt:
            data['oc_opt'].append((cur_oc, ast.literal_eval(cur_oc.data)))
            oc_opt = transaction_ref.objects.filter(transaction_type=oc_ttype, submit=True, active=True)
        data['app_tpl'] = []
        for cur_tpl in tpl_obj_set:
            data['app_tpl'].append((cur_tpl, ast.literal_eval(cur_tpl.data)))
    return(render(request, 'journal_mgmt/shipment_create.html', {'data': data}))


def mrs_preview(request, tref_id):
    data = {}
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    inv_jour_list = inventory_journal.objects.filter(transaction_ref=tref)
    mrs_feed = []
    bom_data = []
    for cur_inv_jour in inv_jour_list:
        mrs_feed.append((cur_inv_jour.item_master.id, cur_inv_jour.balance_qty))
    if request.GET:
        get_data = request.GET
        config = {'multi_layer':get_data['multi_layer']}
        bom_data = bom_collation(mrs_feed, config)
        if 'nested' in get_data:
            bom_data['nested_rm_list'] = []
            nest_res = composite_nest(bom_data['rm_list'])
            for cur_part in nest_res['rm_list']:
                bom_data['nested_rm_list'].append(cur_part)
            nest_res['new_ofct'] = []
            for cur_part in nest_res['new_ofct']:
                bom_data['new_ofct'].append(cur_part)
    new_bom_data = {}
    for cur_bom_key, cur_bom_val in bom_data.items():
        obj_list = conv_part_id_to_obj(cur_bom_val)
        new_bom_data[cur_bom_key] = dj_obj_list_sort(obj_list, {'obj_index':0, 'obj_param':'name'})  # obj_list.sort(key=lambda obj: obj[0].name)
    data['bom_data'] = new_bom_data
    data['tref_obj'] = tref
    return(render(request, 'journal_mgmt/mrs_preview.html', {'data': data}))


def job_shop_order_preview(request, tref_id):
    data = {}
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    if tref.submit == True:
        return HttpResponseRedirect(reverse('journal_mgmt:job_shop_order', args=(tref_id,)))
    inv_jour_list = inventory_journal.objects.filter(transaction_ref=tref)
    plan_dict = job_shop_plan(tref_id)
    rec_item_obj_list = plan_dict['receivable']
    pre_nest_rm_obj_list = plan_dict['pre_nest_rm_req']
    nested_rm_obj_list = plan_dict['nested_rm_req']
    ttype_obj_dict = get_job_shop_ttype(tref.id)
    if request.POST:
        post_data = request.POST
        item_id_prefix = 'item_master_id_'
        mod_qty_prefix = 'mod_qty_'
        mod_qty_dict = {}
        i = 1
        while i < 1000:
            item_id_str = item_id_prefix + str(i)
            mod_qty_str = mod_qty_prefix + str(i)
            if item_id_str in post_data:
                item_master_id = int(post_data[item_id_str])
                cur_qty = float(post_data[mod_qty_str])
                mod_qty_dict[item_master_id] = cur_qty
            else:
                break
            i += 1
        i = 0
        for cur_nest_rm in nested_rm_obj_list:
            mod_qty = mod_qty_dict[cur_nest_rm[0].id]
            nested_rm_obj_list[i][1] += mod_qty
            # nested_rm_feed_list[i][1] += mod_qty
            nested_rm_obj_list[i][2]['mod_qty'] = mod_qty
            nested_rm_obj_list[i][2]['tot_qty'] = nested_rm_obj_list[i][1]
            # nested_rm_feed_list[i][2]['mod_qty'] = mod_qty
            i += 1
    validation_data = job_shop_stk_validate(tref_id, nested_rm_obj_list)
    job_shop_validity = validation_data['valid']
    foreign_stk_data = validation_data['foreign_stk']
    plant_stk_data = validation_data['plant_stk']
    rm_util_item_obj_list = validation_data['rm_util_item_obj_list']
    mov_rm_item_obj_list = validation_data['mov_rm_item_obj_list']
    if request.POST and job_shop_validity == True:
        if not tref.submit == True and ('submit_and_no_indent' in post_data or 'submit_and_rm_indent' in post_data or 'submit_and_all_indent' in post_data):
            '''Creating components receivable'''
            rec_item_feed_list = feed_list_prep(rec_item_obj_list)
            pre_nest_rm_feed_list = feed_list_prep(pre_nest_rm_obj_list)
            nested_rm_feed_list = feed_list_prep(nested_rm_obj_list)
            rec_ttype = ttype_obj_dict['receivable']
            pre_nest_rm_ttype = ttype_obj_dict['pre_nested_rm']
            nested_rm_ttype = ttype_obj_dict['nested_rm']
            rm_util_ttype = ttype_obj_dict['rm_utilization']
            mov_rm_ttype = ttype_obj_dict['move_rm']
            mov_rm_field_list = ttype_obj_dict['move_rm_field_list']
            material_inward_ttype = ttype_obj_dict['material_inward']
            mov_feed_list = job_shop_mov_feed_prepare(material_inward_ttype, mov_rm_item_obj_list)
            mov_rm_tref = auto_create_tref(mov_rm_ttype.transaction_type_ref_no, \
                                           {'field_list':mov_rm_field_list}, mov_feed_list, False, {'chain_tref':tref.id})
            mov_rm_tref = tref_submit(mov_rm_tref.id)
            rec_tref_dict = fetch_tref_data(rec_ttype, [], {})['tref_data']['field_list']
            rec_tref = auto_create_tref(rec_ttype.transaction_type_ref_no, \
                                        rec_tref_dict, rec_item_feed_list, False, {'chain_tref':tref.id})
            pre_nest_rm_tref_dict = fetch_tref_data(pre_nest_rm_ttype, [], {})['tref_data']['field_list']
            pre_nested_tref = auto_create_tref(pre_nest_rm_ttype.transaction_type_ref_no, \
                                               pre_nest_rm_tref_dict, pre_nest_rm_feed_list, False, {'chain_tref':tref.id})
            nested_rm_tref_dict = fetch_tref_data(nested_rm_ttype, [], {})['tref_data']['field_list']
            nested_rm_tref = auto_create_tref(nested_rm_ttype.transaction_type_ref_no, \
                                           nested_rm_tref_dict, nested_rm_feed_list, False, {'chain_tref':tref.id})
            
            tref = tref_submit(tref.id)
            pre_nested_tref = tref_submit(pre_nested_tref.id)
            nested_rm_tref = tref_submit(nested_rm_tref.id)
            rm_util_feed_list = []
            nested_inv_jour = inventory_journal.objects.filter(transaction_ref=nested_rm_tref)
            for cur_nest_inv_jour in nested_inv_jour:
                rm_util_feed_list.append([cur_nest_inv_jour.id, cur_nest_inv_jour.balance_qty, {'tpl_ref':cur_nest_inv_jour.tpl_ref_no}])
            rm_util_tref_dict = fetch_tref_data(rm_util_ttype, [], {})['tref_data']['field_list']
            rm_util_tref = auto_create_tref(rm_util_ttype.transaction_type_ref_no, \
                                           rm_util_tref_dict, rm_util_feed_list, False, {})
            rm_util_tref = allocate_list(rm_util_tref.id)
            rm_util_tref = tref_submit(rm_util_tref.id)
            return HttpResponseRedirect(reverse('journal_mgmt:job_shop_order', args=(tref_id,)))
    data['process'] = inv_jour_list
    data['receivable'] = rec_item_obj_list
    data['rm_req'] = pre_nest_rm_obj_list
    data['nested_rm_req'] = nested_rm_obj_list
    data['plant_stk_data'] = plant_stk_data
    data['foreign_stk_data'] = foreign_stk_data
    data['ref_name'] = ttype_obj_dict['ref_name']
    data['tref'] = tref
    return(render(request, 'journal_mgmt/job_shop_order_preview.html', {'data': data}))   

def job_shop_order(request, tref_id):
    data = {}
    tref = get_object_or_404(transaction_ref, id=tref_id)
    process_item_list = inventory_journal.objects.filter(transaction_ref=tref)
    ttype_obj_dict = get_job_shop_ttype(tref.id)
    rec_tref = get_object_or_404(transaction_ref, chain_tref=tref.id, transaction_type=ttype_obj_dict['receivable'])
    rec_item_list = inventory_journal.objects.filter(transaction_ref=rec_tref)
    pre_nest_rm_tref = get_object_or_404(transaction_ref, chain_tref=tref.id, transaction_type=ttype_obj_dict['pre_nested_rm'])
    pre_nest_rm_item_list = inventory_journal.objects.filter(transaction_ref=pre_nest_rm_tref)
    nested_rm_tref = get_object_or_404(transaction_ref, chain_tref=tref.id, transaction_type=ttype_obj_dict['nested_rm'])
    nested_rm_item_list = inventory_journal.objects.filter(transaction_ref=nested_rm_tref)
    data['process'] = process_item_list
    data['receivable'] = rec_item_list
    data['rm_req'] = pre_nest_rm_item_list
    data['nested_rm_req'] = nested_rm_item_list
    data['tref'] = tref
    return(render(request, 'journal_mgmt/job_shop_order.html', {'data': data}))

def tpl_auto_plan(request, tref_id):
    data = {}
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    inv_jour_list = inventory_journal.objects.filter(transaction_ref=tref)
    inv_jour_list = inv_jour_list.filter(balance_qty__gt = 0)
    state_opt = state.objects.all().order_by('name')
    city_opt = city.objects.all().order_by('name')
    state_list = []
    city_list = []
    mrs_feed = []
    vendor_name_list = []
    bom_data = []
    # data['tpl_inv_jour'] = []
    data['tpl_inv_jour'] = {}
    data['tref'] = tref
    if tref.submit == True:
        for cur_inv_jour in inv_jour_list:
            # get_stock_data(cur_inv_jour.item_master, cur_inv_jour.tpl_ref_no)
            add_data = {}
            vendor_name = ''
            pro_qty = 0
            all_qty = 0
            pur_qty = 0
            cur_action_bal_qty = float(cur_inv_jour.balance_qty)
            cur_location = get_object_or_404(location, id=int(cur_inv_jour.location_ref_val))
            cur_app_stock = current_stock.objects.filter(item_master_ref=cur_inv_jour.item_master, location_ref=cur_location, tpl_ref_no = 0)
            cur_app_stock = cur_app_stock.filter(Q(tpl_ref_no=0) | Q(tpl_ref_no=None))
            temp_stk_cons = {}#gives the temporary stock consumption in order to give the right suggestion
            if len(cur_app_stock) > 0:
                cur_stock = cur_app_stock[0].cur_stock
            else:
                cur_stock = 0
            real_stock = copy.deepcopy(cur_stock)
            if not cur_inv_jour.item_master.id in temp_stk_cons:
                temp_stk_cons[cur_inv_jour.item_master.id] = 0
            cur_stock -= temp_stk_cons[cur_inv_jour.item_master.id]
            if cur_stock > 0:
                if cur_action_bal_qty <= cur_stock:
                    all_qty = cur_action_bal_qty
                else:
                    all_qty = cur_stock
                temp_stk_cons[cur_inv_jour.item_master.id] += all_qty
            cur_action_bal_qty -= all_qty
            if len(ast.literal_eval(cur_inv_jour.item_master.bom)) > 0 and cur_action_bal_qty > 0:
                pro_qty = cur_action_bal_qty - all_qty
                cur_action_bal_qty -= pro_qty
            elif cur_action_bal_qty > 0:
                pur_qty = cur_action_bal_qty
                cur_action_bal_qty -= pur_qty
            add_data['cur_stk_qty'] = real_stock
            add_data['all_qty'] = all_qty
            add_data['pro_qty'] = pro_qty
            add_data['pur_qty'] = pur_qty
            add_data['new_balance_qty'] = cur_action_bal_qty
            cur_vendor_pl_opt = vendor_price.objects.filter(item=cur_inv_jour.item_master).order_by('vendor__name')
            add_data['vendor_pl_opt'] = cur_vendor_pl_opt
            add_data['sel_vendor_id'] = '-'
            data['tpl_inv_jour'][cur_inv_jour.id] = [cur_inv_jour, add_data]
            '''add_data['state_opt'] = select_boxes({'name':'state'})
            add_data['city_opt'] = select_boxes({'name':'city'})    
            add_data['vendor_name_list'] = vendor_name_list'''
            # data['tpl_inv_jour'].append((cur_inv_jour, add_data))
            data['tpl_inv_jour'][cur_inv_jour.id] = [cur_inv_jour, add_data]
        if request.POST:
            post_data = request.POST
            i = 1
            name_dict = {}
            vendor_dict = {}
            pur_ind_list = []
            bom_feed_list = []
            all_ind_list = []
            po_detail_list = []
            error = 0
            while i < 1000:
                id_key = 'inv_jour_id!!' + str(i)
                if id_key in post_data:
                    add_data = {}
                    inv_jour_id = int(post_data[id_key])
                    cur_inv_jour = get_object_or_404(inventory_journal, id=inv_jour_id)
                    all_qty = float(post_data['all_qty!!' + str(i)])
                    pro_qty = float(post_data['pro_qty!!' + str(i)])
                    pur_qty = float(post_data['pur_qty!!' + str(i)])
                    sel_vendor_pl_key = 'sel_vendor_' + str(i)
                    cur_vendor_pl_opt = vendor_price.objects.filter(item=cur_inv_jour.item_master).order_by('vendor__name')
                    add_data['vendor_pl_opt'] = cur_vendor_pl_opt
                    cur_app_stock = current_stock.objects.filter(item_master_ref=cur_inv_jour.item_master, location_ref=cur_location, tpl_ref_no = 0)
                    cur_app_stock = cur_app_stock.filter(Q(tpl_ref_no=0) | Q(tpl_ref_no=None))
                    temp_stk_cons = {}#gives the temporary stock consumption in order to give the right suggestion
                    bal_qty = float(cur_inv_jour.balance_qty)
                    if len(cur_app_stock) > 0:
                        cur_stock = cur_app_stock[0].cur_stock
                    else:
                        cur_stock = 0
                    real_stock = copy.deepcopy(cur_stock)
                    try:
                        int(post_data[sel_vendor_pl_key])
                    except:
                        pur_qty = 0
                    else:
                        sel_vendor_pl_id = int(post_data[sel_vendor_pl_key])
                        sel_vendor_pl_obj = get_object_or_404(vendor_price, id=sel_vendor_pl_id)
                        sel_vendor_id = sel_vendor_pl_obj.vendor.id
                        sel_vendor_name = sel_vendor_pl_obj.vendor.name
                        add_data['sel_vendor_id'] = sel_vendor_id
                        if pur_qty > 0:
                            if not sel_vendor_id in vendor_dict:
                                vendor_dict[sel_vendor_id] = []
                                vendor_name_list.append({'name':sel_vendor_name, 'id':sel_vendor_id})
                            vendor_dict[sel_vendor_id].append((inv_jour_id, pur_qty, {'tpl_ref':tref.id}))
                            #add_data['new_balance_qty'] = bal_qty - pur_qty - all_qty  - pro_qty 
                        '''if all_qty > 0:
                            if not sel_vendor_id in name_dict:
                                name_dict[sel_vendor_id] = []
                                vendor_name_list.append({'name':sel_vendor_name, 'id':sel_vendor_id})
                            name_dict[sel_vendor_id].append((inv_jour_id, pur_qty, {'tpl_ref':tref.id}))
                            add_data['new_balance_qty'] = bal_qty - all_qty - pro_qty - pur_qty'''
                        '''if pro_qty > 0:
                            if not sel_vendor_id in name_dict:
                                name_dict[sel_vendor_id] = []
                                vendor_name_list.append({'name':sel_vendor_name, 'id':sel_vendor_id})
                            name_dict[sel_vendor_id].append((inv_jour_id, pur_qty, {'tpl_ref':tref.id}))
                            add_data['new_balance_qty'] = bal_qty - all_qty - pro_qty - pur_qty'''
                    #add_data['state_opt'] = select_boxes({'name':'state'})
                    #add_data['city_opt'] = select_boxes({'name':'city'}) 
                    add_data['cur_stk_qty'] = real_stock
                    add_data['all_qty'] = all_qty
                    add_data['pro_qty'] = pro_qty
                    add_data['pur_qty'] = pur_qty
                    add_data['new_balance_qty'] = bal_qty - all_qty - pro_qty - pur_qty
                    if add_data['new_balance_qty'] >= 0:
                        data['tpl_inv_jour'][cur_inv_jour.id] = [cur_inv_jour, add_data]
                        '''if pur_qty > 0.0:
                            pur_ind_list.append((cur_inv_jour.id, pur_qty, {'tpl_ref':tref.id}))'''
                        if pro_qty > 0.0:
                            '''dictionary will be added when auto_create_prod is called'''
                            bom_feed_list.append((cur_inv_jour.item_master.id, pro_qty))
                        if all_qty > 0.0:
                            all_ind_list.append((cur_inv_jour.id, all_qty, {'tpl_ref':tref.id, 'location_ref':get_location_raw('plant', 1).id}))
                    else:
                        error = 1
                else:
                    break
                i += 1
            i = 1
            while i < 100:
                vendor_id = 'vendor_id_' + str(i)
                if vendor_id in post_data:
                    sel_vendor_id = int(post_data[vendor_id])
                else:
                    break
                add_data['vendor_id'] = sel_vendor_id
                ship_to = 'ship_to_' + str(i)
                if ship_to in post_data:
                    sel_ship_to = str(post_data[ship_to])
                    add_data['ship_to'] = sel_ship_to
                shiping_address_line_1 = 'shiping_address_line_1_' + str(i)
                if shiping_address_line_1 in post_data:
                    sel_shiping_address_line_1 = str(post_data[shiping_address_line_1])
                    add_data['shiping_address_line_1'] = sel_shiping_address_line_1
                shiping_address_line_2 = 'shiping_address_line_2_' + str(i)
                if shiping_address_line_2 in post_data:
                    sel_shiping_address_line_2 = str(post_data[shiping_address_line_2])
                    add_data['shiping_address_line_2'] = sel_shiping_address_line_2
                sel_city = 'sel_city_' + str(i)
                if sel_city in post_data:
                    sel_city = str(post_data[sel_city])
                    add_data['sel_city'] = sel_city
                sel_state = 'sel_state_' + str(i)
                if sel_state in post_data:
                    sel_state = str(post_data[sel_state])
                    add_data['sel_state'] = sel_state
                date = 'date_' + str(i)
                if date in post_data:
                    date = str(post_data[date])
                    add_data['date'] = date
                i += 1
                po_detail_list.append((add_data['vendor_id'], add_data['ship_to'], add_data['shiping_address_line_1'],
                add_data['shiping_address_line_2'], add_data['sel_city'], add_data['sel_state'], add_data['date']))
            add_data['po_detail_list'] = po_detail_list
            add_data['vendor_dict'] = vendor_dict
            data['state_opt'] = select_boxes({'name':'state'})
            data['city_opt'] = select_boxes({'name':'city'})
            data['vendor_name_list'] = vendor_name_list
            if 'save' in post_data and error == 0:
                ttype = tref.transaction_type
                if len(vendor_dict) == len(po_detail_list):
                    for cur_vendor_id, jour_det_list in vendor_dict.items():
                        '''Purchase ttype ref number is 7'''
                        pur_ord_ttype_obj = get_object_or_404(transaction_type, transaction_type_ref_no=7)
                        pur_ord_tref_dict = fetch_tref_data(pur_ord_ttype_obj, [], {})['tref_data']['field_list']
                        pur_ord_tref_dict['vendor'] = (cur_vendor_id, vendor_name)
                        for cur_vendor in po_detail_list:
                            if cur_vendor_id == cur_vendor[0]:
                                pur_ord_tref_dict['ship_to'] = cur_vendor[1]
                                pur_ord_tref_dict['shipping_addr_line1'] = cur_vendor[2]
                                pur_ord_tref_dict['shipping_addr_line2'] = cur_vendor[3]
                                pur_ord_tref_dict['city'] = cur_vendor[4]
                                pur_ord_tref_dict['state'] = cur_vendor[5]
                                pur_ord_tref_dict['delivery_date'] = cur_vendor[6]
                        auto_create_tref(7, {'field_list':pur_ord_tref_dict}, jour_det_list, True, {})
                    '''
                    purchase indent disabled as purchase order is directly released
                    if len(pur_ind_list) > 0:
                        pur_ttype_obj = get_object_or_404(transaction_type, transaction_type_ref_no=5)
                        pur_tref_dict = fetch_tref_data(pur_ttype_obj, [], {})['tref_data']['field_list']
                        auto_create_tref(5, pur_tref_dict, pur_ind_list, True, {})
                    bom_data = bom_collation(bom_feed_list, {'multi_layer':True})
                    pro_ind_list = []
                    pro_ind_list = bom_data['final_process_list']
                    pro_ind_list += bom_data['sub_process_list']'''
                if len(bom_feed_list) > 0:
                    auto_create_prod_ind(get_location_raw('plant', 1).id, tref.id, bom_feed_list)
                if len(all_ind_list) > 0:
                    all_ttype_obj = get_object_or_404(transaction_type, transaction_type_ref_no=36)
                    all_tref_dict = fetch_tref_data(all_ttype_obj, [], {})['tref_data']['field_list']
                    all_tref = auto_create_tref(36, all_tref_dict, all_ind_list, False, {})
                    all_tref = allocate_list(all_tref.id)
                    if all_tref == 'error':
                        return HttpResponseRedirect(reverse('journal_mgmt:tpl_auto_plan', args=(tref.id,)))
                    all_tref = tref_submit(all_tref.id)
        # config = {'multi_layer':get_data['multi_layer']}
        # bom_data = bom_collation(mrs_feed)
    # data['bom_data'] = bom_data
    return(render(request, 'journal_mgmt/tpl_auto_plan.html', {'data': data}))

@login_required(login_url='/journal_mgmt/login')
def vendor_pl_index(request):
    data = {}
    sel_vendor_id = '*All*'
    sel_item_group_id = '*All*'
    item_name_search = ''
    price_list = vendor_price.objects.all().order_by('vendor')
    page_no = 1
    if request.GET:
        get_data = request.GET
        sel_vendor_id = get_data['sel_vendor_id']
        if 'sel_vendor_id' in get_data:
            try:
                sel_vendor_id = int(sel_vendor_id)
            except:
                '''do nothing'''
            else:
                sel_vendor_id = int(sel_vendor_id)
    if request.POST:
        post_data = request.POST
        if 'sel_vendor' in post_data:
            try:
                int(post_data['sel_vendor'])
            except:
                '''Do Nothing'''
            else:
                sel_vendor_id = post_data['sel_vendor']
                sel_vendor_obj = get_object_or_404(coa, id=sel_vendor_id)
                price_list = price_list.filter(vendor=sel_vendor_obj)
        if 'sel_item_group' in post_data:
            try:
                int(post_data['sel_item_group'])
            except:
                '''Do Nothing'''
            else:
                sel_item_group_id = post_data['sel_item_group']
                sel_item_group_obj = get_object_or_404(item_group, id=sel_item_group_id)
                temp_pl = price_list
                for cur_temp_pl in temp_pl:
                    if not cur_temp_pl.item.item_group == sel_item_group_obj:
                        price_list = price_list.exclude(id=cur_temp_pl.id)
        if 'item_name_search' in post_data:
            item_name_search = post_data['item_name_search']
            data['item_name_search'] = item_name_search
            searched_name_set = item_name_search.split('!!')
            for cur_name_search in searched_name_set:
                price_list = price_list.filter(item__name__icontains=cur_name_search)
            '''
            temp_pl = price_list
            for cur_temp_pl in temp_pl:
                str_found = True
                for cur_name_search in searched_name_set:
                    if not re.search(cur_name_search, cur_temp_pl.item_master.name, re.IGNORECASE):
                        str_found = False
                        break
                if str_found == False:
                    price_list = price_list.exclude(id=cur_temp_pl.id)
            '''
        if 'page_no' in post_data:
            page_no = int(post_data['page_no'])
    result_list = price_list
    data = pagination_detail(data, result_list, 100)
    data['page_no'] = page_no
    disp_result_end = page_no * 100
    if len(data['page_range']) > 0:
        if page_no == max(data['page_range']):
            disp_result_end = data['result_tot']
    data['sel_vendor_id'] = sel_vendor_id
    data['sel_item_group_id'] = sel_item_group_id
    data['item_name_search'] = item_name_search
    data['disp_result_list'] = result_list[(page_no - 1) * 100:disp_result_end]
    data['vendor_opt'] = select_boxes({'name':'vendor'})
    data['item_group_opt'] = item_group.objects.all().order_by('name')
    data['result_list'] = result_list
    return render(request, 'journal_mgmt/vendor_pl_index.html', {'data': data})

def web_gl_test(request):
    data = {}
    return render(request, 'journal_mgmt/web_gl_test.html', {'data': data})

def wc_pl_index(request):
    data = {}
    sel_wc_id = '*All*'
    sel_work_center_id = '*All*'
    sel_item_group_id = '*All*'
    item_name_search = ''
    price_list = work_center_price.objects.all().order_by('work_center')
    page_no = 1
    if request.GET:
        get_data = request.GET
        sel_work_center_id = get_data['sel_wc_id']
        if 'sel_work_center_id' in get_data:
            try:
                sel_work_center_id = int(sel_work_center_id)
            except:
                '''do nothing'''
            else:
                sel_work_center_id = int(sel_work_center_id)
    if request.POST:
        post_data = request.POST
        if 'sel_work_center' in post_data:
            try:
                int(post_data['sel_work_center'])
            except:
                '''Do Nothing'''
            else:
                sel_work_center_id = post_data['sel_work_center']
                sel_work_center_obj = get_object_or_404(coa, id=sel_work_center_id)
                price_list = price_list.filter(work_center=sel_work_center_obj)
        if 'sel_item_group' in post_data:
            try:
                int(post_data['sel_item_group'])
            except:
                '''Do Nothing'''
            else:
                sel_item_group_id = post_data['sel_item_group']
                sel_item_group_obj = get_object_or_404(item_group, id=sel_item_group_id)
                temp_pl = price_list
                for cur_temp_pl in temp_pl:
                    if not cur_temp_pl.item.item_group == sel_item_group_obj:
                        price_list = price_list.exclude(id=cur_temp_pl.id)
        if 'item_name_search' in post_data:
            item_name_search = post_data['item_name_search']
            data['item_name_search'] = item_name_search
            searched_name_set = item_name_search.split('!!')
            for cur_name_search in searched_name_set:
                price_list = price_list.filter(item__name__icontains=cur_name_search)
            '''
            temp_pl = price_list
            for cur_temp_pl in temp_pl:
                str_found = True
                for cur_name_search in searched_name_set:
                    if not re.search(cur_name_search, cur_temp_pl.item_master.name, re.IGNORECASE):
                        str_found = False
                        break
                if str_found == False:
                    price_list = price_list.exclude(id=cur_temp_pl.id)
            '''
        if 'page_no' in post_data:
            page_no = int(post_data['page_no'])
    result_list = price_list
    data = pagination_detail(data, result_list, 100)
    data['page_no'] = page_no
    disp_result_end = page_no * 100
    if len(data['page_range']) > 0:
        if page_no == max(data['page_range']):
            disp_result_end = data['result_tot']
    data['sel_work_center_id'] = sel_work_center_id
    data['sel_item_group_id'] = sel_item_group_id
    data['item_name_search'] = item_name_search
    data['disp_result_list'] = result_list[(page_no - 1) * 100:disp_result_end]
    data['wc_opt'] = select_boxes({'name':'work_center'})
    data['item_group_opt'] = item_group.objects.all().order_by('name')
    data['result_list'] = result_list
    return render(request, 'journal_mgmt/wc_pl_index.html', {'data': data})


def packing_list(request, tref_id):
    data ={}
    packing_list_dict = {}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    pl_item_list = inventory_journal.objects.filter(transaction_ref_id = tref_id)
    packing_list = []
    fin_number = '1-1-1-1-1-1-1-1-1-1-1-1-1'        
    
    for cur_item in pl_item_list:
        net_weight = 0    
        package_weight = 0        
        box_count = 0
        set_count = 0
        qty = 1328
        item_master_id = cur_item.item_master_id
        item_obj = get_object_or_404(item_master, id = item_master_id)
        item_weight = weight_vol_update(item_master_id, {'update_ip_factor':True})
        net_item_weight = item_weight['tot_weight']
        if net_item_weight == 0:
            print('skipping item : ' + item_obj.name)
            continue
        selected_spec_code = cur_item.item_master.imported_item_code[0:21]
        auto_pl_process_obj = get_object_or_404(auto_price_list, spec_code = selected_spec_code)
        selected_pl_id = auto_pl_process_obj.flite_360_price_list_id
        cursor.execute("select * from packing_set where parent_auto_pl_item = %d order by id;" % selected_pl_id)
        object = cursor.fetchall()
        packing_qty = qty
        total_packing_items_weight = []
        for cur_set in object:
            packing_items_list = []
            box_total_weight = 0
            big_box_item_qty = 0
            max_qty = cur_set[7]
            min_qty = cur_set[8]
            max_weight = cur_set[3]
            min_weight = cur_set[4]
            cursor.execute("select * from packing_items where packing_set_ref = %d ;" % cur_set[0])
            packing_items_object = cursor.fetchall()
            broken_item = param_break(item_obj.imported_item_code, item_obj.imported_item_finish)
            rmp_con = get_rmp_con(auto_pl_process_obj.id, 0, 'sale')
            for cur_packing_items in packing_items_object:
                if big_box_item_qty > 0:
                    set_count += 1
                if cur_packing_items[4] != "None":
                    dimension_eqn = str(cur_packing_items[4])
                    d1 = dim_cost_port(broken_item['pn'], auto_pl_process_obj.input_rate_sale, rmp_con[0], \
                                                             rmp_con[1], dimension_eqn, 1)
                    d1 = str(round(eval(d1), 2))
                else:
                    d1 = '0000'
                if len(d1) < 4:
                    d1 = int(d1) + 10000
                    d1 = str(d1)[1:]
                
                if cur_packing_items[5] != "None":
                    dimension_eqn = str(cur_packing_items[5])
                    d2 = dim_cost_port(broken_item['pn'], auto_pl_process_obj.input_rate_sale, rmp_con[0], \
                                                             rmp_con[1], dimension_eqn, 1)
                    d2 = str(round(eval(d2), 2))
                else:
                    d2 = '0000'
                if len(d2) < 4:
                    d2 = int(d2) + 10000
                    d2 = str(d2)[1:]
                if cur_packing_items[6] != "None":
                    dimension_eqn = str(cur_packing_items[6])
                    d3 = dim_cost_port(broken_item['pn'], auto_pl_process_obj.input_rate_sale, rmp_con[0], \
                                                             rmp_con[1], dimension_eqn, 1)
                    d3 = str(round(eval(d3), 2))
                else:
                    d3 = '0000'
                if len(d3) < 4:
                    d3 = int(d3) + 10000
                    d3 = str(d3)[1:]
                
                if cur_packing_items[7] != "None":
                    dimension_eqn = str(cur_packing_items[7])
                    d4 = dim_cost_port(broken_item['pn'], auto_pl_process_obj.input_rate_sale, rmp_con[0], \
                                                             rmp_con[1], dimension_eqn, 1)
                    d4 = str(round(eval(d4), 2))
                else:
                    d4 = '0000'
                if len(d4) < 4:
                    d4 = int(d4) + 10000
                    d4 = str(d4)[1:]
                cursor.execute("select * from price_list where id = %d ;" % cur_packing_items[3])
                pl_object = cursor.fetchall()
                for cur_pl_obj in pl_object:
                    item_spec_code =  str(cur_pl_obj[2] + 1000)[1:] +"-" + str(cur_pl_obj[3] + 100)[1:] +"-" + str(cur_pl_obj[4] + 100)[1:] +"-" + str(cur_pl_obj[5] + 1000)[1:] +"-" \
                            + str(cur_pl_obj[6] + 1000)[1:] +"-" + str(cur_pl_obj[7] + 1000)[1:]
                box_obj = get_object_or_404(auto_price_list, spec_code = item_spec_code)
                
                box_spec_code = box_obj.spec_code[0:21]
                part_no = str(box_spec_code)
                part_no += "-" + str(d1) + "-" + str(d2) + "-" + str(d3) + "-" + str(d4) 
                box_opt = item_master.objects.filter(imported_item_code = part_no, imported_item_finish = fin_number)
                if len(box_opt) == 0:
                    box_create = infinite_update([(part_no, fin_number, 1.0)], True, {'auto_update':True})
                box_item_master_obj = get_object_or_404(item_master, imported_item_code = part_no, imported_item_finish = fin_number) 
                box_item_id = box_item_master_obj.id
                box_weight = weight_vol_update(box_item_id, {'update_ip_factor':True})
                derivative_qty = cur_packing_items[8]
                data['part_description'] = part_description(part_no, fin_number, derivative_qty)
                box_size = data['part_description']['description']+ ' | ' + data['part_description']['size']
                packing_items_list.append(box_size)
                total_packing_items_weight.append(box_weight)
            set_weight = net_item_weight * float(max_qty) + float(box_weight['tot_weight'])
            if len(packing_items_list) > 1:
                data['set_count'] = len(packing_items_list)*2
                data['row_span'] = len(packing_items_list)*4
            else:
                data['set_count'] = len(packing_items_list)*2
                data['row_span'] = len(packing_items_list)*4
            if set_weight > max_weight:
                set_weight = net_item_weight * float(max_qty) - float(box_weight['tot_weight'])
                max_qty = float(set_weight)/float(net_item_weight)
                max_qty = divmod(max_qty, 1)[0]
                if max_qty < cur_set[7]:
                    """"""
                else:
                    max_qty = cur_set[7]
            if set_weight < min_weight:
                max_qty = float(set_weight)/float(net_item_weight)
                max_qty = divmod(max_qty, 1)[0]
                if max_qty < cur_set[7]:
                    """"""
                else:
                    max_qty = cur_set[7]
            if packing_qty > 0 :
                if packing_qty > max_qty:
                    item_packing_qty = packing_qty%max_qty
                    big_box_item_qty = packing_qty - item_packing_qty
                    box = big_box_item_qty/max_qty
                    packing_qty = packing_qty%max_qty
                    box_set = big_box_item_qty%max_qty
                    if box_set == 0:
                        big_box_item_qty = max_qty
                elif packing_qty >= min_qty: 
                    box = 1
                    big_box_item_qty = packing_qty
                    packing_qty = 0
                
                if big_box_item_qty > 0:
                    if not item_obj.id in packing_list_dict:
                        box_count += 1
                        for tot_box_weight in total_packing_items_weight:
                            box_total_weight += float(tot_box_weight['tot_weight'])
                        set_total_weight = float(big_box_item_qty) * float(net_item_weight)
                        package_weight = set_total_weight
                        net_weight = set_total_weight + box_total_weight
                        packing_list_dict[item_obj.id] = []
                        packing_list_dict[item_obj.id].append((item_obj.name, cur_set[1], big_box_item_qty, box, \
                                                               packing_items_list, round(net_item_weight, 2), \
                                                               round(set_total_weight, 2), round(net_weight, 2), \
                                                               data['set_count'], data['row_span']))
                        if packing_qty > min_qty: 
                            set_count += 1
                            box_count += 1
                            box = 1
                            big_box_item_qty = packing_qty
                            set_total_weight = float(big_box_item_qty) * float(net_item_weight)
                            package_weight += set_total_weight
                            packing_qty = 0
                            net_weight = set_total_weight + box_total_weight
                            packing_list_dict[item_obj.id].append(('', cur_set[1], big_box_item_qty, box,\
                                                                   packing_items_list, round(net_item_weight, 2),\
                                                                    round(set_total_weight, 2), round(net_weight, 2), \
                                                                    data['set_count'], data['row_span']))
                    else:
                        box_count += 1
                        for tot_box_weight in total_packing_items_weight:
                            box_total_weight += float(tot_box_weight['tot_weight'])
                        set_total_weight = float(big_box_item_qty) * float(net_item_weight)
                        package_weight += set_total_weight
                        net_weight = set_total_weight + box_total_weight
                        packing_list_dict[item_obj.id].append(('', cur_set[1], big_box_item_qty, box, \
                                                               packing_items_list, round(net_item_weight, 2), \
                                                               round(set_total_weight, 2), round(net_weight, 2), \
                                                               data['set_count'], data['row_span']))
                        
        data['net_weight'] = net_weight
        data['package_weight'] = package_weight
    data['packing_list_dict'] = packing_list_dict
    return(render(request, 'journal_mgmt/packing.html', {'data': data}))


def vendor_pl_detail(request):
    data = {}
    sel_vendor_id = '*All*'
    sel_item_group_id = '*All*'
    item_name_search = ''
    sel_pl = '-'
    sel_item_master_id = '-'
    auto_pl_opt = auto_price_list.objects.all().order_by('id')
    item_master_opt = item_master.objects.all().order_by('name')
    item_group_opt = item_group.objects.all().order_by('name')
    vendor_opt = vendor_price.objects.all().order_by('name')
    tax_format_opt = tax_format.objects.filter(active=True).order_by('name')
    sel_pl_obj_set = ['-']
    spec_code_list = []
    vendor_rmp_obj_set = []
    if request.GET:
        get_data = request.GET
        if 'sel_vendor_id' in get_data:
            sel_vendor_id = get_data['sel_vendor_id']
            if get_data:
                try:
                    sel_vendor_id = int(sel_vendor_id)
                except:
                    '''do nothing'''
                else:
                    sel_vendor_id = int(sel_vendor_id)
                    sel_vendor_obj = get_object_or_404(coa, id=sel_vendor_id)
    if request.POST:
        post_data = request.POST
        sel_vendor_id = int(post_data['sel_vendor'])
        if 'sel_item_master' in post_data:
            sel_item_master_id = int(post_data['sel_item_master'])
        sel_item_group_id = post_data['sel_item_group']
        
        '''Vendor filtering'''
        try:
            int(post_data['sel_vendor'])
        except:
            '''DO Nothing'''
        else:
            sel_vendor_id = int(post_data['sel_vendor'])
            sel_vendor_obj = get_object_or_404(coa, id=sel_vendor_id)
            pl_opt = vendor_price.objects.filter(vendor=sel_vendor_obj).order_by('item__name')
            vendor_rmp_opt = vendor_rmp_auto.objects.filter(vendor = sel_vendor_id)
            data['vendor_rmp_opt'] = vendor_rmp_opt
        '''Item Group filtering'''
        try:
            int(post_data['sel_item_group'])
        except:
            '''DO Nothing'''
        else:
            sel_item_group_id = int(post_data['sel_item_group'])
            sel_item_group_obj = get_object_or_404(item_group, id=sel_item_group_id)
            item_master_opt = item_master_opt.filter(item_group=sel_item_group_obj)
            pl_opt = pl_opt.filter(item__item_group=sel_item_group_obj)
            for cur_spec_code in pl_opt:
                item_id = cur_spec_code.item_id
                item_master_obj = get_object_or_404(item_master, id = item_id)
                sel_spec_code = item_master_obj.imported_item_code[0:21]
                auto_pl_opt = auto_pl_opt.filter(spec_code = sel_spec_code)
                for cur_auto_spec in auto_pl_opt:
                    auto_pl_obj = get_object_or_404(auto_price_list, id =cur_auto_spec.id )
                    if sel_spec_code == auto_pl_obj.spec_code:
                        spec_code_list.append((item_id, auto_pl_obj))
                    data['rmp_obj_set'] = [auto_pl_obj.p1, auto_pl_obj.p2, auto_pl_obj.p3, auto_pl_obj.p4, auto_pl_obj.p5, auto_pl_obj.p6, auto_pl_obj.p7, auto_pl_obj.p8, auto_pl_obj.p9, auto_pl_obj.p10, \
                           auto_pl_obj.p11, auto_pl_obj.p12, auto_pl_obj.p13, auto_pl_obj.p14, auto_pl_obj.p15, auto_pl_obj.p16, auto_pl_obj.p17, auto_pl_obj.p18, auto_pl_obj.p19, auto_pl_obj.p20]
                    rmp_obj_set = data['rmp_obj_set']
                    if len(auto_pl_obj.job_work_price_calc_eqn) < 2 :
                        data['constant_val'] = auto_pl_obj.input_rate_sale
            if len(spec_code_list) > 0:
                for cur_rmp in rmp_obj_set:
                    rmp_id = cur_rmp.id
                    rmp_auto_price_obj = get_object_or_404(rmp_auto , id = rmp_id) 
                    data['list'] = 'False'
                    for cur_vendor_rmp in vendor_rmp_opt:
                        if rmp_id == cur_vendor_rmp.rmp_id:
                            data['list'] = 'true'
                            if rmp_auto_price_obj.constant_value == False:
                                vendor_rmp_obj_set.append((cur_rmp, cur_vendor_rmp.rate, rmp_id, sel_vendor_id, auto_pl_obj.id, item_master_obj.id, cur_rmp.constant_value))
                            vendor_rmp_id = cur_vendor_rmp.rmp_id
                            break
                    if rmp_auto_price_obj.constant_value == True:
                        vendor_rmp_obj_set.append((cur_rmp, rmp_auto_price_obj.rmp_sale_rate, rmp_id, sel_vendor_id, auto_pl_obj.id, item_master_obj.id, cur_rmp.constant_value))
                    if data['list'] == 'False':
                        if rmp_auto_price_obj.constant_value == False:     
                            vendor_rmp_obj_set.append((cur_rmp, 0, rmp_id, sel_vendor_id, auto_pl_obj.id, item_master_obj.id, cur_rmp.constant_value))
            if not 'sel_pl' in post_data:
                sel_pl = '-'
        
        '''Item Name filtering'''
        if 'item_name_search' in post_data:
            item_name_search = post_data['item_name_search']
            searched_name_set = item_name_search.split('!!')
            for cur_str in searched_name_set:
                item_master_opt = item_master_opt.filter(name__icontains=cur_str)
                pl_opt = pl_opt.filter(item__name__icontains=cur_str)
            if not 'sel_pl' in post_data:
                sel_pl = '-'
            
        '''Item Master filtering'''
        try:
            int(post_data['sel_item_master'])
        except:
            '''DO Nothing'''
        else:
            if sel_pl == '-':
                sel_item_master_id = int(post_data['sel_item_master'])
            sel_item_master_obj = get_object_or_404(item_master, id=sel_item_master_id)
            sel_pl_obj_set = vendor_price.objects.filter(vendor=sel_vendor_obj, item=sel_item_master_obj) 
            
            if len(sel_pl_obj_set) == 1:
                sel_pl_obj = sel_pl_obj_set[0]
            elif len(sel_pl_obj_set) > 1:
                del_list = sel_pl_obj_set[1:]
                for cur_del in del_list:
                    cur_del.delete()
            elif len(sel_pl_obj_set) == 0:
                sel_pl = '-'
                if 'create' in post_data:
                    new_pl_obj = vendor_price(vendor=sel_vendor_obj, item=sel_item_master_obj)
                    new_pl_obj.save()
                
            sel_pl_obj_set = vendor_price.objects.filter(vendor=sel_vendor_obj, item=sel_item_master_obj)
            if len(sel_pl_obj_set) > 0:
                sel_pl_obj = get_object_or_404(vendor_price, vendor=sel_vendor_obj, item=sel_item_master_obj)
                sel_pl = sel_pl_obj.id
        
        '''Pl Selected filtering'''
        try:
            int(post_data['sel_pl'])
        except:
            '''DO Nothing'''
        else:
            sel_pl = int(post_data['sel_pl'])
            sel_pl_obj = get_object_or_404(vendor_price, id=sel_pl)
            sel_item_master_id = sel_pl_obj.item.id
        # sel_pl_obj_set = get_object_or_404(vendor = sel_vendor_obj, item = sel_item_master_obj)
        data['vendor_rmp_obj_set'] = vendor_rmp_obj_set
        if 'save' in post_data or 'pur_rate_similar_sizes' in post_data or 'jw_rate_similar_sizes' in post_data or 'jw_rate_all_variants' in post_data or 'eqn_jw_rate_similar_sizes' in post_data or 'eqn_jw_rate_all_variants' in post_data:
            sel_pl = int(post_data['sel_pl'])
            pl_obj = get_object_or_404(vendor_price, id=sel_pl)
            pl_obj.job_work_rate = float(post_data['jw_rate'])
            pl_obj.purchase_rate = float(post_data['pur_rate'])
            sel_jw_tax_format_id = int(post_data['jw_tax'])
            sel_pur_tax_format_id = int(post_data['pur_tax'])
            sel_jw_tax_format_obj = get_object_or_404(tax_format, id=sel_jw_tax_format_id)
            sel_pur_tax_format_obj = get_object_or_404(tax_format, id=sel_pur_tax_format_id)
            pl_obj.job_work_tax_format = sel_jw_tax_format_obj
            pl_obj.purchase_tax_format = sel_pur_tax_format_obj
            pl_obj.last_updated = timezone.now()
            pl_obj.save()
            if 'eqn_jw_rate_similar_sizes' in post_data or 'eqn_jw_rate_all_variants' in post_data:
                item_master_obj = get_object_or_404(item_master, id = pl_obj.item_id)
                broken_item = param_break(item_master_obj.imported_item_code, item_master_obj.imported_item_finish)
                rmp_con = get_rmp_con(auto_pl_obj.id, sel_vendor_id, 'vendor')
                changed_eqn = dim_cost_port(broken_item['pn'], auto_pl_obj.input_rate_sale, rmp_con[0], \
                                                     rmp_con[1], auto_pl_obj.input_factor_calc_eqn, 1)
                data['new_rate'] = round(eval(changed_eqn), 2)
                pl_obj.job_work_rate = data['new_rate']
                pl_obj.save()
            if 'change_eqn' in post_data:
                auto_pl_id = int(post_data['jc_id'])
                auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
                auto_pl_obj.job_work_price_calc_eqn = str(post_data['jc_eqn'])
                auto_pl_obj.save()
            if 'change_eqn_pur' in post_data:
                auto_pl_id = int(post_data['jc_id'])
                auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
                auto_pl_obj.purchase_price_calc_eqn = str(post_data['pc_eqn'])
                auto_pl_obj.save()
            pl_obj = get_object_or_404(vendor_price, id=sel_pl)
            if not 'save' in post_data:
                imp_item_code = pl_obj.item.imported_item_code
                item_spec_code = imp_item_code[:21]
                auto_pl_obj = get_object_or_404(auto_price_list, spec_code = item_spec_code)
                item_sim_sizes = item_master.objects.filter(imported_item_code = imp_item_code)
                item_all_sizes = item_master.objects.filter(imported_item_code__startswith = item_spec_code)
                if 'pur_rate_similar_sizes' in post_data or 'jw_rate_similar_sizes' in post_data or 'eqn_jw_rate_similar_sizes' in post_data:
                    loop_items = item_sim_sizes
                elif 'jw_rate_all_variants' in post_data or 'eqn_jw_rate_all_variants' in post_data:
                    loop_items = item_all_sizes
                for cur_item_master in loop_items:
                    vendor_pl_opt = vendor_price.objects.filter(item = cur_item_master, vendor = sel_vendor_obj)
                    if len(vendor_pl_opt) > 0:
                        cur_vendor_pl = get_object_or_404(vendor_price, item = cur_item_master, vendor = sel_vendor_obj)
                    else:
                        cur_vendor_pl = vendor_price(item = cur_item_master, vendor = sel_vendor_obj)
                        cur_vendor_pl.save()
                    cur_vendor_pl = get_object_or_404(vendor_price, item = cur_item_master, vendor = sel_vendor_obj)
                    if 'pur_rate_similar_sizes' in post_data:
                        new_pur_rate = pl_obj.purchase_rate
                        rate_diff = cur_vendor_pl.purchase_rate - new_pur_rate
                        if rate_diff > 0.01 or rate_diff < -0.01:
                            pur_rate_his = ast.literal_eval(str(cur_vendor_pl.pur_rate_history))
                            pur_rate_his.append({'dt':str(timezone.now()), 'rate':float(new_pur_rate)})
                            cur_vendor_pl.pur_rate_history = pur_rate_his
                        cur_vendor_pl.last_updated = timezone.now()
                        cur_vendor_pl.purchase_rate = pl_obj.purchase_rate
                        cur_vendor_pl.purchase_tax_format = pl_obj.purchase_tax_format
                        cur_vendor_pl.save()
                if 'jw_rate_similar_sizes' in post_data or 'jw_rate_all_variants' in post_data or 'eqn_jw_rate_all_variants' in post_data or 'eqn_jw_rate_similar_sizes' in post_data:
                    jw_rate_history = vendor_jw_rate_update(loop_items, pl_obj, sel_vendor_obj)
        data['sel_pl_obj_set'] = sel_pl_obj_set    
        data['pl_opt'] = pl_opt
        data['sel_item_master_id'] = sel_item_master_id
    data['spec_code_list'] = spec_code_list
    data['item_name_search'] = item_name_search
    data['item_group_opt'] = item_group_opt
    data['sel_item_group_id'] = sel_item_group_id
    data['vendor_opt'] = get_coa(2004)
    data['item_master_opt'] = item_master_opt[0:1000]
    data['sel_vendor_id'] = sel_vendor_id
    data['tax_format_opt'] = tax_format_opt
    data['sel_pl'] = sel_pl
    if not sel_pl == '-':
        data['sel_pl_obj'] = get_object_or_404(vendor_price, id=sel_pl)
    return render(request, 'journal_mgmt/vendor_pl_detail.html', {'data': data})


def vendor_rmp_supplier_detail(request, auto_rmp_id, sup_type, pl_sup_id):
    data = {}
    auto_rmp_obj = get_object_or_404(rmp_auto, id=auto_rmp_id)
    data['auto_rmp'] = auto_rmp_obj
    data['supplier_opt'] = []
    get_data = request.GET
    data['type'] = sup_type
    data['pl_vendor_id'] = 0
    data['pl_work_center_id'] = 0
    if get_data:
        if data['type'] == 'vendor':
            '''get all vendors - job work & purchase'''
            data['pl_vendor_id'] = pl_sup_id
            pl_sup_obj = get_object_or_404(coa, id=pl_sup_id)
            vendor_rmp_set = vendor_rmp_auto.objects.filter(rmp=auto_rmp_obj, vendor=pl_sup_id)
            if len(vendor_rmp_set) > 0:
                rmp_sup = vendor_rmp_set[0]
            else:
                rmp_sup = vendor_rmp_auto(rmp = auto_rmp_obj, vendor_id = pl_sup_id, name = pl_sup_obj.name)
        
        elif data['type'] == 'work_center':
            data['pl_work_center_id'] = pl_sup_id
            pl_sup_obj = get_object_or_404(coa, id=pl_sup_id)
            work_center_rmp_set = work_center_rmp_auto.objects.filter(rmp=auto_rmp_obj, work_center=pl_sup_id)
            if len(work_center_rmp_set) > 0:
                rmp_sup = work_center_rmp_set[0]
            else:
                rmp_sup = work_center_rmp_auto(rmp=auto_rmp_obj, work_center=pl_sup_id, name=pl_sup_obj.name)
        rmp_sup.name = pl_sup_obj.name
        rmp_sup.save()
        data['rmp_supply'] = rmp_sup
        data['auto_pl_id'] = get_data['auto_pl_id']
        data['item_master_id'] = get_data['item_master_id']
    return(render(request, 'journal_mgmt/vendor_rmp_supplier.html', {'data': data}))


def wc_pl_detail(request):
    data = {}
    sel_work_center_id = '*All*'
    sel_item_group_id = '*All*'
    item_name_search = ''
    sel_pl = '-'
    sel_item_master_id = '-'
    auto_pl_opt = auto_price_list.objects.all().order_by('id')
    item_master_opt = item_master.objects.all().order_by('name')
    item_group_opt = item_group.objects.all().order_by('name')
    work_center_opt = work_center_price.objects.all().order_by('name')
    # tax_format_opt = tax_format.objects.all().order_by('name')
    sel_pl_obj_set = ['-']
    spec_code_list = []
    wc_rmp_obj_set = []
    get_data = request.GET
    if request.GET:
        get_data = request.GET
        if 'sel_work_center_id' in get_data:
            sel_work_center_id = get_data['sel_work_center_id']
            if get_data:
                try:
                    sel_work_center_id = int(sel_work_center_id)
                except:
                    '''do nothing'''
                else:
                    sel_work_center_id = int(sel_work_center_id)
                    sel_work_center_obj = get_object_or_404(coa, id=sel_work_center_id)   
    if request.POST:
        post_data = request.POST
        sel_work_center_id = int(post_data['sel_work_center'])
        if 'sel_item_master' in post_data:
            sel_item_master_id = int(post_data['sel_item_master'])
        sel_item_group_id = post_data['sel_item_group']
        
        '''Work Center filtering'''
        try:
            int(post_data['sel_work_center'])
        except:
            '''DO Nothing'''
        else:
            sel_work_center_id = int(post_data['sel_work_center'])
            sel_work_center_obj = get_object_or_404(work_center, id=sel_work_center_id)
            pl_opt = work_center_price.objects.filter(work_center=sel_work_center_obj).order_by('item__name')
            wc_rmp_opt = work_center_rmp_auto.objects.filter(work_center = sel_work_center_id)
            data['wc_rmp_opt'] = wc_rmp_opt
        '''Pl Selected filtering'''
        try:
            int(post_data['sel_pl'])
        except:
            '''DO Nothing'''
        else:
            sel_pl = int(post_data['sel_pl'])
            sel_pl_obj = get_object_or_404(work_center_price, id=sel_pl)
            sel_item_master_id = sel_pl_obj.item.id
        '''Item Master filtering'''
        try:
            int(post_data['sel_item_master'])
        except:
            '''DO Nothing'''
        else:
            if sel_pl == '-':
                sel_item_master_id = int(post_data['sel_item_master'])
            sel_item_master_obj = get_object_or_404(item_master, id=sel_item_master_id)
            sel_pl_obj_set = work_center_price.objects.filter(work_center=sel_work_center_obj, item=sel_item_master_obj) 
            if len(sel_pl_obj_set) == 1:
                sel_pl_obj = sel_pl_obj_set[0]
            elif len(sel_pl_obj_set) > 1:
                del_list = sel_pl_obj_set[1:]
                for cur_del in del_list:
                    cur_del.delete()     
            elif len(sel_pl_obj_set) == 0:
                sel_pl = '-'
                if 'create' in post_data:
                    new_pl_obj = work_center_price(work_center=sel_work_center_obj, item=sel_item_master_obj)
                    new_pl_obj.save()
                
            sel_pl_obj_set = work_center_price.objects.filter(work_center=sel_work_center_obj, item=sel_item_master_obj)
            if len(sel_pl_obj_set) > 0:
                sel_pl_obj = get_object_or_404(work_center_price, work_center=sel_work_center_obj, item=sel_item_master_obj)
                sel_pl = sel_pl_obj.id
        '''Item Group filtering'''
        try:
            int(post_data['sel_item_group'])
        except:
            '''DO Nothing'''
        else:
            sel_item_group_id = int(post_data['sel_item_group'])
            sel_item_group_obj = get_object_or_404(item_group, id=sel_item_group_id)
            item_master_opt = item_master.objects.filter(item_group=sel_item_group_obj)
            pl_opt = pl_opt.filter(item__item_group=sel_item_group_obj)
            for cur_spec_code in pl_opt:
                item_id = cur_spec_code.item_id
                item_master_obj = get_object_or_404(item_master, id = item_id)
                sel_spec_code = item_master_obj.imported_item_code[0:21]
                auto_pl_opt = auto_pl_opt.filter(spec_code = sel_spec_code)
                for cur_auto_spec in auto_pl_opt:
                    auto_pl_obj = get_object_or_404(auto_price_list, id = cur_auto_spec.id )
                    if sel_spec_code == auto_pl_obj.spec_code:
                        spec_code_list.append((item_id, auto_pl_obj))
                    data['rmp_obj_set'] = [auto_pl_obj.p1, auto_pl_obj.p2, auto_pl_obj.p3, auto_pl_obj.p4, auto_pl_obj.p5, auto_pl_obj.p6, auto_pl_obj.p7, auto_pl_obj.p8, auto_pl_obj.p9, auto_pl_obj.p10, \
                           auto_pl_obj.p11, auto_pl_obj.p12, auto_pl_obj.p13, auto_pl_obj.p14, auto_pl_obj.p15, auto_pl_obj.p16, auto_pl_obj.p17, auto_pl_obj.p18, auto_pl_obj.p19, auto_pl_obj.p20]
                    rmp_obj_set = data['rmp_obj_set']
                    if len(auto_pl_obj.job_work_price_calc_eqn) < 2 :
                        data['constant_val'] = auto_pl_obj.input_rate_sale
            if len(spec_code_list) > 0:
                for cur_rmp in rmp_obj_set:
                    rmp_id = cur_rmp.id
                    rmp_auto_price_obj = get_object_or_404(rmp_auto , id = rmp_id) 
                    data['list'] = 'False'
                    for cur_wc_rmp in wc_rmp_opt:
                        if rmp_id == cur_wc_rmp.rmp_id:
                            data['list'] = 'true'
                            if rmp_auto_price_obj.constant_value == False:
                                wc_rmp_obj_set.append((cur_rmp, cur_wc_rmp.rate, rmp_id, sel_work_center_id, auto_pl_obj.id, item_master_obj.id, cur_rmp.constant_value))
                            vendor_rmp_id = cur_wc_rmp.rmp_id
                            break
                    if rmp_auto_price_obj.constant_value == True:
                        wc_rmp_obj_set.append((cur_rmp, cur_rmp.rmp_sale_rate, rmp_id, sel_work_center_id, auto_pl_obj.id, item_master_obj.id, cur_rmp.constant_value))
                    if data['list'] == 'False':
                        if rmp_auto_price_obj.constant_value == False:     
                            wc_rmp_obj_set.append((cur_rmp, 0, rmp_id, sel_work_center_id, auto_pl_obj.id, item_master_obj.id, cur_rmp.constant_value))
        '''Item Name filtering'''
        if 'item_name_search' in post_data:
            item_name_search = post_data['item_name_search']
            searched_name_set = item_name_search.split('!!')
            for cur_str in searched_name_set:
                item_master_opt = item_master_opt.filter(name__icontains=cur_str)
                pl_opt = pl_opt.filter(item__name__icontains=cur_str)
        
        '''Pl Selected filtering'''
        try:
            int(post_data['sel_pl'])
        except:
            '''DO Nothing'''
        else:
            sel_pl = int(post_data['sel_pl'])
            sel_pl_obj = get_object_or_404(work_center_price, id=sel_pl)
            sel_item_master_id = sel_pl_obj.item.id
        # sel_pl_obj_set = get_object_or_404(vendor = sel_vendor_obj, item = sel_item_master_obj)
        data['spec_code_list'] = spec_code_list
        data['wc_rmp_obj_set'] = wc_rmp_obj_set
        if 'save' in post_data or 'wc_rate_similar_sizes' in post_data or 'wc_rate_all_variants' in post_data or 'eqn_wc_rate_all_variants' in post_data or 'eqn_wc_rate_similar_sizes' in post_data:
            sel_pl = int(post_data['sel_pl'])
            pl_obj = get_object_or_404(work_center_price, id=sel_pl)
            pl_obj.rate = float(post_data['rate'])
            pl_obj.last_updated = timezone.now()
            pl_obj.save()
            pl_obj = get_object_or_404(work_center_price, id=sel_pl)
            if 'eqn_wc_rate_similar_sizes' in post_data or 'eqn_wc_rate_all_variants' in post_data:
                item_master_obj = get_object_or_404(item_master, id = pl_obj.item_id)
                broken_item = param_break(item_master_obj.imported_item_code, item_master_obj.imported_item_finish)
                rmp_con = get_rmp_con(auto_pl_obj.id, sel_work_center_id, 'work_center')
                changed_eqn = dim_cost_port(broken_item['pn'], auto_pl_obj.input_rate_sale, rmp_con[0], \
                                                     rmp_con[1], auto_pl_obj.input_factor_calc_eqn, 1)
                data['new_rate'] = round(eval(changed_eqn), 2)
                pl_obj.rate = data['new_rate']
                pl_obj.save()
            if 'change_eqn' in post_data:
                auto_pl_id = int(post_data['wc_id'])
                auto_pl_obj = get_object_or_404(auto_price_list, id = auto_pl_id)
                auto_pl_obj.job_work_price_calc_eqn = str(post_data['wc_eqn'])
                auto_pl_obj.save()
            pl_obj = get_object_or_404(work_center_price, id=sel_pl)
            if not 'save' in post_data:
                imp_item_code = pl_obj.item.imported_item_code
                item_spec_code = imp_item_code[:21]
                auto_pl_obj = get_object_or_404(auto_price_list, spec_code = item_spec_code)
                item_sim_sizes = item_master.objects.filter(imported_item_code = imp_item_code)
                item_all_sizes = item_master.objects.filter(imported_item_code__startswith = item_spec_code)
                if 'wc_rate_similar_sizes' in post_data or 'eqn_wc_rate_similar_sizes' in post_data:
                    loop_items = item_sim_sizes
                elif 'wc_rate_all_variants' in post_data or 'eqn_wc_rate_all_variants' in post_data:
                    loop_items = item_all_sizes
                for cur_item_master in loop_items:
                    work_center_pl_opt = work_center_price.objects.filter(item = cur_item_master, work_center = sel_work_center_obj)
                    if len(work_center_pl_opt) > 0:
                        cur_work_center_pl = get_object_or_404(work_center_price, item = cur_item_master, work_center = sel_work_center_obj)
                    else:
                        cur_work_center_pl = work_center_price(item = cur_item_master, work_center = sel_work_center_obj)
                        cur_work_center_pl.save()
                    cur_work_center_pl = get_object_or_404(work_center_price, item = cur_item_master, work_center = sel_work_center_obj)
                if 'wc_rate_similar_sizes' in post_data or 'wc_rate_all_variants' in post_data or 'eqn_wc_rate_all_variants' in post_data or 'eqn_wc_rate_similar_sizes' in post_data:
                    rate_history = wc_rate_update(loop_items, pl_obj, sel_work_center_obj)
        data['sel_pl_obj_set'] = sel_pl_obj_set    
        data['pl_opt'] = pl_opt
        data['sel_item_master_id'] = sel_item_master_id
        data['sel_work_center_id'] = sel_work_center_id
    data['work_center_opt'] = select_boxes({'name':'work_center'})
    data['item_name_search'] = item_name_search
    data['item_group_opt'] = item_group_opt
    data['sel_item_group_id'] = sel_item_group_id
    data['item_master_opt'] = item_master_opt[0:5000]
    # data['tax_format_opt'] = tax_format_opt
    data['sel_pl'] = sel_pl
    if not sel_pl == '-':
        data['sel_pl_obj'] = get_object_or_404(work_center_price, id=sel_pl)
    return render(request, 'journal_mgmt/wc_pl_detail.html', {'data': data})

def wc_vendor_rmp_supplier_detail(request, auto_rmp_id, sup_type, pl_sup_id):
    data = {}
    auto_rmp_obj = get_object_or_404(rmp_auto, id=auto_rmp_id)
    data['auto_rmp'] = auto_rmp_obj
    data['supplier_opt'] = []
    get_data = request.GET
    post_data = request.POST
    data['type'] = sup_type
    data['pl_vendor_id'] = 0
    data['pl_work_center_id'] = 0
    if get_data:
        if data['type'] == 'vendor':
            '''get all vendors - job work & purchase'''
            data['pl_sup_id'] = pl_sup_id
            pl_sup_obj = get_object_or_404(coa, id=pl_sup_id)
            vendor_rmp_set = vendor_rmp_auto.objects.filter(rmp=auto_rmp_obj, vendor=pl_sup_obj.id)
            if len(vendor_rmp_set) > 0:
                rmp_sup = vendor_rmp_set[0]
            else:
                rmp_sup = vendor_rmp_auto(rmp=auto_rmp_obj, vendor_id=pl_sup_obj.id, name=pl_sup_obj.name)
        elif data['type'] == 'work_center':
            data['pl_sup_id'] = pl_sup_id
            pl_sup_obj = get_object_or_404(work_center, id=pl_sup_id)
            work_center_rmp_set = work_center_rmp_auto.objects.filter(rmp=auto_rmp_obj, work_center=pl_sup_obj.id)
            if len(work_center_rmp_set) > 0:
                rmp_sup = work_center_rmp_set[0]
            else:
                rmp_sup = work_center_rmp_auto(rmp=auto_rmp_obj, work_center_id=pl_sup_obj.id, name=pl_sup_obj.name)
        rmp_sup.name = pl_sup_obj.name
        rmp_sup.save()
        data['rmp_supply'] = rmp_sup
        data['auto_pl_id'] = get_data['auto_pl_id']
        data['item_master_id'] = get_data['item_master_id']
    if '_save' in post_data:
        auto_pl_id = int(post_data['auto_pl_id'])
        item_master_id = int(post_data['item_master_id'])
        if post_data['type'] == 'vendor':
            rmp_supply = get_object_or_404(vendor_rmp_auto, id=int(post_data['rmp_supply_id']))
            pl_vendor_id = post_data['pl_vendor_id']
        elif post_data['type'] == 'work_center':
            rmp_supply = get_object_or_404(work_center_rmp_auto, id=int(post_data['rmp_supply_id']))
            pl_work_center_id = post_data['pl_work_center_id']
        # return(render(request, 'journal_mgmt/test_response.html', {'data': rmp_supply.name}))
        rmp_supply.rate = Decimal(post_data['rmp_supply_value'])
        rmp_supply.save()
        data['pl_sup_id'] = pl_sup_id
        data['message'] = 'New Supplier Added Successfully'
        data['item_master_id'] = item_master_id
        data['auto_pl_id'] = auto_pl_id
        data['rmp_supply'] = rmp_supply
        return(render(request, 'journal_mgmt/wc_vendor_rmp_supplier.html', {'data': data}))
    return(render(request, 'journal_mgmt/wc_vendor_rmp_supplier.html', {'data': data}))


def cons_dwg_tref(request):
    data = {}
    tot_cons_list = {}
    tot_auto_pl_dict = {}
    tref_obj_set = {}
    # if request.POST:
        # post_data = request.POST
    '''
    tot_auto_pl_list = {'auto_pl_spec_code':{'item_master_id1':tot_cons_list[item_master_id1], \
        'item_master_id2':tot_cons_list[item_master_id2]}}
    tot_cons_list = {'item_master_id1':{'obj':item_master_obj, 'tot_qty':00, tpl_qty':{'tpl1':qty1, 'tpl2':qty2}}, \
        'item_master_id2':{'obj':item_master_obj, 'tot_qty':00, tpl_qty':{'tpl1':qty1, 'tpl2':qty2}}}'''
    post_data = {'tpl_set':'231,235,245'}
    tref_set = post_data['tpl_set'].split(',')
    if len(tref_set) > 0:
        for cur_tref_id in tref_set:
            cur_tref_id = int(cur_tref_id)
            cur_tref_obj = get_object_or_404(transaction_ref, id=cur_tref_id)
            tref_obj_set[cur_tref_id] = {'obj':cur_tref_obj, 'obj_data':ast.literal_eval(cur_tref_obj.data)}
            inv_jour_set = inventory_journal.objects.filter(transaction_ref=cur_tref_obj)
            for cur_inv_jour in inv_jour_set:
                cur_item_master_id = cur_inv_jour.item_master.id
                cur_qty = float(cur_inv_jour.balance_qty)
                cur_spec_code = cur_inv_jour.item_master.imported_item_code[:21]
                cur_auto_pl_obj = get_object_or_404(auto_price_list, spec_code=cur_spec_code)
                if not cur_item_master_id in tot_cons_list:
                    tot_cons_list[cur_item_master_id] = {'item_id':cur_item_master_id, 'tpl_qty':{}, \
                                                        'obj':cur_inv_jour.item_master, 'tot_qty':0}
                tot_cons_list[cur_item_master_id]['tpl_qty'][cur_tref_id] = cur_qty
                tot_cons_list[cur_item_master_id]['tot_qty'] += cur_qty
    data['tot_cons_list'] = tot_cons_list
    for cur_item_id, cur_val_dict in tot_cons_list.items():
        cur_item_master_obj = cur_val_dict['obj']
        cur_spec_code = cur_item_master_obj.imported_item_code[:21]
        cur_auto_pl_obj = get_object_or_404(auto_price_list, spec_code=cur_spec_code)
        if not cur_spec_code in tot_auto_pl_dict:
            tot_auto_pl_dict[cur_spec_code] = {'auto_pl_obj':cur_auto_pl_obj, 'item_master_list':[]}
        tot_auto_pl_dict[cur_spec_code]['item_master_list'].append(cur_val_dict)
    data['auto_pl_obj_set'] = tot_auto_pl_dict
    data['tref_obj_set'] = tref_obj_set
    '''data['auto_pl_obj_set':{'spec_code':{'auto_pl_obj':obj, 
    'item_master_list':[{'item_id':id, 'obj':item_master_obj, 'tot_qty':123, 
    'tpl_qty':{'tref_id1':qty, 'tref_id2':qty}}, {}, {},...]}}]'''
    return(render(request, 'journal_mgmt/cons_dwg_tref.html', {'data': data}))

def cur_stock(request):
    data = {}
    item_name_search = ''
    location_type_obj = 0
    location_type_list = []
    location_ref_list = []
    sel_current_stock_list = []
    location_ref_opt = []
    current_stock_list = []
    current_stock_obj = 0
    cur_loc_type_id = '*All*'
    cur_loc_ref_id = '*All*'
    item_master_opt = item_master.objects.all().order_by('name')
    location_type_opt = location_type.objects.all().order_by('name')
    if request.POST:
        post_data = request.POST
        current_stock_list = current_stock.objects.all().order_by('item_master_ref__name')
        if 'sel_location_type_id' in post_data:
            cur_loc_type_id = post_data['sel_location_type_id']
            try:
                int(cur_loc_type_id)
            except:
                '''do nothing'''
            else:
                cur_loc_type_id = int(cur_loc_type_id)
                location_type_obj = get_object_or_404(location_type, id=int(cur_loc_type_id))
                location_ref_opt = select_boxes({'name':location_type_obj.short_hand})
                current_stock_list = current_stock_list.filter(location_ref__location_type_ref=location_type_obj)
                
        if 'sel_location_ref_id' in post_data:
            cur_loc_ref_id = post_data['sel_location_ref_id']
            try:
                int(cur_loc_ref_id)
            except:
                '''do nothing'''
            else:
                cur_loc_ref_id = int(cur_loc_ref_id)
                location_availability = location.objects.filter(location_type_ref=location_type_obj, ref_no=cur_loc_ref_id)
                if len(location_availability) > 0:
                    cur_location_obj = get_object_or_404(location, location_type_ref=location_type_obj, ref_no=cur_loc_ref_id)
                    current_stock_list = current_stock_list.filter(location_ref__ref_no=cur_location_obj.ref_no)
                else:
                    current_stock_list = []
        '''Item Name filtering'''
        if 'item_name_search' in post_data:
            item_name_search = post_data['item_name_search']
            searched_name_set = item_name_search.split('!!')
            for cur_str in searched_name_set:
                item_master_opt = item_master_opt.filter(name__icontains=cur_str)
                if len(current_stock_list) > 0:
                    current_stock_list = current_stock_list.filter(item_master_ref__name__icontains=cur_str)
    data['sel_location_type_id'] = cur_loc_type_id
    data['sel_location_ref_id'] = cur_loc_ref_id
    data['sel_current_stock_list'] = current_stock_list
    data['location_ref_opt'] = location_ref_opt
    data['location_type_opt'] = location_type_opt
    data['location_type_obj'] = location_type_obj
    return(render(request, 'journal_mgmt/cur_stock.html', {'data': data}))

def tpl_consolidation(request):
    data = {}
    oc_ttype = get_object_or_404(transaction_type, transaction_type_ref_no=59)
    oc_tref_list = transaction_ref.objects.filter(transaction_type=oc_ttype, submit=True, active=True)
    oc_object_list = []
    tpl_object_list = []
    tpl_list = []
    sel_tpl_list = []
    oc_obj = 0
    oc_obj_id = 0
    sel_tpl_obj = 0
    for cur_tref in oc_tref_list:
        oc_object_list.append((cur_tref, ast.literal_eval(cur_tref.data)))
    if request.POST:
        post_data = request.POST
        i = 1
        while (i < 10):
            cur_key = 'sel_tpl_' + str(i)
            if cur_key in post_data:
                sel_tpl_old_obj = get_object_or_404(transaction_ref, id=int(post_data[cur_key]))
                sel_tpl_list.append((sel_tpl_old_obj, ast.literal_eval(sel_tpl_old_obj.data)))              
            else:
                break
            i += 1
        if 'order_confirmation' in post_data:
            oc_obj = get_object_or_404(transaction_ref, id=int(post_data['order_confirmation']))
            oc_obj_id = oc_obj.id
            tpl_ttype = get_object_or_404(transaction_type, transaction_type_ref_no=2)
            tpl_tref_list = transaction_ref.objects.filter(transaction_type=tpl_ttype, submit=True, active=True)
            search_dict = {'order_confirmation':str(oc_obj.id)}
            tpl_tref_obj_list = tref_field_filter(tpl_tref_list, search_dict)        
        for cur_tref in tpl_tref_obj_list:
            tpl_object_list.append((cur_tref, ast.literal_eval(cur_tref.data)))
        data['tpl_object_list'] = tpl_object_list
        
        if 'select_tpl' in post_data:
            sel_tpl_obj = get_object_or_404(transaction_ref, id=int(post_data['sel_tpl_id']))
            sel_tpl_list.append((sel_tpl_obj, ast.literal_eval(sel_tpl_obj.data)))
    data['oc_object_list'] = oc_object_list
    data['sel_oc'] = oc_obj
    data['sel_oc_id'] = oc_obj_id
    data['sel_tpl_list'] = sel_tpl_list 
    data['sel_tpl'] = sel_tpl_obj  
    return render(request, 'journal_mgmt/tpl_consolidation.html', {'data': data})

def doc_list(request, tab_name, tab_id, doc_type_id):
    data = {}
    if tab_name == 'auto_pl':
        rec_obj = get_object_or_404(auto_price_list, id=int(tab_id))
        data['auto_pl'] = rec_obj
    # Handle file upload   , tab_name, tab_id
    if request.method == 'POST':
        post_data = request.POST
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc_type_obj = get_object_or_404(doctype, id = doc_type_id)
            docsave = document(docfile=request.FILES['docfile'], tab_name=tab_name, tab_id=tab_id, doctype = doc_type_obj)
            docsave.save()
            # Redirect to the document list after POST
            return HttpResponseRedirect(reverse('journal_mgmt:doc_list', args=(tab_name, rec_obj.id, doc_type_obj.id)))
        
    else:
        form = DocumentForm()  # A empty, unbound form
    # Load documents for the list page
    documents = document.objects.filter(tab_name=tab_name, tab_id=tab_id, doctype=1)#showing documents of type preview
    # Render list page with the documents and the form
    return render_to_response(
        'journal_mgmt/doc_list.html',
        {'documents': documents, 'form': form, 'data': data},
        context_instance=RequestContext(request)
    )

def doc_delete(request, doc_id):
    referer = request.META.get('HTTP_REFERER')
    document_obj = get_object_or_404(document, id = doc_id)
    site_path = get_site_path()
    file_loc = str(document_obj.docfile)
    file_path = site_path + '/media/' + file_loc
    if os.path.isfile(file_path):
        os.remove(file_path)
    document_obj.delete()
    return HttpResponseRedirect(referer)


def production_auto_plan_backup(request, tref_id):
    data = {}
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    inv_jour_list = inventory_journal.objects.filter(transaction_ref=tref)
    bom_data = []
    data['pro_inv_jour'] = {}
    data['tref'] = tref
    state_opt = state.objects.all().order_by('name')
    city_opt = city.objects.all().order_by('name')
    wc_name_dict = {}
    vendor_list_dict = {}
    vendor_pl_list = []
    vendor_list = []
    wc_list = []
    wc_name_list = []
    wc_name_list.append('------')
    vendor_list.append('------')
    vendor_dict = {}
    wc_dict = {}
    if tref.submit == True:
        for cur_inv_jour in inv_jour_list:
            add_data = {}
            shop_qty = 0
            job_qty = 0
            vendor_name = ''
            work_center_name = ''
            next_prod = True
            bal_qty = cur_inv_jour.balance_qty
            bom_data = ast.literal_eval(cur_inv_jour.item_master.bom)
            cur_vendor_pl_opt = vendor_price.objects.filter(item = cur_inv_jour.item_master)
            for cur_vendor in cur_vendor_pl_opt:
                if not cur_vendor.vendor.id in vendor_list_dict:
                    vendor_list_dict[cur_vendor.vendor.id] = []
                    vendor_list.append(cur_vendor.vendor)
            cur_wc_pl_opt = work_center_price.objects.filter(item = cur_inv_jour.item_master)
            for cur_wc in cur_wc_pl_opt:
                if not cur_wc.work_center.id in wc_name_dict:
                    wc_name_dict[cur_wc.work_center.id] = []
                    wc_name_list.append(cur_wc.work_center)
            for cur_bom in bom_data:
                cur_bom_obj = get_object_or_404(item_master , id = cur_bom[0])
                inventory_journal_obj = inventory_journal.objects.filter(item_master = cur_bom_obj, tpl_ref_no = cur_inv_jour.tpl_ref_no,\
                                                 transaction_ref = tref, balance_qty__gt = 0)
                if len(inventory_journal_obj) > 0:
                    next_prod = False
                    break
            data['vendor_list'] = vendor_list
            add_data['next'] = next_prod
            add_data['shop_qty'] = shop_qty
            add_data['job_qty'] = job_qty
            add_data['new_balance_qty'] = bal_qty - shop_qty - job_qty
            add_data['vendor_pl_opt'] = cur_vendor_pl_opt
            add_data['wc_pl_opt'] = cur_wc_pl_opt
            data['pro_inv_jour'][cur_inv_jour.id] = [cur_inv_jour, add_data]
            data['wc_name_list'] = wc_name_list
        if request.POST:
            post_data = request.POST
            i = 1
            vendor_name_list = []
            jo_detail_list = []
            so_detail_list = []
            wc_nested_list = []
            nested_list = []
            wc_list_name = []
            id_list = []
            if 'cur_sel_wc' in post_data:
                if post_data['cur_sel_wc'] == '':
                    """ DO NOTHING """
                else:
                    sel_wc = int(post_data['cur_sel_wc'])
                    data['sel_wc'] = sel_wc
            if 'cur_sel_vendor' in post_data:
                if post_data['cur_sel_vendor'] == '':
                    """ DO NOTHING """
                else:
                    cur_sel_vendor = int(post_data['cur_sel_vendor'])
                    data['sel_vendor'] = cur_sel_vendor
            while i < 1000:
                id_key = 'inv_jour_id!!' + str(i)
                if id_key in post_data:
                    add_data = {}
                    mod_qty = 0
                    wc_mod_qty = 0
                    add_data['mod_qty'] = mod_qty
                    add_data['wc_mod_qty'] = wc_mod_qty
                    inv_jour_id = int(post_data[id_key])
                    cur_inv_jour = get_object_or_404(inventory_journal, id=inv_jour_id)
                    cur_item_master = cur_inv_jour.item_master
                    bal_qty = float(cur_inv_jour.balance_qty)
                    sel_vendor_pl_key = 'sel_vendor_' + str(i)
                    bom_data = ast.literal_eval(cur_inv_jour.item_master.bom)
                    add_data['next'] = True
                    add_data['new_balance_qty'] = bal_qty
                    for cur_bom in bom_data:
                        cur_bom_obj = get_object_or_404(item_master , id = cur_bom[0])
                        inventory_journal_obj = inventory_journal.objects.filter(item_master = cur_bom_obj, tpl_ref_no = cur_inv_jour.tpl_ref_no,\
                                                 transaction_ref = tref, balance_qty__gt = 0)
                        if len(inventory_journal_obj) > 0:
                            add_data['next'] = False
                            break
                    add_data['vendor'] = 'False'    
                    if 'cur_sel_vendor' in post_data:
                        sel_vendor = str(post_data['cur_sel_vendor'])
                        if sel_vendor == '':
                            ''' DO NOTHING'''
                        else:
                            if (post_data['job_qty!!' + str(i)]) == '':
                                job_qty = 0.0
                            else:
                                job_qty = float(post_data['job_qty!!' + str(i)])
                            add_data['job_qty'] = job_qty
                            add_data['new_balance_qty'] = bal_qty - shop_qty - job_qty
                            sel_vendor = int(post_data['cur_sel_vendor'])
                            cur_vendor_pl_opt = vendor_price.objects.filter(item = cur_item_master, vendor = sel_vendor)
                            add_data['vendor_pl_opt'] = cur_vendor_pl_opt
                            for cur_vendor in cur_vendor_pl_opt:
                                sel_vendor_pl_obj = get_object_or_404(vendor_price, item = cur_item_master, vendor = sel_vendor)
                                sel_vendor_id = sel_vendor_pl_obj.vendor.id
                                add_data['sel_id'] = sel_vendor_id
                                add_data['vendor'] = 'True'
                                if job_qty > 0 :
                                    if len(vendor_name_list)< 1:
                                        vendor_name_list.append({'name':cur_vendor.vendor.name, 'id':sel_vendor})
                                        data['sel_vendor'] = sel_vendor
                                    add_data['sel_vendor'] = sel_vendor
                            if job_qty > 0:
                                if not sel_vendor_id in vendor_dict:
                                    vendor_dict[sel_vendor_id] = []
                                    id_list.append(sel_vendor_id)
                            if job_qty > 0:
                                vendor_dict[sel_vendor_id].append((inv_jour_id, job_qty, {'tpl_ref':tref.id}))
                            data['vendor_dict'] = vendor_dict
                        add_data['work_center'] = 'False'
                    if 'cur_sel_wc' in post_data:
                        sel_wc = str(post_data['cur_sel_wc'])
                        
                        if sel_wc == '':
                            ''' DO NOTHING'''
                        else:
                            if (post_data['shop_qty!!' + str(i)]) == '':
                                shop_qty = 0.0
                            else:
                                shop_qty = float(post_data['shop_qty!!' + str(i)])
                            add_data['shop_qty'] = shop_qty
                            add_data['new_balance_qty'] = bal_qty - shop_qty - job_qty
                            sel_wc = int(post_data['cur_sel_wc'])
                            cur_wc_pl_opt = work_center_price.objects.filter(item = cur_item_master, work_center = sel_wc)
                            add_data['wc_pl_opt'] = cur_wc_pl_opt
                            add_data['work_center'] = 'False'
                            for cur_wc in cur_wc_pl_opt:
                                sel_wc_obj = get_object_or_404(work_center_price, item = cur_item_master, work_center = sel_wc)
                                sel_wc_id = sel_wc_obj.work_center.id
                                add_data['work_center'] = 'True'
                                if shop_qty > 0:
                                    if len(wc_list_name)< 1:
                                        wc_list_name.append({'name':cur_wc.work_center.name, 'id':sel_wc})
                                if not sel_wc_id in wc_dict:
                                    wc_dict[sel_wc_id] = []
                                    id_list.append(sel_wc_id)
                                    add_data['sel_id'] = sel_wc_id
                                wc_dict[sel_wc_id].append((inv_jour_id, shop_qty, {'tpl_ref':tref.id}))
                                data['wc_dict'] = wc_dict
                            add_data['sel_wc'] = sel_wc
                            data['sel_wc'] = sel_wc
                    if add_data['new_balance_qty'] >= 0:
                        data['pro_inv_jour'][cur_inv_jour.id] = [cur_inv_jour, add_data]
                    else:
                        error = 1
                else:
                    break
                i += 1
            add_data['state_opt'] = select_boxes({'name':'state'})
            add_data['city_opt'] = select_boxes({'name':'city'})
            add_data['jo_detail_list'] = jo_detail_list
            i = 1
            while i < 100:
                vendor_id = 'vendor_id_' + str(i)
                if vendor_id in post_data:
                    sel_vendor_id = int(post_data[vendor_id])
                    add_data['vendor_id'] = sel_vendor_id
                ship_to = 'ship_to_' + str(i)
                if ship_to in post_data:
                    sel_ship_to  = str(post_data[ship_to])
                    add_data['ship_to'] = sel_ship_to
                shiping_address_line_1 = 'shiping_address_line_1_' + str(i)
                if shiping_address_line_1 in post_data:
                    sel_shiping_address_line_1  = str(post_data[shiping_address_line_1])
                    add_data['shiping_address_line_1'] = sel_shiping_address_line_1
                shiping_address_line_2 = 'shiping_address_line_2_' + str(i)
                if shiping_address_line_2 in post_data:
                    sel_shiping_address_line_2  = str(post_data[shiping_address_line_2])
                    add_data['shiping_address_line_2'] = sel_shiping_address_line_2
                sel_city = 'sel_city_' + str(i)
                if sel_city in post_data:
                    sel_city  = str(post_data[sel_city])
                    add_data['sel_city'] = sel_city
                sel_state = 'sel_state_' + str(i)
                if sel_state in post_data:
                    sel_state  = str(post_data[sel_state])
                    add_data['sel_state'] = sel_state
                date = 'date_' + str(i)
                mod_qty = 'mod_qty_' + str(i)
                if mod_qty in post_data:
                    mod_qty = float(post_data[mod_qty])
                    add_data['mod_qty'] = mod_qty
                if date in post_data:
                    date  = str(post_data[date])
                    add_data['date'] = date
                else:
                    break
                i += 1
                jo_detail_list.append((add_data['vendor_id'], add_data['ship_to'], add_data['shiping_address_line_1'],
                                       add_data['shiping_address_line_2'], add_data['sel_city'], add_data['sel_state'], add_data['date']))
            i = 1
            while i < 100:
                sel_work_center_id = 'wc_id_' + str(i)
                if sel_work_center_id in post_data:
                    work_center_id = int(post_data[sel_work_center_id])
                    add_data['work_center_id'] = work_center_id
                wc_mod_qty = 'wc_mod_qty_' + str(i)
                if wc_mod_qty in post_data:
                    wc_mod_qty = float(post_data[wc_mod_qty])
                    add_data['wc_mod_qty'] = wc_mod_qty
                completion_date = 'completion_date_' + str(i)
                if completion_date in post_data:
                    sel_completion_date = str(post_data[completion_date])
                    add_data['completion_date'] = sel_completion_date
                else:
                    break
                i += 1
                so_detail_list.append((add_data['work_center_id'], add_data['completion_date']))
            add_data['jo_detail_list'] = jo_detail_list
            add_data['vendor_name_list'] = vendor_name_list
            add_data['wc_list_name'] = wc_list_name    
            add_data['so_detail_list'] = so_detail_list
            if len(vendor_dict) > 0:
                add_data['jo_detail_list'] = jo_detail_list
                job_shop_deatil = job_shop_prepare(vendor_dict, inv_jour_id, id_list, add_data, {'save':False}, tref_id)
                nested_list = job_shop_deatil['nested_list']
            add_data['nested_list'] = nested_list
            if len(wc_dict) > 0:
                add_data['so_detail_list'] = so_detail_list
                job_shop_deatil = job_shop_prepare(wc_dict, inv_jour_id, id_list, add_data, {'save':False}, tref_id)
                wc_nested_list = job_shop_deatil['nested_list']
            add_data['wc_nested_list'] = wc_nested_list
            if 'save' in post_data:    
                return HttpResponseRedirect(reverse('journal_mgmt:production_auto_plan', args=(tref.id,)))
    return(render(request, 'journal_mgmt/production_auto_plan.html', {'data': data}))

def production_auto_plan(request, tref_id):
    data = {}
    tref = get_object_or_404(transaction_ref, id=int(tref_id))
    inv_jour_list = inventory_journal.objects.filter(transaction_ref=tref)
    inv_jour_list = inv_jour_list.filter(balance_qty__gt = 0)
    bom_data = []
    data['pro_inv_jour'] = {}
    data['tref'] = tref
    state_opt = state.objects.all().order_by('name')
    city_opt = city.objects.all().order_by('name')
    work_center_opt = []
    vendor_opt = []
    sel_vendor = "*All*"
    sel_work_center = "*All*"
    pro_inv_jour_items = []
    nested_list = []
    job_shop_dict = {}
    balance_check = {}
    sel_vendor_obj = None
    sel_work_center_obj = None
    vendor_selected = False
    work_center_selected = False
    pro_ord_feed_list = []
    error = False
    error_message = ''
    if tref.submit == True:
        if request.POST:
            post_data = request.POST
            i = 1
            tref_add_data = {}
            if 'sel_work_center' in post_data:
                try:
                    int(post_data['sel_work_center'])
                except:
                    '''do nothing'''
                else:
                    work_center_selected = True
                    sel_work_center = int(post_data['sel_work_center'])
                    sel_work_center_obj = get_object_or_404(work_center, id = sel_work_center)
            elif 'sel_vendor' in post_data:
                try:
                    int(post_data['sel_vendor'])
                except:
                    '''do nothing'''
                else:
                    vendor_selected = True
                    sel_vendor = int(post_data['sel_vendor'])
                    sel_vendor_obj = get_object_or_404(coa, id = sel_vendor)
                    '''vendor data is stored in COA Table'''
                    tref_add_data['vendor'] = True
                    tref_add_data['sel_id'] = sel_vendor_obj.id
        work_center_opt = select_boxes({'name':'work_center'})
        app_wc_id_used = []
        temp_inv_jour_list = copy.deepcopy(inv_jour_list)
        vendor_opt = select_boxes({'name':'vendor'})
        app_vendor_id_used = []
        temp_inv_jour_list = copy.deepcopy(inv_jour_list)
        for cur_temp_inv_jour in temp_inv_jour_list:
            cur_app_wc_pl = work_center_price.objects.filter(item = cur_temp_inv_jour.item_master)
            if len(cur_app_wc_pl) == 0 and work_center_selected == True:
                inv_jour_list = inv_jour_list.exclude(item_master = cur_temp_inv_jour.item_master)
            for cur_wc_pl in cur_app_wc_pl:
                if not cur_wc_pl.work_center.id in app_wc_id_used:
                    app_wc_id_used.append(cur_wc_pl.work_center.id)
            cur_app_vendor_pl = vendor_price.objects.filter(item = cur_temp_inv_jour.item_master)
            if len(cur_app_vendor_pl) == 0 and vendor_selected == True:
                inv_jour_list = inv_jour_list.exclude(item_master = cur_temp_inv_jour.item_master)
            for cur_vendor_pl in cur_app_vendor_pl:
                if not cur_vendor_pl.vendor.id in app_vendor_id_used:
                    app_vendor_id_used.append(cur_vendor_pl.vendor.id)
        for cur_work_center in work_center_opt:
            if not cur_work_center.id in app_wc_id_used:
                work_center_opt = work_center_opt.exclude(id=cur_work_center.id)
        for cur_vendor in vendor_opt:
            if not cur_vendor.id in app_vendor_id_used:
                vendor_opt = vendor_opt.exclude(id=cur_vendor.id)
        for cur_inv_jour in inv_jour_list:
            add_data = {}
            next_prod = True
            bom_data = ast.literal_eval(cur_inv_jour.item_master.bom)
            for cur_bom in bom_data:
                cur_bom_obj = get_object_or_404(item_master, id = cur_bom[0])
                inventory_journal_obj = inventory_journal.objects.filter(item_master = cur_bom_obj, tpl_ref_no = cur_inv_jour.tpl_ref_no,\
                                                 transaction_ref = tref, balance_qty__gt = 0)
                if len(inventory_journal_obj) > 0:
                    next_prod = False
                    break
            add_data['next'] = next_prod
            add_data['issue_qty'] = float(cur_inv_jour.balance_qty)
            add_data['plant_stock'] = 0 
            add_data['work_center_stock'] = 0
            add_data['vendor_stock'] = 0
            #add_data['allocate_qty'] = 0
            add_data['red_due_allocation'] = 0
            add_data['new_balance_qty'] = 0
            add_data['work_center_pl_opt'] = work_center_price.objects.filter(item = cur_inv_jour.item_master)
            add_data['vendor_pl_opt'] = vendor_price.objects.filter(item = cur_inv_jour.item_master)
            pro_inv_jour_items.append({'inv_jour_id':cur_inv_jour.id, 'inv_jour_obj':cur_inv_jour, 'add_data':add_data})
        if request.POST:
            post_data = request.POST
            error = False
            if ('preview' in post_data or 'save' in post_data) and (vendor_selected == True or work_center_selected == True):
                inv_jour_list = []
                while i < 1000:
                    id_key = 'inv_jour_id!!' + str(i)
                    issue_qty_key = 'issue_qty!!' + str(i)
                    #allocate_qty_key = 'allocate_qty!!' + str(i)
                    if id_key in post_data:
                        inv_jour_id = int(post_data[id_key])
                        issue_qty = float(post_data[issue_qty_key])
                        #allocate_qty = float(post_data[allocate_qty_key])
                        cur_inv_jour = get_object_or_404(inventory_journal, id=inv_jour_id)
                        pro_inv_jour_index = [x for x, y in enumerate(pro_inv_jour_items) if y['inv_jour_id'] == inv_jour_id]
                        pro_inv_jour_index = pro_inv_jour_index[0]
                        add_data = copy.deepcopy(pro_inv_jour_items[pro_inv_jour_index]['add_data'])
                        add_data['issue_qty'] = float(issue_qty)
                        #add_data['allocate_qty'] = float(allocate_qty)
                        pro_inv_jour_items[pro_inv_jour_index]['add_data'] = add_data
                    else:
                        break
                    i += 1
                for cur_pro_jour in pro_inv_jour_items:
                    cur_inv_jour_obj = cur_pro_jour['inv_jour_obj']
                    cur_pro_inv_jour_index = [x for x, y in enumerate(pro_inv_jour_items) if y['inv_jour_id'] == cur_inv_jour_obj.id][0]
                    cur_pro_inv_jour_add_data = copy.deepcopy(pro_inv_jour_items[cur_pro_inv_jour_index]['add_data'])
                    cur_bal_qty = float(cur_inv_jour_obj.balance_qty)
                    issue_qty = cur_pro_inv_jour_add_data['issue_qty']
                    new_bal_qty = cur_bal_qty - issue_qty
                    pro_inv_jour_items[cur_pro_inv_jour_index]['add_data']['new_balance_qty'] = new_bal_qty
                    inv_jour_list.append([cur_inv_jour_obj.id, issue_qty, {'tpl_ref':cur_inv_jour.tpl_ref_no}])
                    if not cur_inv_jour_obj.id in balance_check:
                        cur_bal_dict = {}
                        cur_bal_dict['cur_issue_qty'] = 0
                        cur_bal_dict['new_bal_qty'] = cur_bal_qty
                        cur_bal_dict['red_due_allocation'] = 0
                    else:
                        cur_bal_dict = copy.deepcopy(balance_check[cur_inv_jour_obj.id])
                    cur_bal_dict['cur_issue_qty'] = issue_qty
                    cur_bal_dict['new_bal_qty'] = cur_bal_qty - issue_qty
                    balance_check[cur_inv_jour_obj.id] = cur_bal_dict
                    if cur_bal_dict['new_bal_qty'] < 0:
                        error = True
                        error_message = 'cannot release' + cur_inv_jour_obj.name + 'more than balance'
                job_shop_detail = job_shop_plan_inv_jour(inv_jour_list)
                nested_list = job_shop_detail['nested_rm_req']
                i = 0
                for cur_nested_item in nested_list:
                    nested_item_obj = cur_nested_item[0]
                    cur_tpl_ref = cur_nested_item[2]['tpl_ref']
                    if vendor_selected == True:
                        foreign_location_obj = get_location_raw('vendor', sel_vendor_obj.id)
                    elif work_center_selected == True:
                        foreign_location_obj = get_location_raw('work_center', sel_work_center_obj.id)
                    plant_location_obj = get_location_raw('plant', 1)
                    app_foreign_stk = current_stock.objects.filter(item_master_ref = nested_item_obj, location_ref = foreign_location_obj, tpl_ref_no = cur_tpl_ref)
                    app_plant_stk = current_stock.objects.filter(item_master_ref = nested_item_obj, location_ref = plant_location_obj, tpl_ref_no = cur_tpl_ref)
                    plant_stk = 0
                    foreign_stk = 0
                    if len(app_foreign_stk) > 0:
                        foreign_stk_obj = get_object_or_404(current_stock, item_master_ref = nested_item_obj, location_ref = foreign_location_obj, tpl_ref_no = cur_tpl_ref)
                        foreign_stk = foreign_stk_obj.cur_stock
                    if len(app_plant_stk) > 0:
                        plant_stk_obj = get_object_or_404(current_stock, item_master_ref = nested_item_obj, location_ref = plant_location_obj, tpl_ref_no = cur_tpl_ref)
                        plant_stk = plant_stk_obj.cur_stock
                    nested_rm_qty = float(cur_nested_item[1])
                    stock_color = 'green'
                    if (plant_stk + foreign_stk) < nested_rm_qty:
                        stock_color = 'red'
                        error = True
                        error_message = 'Stock Unavailable'
                    nested_list[i][2]['color'] = stock_color
                    nested_list[i][2]['plant_stock'] = plant_stk
                    nested_list[i][2]['foreign_stock'] = foreign_stk
                    if (len(ast.literal_eval(nested_item_obj.bom))) > 0:
                        app_prod_ind_inv_jour = get_object_or_404(inventory_journal, item_master = nested_item_obj, tpl_ref_no = cur_tpl_ref, transaction_ref = tref)
                        nested_list[i][2]['app_inv_jour_obj'] = app_prod_ind_inv_jour
                        if not app_prod_ind_inv_jour.id in balance_check:
                            cur_bal_dict = {}
                            cur_bal_dict['cur_issue_qty'] = 0
                            cur_bal_dict['new_bal_qty'] = float(app_prod_ind_inv_jour.balance_qty)
                            cur_bal_dict['red_due_allocation'] = 0
                        else:
                            cur_bal_dict = copy.deepcopy(balance_check[app_prod_ind_inv_jour.id])
                        cur_bal_dict['red_due_allocation'] += nested_rm_qty
                        cur_bal_dict['new_bal_qty'] -= nested_rm_qty
                        balance_check[app_prod_ind_inv_jour.id] = cur_bal_dict
                        if cur_bal_dict['new_bal_qty'] < 0:
                            error = True
                            error_message = 'Item ' + nested_item_obj.name + 'already released to production, balance:' + str(app_prod_ind_inv_jour.balance_qty)
                    i += 1
                if vendor_selected == True:
                    job_shop_dict[sel_vendor_obj.id] = inv_jour_list
                    jo_field_list = {}
                    jo_field_list['vendor'] = [sel_vendor_obj.id, sel_vendor_obj.name]
                    jo_field_list['state']  = str(post_data['state'])
                    jo_field_list['city']  = str(post_data['city'])
                    jo_field_list['ship_to']  = str(post_data['ship_to'])
                    jo_field_list['shipping_addr1']  = str(post_data['shipping_addr1'])
                    jo_field_list['shipping_addr2']  = str(post_data['shipping_addr2'])
                    jo_field_list['delivery_date'] = str(post_data['delivery_dt'])
                    tref_add_data['jo_detail_list'] = jo_field_list
                    tref_add_data['vendor'] = True
                    tref_add_data['sel_id'] = sel_vendor_obj.id
                    stock_ref_id_list = [sel_vendor_obj.id]
                else:
                    job_shop_dict[sel_work_center_obj.id] = inv_jour_list
                    so_field_list = {}
                    so_field_list['work_center'] = [sel_work_center_obj.id, sel_work_center_obj.name]
                    so_field_list['delivery_date'] = str(post_data['delivery_dt'])
                    tref_add_data['so_detail_list'] = so_field_list
                    tref_add_data['work_center'] = True
                    tref_add_data['sel_id'] = sel_work_center_obj.id
                    stock_ref_id_list = [sel_work_center_obj.id]
                
                #production_order_list(pro_ord_feed_list)
                #job_shop_detail = job_shop_prepare(job_shop_dict, inv_jour_id, stock_ref_id_list, tref_add_data, {'save':False}, tref_id)
                #nested_list = job_shop_detail['nested_list']
                if 'save' in post_data and error == False:
                    tref_dict = {}
                    if vendor_selected == True:
                        ttype_ref_id = 12#Job order ttype ref no
                        tref_dict['field_list'] = jo_field_list
                    else:
                        ttype_ref_id = 16#Shop order ttype ref no
                        tref_dict['field_list'] = so_field_list
                    job_shop_order_process = auto_create_tref(ttype_ref_id, tref_dict, inv_jour_list, False, {})
                    return HttpResponseRedirect(reverse('journal_mgmt:job_shop_order_preview', args=(job_shop_order_process.id,)))
        data['work_center_opt'] = work_center_opt
        data['vendor_opt'] = vendor_opt
        data['sel_vendor_obj'] = sel_vendor_obj
        data['sel_work_center_obj'] = sel_work_center_obj
        data['sel_work_center'] = sel_work_center
        data['pro_inv_jour_items'] = pro_inv_jour_items
        data['nested_list'] = nested_list
        data['balance_check'] = balance_check
        data['vendor_selected'] = vendor_selected
        data['work_center_selected'] = work_center_selected
        data['state_opt'] = state_opt
        data['city_opt'] = city_opt
        data['error'] = error
        data['error_message'] = error_message
        #return(render(request, 'journal_mgmt/production_auto_plan_backup.html', {'data': data}))
        return(render(request, 'journal_mgmt/production_auto_plan.html', {'data': data}))


def crm_auto_pl_mgmt(request):
    data = {}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    bom_index = []
    derivative_index = []
    fg_bom_index = []
    fg_derivative_index = []
    searched_str = ''
    bom_searched_str = ''
    parent_list = []
    fg_parent_list = []
    bom_det = []
    fg_bom_det = []
    int_p20 = []
    change_rm = False
    sel_pl = None
    new_bom_derivative_opt = []
    new_fg_bom_derivative_opt = []
    bom_auto_pl_opt = []
    bom_sel_pl = None
    sel_unique_id = '*select*'
    sel_unique_row = ''
    unq_filter = False
    sel_pl_id = '*select*'
    bom_sel_pl_id = '*select*'
    bom_sel_unique_id = '*select*'
    create_pl = False
    sel_pl_unique = ''
    auto_pl_id_list = []
    cursor.execute("select * from department order by name")
    department_opt = cursor.fetchall()
    cursor.execute("select * from price_list order by name")
    auto_pl_name_opt = cursor.fetchall()
    bom_pl_name_opt = auto_pl_name_opt
    i = 1
    while i <= 20:
        int_p20.append('p' + str(i))
        i += 1
    cursor.execute("select * from pg_unique order by name")
    unique_opt = cursor.fetchall()
    cursor.execute("select * from raw_material_price order by name")
    rm_price_opt = cursor.fetchall()
    filter_qry = "name ilike '%%'"
    exclude_qry = "name ilike ''"#as this is used to exclude items we cannot use %% as everything gets excluded
    if request.GET:
        get_data = request.GET
        sel_pl_id = int(get_data['parent_pl_id'])
        cursor.execute("select * from price_list where id=%d order by name" % (sel_pl_id))
        sel_pl = cursor.fetchone()
        sel_unique_id = int(sel_pl['unique_id'])
        unq_filter = True
        if 'child_pl_id' in get_data:
            try:
                int(get_data['child_pl_id'])
            except:
                '''do nothing'''
            else:
                bom_sel_pl_id = int(get_data['child_pl_id'])
    if request.POST:
        post_data = request.POST
        searched_str = post_data['searched_str']
        sel_unique_id = post_data['unique_id']
        if 'unique_id' in post_data:
            try:
                int(sel_unique_id)
            except:
                '''do nothing'''
            else:
                unq_filter = True
                sel_unique_id = int(sel_unique_id)
        if 'sel_pl_id' in post_data:
            sel_pl_id = post_data['sel_pl_id']
            if not sel_pl_id == '*select*':
                sel_pl_id = int(post_data['sel_pl_id'])
                cursor.execute("select * from price_list where id=%d order by name" % (sel_pl_id))
                sel_pl = cursor.fetchone()
                sel_unique_id = int(sel_pl['unique_id'])
                unq_filter = True
    pl_qry = name_filter_qry_builder({'input_type':'!~', 'input':searched_str})
    filter_qry = pl_qry['filter_qry']
    exclude_qry = pl_qry['exclude_qry']
    if not sel_unique_id == '*select*':
        cursor.execute("select * from price_list where unique_id=%d order by name" % (sel_unique_id))
        auto_pl_name_opt = cursor.fetchall()
    qry = ''
    if unq_filter == False:
        qry = "select * from price_list where (%s) and not (%s) order by name" % (filter_qry, exclude_qry)
        cursor.execute("select * from price_list where (%s) and not (%s) order by name" % (filter_qry, exclude_qry))
    else:
        qry = "select * from price_list where (unique_id=%d and (%s) and not (%s)) order by name" % (sel_unique_id, filter_qry, exclude_qry)
        cursor.execute("select * from price_list where (unique_id=%d and (%s) and not (%s)) order by name" % (sel_unique_id, filter_qry, exclude_qry))
    auto_pl_opt = cursor.fetchall()
    for cur_auto_pl in auto_pl_opt:
        auto_pl_id_list.append(cur_auto_pl['id'])
    if len(auto_pl_opt) == 1:
        '''in case exact name is searched, we might as well make this the selected PL'''
        sel_pl_id = auto_pl_opt[0]['id']
    if request.POST:
        post_data = request.POST
        searched_str = post_data['searched_str']
        if 'change_rm' in post_data:
            change_rm = True
        if 'sel_pl_id' in post_data:
            sel_pl_id = post_data['sel_pl_id']
        if 'delete' in post_data:
            try:
                int(sel_pl_id)
            except:
                '''do nothing'''
            else:
                cursor.execute("delete from fg_derivative where pl_id=%d" % (int(sel_pl_id),))
                db.commit()
                cursor.execute("delete from derivative where pl_id=%d" % (int(sel_pl_id),))
                db.commit()
                cursor.execute("delete from associated_fg where pl_id=%d" % (int(sel_pl_id),))
                db.commit()
                cursor.execute("delete from b_o_m where pl_id=%d" % (int(sel_pl_id),))
                db.commit()
                cursor.execute("delete from price_list where id=%d" % (int(sel_pl_id),))
                db.commit()
                sel_pl_id = '*select*'
        if 'bom_unique_id' in post_data:
            bom_sel_unique_id = post_data['bom_unique_id']
            bom_unq_filter = False
            try:
                int(bom_sel_unique_id)
            except:
                '''do nothing'''
            else:
                bom_unq_filter = True
                bom_sel_unique_id = int(bom_sel_unique_id)
                cursor.execute("select * from price_list where unique_id=%d order by name" % (bom_sel_unique_id))
                bom_pl_name_opt = cursor.fetchall()
            bom_searched_str = post_data['bom_searched_str']
            bom_sel_pl_id = post_data['bom_sel_pl_id']
            pl_qry = name_filter_qry_builder({'input_type':'!~', 'input':bom_searched_str})
            filter_qry = pl_qry['filter_qry']
            exclude_qry = pl_qry['exclude_qry']
            if bom_unq_filter == False:
                cursor.execute("select * from price_list where (%s) and not (%s) order by name" % (filter_qry, exclude_qry))
            else:
                cursor.execute("select * from price_list where unique_id=%d and (%s) and not (%s) order by name" % (bom_sel_unique_id, filter_qry, exclude_qry))
            bom_auto_pl_opt = cursor.fetchall()
            try:
                int(bom_sel_pl_id)
            except:
                '''do nothing'''
            else:
                bom_sel_pl_id = int(bom_sel_pl_id)
                cursor.execute("select * from price_list where id=%d" % (int(bom_sel_pl_id)))
                bom_sel_pl = cursor.fetchall()[0]
                cursor.execute("select * from derivative where pl_id=%d" % (int(bom_sel_pl_id)))
                new_bom_derivative_opt = cursor.fetchall()
                cursor.execute("select * from fg_derivative where pl_id=%d" % (int(bom_sel_pl_id)))
                new_fg_bom_derivative_opt = cursor.fetchall()
        if 'new_s3_opt' in post_data or 'update_s3_opt' in post_data:
            new_s3_str = post_data['new_s3_str']
            cursor.execute("select * from pg_unique where id=%d" % (int(sel_unique_id)))
            sel_unique_row = cursor.fetchone()
            part_group_id = int(sel_unique_row['ptr_s3'])
            cursor.execute("select * from part_lookup where group_id=%d and name ilike '%s'" % (part_group_id, new_s3_str))
            sel_part_lookup_row = cursor.fetchall()
            if len(sel_part_lookup_row) == 0:
                if 'new_s3_opt' in post_data:
                    cursor.execute("select * from part_lookup where group_id=%d order by -param;" % (part_group_id,))
                    ordered_lookup = cursor.fetchall()
                    if len(ordered_lookup) > 0:
                        max_lookup = int(ordered_lookup[0]['param'])
                    else:
                        max_lookup = 0
                    cursor.execute("insert into part_lookup (id, name, group_id, param) VALUES (default, '%s', %d, %d);" % (new_s3_str, part_group_id, max_lookup + 1))
                    db.commit()
                if 'update_s3_opt' in post_data:
                    lookup_id = int(post_data['s3'])
                    cursor.execute("update part_lookup set name='%s' where  group_id=%d and param=%d;" % (new_s3_str, part_group_id, lookup_id))
                    db.commit()
    
    crm_part_no = '*select*'
    
    try:
        int(sel_pl_id)
    except:
        '''do nothing'''
    else:
        sel_pl_id = int(sel_pl_id)
        cursor.execute("select * from price_list where id=%d order by id" % (sel_pl_id,))
        sel_pl = cursor.fetchone()
        unique_id = int(sel_pl['unique_id'])
        sel_unique_id = unique_id

    allow_pl_create = False
    lookup_data = {}
    try:
        int(sel_unique_id)
    except:
        '''do nothing'''
    else:
        allow_pl_create = True
        cursor.execute("select * from pg_unique where id=%d" % (int(sel_unique_id),))
        sel_unique_row = cursor.fetchone()
    if allow_pl_create:
        lookup_data = get_part_lookup_opt(sel_unique_id)
        post_data = request.POST
        if 'auto_pl_id_list' in post_data:
            sel_pl_id = int(post_data['sel_pl_id'])
            auto_pl_id_list = ast.literal_eval(post_data['auto_pl_id_list'])
            bulk_bom_pl_id = int(post_data['bulk_bom_pl_id'])
            bulk_derivative_id = int(post_data['bulk_derivative_id'])
            if post_data['update_type'] == 'fg_bom':
                cursor.execute("select * from fg_derivative where id=%d and pl_id=%d" % (bulk_derivative_id, bulk_bom_pl_id))
                match_check = cursor.fetchall()
                table_name = 'associated_fg'
                pl_col_name = 'pl_id'
                derivative_col_name = 'fg_derivative_id'
                bom_col_name = 'associated_fg_id' 
            elif post_data['update_type'] ==  'production_bom':
                cursor.execute("select * from derivative where id=%d and pl_id=%d" % (bulk_derivative_id, bulk_bom_pl_id))
                match_check = cursor.fetchall()
                table_name = 'b_o_m'
                pl_col_name = 'pl_id'
                derivative_col_name = 'derivative_id'
                bom_col_name = 'bom_id'
            if len(match_check) == 1:
                if 'update_all' in post_data:
                    for cur_auto_pl_id in auto_pl_id_list:
                        cursor.execute("update '%s' set %s=%d where %s=%d and %s=%d" % 
                                       (table_name, derivative_col_name, bulk_derivative_id, pl_col_name, cur_auto_pl_id, bom_col_name, bulk_bom_pl_id))
                        db.commit()
                if 'create_all' in post_data:
                    for cur_auto_pl_id in auto_pl_id_list:
                        cursor.execute("select * from %s where %s=%d and %s=%d and %s=%d" % 
                                       (table_name, derivative_col_name, bulk_derivative_id, pl_col_name, cur_auto_pl_id, bom_col_name, bulk_bom_pl_id))
                        matching_row = cursor.fetchall()
                        if len(matching_row) == 0:
                            cursor.execute("insert into %s (%s,%s,%s) VALUES (%d, %d, %d)" % 
                                           (table_name, derivative_col_name, pl_col_name, bom_col_name, bulk_derivative_id, cur_auto_pl_id, bulk_bom_pl_id))
                            db.commit()
                if 'delete_all' in post_data:
                    for cur_auto_pl_id in auto_pl_id_list:
                        cursor.execute("select * from %s where %s=%d and %s=%d and %s=%d" % 
                                       (table_name, derivative_col_name, bulk_derivative_id, pl_col_name, cur_auto_pl_id, bom_col_name, bulk_bom_pl_id))
                        matching_row = cursor.fetchall()
                        if len(matching_row) > 0:
                            cursor.execute("delete from %s where %s=%d and %s=%d and %s=%d" % 
                                       (table_name, derivative_col_name, bulk_derivative_id, pl_col_name, cur_auto_pl_id, bom_col_name, bulk_bom_pl_id))
                            db.commit()
            #return HttpResponseRedirect(reverse('journal_mgmt:crm_auto_pl_mgmt', args=()) + '?parent_pl_id=' + str(sel_pl_id))
        if 'copy_and_create' in post_data or 'update' in post_data or 'create' in post_data or 'update_s3_opt' in post_data:
            cur_pl_id = sel_pl_id
            system_id = int(post_data['system'])
            material_id = int(post_data['material'])
            s1 = int(post_data['s1'])
            s2 = int(post_data['s2'])
            s3 = int(post_data['s3'])
            pn_exists = False
            cursor.execute("select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d" % (sel_unique_id, system_id, material_id, s1, s2, s3))
            qry_ret = cursor.fetchall()
            if len(qry_ret) > 0:
                pn_exists = True
            crm_part_no = str(1000 + sel_unique_id)[1:] + '-' + str(100 + system_id)[1:] + '-' +  str(100 + material_id)[1:] + '-' \
                    + str(1000+s1)[1:] +  '-' + str(1000+s2)[1:] +  '-' + str(1000+s3)[1:] + '-0000-0000-0000-0000'
            new_description = description_gen(crm_part_no)
            if ('create' in post_data or 'copy_and_create' in post_data) and pn_exists == False:
                qry_build = "insert into price_list (id, name, unique_id, system_id, material_id, s1, s2, s3) VALUES (default, '%s', %d, %d, %d, %d, %d, %d) RETURNING id"
                qry_values = [new_description, sel_unique_id, system_id, material_id, s1, s2, s3]
                cursor.execute(qry_build % tuple(qry_values))
                db.commit()
                new_pl_id = cursor.fetchone()[0]
                cur_pl_id = new_pl_id
                if 'copy_and_create' in post_data:
                    cursor.execute("select * from b_o_m where pl_id=%d" % (sel_pl_id,))
                    available_bom = cursor.fetchall()
                    for cur_bom in available_bom:
                        cursor.execute("insert into b_o_m (id, pl_id, bom_id, derivative_id) VALUES (default, %d, %d, %d)" % (new_pl_id, cur_bom['bom_id'], cur_bom['derivative_id']))
                        db.commit()
                    cursor.execute("select * from associated_fg where pl_id=%d" % (sel_pl_id,))
                    available_fg_bom = cursor.fetchall()
                    for cur_fg_bom in available_fg_bom:
                        cursor.execute("insert into associated_fg (id, name, pl_id, associated_fg_id, fg_derivative_id) VALUES (default, 'abc', %d, %d, %d)" % (new_pl_id, cur_fg_bom['associated_fg_id'], cur_fg_bom['fg_derivative_id']))
                        db.commit()
                    cursor.execute("select * from derivative where pl_id=%d" % (sel_pl_id,))
                    available_derivative = cursor.fetchall()
                    for cur_der in available_derivative:
                        qry_build = "insert into derivative (id, name, pl_id, d1, d2, d3, d4, qty, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12) VALUES" 
                        qry_build += "(default, '%s', %d, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')"
                        qry_values = [cur_der.name, new_pl_id, cur_der['d1'], cur_der['d2'], cur_der['d3'], cur_der['d4'], cur_der['qty']]
                        i = 1
                        while i <= 12:
                            qry_values.append(cur_der['f'+str(i)])
                            i += 1
                        cursor.execute(qry_build % tuple(qry_values))
                        db.commit()
                    cursor.execute("select * from fg_derivative where pl_id=%d" % (sel_pl_id,))
                    available_fg_derivative = cursor.fetchall()
                    for cur_der in available_fg_derivative:
                        qry_build = "insert into fg_derivative (id, name, pl_id, d1, d2, d3, d4, qty, fin_str) VALUES" 
                        qry_build += "(default, '%s', %d, '%s', '%s', '%s', '%s', '%s', '%s')"
                        qry_values = [cur_der['name'], new_pl_id, cur_der['d1'], cur_der['d2'], cur_der['d3'], cur_der['d4'], cur_der['qty'], cur_der['fin_str']]
                        cursor.execute(qry_build % tuple(qry_values))
                        db.commit()
            elif 'update' in post_data and pn_exists == False:
                cursor.execute("update price_list set unique_id=%d, system_id=%d, material_id=%d, s1=%d, s2=%d, s3=%d where id=%d" % (sel_unique_id, system_id, material_id, s1, s2, s3, sel_pl_id))
                db.commit()
            '''check for PN again'''
            cursor.execute("select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d" % (sel_unique_id, system_id, material_id, s1, s2, s3))
            qry_ret = cursor.fetchall()
            if len(qry_ret) > 0:
                pn_exists = True
            if pn_exists == True:
                qry_build = "update price_list set name='%s', calculation='%s', calculation_bom='%s', input_calc='%s', sale_margin=%f, price=%f, "
                qry_build += "units='%s', department_id=%d, imaginary_item=%s"
                imaginary_item = False
                if 'imaginary_item' in post_data:
                    imaginary_item = True
                if 'update_unique' in post_data:
                    if imaginary_item:
                        imag_val = 1
                    else:
                        imag_val = 0
                    cursor.execute("update pg_unique set imaginary='%s' where id=%d" % (str(imag_val), sel_unique_id))
                    db.commit()
                qry_values = []
                calculation = post_data['calculation'] if (not post_data['calculation'] == None and not post_data['calculation'] == '') else 0
                calculation_bom = post_data['calculation_bom'] if (not post_data['calculation_bom'] == None and not post_data['calculation_bom'] == '') else 0
                input_calc = post_data['input_calc'] if (not post_data['input_calc'] != None and not post_data['input_calc'] == '') else 0
                sale_margin = float(post_data['sale_margin']) if (not post_data['sale_margin'] == None and not post_data['sale_margin'] == '') else 0
                price = float(post_data['price']) if (not post_data['price'] == None and not post_data['price'] == '') else 0
                units = post_data['units'] if (not post_data['units'] == None and not post_data['units'] == '') else 0
                department = int(post_data['department']) if (not post_data['department'] == None and not post_data['department'] == '') else 0
                qry_values += [new_description, calculation, calculation_bom, input_calc, sale_margin, price, units, department, imaginary_item]
                i = 1
                while i <= 20:
                    cur_key = "p" + str(i)
                    cur_col = "p" + str(i)
                    qry_build += ", " + cur_col + "=%d"
                    qry_values.append(int(post_data[cur_key]))
                    i += 1
                qry_build += ' where id=%d;'
                qry_values.append(cur_pl_id)
                cursor.execute(qry_build % tuple(qry_values))
                db.commit()
                #return HttpResponseRedirect(reverse('journal_mgmt:crm_auto_pl_mgmt', args=()) + '?parent_pl_id=' + str(cur_pl_id))
    
    '''auto selection of pl id in case only 1 applicable PL, this is done after creation/updation of PL'''
    pl_qry = name_filter_qry_builder({'input_type':'!~', 'input':searched_str})
    filter_qry = pl_qry['filter_qry']
    exclude_qry = pl_qry['exclude_qry']
    if not sel_unique_id == '*select*':
        cursor.execute("select * from price_list where unique_id=%d order by name" % (sel_unique_id))
        auto_pl_name_opt = cursor.fetchall()
    qry = ''
    if unq_filter == False:
        qry = "select * from price_list where (%s) and not (%s) order by name" % (filter_qry, exclude_qry)
        cursor.execute("select * from price_list where (%s) and not (%s) order by name" % (filter_qry, exclude_qry))
    else:
        qry = "select * from price_list where (unique_id=%d and (%s) and not (%s)) order by name" % (sel_unique_id, filter_qry, exclude_qry)
        cursor.execute("select * from price_list where (unique_id=%d and (%s) and not (%s)) order by name" % (sel_unique_id, filter_qry, exclude_qry))
    auto_pl_opt = cursor.fetchall()
    for cur_auto_pl in auto_pl_opt:
        auto_pl_id_list.append(cur_auto_pl['id'])
    if len(auto_pl_opt) == 1:
        '''in case exact name is searched, we might as well make this the selected PL'''
        sel_pl_id = auto_pl_opt[0]['id']
    
    
    '''Getting data for display'''
    if not sel_pl_id == '*select*':
        sel_pl_id = int(sel_pl_id)
        cursor.execute("select * from price_list where id=%d order by id" % (sel_pl_id,))
        sel_pl = cursor.fetchone()
        unique_id = int(sel_pl['unique_id'])
        sel_unique_id = unique_id
        system_id = int(sel_pl['system_id'])
        material_id = int(sel_pl['material_id'])
        s1 = int(sel_pl['s1'])
        s2 = int(sel_pl['s2'])
        s3 = int(sel_pl['s3'])
        crm_part_no = str(1000 + unique_id)[1:] + '-' + str(100 + system_id)[1:] + '-' +  str(100 + material_id)[1:] + '-' \
                    + str(1000+s1)[1:] +  '-' + str(1000+s2)[1:] +  '-' + str(1000+s3)[1:] + '-0000-0000-0000-0000'
        cursor.execute("select * from pg_unique where id=%d" % (unique_id,))
        sel_pl_unique = cursor.fetchone()
        cursor.execute("select * from b_o_m where pl_id=%d order by pl_id" % (sel_pl_id,))
        bom_index = cursor.fetchall()
        cursor.execute("select * from derivative where pl_id=%d order by pl_id" % (sel_pl_id,))
        derivative_index = cursor.fetchall()
        cursor.execute("select * from associated_fg where pl_id=%d order by pl_id" % (sel_pl_id,))
        fg_bom_index = cursor.fetchall()
        cursor.execute("select * from fg_derivative where pl_id=%d order by pl_id" % (sel_pl_id,))
        fg_derivative_index = cursor.fetchall()
        cursor.execute("select * from price_list where exists (select * from b_o_m where bom_id=%d and pl_id=price_list.id) order by name;" % (sel_pl_id,))
        parent_list = cursor.fetchall()
        cursor.execute("select * from price_list where exists (select * from associated_fg where associated_fg_id=%d and pl_id=price_list.id) order by name;" % (sel_pl_id,))
        fg_parent_list = cursor.fetchall()
        for cur_bom_index in bom_index:
            cursor.execute("select * from price_list where id=%d" % (cur_bom_index['bom_id'],))
            pl_record = cursor.fetchone()
            cursor.execute("select * from derivative where id=%d" % (cur_bom_index['derivative_id'],))
            derivative_record = cursor.fetchone()
            cursor.execute("select * from derivative where pl_id=%d" % (cur_bom_index['bom_id'],))
            derivative_opt = cursor.fetchall()
            bom_det.append({'bom_record':cur_bom_index, 'pl_record':pl_record, 'derivative_record':derivative_record, \
                            'derivative_opt':derivative_opt})
        for cur_fg_bom_index in fg_bom_index:
            cursor.execute("select * from price_list where id=%d" % (cur_fg_bom_index['associated_fg_id'],))
            pl_record = cursor.fetchone()
            cursor.execute("select * from fg_derivative where id=%d" % (cur_fg_bom_index['fg_derivative_id'],))
            derivative_record = cursor.fetchone()
            cursor.execute("select * from fg_derivative where pl_id=%d" % (cur_fg_bom_index['associated_fg_id'],))
            derivative_opt = cursor.fetchall()
            fg_bom_det.append({'bom_record':cur_fg_bom_index, 'pl_record':pl_record, 'derivative_record':derivative_record, \
                            'derivative_opt':derivative_opt})
    
    
    
    
    data['department_opt'] = department_opt
    data['lookup_data'] = lookup_data
    data['allow_pl_create'] = allow_pl_create
    data['auto_pl_opt'] = auto_pl_opt
    data['auto_pl_id_list'] = auto_pl_id_list
    data['bom_auto_pl_opt'] = bom_auto_pl_opt
    data['bom_index'] = bom_index
    data['bom_det'] = bom_det
    data['bom_searched_str'] = bom_searched_str
    data['bom_sel_pl'] = bom_sel_pl
    data['bom_sel_pl_id'] = bom_sel_pl_id
    data['bom_sel_unique_id'] = bom_sel_unique_id
    data['change_rm'] = change_rm
    data['derivative_index'] = derivative_index
    data['fg_bom_index'] = fg_bom_index
    data['fg_bom_det'] = fg_bom_det
    data['fg_derivative_index'] = fg_derivative_index
    data['fg_parent_list'] = fg_parent_list
    data['int_p20'] = int_p20
    data['new_bom_derivative_opt'] = new_bom_derivative_opt
    data['new_fg_bom_derivative_opt'] = new_fg_bom_derivative_opt
    data['parent_list'] = parent_list
    data['rm_price_opt'] = rm_price_opt
    data['sel_unique_id'] = sel_unique_id
    data['searched_str'] = searched_str
    data['sel_pl'] = sel_pl
    data['sel_pl_id'] = sel_pl_id
    data['unique_opt'] = unique_opt
    data['sel_unique_row'] = sel_unique_row
    data['crm_part_no'] = crm_part_no
    data['sel_pl_unique'] = sel_pl_unique
    data['auto_pl_name_opt'] = auto_pl_name_opt
    data['bom_pl_name_opt'] = bom_pl_name_opt
    cursor.close()
    db.close()
    #return(render(request, 'journal_mgmt/test_response.html', {'data': data}))
    return(render(request, 'journal_mgmt/crm_auto_pl_mgmt.html', {'data': data}))

def crm_bom_crud(request, action_type, table_name):
    data = {}
    if request.POST:
        db_crm_dict = crm_connect_data()
        db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        post_data = request.POST
        parent_pl_id = int(post_data['parent_pl_id'])
        child_pl_id = '*select*'
        try:
            int(post_data['child_pl_id'])
        except:
            '''do nothing'''
        else:
            child_pl_id = int(post_data['child_pl_id'])
        if 'derivative_id' in post_data:
            derivative_id = int(post_data['derivative_id'])
        if table_name == 'bom':
            if action_type == 'create':
                cursor.execute("insert into b_o_m (pl_id, bom_id, derivative_id) VALUES (%d, %d, %d)" % (parent_pl_id, child_pl_id, derivative_id))
                db.commit()
            elif action_type == 'update':
                bom_prim_key = int(post_data['child_prim_key'])
                cursor.execute("update b_o_m set derivative_id=%d where id=%d" % (derivative_id, bom_prim_key))
                db.commit()
            elif action_type == 'delete':
                bom_prim_key = int(post_data['child_prim_key'])
                cursor.execute("delete from b_o_m where id=%d" % (bom_prim_key,))
                db.commit()
        elif table_name == 'fg_bom':
            if action_type == 'create':
                cursor.execute("insert into associated_fg (pl_id, associated_fg_id, fg_derivative_id) VALUES (%d, %d, %d)" % (parent_pl_id, child_pl_id, derivative_id))
                db.commit()
            elif action_type == 'update':
                bom_prim_key = int(post_data['child_prim_key'])
                cursor.execute("update associated_fg set fg_derivative_id=%d where id=%d" % (derivative_id, bom_prim_key))
                db.commit()
            elif action_type == 'delete':
                bom_prim_key = int(post_data['child_prim_key'])
                cursor.execute("delete from associated_fg where id=%d" % (bom_prim_key,))
                db.commit()
        cursor.close()
        db.close()
    return HttpResponseRedirect(reverse('journal_mgmt:crm_auto_pl_mgmt') + '?parent_pl_id=' + str(parent_pl_id) + '&child_pl_id=' + str(child_pl_id))

def crm_derivative_crud(request, action_type, table_name):
    data = {}
    if request.POST:
        db_crm_dict = crm_connect_data()
        db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        post_data = request.POST
        pl_id = int(post_data['sel_pl_id'])
        if action_type == 'delete':
            derivative_id = int(post_data['id'])
            if table_name == 'derivative':
                cursor.execute("delete from derivative where id=%d" % (derivative_id,))
                db.commit()
            elif table_name == 'fg_derivative':
                cursor.execute("delete from fg_derivative where id=%d" % (derivative_id,))
                db.commit()
            return HttpResponseRedirect(reverse('journal_mgmt:crm_auto_pl_mgmt') + '?parent_pl_id=' + str(pl_id))
        name = post_data['name']
        d1 = post_data['d1']
        d2 = post_data['d2']
        d3 = post_data['d3']
        d4 = post_data['d4']
        qty = post_data['qty']
        if 'derivative_id' in post_data:
            derivative_id = int(post_data['derivative_id'])
        if table_name == 'derivative':
            f1 = post_data['f1']
            f2 = post_data['f2']
            f3 = post_data['f3']
            f4 = post_data['f4']
            f5 = post_data['f5']
            f6 = post_data['f6']
            f7 = post_data['f7']
            f8 = post_data['f8']
            f9 = post_data['f9']
            f10 = post_data['f10']
            f11 = post_data['f11']
            f12 = post_data['f12']
            std_insert_qry_part = "(name, d1, d2, d3, d4, qty, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, pl_id)"
            std_insert_qry_part += " VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %d)"
            std_update_qry_part = "name='%s', d1='%s', d2='%s', d3='%s', d4='%s', qty='%s',"
            std_update_qry_part += " f1='%s', f2='%s', f3='%s', f4='%s', f5='%s', f6='%s', f7='%s', f8='%s', f9='%s', f10='%s', f11='%s', f12='%s', pl_id=%d where id=%d"
            if action_type == 'create':
                qry_build = "insert into derivative " + std_insert_qry_part
                cursor.execute(qry_build % (name, d1, d2, d3, d4, qty, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, pl_id))
                db.commit()
            elif action_type == 'update':
                derivative_id = int(post_data['id'])
                qry_build = "update derivative set " + std_update_qry_part
                cursor.execute(qry_build % (name, d1, d2, d3, d4, qty, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, pl_id, derivative_id))
                db.commit()
        elif table_name == 'fg_derivative':
            fin_str = post_data['fin_str']
            if action_type == 'create':
                qry_build = "insert into fg_derivative (name, d1, d2, d3, d4, qty, fin_str, pl_id) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', %d)"
                cursor.execute(qry_build % (name, d1, d2, d3, d4, qty, fin_str, pl_id))
                db.commit()
            elif action_type == 'update':
                derivative_id = int(post_data['id'])
                qry_build = "update fg_derivative set name='%s', d1='%s', d2='%s', d3='%s', d4='%s', qty='%s', fin_str='%s', pl_id=%d where id=%d"
                cursor.execute(qry_build % (name, d1, d2, d3, d4, qty, fin_str, pl_id, derivative_id))
                db.commit()
        cursor.close()
        db.close()
    return HttpResponseRedirect(reverse('journal_mgmt:crm_auto_pl_mgmt') + '?parent_pl_id=' + str(pl_id))

def auto_pl_mgmt(request):
    data = {}
    bom_pl_list = []
    final_parent_list = []
    parent_list =[]
    derivative_id_list = []
    pl_item_list = []
    raw_material_obj = rmp_auto.objects.all().order_by('name')
    pl_list = auto_price_list.objects.all().order_by('name')
    deravitive_object = 0
    cur_name_search = ''
    price_list_object_list = []
    item_list = []
    raw_material_list = []
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    name = ''
    pl_obj = ''
    bom_pl_object = 0
    id_list = []
    del_item_list = []
    sel_pl_id = 0
    price_list_object = ''
    delete = "False"
    sel_raw_material_id = 0
    searched_name_set = ''
    weight_calc_eqn = ''
    volume_calc_eqn = ''
    for cur_raw in raw_material_obj:
        raw_material_list.append(cur_raw)
    if request.GET:
        get_data = request.GET
        sel_raw_material_id = int(get_data['raw_material_id'])
        sel_pl_id = int(get_data['pl_item_id'])
        name = str(get_data['searched_name'])
    if request.POST:
        post_data = request.POST
        i = 1
        try:
            int(post_data['raw_material'])
        except:
            sel_raw_material_id = 0
        else:
            sel_raw_material_id = int(post_data['raw_material'])
        if 'searched_param' in post_data:
            searched_name_set = post_data['searched_param'].split('!!')
            name = post_data['searched_param']
        if 'edit' in post_data:
            data['edit'] = "True"
            cursor.execute("select * from derivative where id = %d ;" % (int(post_data['edit'])))
            object = cursor.fetchall() 
            for cur_boj in object:
                derivative_id_list.append(cur_boj)
            """ UPDATEING DERIVATIVE """
        if 'add' in post_data:
            while i < 2:
                d1_value = 'd1'
                if d1_value in post_data:
                    d1 = str(post_data[d1_value])
                d2_value = 'd2'
                if d2_value in post_data:
                    d2 = str(post_data[d2_value])
                d3_value = 'd3'
                if d3_value in post_data:
                    d3 = str(post_data[d3_value])
                d4_value = 'd4'
                if d4_value in post_data:
                    d4 = str(post_data[d4_value])
                qty_value = 'qty'
                if qty_value in post_data:
                    qty = str(post_data[qty_value])
                data['d1'] = d1
                data['d2'] = d2
                data['d3'] = d3
                data['d4'] = d4    
                data['qty'] = qty
                i += 1
            derivative_id = int(post_data['add'])
            cursor.execute("update derivative set d1 = '%s', d2 = '%s', d3 = '%s', d4 = '%s', qty = '%s' where id = %d " 
                           % (d1, d2, d3, d4, qty, int(derivative_id)))
            db.commit()
        if 'add_pl_eqn' in post_data:
            if 'weight_calc_eqn' in post_data:
                weight_calc_eqn = str(post_data['weight_calc_eqn'])
                
            if 'volume_calc_eqn' in post_data:
                volume_calc_eqn = str(post_data['volume_calc_eqn'])
        if 'pl_item' in post_data:
            if post_data['pl_item'] == '':
                """ DO NOTHING """
            else:
                sel_pl_id = int(post_data['pl_item'])
                get_str = "?pl_item_id=" + str(sel_pl_id) + "&raw_material_id=" + str(sel_raw_material_id) + "&searched_name=" + str(name) 
                i = 0
                while i < 100:
                    if 'delete_' + str(i) in post_data:
                        delete = "True"
                        break
                    else:
                        i += 1
    
    for cur_name_search in searched_name_set:
        pl_item_list = auto_price_list.objects.filter(name__icontains=cur_name_search).order_by('name')
    #pl_item_list = auto_price_list.objects.all()
    if sel_raw_material_id > 0:
        pl_item_list = auto_price_list.objects.filter((Q(p1=sel_raw_material_id) | Q(p2=sel_raw_material_id) | Q(p3=sel_raw_material_id) | Q(p4=sel_raw_material_id) | Q(p5=sel_raw_material_id) |\
                                                        Q(p6=sel_raw_material_id) | Q(p7=sel_raw_material_id) | Q(p8=sel_raw_material_id) | Q(p9=sel_raw_material_id) | Q(p10=sel_raw_material_id) |\
                                                        Q(p11=sel_raw_material_id) | Q(p12=sel_raw_material_id) | Q(p13=sel_raw_material_id) | Q(p14=sel_raw_material_id) | Q(p15=sel_raw_material_id) |\
                                                       Q(p16=sel_raw_material_id) | Q(p17=sel_raw_material_id) | Q(p18=sel_raw_material_id) | Q(p19=sel_raw_material_id) | Q(p20=sel_raw_material_id))).order_by('name')
    
    for cur_pl_item in pl_item_list:
        item_list.append(cur_pl_item)
    if request.GET:
        if 'parent_pl_item_id' in get_data:
            parent_id = int(get_data['parent_pl_item_id'])
            cursor.execute("select * from price_list where id = %d ;" % (int(parent_id)))
            object = cursor.fetchall() 
            for cur_pl_obj in object:
                parent_spec_code = str(cur_pl_obj[2] + 1000)[1:] +"-" + str(cur_pl_obj[3] + 100)[1:] +"-" + str(cur_pl_obj[4] + 100)[1:] +"-" + str(cur_pl_obj[5] + 1000)[1:] +"-" \
                            + str(cur_pl_obj[6] + 1000)[1:] +"-" + str(cur_pl_obj[7] + 1000)[1:]
            parent_pl_obj = get_object_or_404(auto_price_list, spec_code = parent_spec_code)
            sel_pl_id = parent_pl_obj.id
    if sel_pl_id > 0:
        pl_obj = get_object_or_404(auto_price_list, id = sel_pl_id)     
        query2 = "SELECT pl_id FROM b_o_m WHERE bom_id =%d ;" %  (int(pl_obj.flite_360_price_list_id)) 
        cursor.execute(query2)
        parent_bom_pl_object = cursor.fetchall()
        
        for cur_parent_bom in parent_bom_pl_object:
            query3 = "select id, name from price_list where id = " + str(cur_parent_bom[0]) + " ;" 
            cursor.execute(query3)
            sel_parent_bom_pl_object = cursor.fetchall()
            for cur_bom in sel_parent_bom_pl_object:
                query4 = "select derivative_id from b_o_m where pl_id = %d and bom_id = %d ;" % (int(cur_bom[0]), int(pl_obj.flite_360_price_list_id)) 
                cursor.execute(query4)
                final_parent_derivative_object = cursor.fetchall()
                id_list.append(cur_bom[0])
            for cur_derivative in final_parent_derivative_object:
                cursor.execute("select * from derivative where id = %d ;" % (int(cur_derivative[0])))
                parent_derivative_object = cursor.fetchall()
            count = 0
            for cur_id in  id_list:
                if cur_id == cur_bom[0]:
                    count += 1
            if count == 1:
                for cur_parent_derivative in parent_derivative_object:
                    id = str(cur_parent_derivative[0])
                    derivative_name = str(cur_parent_derivative[1])
                    d1 = str(cur_parent_derivative[2])
                    d2 = str(cur_parent_derivative[3])
                    d3 = str(cur_parent_derivative[4])
                    d4 = str(cur_parent_derivative[5])
                    qty = str(cur_parent_derivative[6])
                    parent_list.append((cur_bom[0], cur_bom[1], derivative_name, d1, d2, d3, d4, qty, id))
        query = "SELECT bom_id , derivative_id FROM b_o_m WHERE pl_id =%d ;" %  (int(pl_obj.flite_360_price_list_id)) 
        cursor.execute(query)
        bom_pl_object = cursor.fetchall()
        if len(bom_pl_object) > 0 :
            for cur_bom_id in bom_pl_object:
                pl_id = cur_bom_id[0]
                derivative_id = cur_bom_id[1]
                cursor.execute("select id, name from price_list where id = %d" % (int(pl_id)))
                bom_obj = cursor.fetchall()
                query1 = "select * from derivative where id = " + str(derivative_id) + " ;" 
                cursor.execute(query1)
                deravitive_object = cursor.fetchall()
                for cur_derivative in deravitive_object:
                    bom_pl_list.append((bom_obj[0][0], bom_obj[0][1], cur_derivative[2], cur_derivative[3], cur_derivative[4], cur_derivative[5], cur_derivative[6]))
            
        else:
            """ DO NOTHING """
        
        query = "SELECT * FROM price_list WHERE id = " + str(pl_obj.flite_360_price_list_id) + " ;" 
        cursor.execute(query)
        price_list_object = cursor.fetchall()
    if len(weight_calc_eqn) > 0:
        query = "UPDATE price_list set weight_calc_eqn = '" + weight_calc_eqn + "'  WHERE id = " + str(pl_obj.flite_360_price_list_id) + " ;" 
        cursor.execute(query)
        db.commit()
    if len(volume_calc_eqn) > 0:
        query = "UPDATE price_list set volume_calc_eqn = '" + volume_calc_eqn + "'  WHERE id = " + str(pl_obj.flite_360_price_list_id) + " ;" 
        cursor.execute(query)
        db.commit()
    for cur_pl_obj in price_list_object:
        cur_spec_code = str(1000 + int(cur_pl_obj[2]))[1:] + '-' + str(100 + int(cur_pl_obj[3]))[1:] + '-' + str(100 + int(cur_pl_obj[4]))[1:] + '-' + \
                                str(1000 + int(cur_pl_obj[5]))[1:] + '-' + str(1000 + int(cur_pl_obj[6]))[1:] + '-' + str(1000 + int(cur_pl_obj[7]))[1:]
        price_list_object_list.append(cur_pl_obj)
        update = sync_down_pl_360(cur_spec_code)
    if delete == "True":
        i  = i - 1
        for cur_del_id in bom_pl_list[i]:
            delete_id = cur_del_id
            cursor.execute("delete from b_o_m where pl_id = %d and bom_id = %d" % (int(pl_obj.flite_360_price_list_id), int(delete_id)))
            db.commit()
            delete_id = 0
            data['delete_id'] = delete_id
            return HttpResponseRedirect(reverse('journal_mgmt:auto_pl_mgmt') + get_str)
    
    data['raw_material_list'] = raw_material_list
    data['bom_pl_object'] = bom_pl_object
    data['deravitive_object'] = deravitive_object
    data['bom_pl_list'] = bom_pl_list
    data['sel_pl_id'] = sel_pl_id
    data['price_list_object_list'] = price_list_object_list
    data['derivative_id_list'] = derivative_id_list             
    data['pl_obj'] = pl_obj
    data['searched_param'] = name
    data['parent_list'] = parent_list
    data['sel_raw_material_id'] = sel_raw_material_id
    data['item_list'] = item_list
    return(render(request, 'journal_mgmt/auto_pl_mgmt.html', {'data': data}))


def bom_add_popup(request, pl_id):
    data = {}
    db_crm_dict = crm_connect_data()
    db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
    cursor = db.cursor()
    derivative_list = []
    sel_derivative_list = []
    item_list = []
    name = ''
    bom_pl_list = []
    pl_obj = get_object_or_404(auto_price_list , id = pl_id)
    query = "SELECT bom_id , derivative_id FROM b_o_m WHERE pl_id =%d ;" %  (int(pl_obj.flite_360_price_list_id)) 
    cursor.execute(query)
    bom_pl_object = cursor.fetchall()
    deravitive_object = ''
    sel_pl_item_id = 0
    auto_pl = auto_price_list.objects.all().order_by('name')
    sel_derivative_id = 0
    if len(bom_pl_object) > 0 :
        for cur_bom_id in bom_pl_object:
            pl_id = cur_bom_id[0]
            derivative_id = cur_bom_id[1]
            cursor.execute("select id, name from price_list where id = %d" % (int(pl_id)))
            bom_obj = cursor.fetchall()
            query1 = "select * from derivative where id = " + str(derivative_id) + " ;" 
            cursor.execute(query1)
            deravitive_object = cursor.fetchall()
            for cur_derivative in deravitive_object:
                bom_pl_list.append((bom_obj[0][0], bom_obj[0][1], cur_derivative[2], cur_derivative[3], cur_derivative[4], cur_derivative[5], cur_derivative[6]))
    
    data['bom_pl_object'] = bom_pl_object
    data['deravitive_object'] = deravitive_object
    data['derivative_list'] = derivative_list
    data['item_list'] = item_list
    data['bom_pl_list'] = bom_pl_list
    data['pl_obj'] = pl_obj
    if request.GET:
        get_data = request.GET
        searched_name = get_data['searched_param']
        pl_item = get_data['pl_item']
        derivative_id = get_data['derivative_id']
    if request.POST:
        post_data = request.POST
        if 'searched_param' in post_data:
            searched_name_set = post_data['searched_param'].split('!!')
            name = post_data['searched_param']
            for cur_name_search in searched_name_set:
                auto_pl = auto_pl.filter(name__icontains=cur_name_search)
        if 'pl_item' in post_data:
            pl_item = int(post_data['pl_item'])
            if pl_item == 0:
                """ DO NOTHING """
            else:
                data['sel_derivative'] = "True"
                sel_pl_item_id = int(post_data['pl_item'])   
                sel_item_obj = get_object_or_404(auto_price_list, id = sel_pl_item_id)
                unique_id = sel_item_obj.flite_360_price_list_id
                cursor.execute("select id , name from price_list where id = %d ;" % (int(unique_id)))
                bom_object = cursor.fetchall()
                for cur_bom_derivative in bom_object:
                    pl_id = cur_bom_derivative[0]
                    cursor.execute("select * from derivative where pl_id = %d ;" % (int(pl_id)))
                    derivative_object = cursor.fetchall()
                for cur_derivative in derivative_object:
                    derivative_list.append((cur_derivative[0], cur_derivative[1], cur_derivative[6]))
                data['sel_pl_item_id'] = sel_pl_item_id
        if 'derivative' in post_data:
            if post_data['derivative'] == '':
                """ DO NOTHING """
            else:
                sel_derivative_id = int(post_data['derivative']) 
                cursor.execute("select * from derivative where id = %d ;" % (int(sel_derivative_id)))
                sel_derivative_object = cursor.fetchall()
                for cur_sel_derivative in sel_derivative_object:
                    sel_derivative_list.append(cur_sel_derivative) 
        if 'add_derivative' in post_data:
            data['derivative_add'] = "True"
            
        if "add_pl_derivative" in post_data:
            query = "INSERT INTO derivative (name, d1, d2, d3, d4, qty, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, pl_id) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %d);" % (
                                str(post_data['derivative_name']), str(post_data['d1']), str(post_data['d2']), str(post_data['d3']), str(post_data['d4']), str(post_data['qty']), str(post_data['f1']), \
                                str(post_data['f2']), str(post_data['f3']), str(post_data['f4']), str(post_data['f5']), \
                                str(post_data['f6']), str(post_data['f7']), str(post_data['f8']), str(post_data['f9']), str(post_data['f10']), \
                                str(post_data['f11']), str(post_data['f12']), int(unique_id))
            cursor.execute(query)
            db.commit()
            return HttpResponseRedirect(reverse('journal_mgmt:bom_add_popup', args=(pl_obj.id,)))    
        if 'add' in post_data:
            if post_data['add'] == '':
                """ DO NOTHING """
            else: 
                cursor.execute("INSERT INTO b_o_m (pl_id, bom_id, derivative_id) values (%d, %d, %d);" % ((int(pl_obj.flite_360_price_list_id)), (int(pl_id)), (int(sel_derivative_id))))
                db.commit()
            sel_derivative_id = 0
            return HttpResponseRedirect(reverse('journal_mgmt:bom_add_popup', args=(pl_obj.id,)))    
    data['sel_derivative_list'] = sel_derivative_list
    data['auto_pl'] = auto_pl
    data['searched_param'] = name
    data['sel_derivative_id'] = sel_derivative_id
    return(render(request, 'journal_mgmt/pl_add_popup.html', {'data': data}))

def test_rig(request):
    data = {}
    data['message'] = {}
    data['message']['error_items'] = []
    all_item_master = item_master.objects.all()
    display_items = []
    get_data = request.GET
    data['get_data'] = get_data
    if get_data:
        if 'delete_duplicate_masters' in get_data:
            for cur_item in all_item_master:
                repeated_items = item_master.objects.filter(imported_item_code=cur_item.imported_item_code, imported_item_finish=cur_item.imported_item_finish)
                if len(repeated_items) > 1:
                    data['message']['error_items'].append(cur_item)
                    i = len(repeated_items)
                    while i > 1:
                        repeated_items[i - 1].delete()
                        i -= 1
        if 'normalize_spec_code' in get_data:
            data['count'] = 0
            for cur_item in all_item_master:
                if len(cur_item.imported_item_code) == 40:
                    cur_item.imported_item_code = '0' + cur_item.imported_item_code
                    cur_item.save()
                    data['count'] += 1
        if 'master_name_too_long' in get_data:
            data['long_item_master'] = []
            for cur_item in all_item_master:
                if len(cur_item.name) > 175:
                    find_res = cur_item.name.find('*Truncated')
                    if find_res > 0:
                        cur_item.name = cur_item.name[:130] + ' *Truncated Please see description'
                        cur_item.save()
                        data['long_item_master'].append(cur_item)
        if 'normalize_price_list_360' in get_data:
            if get_data['normalize_price_list_360'] == 'true':
                data['quote_pl'] = normalize_pl_360()
        
        if 'normalize_derivative_360' in get_data:
            if get_data['normalize_derivative_360'] == 'true':
                normalize_derivative_360()
        
        if 'test_360_update' in get_data:
            if get_data['test_360_update'] == 'true':
                db_crm_dict = crm_connect_data()
                db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
                cursor = db.cursor()
                cursor.execute('update price_list set material_id=%d where id=%d' % (0, 2561))
                cursor.close()
                db.close()
        
        if 'sync_rmp_price_list' in get_data:
            if get_data['sync_rmp_price_list'] == 'true':
                synchronize_rmp()
        
        if 'sync_item_group' in get_data:
            if get_data['sync_item_group'] == 'true':
                synchronize_item_group()
                
        if 'sync_item_group' in get_data:
            if get_data['sync_item_group'] == 'true':
                synchronize_item_department()
                
        if 'sync_price_list' in get_data:
            if 'sync_price_list' in get_data:
                normalize_pl_360()
                normalize_derivative_360()
                synchronize_rmp()
                synchronize_item_group()
                synchronize_item_department()
                auto_pl_list = auto_price_list
                feed_part_no = '015-06-04-003-000-000-0360-0900-0000-0000'
                feed_part_no = '069-02-01-900-002-000-0000-0000-0000-0000'
                # feed_part_fin = '1-0-0-0-0-0-0-0-0-0-0-0-0'
                feed_part_fin = '1-1-1-1-1-1-1-1-1-1-1-1-1'
                part_desc = description_gen(feed_part_no)
                print('Test Exit0')
                tup = (feed_part_no, feed_part_fin, 1.0)
                sync_pl_array = []
                auto_pl_list = auto_price_list.objects.all()
                auto_pl_list = auto_pl_list.exclude(spec_code__startswith='102')
                auto_pl_list = auto_pl_list.exclude(spec_code__startswith='103')
                # auto_pl_list = auto_pl_list.filter(spec_code__startswith = '078-01')
                # 9480938194 - hemanth pushpak
                for cur_auto_pl in auto_pl_list:
                    sync_pl_array.append((cur_auto_pl.spec_code))
                print('Feed Array for synchronization : ' + str(sync_pl_array))
                for cur_sync_pl in sync_pl_array:
                    test = 0
                    sync_down_pl_360(cur_sync_pl)
                    
        if 'update_all' in get_data:
            feed_type = {}
            feed_type['type'] = 'start_end'
            feed_type['renew'] = True
            all_item_master = item_master.objects.order_by('imported_item_code')
            all_item_master = all_item_master.exclude(imported_item_code__startswith='102')
            all_item_master = all_item_master.exclude(imported_item_code__startswith='103')
            if get_data['update_all'] == 'true':
                '''if get_data['renew'] == 'false':
                    feed_type['renew'] = False'''
                if 'group' in get_data:
                    grp_str = get_data['group']
                    all_item_master = all_item_master.filter(imported_item_code__startswith=grp_str)
                if 'bom_contains' in get_data:
                    bom_str = get_data['bom_contains']
                    all_item_master = all_item_master.filter(imported_bom__icontains=bom_str)
                if 'start' in get_data:
                    start = int(get_data['start'])
                else:
                    start = 0
                if 'end' in get_data:
                    end = int(get_data['end'])
                else:
                    end = 0
                respond = False
                count = 0
                if 'return' in get_data:
                    if get_data['return'] == 'true':
                        respond = True
                tot_len = len(all_item_master)
                all_item_master = all_item_master[start:end]
                start_time = timezone.now()
                time_up = False
                if get_data['func'] == 'bom':
                    ret_dict = update_all_bom(all_item_master, respond)
                    return(render(request, 'journal_mgmt/test_response.html', {'data': ret_dict['message']}))
                elif get_data['func'] == 'input_factor':
                    for cur_item_master in all_item_master:
                        if len(cur_item_master.imported_item_code.split('-')) == 10:
                            update_input_factor(cur_item_master.id)
                            count += 1
                        current_time = timezone.now()
                        time_diff = current_time - start_time
                        if time_diff >= timedelta(seconds=250) and respond == True:
                            time_up = True
                            break
                elif get_data['func'] == 'bom_sale_price':
                    for cur_item_master in all_item_master:
                        if len(cur_item_master.imported_item_code.split('-')) == 10:
                            bom_input_sum(cur_item_master.id, {'update_ip_factor':False})
                            count += 1
                        current_time = timezone.now()
                        time_diff = current_time - start_time
                        if time_diff >= timedelta(seconds=250) and respond == True:
                            time_up = True
                            break
                data = {'message':'Updated ' + str(count) + 'start from : ' + str(start+count) + ' given End point ' + str(end) + ' Total Items:' + str(tot_len)}
        if 'update_all_input_factor' in get_data:
            all_auto_pl = auto_price_list.objects.order_by('spec_code')
            all_auto_pl = all_auto_pl.exclude(spec_code__startswith='102')
            all_auto_pl = all_auto_pl.exclude(spec_code__startswith='103')
            if 'group' in get_data:
                all_auto_pl = all_auto_pl.filter(spec_code__startswith=get_data['group'])
            if 'start' in get_data:
                start = int(get_data['start'])
            else:
                start = 0
            if 'end' in get_data:
                end = int(get_data['end'])
            else:
                end = 0
            tot_len = len(all_auto_pl)
            all_auto_pl = all_auto_pl[start:end]
            for cur_auto_pl in all_auto_pl:
                update_batch_input_factor(cur_auto_pl.id)
            data = {'message':'Updated ' + str(end - start) + ' Items' + ' Total Items:' + str(tot_len)}
        if 'test_bom_gen' in get_data:
            item_id = int(get_data['id'])
            item_master_obj = get_object_or_404(item_master, id=item_id)
            data['bom'] = bom_generation(item_master_obj.imported_item_code, item_master_obj.imported_item_finish, 1.0)
        if 'add_pl_360' in get_data:
            if get_data['add_pl_360'] == 'true':
                # clone_price_list_360(73, '23-0-2-1-')
                test_auto_pl_create()
        if 'array_write_back' in get_data:
            if get_data['array_write_back'] == 'true':
                db_crm_dict = crm_connect_data()
                db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
                cursor = db.cursor()
                cursor.execute("""select data from quotation where id=3068""")
                fetched_data = cursor.fetchall()[0]
                print('Fetched Data : ' + str(fetched_data))
                test_data = {"pt": [], "lyt": {"2676": "BOM PRICING TEST layout"}, "ot": [], "oc": [], "items": {"16573": {"sl": "02", "n": "test part modifications", "2676": 1, "d": {"Name": "test"}, "tid": 9, "r": "", "c": 23042}}, "lvy": {"1": {"Excise Duty": "12.36"}, "2": {"Freight and Insurance": "5.00"}, "3": {"VAT": "14.50"}}}
                print('Test Data : ' + str(test_data))
                cursor.execute("""update quotation set data='%s' where id=3068""" % (json.dumps(test_data),))
                db.commit()
                cursor.close()
                db.close()
        if 'quote_pl_write_back' in get_data:
            if get_data['quote_pl_write_back'] == 'true':
                db_crm_dict = crm_connect_data()
                db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
                cursor = db.cursor()
                cursor.execute("""select parts from quote_pl where id=18735""")
                fetched_data = cursor.fetchall()[0]
                print('Fetched Data : ' + str(fetched_data))
                # test_data = {"B.Wood Department":[["083-01-00-000-000-000-0000-0000-0000-0000", "Zen Table Main Table + Side Storage - 1500", "-", "0-0-0-0-0-0-0-0-0-0-0-0-0", 1, 1, "23042.00", 23042, 23042]], "item":{"test - type 2 storage":1}}
                test_data = {"B.Wood Department":[["083-01-00-000-000-000-0000-0000-0000-0000", "Zen Table Main Table + Side Storage - 1500", "-", "1-1-1-1-1-1-1-1-1-1-1-1-0", 1, 1, "23042.00", 23042, 23042]], "item":{"test - type 2 storage":1}}
                print('Test Data : ' + str(test_data))
                cursor.execute("""update quote_pl set parts='%s' where id=18735""" % (json.dumps(test_data),))
                db.commit()
                cursor.close()
                db.close()
        if 'irrelevant_auto_pl' in get_data:
            if get_data['irrelevant_auto_pl'] == 'true':
                data['auto_pl_list'] = auto_price_list.objects.all()
                data['auto_pl_list'] = data['auto_pl_list'].exclude(spec_code__startswith='102')
                data['auto_pl_list'] = data['auto_pl_list'].exclude(spec_code__startswith='103')
                # data['auto_pl_count']
        # if 'wastage_correction' in get_data:
            # if get_data['wastage_correction'] == 'true':
        if 'del_auto_pl' in get_data:
            if get_data['del_auto_pl'] == 'true':
                del_auto_pl_360()
        if 'del_crm_auto_pl_complete' in get_data:
            if 'spec_code' in get_data:
                spec_code = get_data['spec_code']
                spec_split = spec_code.split('-')
                pl_search_str_bom = 'select * from price_list where unique_id=%d and system_id=%d and material_id=%d and s1=%d and s2=%d and s3=%d'
                pl_search_param_bom = (int(spec_split['n']), int(spec_split['s']), int(spec_split['m']), int(spec_split['s1']), int(spec_split['s2']), int(spec_split['s3']))
                cursor.execute(pl_search_str_bom % tuple(pl_search_param_bom))
        if 'update_input_factor' in get_data:
            if get_data['update_input_factor'] == 'true':
                data['tot'] = update_input_factor(int(get_data['id']))
        if 'part_id_conv' in get_data:
            if get_data['part_id_conv'] == 'true':
                start_count = int(get_data['start'])
                end_count = int(get_data['end'])
                update_pl = item_master.objects.all()
                update_pl = update_pl.exclude(imported_bom='[]')
                update_pl = update_pl.exclude(imported_bom='{}')
                update_pl = update_pl.filter(Q(bom='{}') | Q(bom='[]'))
                update_pl = update_pl.exclude(imported_item_code__startswith='102')
                update_pl = update_pl.exclude(imported_item_code__startswith='103')
                update_pl = update_pl[start_count:end_count]
                for cur_pl in update_pl:
                    cur_pl = get_object_or_404(item_master, id=cur_pl.id)
                    if len(cur_pl.imported_item_code.split('-')) == 10 and len(cur_pl.imported_item_code) == 41:
                        print(cur_pl.id)
                        imp_bom = ast.literal_eval(cur_pl.imported_bom)
                        bom = ast.literal_eval(cur_pl.bom)
                        if not len(bom) == len(imp_bom):
                            part_id_conversion([(cur_pl.imported_item_code, cur_pl.imported_item_finish, 1)])
        if 'test_func' in get_data:
            if get_data['test_func'] == 'true':
                app_item_master = item_master.objects.filter(Q(imported_bom__icontains='202-') | Q(imported_bom__icontains='212-') | Q(imported_bom__icontains='222-'))
                app_item_master = app_item_master.filter(id = 48052)
                update_all_bom(all_item_master)
                data['tot'] = 0
                #app_item_master = app_item_master[0:10]
                # part_id = int(get_data['id'])
                # bom_input_sum(int(get_data['id']), {'update_ip_factor':True})
        if 'excel_price_list' in get_data:
            if get_data['excel_price_list'] == 'true':
                db_crm_dict = crm_connect_data()
                db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
                cursor = db.cursor()
                cursor.execute("""select name, unique_id, price from price_list order by unique_id, system_id, material_id, s1, s2, s3""")
                fetched_data = cursor.fetchall()[0:2000]
                print('Fetched Data : ' + str(fetched_data))
                cursor.close()
                db.close()
                return penetration_xls(fetched_data)
        if 'excel_raw_material_price' in get_data:
            if get_data['excel_raw_material_price'] == 'true':
                db_crm_dict = crm_connect_data()
                db = psycopg2.connect(database=db_crm_dict['database'], user=db_crm_dict['user'], password=db_crm_dict['password'], host=db_crm_dict['host'], port=db_crm_dict['port'])
                cursor = db.cursor()
                cursor.execute("""select name, value, definition, constant_value from raw_material_price order by id""")
                fetched_data_1 = cursor.fetchall()[0:2000]
                print('Fetched Data : ' + str(fetched_data_1))
                cursor.close()
                db.close()
                return rmp_export(fetched_data_1)
        if 'replace_item_master' in get_data:
            old_item_id = int(get_data['old_item_id'])
            new_item_id = int(get_data['old_item_id'])
            replace_item_master(old_item_id, new_item_id)
        if 'price_matrix_xls' in get_data:
            export_genre = get_data['export_genre']
            dim_data = xls_price_matrix_data()
            req_dict = {k: v for k, v in dim_data.items() if v[0]['sheet'] == export_genre}
            if len(req_dict) == 0:
                error_message = 'genre not available please choose from : '
                unique_genre = []
                for cur_auto_pl_id, dim_dict in dim_data.items():
                    if not dim_dict[0]['sheet'] in unique_genre:
                        error_message += str(dim_dict[0]['sheet']) + ', '
                return Exception(error_message)
            else:
                auto_pl_feed = []
                max_col = 0
                for cur_auto_pl_id, dim_dict in sorted(req_dict.items()):
                    for cur_dim_dict in dim_dict:
                        auto_pl_feed.append(cur_auto_pl_id)
                        for cur_d3_d4_dict in dim_dict:
                            if max_col < len(cur_d3_d4_dict['d1']):
                                max_col = len(cur_d3_d4_dict['d1'])
                return price_matrix_xls({'input_type':'stored_genre', 'auto_pl_id_list':[auto_pl_feed], 'max_cols':max_col})
    return(render(request, 'journal_mgmt/test_response.html', {'data': data}))




























