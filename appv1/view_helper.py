import os
import ast
import json
from json import dumps
from datetime import date, datetime, timedelta
import collections
from collections import OrderedDict, defaultdict
from django.http import HttpResponse, HttpResponseRedirect, response
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from appv1.models import UserProfile
from session_handler import SessionHandler
from cloudability import Cloudability
from chef_helper import ChefHelper
from atlas_helper_methods import AtlasHelper
from object_helper import ObjectHelper
from aws_helper import AwsHelper
from database_helper import DatabaseHelper
from aws_module import AwsModule
from chef_module import ChefModule



class ViewsHelper():

    def __init__(self):
        self.awshelper_obj = AwsHelper()
        self.session_obj = SessionHandler()
        self.objhelper_obj = ObjectHelper()
        self.ah_obj = AtlasHelper()
        self.awshelper_obj = AwsHelper()


    def context_for_custom_processor(self, request):
        """
        Help context processor.
        """
        if request.user.username:
            up = UserProfile.objects.get(user__username=request.user.username)
        region_vpc_dict = {}
        region_list = self.awshelper_obj.get_regions()
        vpc_list = []
        for region in region_list:
            vpc_list = self.awshelper_obj.get_vpc_in_region(region)
            if vpc_list: region_vpc_dict[region] = vpc_list
            else: region_vpc_dict[region] = []

        user_region_vpc_dict = self.session_obj.load_region_session(request)
        user_region_list = []
        user_vpc_list = []
        if not user_region_vpc_dict:
            user_region_vpc_dict = region_vpc_dict

        for key, values in user_region_vpc_dict.iteritems():
            user_region_list.append(key)
            if values: 
                for index in values: user_vpc_list.append(index)

        dash_environments = self.awshelper_obj.get_dash_environments()
        if request.is_secure():
            url_scheme = 'https://'
        else:
            url_scheme = 'http://'

        return{
             'region_vpc_dict': json.dumps(region_vpc_dict),
             'user_region_list' : user_region_list,
             'user_vpc_list' : user_vpc_list,
             'default_regions' :region_list,
             'default_vpc': vpc_list,
             'dash_environments' : dash_environments,
             'user_region_vpc_dict': user_region_vpc_dict,
             'default_region_vpc_dict' : region_vpc_dict,
             'home_url': url_scheme + request.get_host(),
        }

    def create_module_list(self):
        """
        Get the list of modules. It is required for the dashboard do not delete it.
        """
        module_list = ['aws_module'] #initialize default module
        other_modules = self.ah_obj.get_atlas_config_data("global_config_data", 'modules')[0]
        other_modules.remove('aws_module')
        module_list.extend(other_modules)
        return module_list

    def refresh_environment_information(self,request):
        module_list = self.create_module_list()
        for module in module_list:
            module_object = self.objhelper_obj.get_module_object(module, request)
            module_object.refresh_information()

    def handle_dashboard_post_requests(self, request):
        """
        Handle ajax post requests and send the status.
        """
        if (int(request.POST.get('refresh_atlas_data', 0)) == 1) and (request.POST.get('refresh_flag') == "refresh"):
            self.refresh_environment_information(request)
            return HttpResponse(status=202)

        if int(request.POST.get('session_var_save', 0)) == 1:
            module_object = self.objhelper_obj.get_module_object(request.POST.get('module'), request)
            module_object.save_session(request)
            return HttpResponse(status=202)

        if request.POST.get('module'):
            module = request.POST.get('module')
            module_obj = self.objhelper_obj.get_module_object(module,request);
            if module_obj:
                module_obj.save_session(environment=None, request=request)
                return HttpResponse(status=202)


    def get_dashboard_status(self, module_object, request):
        status_list, status_dict =[], {}
        status_icon_list, icon_position_list = [], []
        module_status_list, module_style_dict = [] , {}
        status = module_object.get_status()
        if isinstance(status, tuple) and status is not None:
            if status[0] and status[1]:
                status_dict = status[1]
                module_status_info = status[0]
                module_style_dict = module_status_info[1]
                status_icon_list, icon_position_list = [], []
                if module_style_dict:
                    for status_key, style_dict in module_style_dict.iteritems():
                        status_list.append(status_key)
                        for key in style_dict.keys():
                            if key == "icon_file": status_icon_list.append(style_dict[key])
                            if key == "position": icon_position_list.append(style_dict[key])
        return [status_list, status_icon_list, icon_position_list, status_dict]
       
    def load_dashboard_session(self, module_object, request):
        module_session_dict = module_object.load_session(request)
        if module_session_dict is not None:
            for sessions, session_dict in module_session_dict.iteritems():
                for session_key, session_value in session_dict.iteritems():
                    request.session[session_key] = session_value

    def get_dashboard_aggregates(self, module_object, request):
        """
        Get all aggregate vales for dashboard display.
        """
        aggregates = module_object.get_aggregates()
        if isinstance(aggregates, tuple):
            return aggregates


    def dashboard_data_for_module(self, request, module, dash_environments):
        module_object = self.objhelper_obj.get_module_object(module, request)
        #load dashboard session variables
        self.load_dashboard_session(module_object, request)
        #get dashboard aggregates   
        dashboard_aggregates = self.get_dashboard_aggregates(module_object, request)
        #get dashboard status
        mod_status = self.get_dashboard_status(module_object, request)

        return (dashboard_aggregates, mod_status)


    def generate_dashboard_data(self, request):
        """
        Generate required data for each module for dashboard display.
        """ 
        #modules list
        module_list = self.create_module_list()
        #environment list
        dash_environments = self.awshelper_obj.get_dash_environments()

        #inititalize variables
        status_info_dict = collections.defaultdict(list)
        module_status_list = []
        aggregate_list, aggregate_values_list = [], []

        for module in module_list:
             with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future = executor.submit(self.dashboard_data_for_module, request, module, dash_environments)
                (dashboard_aggregates, mod_status) = future.result()
                
                module_status_list.extend(mod_status[0])
                for env in dash_environments:
                    if env in mod_status[3]:
                        status_info_dict[env].extend(zip(mod_status[0], mod_status[1], mod_status[2], mod_status[3][env]))

                if dashboard_aggregates is not None:
                    aggregate_list.extend(dashboard_aggregates[0])
                    aggregate_values_list.extend(dashboard_aggregates[1])
        return {
        'dash_statuses' : module_status_list,
        'dash_status_info' : self.ah_obj.defaultdict_to_dict(status_info_dict),
        'aggregate_values' : zip(aggregate_list, aggregate_values_list),
        'selected_dash_status': None if not request.session.has_key('config_selected') else request.session['config_selected'],
        'selected_dash_env': None if not request.session.has_key('env_selected') else request.session['env_selected'],
        }


    def save_environment_session_data(self, request, environment):
        """
        Save session data for user related to environment.
        """
        module_object = self.objhelper_obj.get_module_object(request.POST.get('module'), request, environment)
        module_object.save_session(request, environment)

    def perform_environment_actions(self, request, environment):
        """
        Perform instance, instance_group, stack or vpc actions.
        """
        actions_json = ast.literal_eval(request.POST.get('actions_data', "{}"))
        actions_json['user'] = request.user.username
        module = actions_json["module"]
        module_object = self.objhelper_obj.get_module_object(module, request, environment)
        actions_json['username'] = request.user.username
        actions_json['environment'] = environment
        if actions_json["action_type"] == "instance_action":
            if 'edit_flag' in actions_json and int(actions_json['edit_flag']) == 1:
                actions_status = module_object.perform_instance_actions(actions_json)
                return actions_status
            instance_actions = module_object.get_instance_actions()
            if instance_actions:
                if actions_json["action"] in instance_actions:
                    actions_status = module_object.perform_instance_actions(actions_json)
                    return actions_status
        elif actions_json["action_type"] == "instance_group_action":
            if 'edit_flag' in actions_json and int(actions_json['edit_flag']) == 1:
                actions_status = module_object.perform_instance_actions(actions_json)
                return actions_status
            group_actions = module_object.get_instance_group_actions()
            if group_actions:
                if actions_json["action"] in group_actions:
                    actions_status = module_object.perform_instancegroup_actions(actions_json, environment)
                    return actions_status
        elif actions_json["action_type"] == "vpc_action":
            vpc_actions = module_object.get_vpc_actions()
            if vpc_actions:
                if actions_json["action"] in vpc_actions:
                    actions_status = module_object.perform_vpc_actions(actions_json, environment)
                    return actions_status
        elif actions_json["action_type"] == "stack_action":
            stack_actions = module_object.get_stack_actions()
            if stack_actions:
                if actions_json["action"] in stack_actions:
                    actions_status = module_object.perform_stack_actions(actions_json, environment)
                    return actions_status


    def check_environment_action_status(self, request, environment):
        """
        Check the status of actions performed if they have completed or in progress.
        """
         
        actions_json = ast.literal_eval(request.POST.get('actions_data', "{}"))
        action_type = actions_json['action_type']
        module = actions_json["module"]
        module_object = self.objhelper_obj.get_module_object(module, request, environment)
        if action_type == 'instance_action':
            if actions_json["action"] in module_object.get_instance_actions():
                actions_status = module_object.get_instance_status(actions_json, environment)
                return actions_status

        if action_type == 'instance_group_action':
            if actions_json["action"] in module_object.get_instance_group_actions():
                actions_status = module_object.get_instancegroup_status(actions_json, environment)
                return actions_status

        if action_type == 'vpc_action':
            if actions_json["action"] in module_object.get_vpc_actions():
                actions_status = module_object.get_action_status(actions_json, environment)
                return actions_status
        if action_type == 'stack_action':

            if actions_json["action"] in module_object.get_stack_actions():
                actions_status = module_object.get_action_status(actions_json, environment)
                return actions_status



    def load_env_session_variables(self, request, environment, module_object):
        """
        Load session variables for each module.
        """
        module_session_dict = module_object.load_session(request,environment)
        if module_session_dict is not None:
            for sessions, session_dict in module_session_dict.iteritems():
                for session_key, session_value in session_dict.iteritems():
                    request.session[session_key] = session_value

    def get_tabsinfo_for_environment(self, request, environment, module_object):
        """
        Get a list of tabs and information for each tab.
        """
        tabs_list, tabs_info_list, instances_list = [], [], []
        tab_details = module_object.get_tabs(environment)
        if tab_details:
            tabs_list = tab_details[0]
            if tab_details[1]:
                tab_details_dict = {}
                if module_object.__class__ is AwsModule:
                    tabs_info_list = tab_details[1]
                    instances_list = tab_details[1].keys()
                else:
                    for instances in instances_list:
                        if tab_details[1].has_key(instances):
                            tab_details_dict[key] = tab_details[1][key]
                    if collections.Counter(tab_details_dict.keys()) == collections.Counter(instances_list):
                        tabs_info_list = tab_details[1]
        return (tabs_list, tabs_info_list)


    def get_column_data_for_environment(self, request, environment, module_object):
        """
        Get columns and data for columns for each environment.
        """
        return module_object.get_columns(environment)
    

    def get_aggregates_value_for_environment(self, request, environment, module_object):
        """
        Get aggregates value for environment.
        """
        aggregates_zip=[]
        aggregates_dict = module_object.get_aggregates(environment)
        if aggregates_dict:
            return(zip(aggregates_dict.keys(), aggregates_dict.values()))
      


    def get_statusinfo_for_environment(self, request, environment, module_object):
        """
        Get status value for each environment.
        """
        module_status_list = []
        status_details_dict=collections.defaultdict(list)
        module_status = module_object.get_status(environment)
        if module_status:
            if module_status[0] and module_status[1]:
                module_status_info = module_status[0]
                module_status_list = module_status_info[0]
                module_style_dict = module_status_info[1]
                status_icon_list, icon_position_list = [], []
                if module_style_dict:
                    for status_key, style_dict in module_style_dict.iteritems():
                        for key in style_dict.keys():
                            if key == "icon_file": status_icon_list.append(style_dict[key])
                            if key == "position": icon_position_list.append(style_dict[key]) 
                for key in module_status[1]: #change this
                    status_details_dict[key] = zip(module_status_list, status_icon_list, icon_position_list, module_status[1][key])
        return (module_status_list, status_details_dict)

    def get_stackattributes_for_environment(self, request, environment, module_object):
        """
        Get stack attributes and corresponding values for each attribute.
        """
        stack_attributes_list, stack_attributes_dict, attribute_values_dict =[], {}, {}
        stack_attributes = module_object.get_stack_attributes(environment)
        attributes = []
        if stack_attributes:
           stack_attributes_list = stack_attributes[0]
           stack_attributes_dict = stack_attributes[1]       
        attribute_values = module_object.get_attribute_values(environment)
        if attribute_values is not None:
            attribute_values_dict = attribute_values
        return (stack_attributes_list, stack_attributes_dict, attribute_values_dict)

    def get_instance_action_data(self, request, environment, module_object):
        """
        Get a list of instance actions for each module.
        """
        return module_object.get_instance_actions()
       

    def get_instance_group_action_data(self, request, environment, module_object):
        """
        Get instance group action data.
        """
        return module_object.get_instance_group_actions()

    def get_stack_action_data(self, request, environment, module_object):
        """
        Get a list of stack action and stack action parameters.
        """
        stack_actions, stack_action_parameters = [], {}
        if module_object.__class__ != ChefModule:
            s_actions_list = module_object.get_stack_actions()
            if s_actions_list is not None:
                stack_actions.extend(s_actions_list)
                action_parameters = module_object.get_action_parameters(action_type="stack_actions", environment=environment)
                if action_parameters:
                    for key, values in action_parameters.iteritems():
                        stack_action_parameters[key] = values
        return (stack_actions, stack_action_parameters)
        
    def get_vpc_action_data(self, request, environment, module_object):  
        """
        Get a list of vpc actions and parameters.
        """
        vpc_actions, vpc_action_parameters = [], {}  
        vpc_actions_list = module_object.get_vpc_actions()
        if vpc_actions_list:
            vpc_actions.extend(vpc_actions_list)
            action_parameters = module_object.get_action_parameters(action_type="vpc_actions", environment=environment)
            if action_parameters:
                for key, values in action_parameters.iteritems():
                    vpc_action_parameters[key] = values
        return (vpc_actions, vpc_action_parameters)


    def environment_data_for_module(self, request, environment, module):
        module_object = self.objhelper_obj.get_module_object(module, request, environment);
        module_details_dict = {}
        if module_object:
            self.load_env_session_variables(request, environment, module_object)
            module_details_dict['module_aggregates'] = self.get_aggregates_value_for_environment(request, environment, module_object)
            module_details_dict['module_status'] = self.get_statusinfo_for_environment(request, environment, module_object)
            module_details_dict['module_tabs'] = self.get_tabsinfo_for_environment(request, environment, module_object)
            module_details_dict['module_columns'] = self.get_column_data_for_environment(request, environment, module_object)
            module_details_dict['module_stack_attributes'] = self.get_stackattributes_for_environment(request, environment, module_object)
            module_details_dict['module_inst_actions'] = self.get_instance_action_data(request, environment, module_object)
            module_details_dict['module_group_actions'] = self.get_instance_group_action_data(request, environment, module_object)
            module_details_dict['module_stack_actions'] = self.get_stack_action_data(request, environment, module_object)
            module_details_dict['module_vpc_actions'] = self.get_vpc_action_data(request, environment, module_object)
        return module_details_dict

    def generate_environment_data(self, request, environment):
        """
        Generate data to be displayed for each environment.
        """
        aggregates_zip = []
        status_list, status_values_dict= [], collections.defaultdict(list)
        column_list, column_data_dict = [], {}
        instance_actions, stack_actions, vpc_actions, group_actions = [], [], [], []
        module_actions_dict = {}
        vpc_action_parameters, stack_action_parameters= {}, {}
        tabs_list, tabs_info_list = [], []
        selected_apps, selected_subnets = [], []
        stack_attributes_list, stack_attributes_dict = [], {}
        attribute_values_dict = {}

        module_list = self.create_module_list()
        for module in module_list: 
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future = executor.submit(self.environment_data_for_module, request, environment,module)
                module_details_dict = future.result()
                
                module_aggregates =  module_details_dict['module_aggregates']
                if module_aggregates is not None: aggregates_zip.extend(module_aggregates)

                (module_status_list, status_details_dict) = module_details_dict['module_status']
                status_list.append(module_status_list)
                for vpc in status_details_dict:
                    if vpc in status_details_dict:
                        status_values_dict[vpc].extend(status_details_dict[vpc])

                (module_tabs_list, module_tabs_info_list) = module_details_dict['module_tabs']
                tabs_list.append(module_tabs_list)
                tabs_info_list.append(module_tabs_info_list)

                column_data =  module_details_dict['module_columns']
                if column_data is not None and column_data[0] is not None:
                    column_list.extend(column_data[0])
                    if column_data[1] is not None: 
                        generator_object = self.ah_obj.merge_dictionaries(column_data_dict, column_data[1])
                        column_data_dict = {key:value for key, value in generator_object}

                (stack_attr_list, stack_attributes, attribute_values) = module_details_dict['module_stack_attributes']
                if stack_attr_list is not None: stack_attributes_list.extend(stack_attr_list)
                if stack_attributes_dict is None:
                    stack_attributes_dict.update(stack_attributes)
                else:
                    generator_object = self.ah_obj.merge_dictionaries(stack_attributes_dict, stack_attributes)
                    stack_attributes_dict = {key:value for key, value in generator_object}
                if attribute_values_dict is None:
                    attribute_values_dict.update(attribute_values)
                else:
                    generator_object = self.ah_obj.merge_dictionaries(attribute_values_dict, attribute_values)
                    attribute_values_dict = {key:value for key, value in generator_object}


                module_actions_dict[module] = {}
                inst_actions_list =  module_details_dict['module_inst_actions']
                if inst_actions_list is not None: 
                    instance_actions.extend(inst_actions_list)
                    module_actions_dict[module]['instance_actions'] = inst_actions_list 
                group_actions_list = module_details_dict['module_group_actions']
                if group_actions_list is not None: 
                    group_actions.extend(group_actions_list)
                    module_actions_dict[module]['instance_group_actions'] = group_actions_list
                (stack_actions_list, stack_action_parameters) =  module_details_dict['module_stack_actions']
                stack_actions.extend(stack_actions_list)
                (vpc_actions_list, vpc_action_parameters) = module_details_dict['module_vpc_actions'] 
                vpc_actions.extend(vpc_actions_list)
                module_actions_dict[module]['stack_actions'] = stack_actions_list
                module_actions_dict[module]['vpc_actions'] = vpc_actions_list    
 
        return  {
            'environment': environment,
            'aggregate_info_zip' : aggregates_zip,
            'status_values_dict': dict(status_values_dict),
            'status_list': status_list,
            'table_columns' : column_list,
            'column_data_dict' : column_data_dict,
            'tabs_list' : tabs_list,
            'tabs_list_string' : json.dumps(tabs_list),
            'tabs_info_string': json.dumps(tabs_info_list),
            'instance_actions' : json.dumps(instance_actions),
            'stack_actions' : json.dumps(stack_actions),
            'group_actions' : json.dumps(group_actions),
            'vpc_actions' : vpc_actions,
            'vpc_action_parameters': json.dumps(vpc_action_parameters),
            'stack_action_parameters':json.dumps(stack_action_parameters),
            'module_actions_dict' : json.dumps(module_actions_dict),
            'stack_attributes_list': stack_attributes_list,
            'stack_attributes_dict': stack_attributes_dict,
            'attribute_values_dict' : dict(attribute_values_dict),
            'attribute_values_string': json.dumps(attribute_values_dict)
        }
               
                
   