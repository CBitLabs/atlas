import os
import json
from datetime import date, datetime, timedelta
import time
import collections
from collections import OrderedDict, defaultdict
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor


from django.shortcuts import render, redirect, render_to_response
from django.http import HttpResponse, HttpResponseRedirect, response
from django.template import loader, RequestContext, Context, TemplateDoesNotExist
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.decorators.cache import cache_page
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import never_cache

#import UserProfile to persis sessions
from appv1.models import UserProfile
from session_handler import SessionHandler
from cloudability import Cloudability
from chef_helper import ChefHelper
from atlas_helper_methods import AtlasHelper
from object_helper import ObjectHelper
from aws_helper import AwsHelper
from database_helper import DatabaseHelper
from atlas_helper_methods import AtlasHelper
from view_helper import ViewsHelper
from aws_module import AwsModule
from object_helper import ObjectHelper
from appv1.forms import LoginForm


def custom_processor(request):
    views_helperobj = ViewsHelper()
    return views_helperobj.context_for_custom_processor(request)
    
#atlas dashboard
@login_required
def atlas_dashboard(request):
    """Generate data for atlas dashboard."""
    if request.user.is_authenticated():
        try: 
            views_helperobj = ViewsHelper()
            objhelper_obj = ObjectHelper()

            if request.is_ajax() or request.method == 'POST':
                return views_helperobj.handle_dashboard_post_requests(request)
                
            module_list = views_helperobj.create_module_list()
            dashboard_context = views_helperobj.generate_dashboard_data(request)
            return render_to_response('appv1/dashboard.html', \
                                        dashboard_context, context_instance=RequestContext \
                                        (request, processors = [custom_processor]))
        except PermissionDenied:
            return render_to_response('appv1/403.html')
        except TemplateDoesNotExist:
            return render_to_response('appv1/404.html')
        except Exception:
            return render_to_response('appv1/500.html')


def login_error(request):
    """Display error message on invalid login."""
    template = loader.get_template('/registration/error.html')
    dashboard_context = RequestContext(request)
    return HttpResponse(template.render(dashboard_context))


@login_required
def atlas_applications(request, environment):
    """ Generate data for each environment."""
    if request.user.is_authenticated():   
        try:
            views_helperobj = ViewsHelper()
            objhelper_obj = ObjectHelper()
            module_list = views_helperobj.create_module_list()
            environment_context = {}

            if request.is_ajax() and (request.method == 'POST' and (int(request.POST.get('refresh_atlas_data', 0)) != 1)):
                   
                if int(request.POST.get('session_var_save', 0)) == 1:
                    views_helperobj.save_environment_session_data(request, environment)
                    return HttpResponse(status=202)
                    
                actions_flag = int(request.POST.get('actions_flag', 0))
                if actions_flag == 1:
                    actions_status = views_helperobj.perform_environment_actions(request, environment)
                    return HttpResponse(json.dumps(actions_status))
                
                status_flag = int(request.POST.get('status_flag', 0))
                if status_flag == 1:
                    actions_status = views_helperobj.check_environment_action_status(request, environment)
                    return HttpResponse(json.dumps(actions_status))

            else:
                if request.is_ajax() and (request.method == 'POST' and (int(request.POST.get('refresh_atlas_data', 0)) == 1)):
                    views_helperobj.refresh_environment_information(request)
        

                if environment=="" or environment == 'accounts_login':
                    pass
                else:
                    home_url = os.environ.get("APPLICATION_URL")
                    app_url = home_url+"environment/"+environment+"/"
                    request.session['url'] = app_url


                    #this is the information from aws module required to build the console.
                    #please do not remove this
                    awsmodule_obj = objhelper_obj.get_module_object("aws_module", request, environment)
                    apps_in_environment = awsmodule_obj.get_information(environment, apps_in_environment='true')
                    user_apps_subnets = awsmodule_obj.get_information(environment, request, user_selections='true', application_url=app_url)
                    env_info_list = awsmodule_obj.get_information(environment, env_subnet_list='true')
                    aws_info_dict = awsmodule_obj.get_information(environment, aws_info_dict='true')
                    stack_list = awsmodule_obj.get_information(environment, stack='true')
                    profile_list = awsmodule_obj.get_information(environment, profiles='true')
                    environment_subnets = awsmodule_obj.get_information(environment, environment_subnets='true')
                    vpc_attributes_dict = awsmodule_obj.get_information(environment, vpc_attributes='true')
                    application_subnets = awsmodule_obj.get_information(environment, application_subnets='true')
                    subnet_with_instances = awsmodule_obj.get_information(environment, subnets_with_instances='true')
                    region_vpc_selection = awsmodule_obj.get_information(environment, region_vpc_dict='true')
                    environment_context = views_helperobj.generate_environment_data(request, environment)
                   
                    environment_context.update({
                    'env_subnets_string' : json.dumps(env_info_list),
                    'vpc_attributes': vpc_attributes_dict,
                    'application_subnets': application_subnets,
                    'not_present_subnet' : subnet_with_instances,
                    'not_present_subnet_string': json.dumps(subnet_with_instances),
                    'environment_subnets_dict': json.dumps(environment_subnets),
                    'aws_information_string' : json.dumps(aws_info_dict),
                    'applications' : apps_in_environment,
                    'subnets': env_info_list,
                    'applications_string' : json.dumps(apps_in_environment),
                    'env_subnets_list': env_info_list,
                    'selected_apps': None if environment == "uncategorized" or request.session['selected_applications'] =="" else request.session['selected_applications'],
                    'selected_subnets': None if environment == "uncategorized" or request.session['selected_subnets'] == "" else request.session['selected_subnets'],
                    'selected_status': None if request.session['selected_status']=="" else request.session['selected_status'],
                })

                return render_to_response('appv1/applications.html', \
                                            environment_context, context_instance=RequestContext \
                                            (request, processors = [custom_processor]))
        except TemplateDoesNotExist:
            raise Http404
        except PermissionDenied:
            return render_to_response('appv1/403.html')
        except Exception:
            return render_to_response('appv1/500.html')

