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
import re

def get_site_path():
    site_path = 'D:/featherlite_erp/'
    return(site_path)





