import boto, boto.ec2
from atlas_helper_methods import AtlasHelper
from aws_helper import AwsHelper
from atlas_base import AtlasBase
from session_handler import SessionHandler
import ast
from awsdetails import AwsInstanceHelper
from aws_actions import AwsActions
from chef_actions import ChefActions
import logging


class AwsModule(AtlasBase):
#class to fetch data from aws for atlas

    def __init__(self,request=None, environment=None):
        self.ah_obj = AtlasHelper()
        self.awshelper_obj = AwsHelper()
        self.instance_obj = AwsInstanceHelper()
        self.actions_obj = AwsActions()
        self.session_obj = SessionHandler()
        self.region_vpc_dict = self.session_obj.load_region_session(request)
        self.module = 'aws_module'
        if environment==None:
            self.information_dict = {'aggregates':{},'details':{}}
            self.aws_details_dict = self.instance_obj.get_aws_details(self.region_vpc_dict)
        else:
            self.information_dict = self.instance_obj.get_environment_details(environment, self.region_vpc_dict)

    def get_information(self, environment=None, request=None, **kwargs):
        if environment is None:
            if 'environments' in kwargs.keys():
                if kwargs['environments'] == 'true':
                    return self.aws_details_dict['environment_list']
            if 'status' in kwargs.keys():
                if kwargs['status'] == 'true':
                    return self.aws_details_dict['total_list']
            if 'aggregates' in kwargs.keys():
                if kwargs['aggregates'] == 'true':
                    return [self.aws_details_dict['total_count'], self.aws_details_dict['total_running'], self.aws_details_dict['total_stopped']]
        else:
            if 'aggregates' in kwargs.keys():
                if kwargs['aggregates']=='true':
                    return self.instance_obj.get_environment_aggregates(environment, self.region_vpc_dict)
            if 'status' in kwargs.keys():
                if kwargs['status']=='true':
                    return self.instance_obj.get_environment_status(environment, self.region_vpc_dict)
            if 'vpc_attributes' in kwargs.keys():
                if kwargs['vpc_attributes']=='true':
                    if 'vpc_attribute_dict' in self.information_dict:
                        return self.information_dict['vpc_attribute_dict']
            if 'profiles' in kwargs.keys():
                if kwargs['profiles'] == 'true':
                    return self.awshelper_obj.get_profiles()
            if 'user_selections' and 'application_url' in kwargs:
                if kwargs['user_selections'] == 'true':
                    return self.session_obj.load_env_session(request, environment)
            if 'environments' in kwargs:
                if kwargs['environment'] == 'true':
                    return self.awshelper_obj.get_dash_environments()
            if 'application_subnets' in kwargs:
                if kwargs['application_subnets'] == 'true':
                    if 'application_subnets' in self.information_dict:
                        return self.information_dict['application_subnets']
            if 'region_vpc_dict' in kwargs:
                if kwargs['region_vpc_dict'] == 'true':
                    return self.region_vpc_dict
            if 'env_subnet_list' in kwargs:
                if kwargs['env_subnet_list'] == 'true':
                    if 'env_subnet_list' in self.information_dict:
                        return self.information_dict['env_subnet_list']
            if 'environment_subnets' in kwargs:
                if kwargs['environment_subnets'] == 'true':
                    if 'environment_subnets' in self.information_dict:
                        return self.information_dict['environment_subnets']
            if 'apps_in_environment' in kwargs:
                if kwargs['apps_in_environment'] == 'true':
                    if 'apps_in_environment' in self.information_dict:
                        return self.information_dict['apps_in_environment']
            if 'aws_info_dict' in kwargs:
                if kwargs['aws_info_dict'] == 'true':
                    if 'aws_info_dict' in self.information_dict:
                        return self.information_dict['aws_info_dict']
            if 'subnets_with_instances' in kwargs:
                if kwargs['subnets_with_instances'] == 'true':
                    if 'subnets_with_instances' in self.information_dict:
                        return self.information_dict['subnets_with_instances']
            if 'region_vpc_dict' in kwargs:
                if kwargs['region_vpc_dict'] == 'true':
                    return self.region_vpc_dict
            if kwargs.has_key('instance_data'):
                if kwargs['instance_data'] == 'true':
                    return self.instance_obj.get_column_data(environment)

    def get_status(self, environment=None):
        status_information = self.get_configuration_data('status')
        vpc_status_dict = {}
        if environment==None:
            dash_environments = self.get_information(environments='true')
            env_status_list = self.get_information(status='true')
            for count in range(len(dash_environments)):
                vpc_status_dict[dash_environments[count]] = env_status_list[count][1:]
            return (status_information, vpc_status_dict)
        else:
            vpc_dict = self.get_information(environment, status='true')
            if environment== 'uncategorized':
                for region in vpc_dict.keys():
                    vpc_status_dict[region] = vpc_dict[region]['status']
            else:
                for vpc in vpc_dict.keys():
                    vpc_status_dict[vpc] = vpc_dict[vpc]['status']
            return (status_information, vpc_status_dict)


    def get_tabs(self, environment=None):
        tabs_list = self.get_configuration_data('tabs')
        if environment == None:
            pass
        else:
            tabs_info_dict= self.get_information(environment, aws_info_dict='true')
            return (tabs_list, tabs_info_dict)

    def get_instance_actions(self, environment=None):
        instance_actions = self.get_configuration_data('instance_actions')
        if instance_actions:
            return instance_actions


    def get_instance_group_actions(self):
        return self.get_configuration_data('instance_group_actions')


    def get_stack_actions(self, environment=None):
        pass


    def get_vpc_actions(self):
       pass

    def get_environment_actions(self, environment=None):
        return self.get_configuration_data('environment_actions')

    def get_action_parameters(self, environment=None):
        pass

    def get_configuration_data(self, key):
        value = self.ah_obj.get_atlas_config_data(self.module, key)
        if isinstance(value, dict): return value[0]
        else: return value

    def perform_instance_actions(self,  instance_json, environment=None):
        action_status = self.actions_obj.instance_actions(instance_json, environment)
        #action_status['action_type'] = instance_json['action_type']
        return action_status


    def get_instance_status(self, instance_json, environment):
        action_status = self.actions_obj.instance_status(instance_json, environment)
        #action_status['action_type'] = instance_json['action_type']
        return action_status

    def get_instancegroup_status(self, instance_json, environment):
        action_status = self.get_instance_status(instance_json, environment)
        return action_status


    def perform_instancegroup_actions(self, instances_json, environment):

        initial_status = self.perform_instance_actions(instances_json)
        return initial_status

    def perform_stack_actions():
        pass


    def perform_vpc_actions(self, json_data):
        pass


    def perform_environment_actions(self, environment=None):
        return self.get_configuration_data('environment_actions')


    def get_columns(self, environment=None):
        columns = self.get_configuration_data('columns')
        column_dict = self.get_information(environment, instance_data='true')
        return (columns, column_dict)

    def load_session(self,request, environment=None):
        session_dict = {}
        if environment is None:
            session_dict['selected_status_envs'] = self.session_obj.load_dash_session(request)
        else:
            session_dict['selected_env_details'] = self.session_obj.load_env_session(request, environment)
        session_dict['selected_region_vpcs'] = self.session_obj.load_region_session(request)
        return session_dict

    def save_session(self, request, environment=None):
        try:
            var_type = request.POST.get("var_type")
            if var_type == 'region_vpc_selection':
                    self.session_obj.save_region_session(request, ast.literal_eval(request.POST.get('selected_region_vpcs')))
            if environment is None:
                if var_type == 'selected_status_env':
                    self.session_obj.save_dash_session(request, ast.literal_eval(request.POST.get('status_env_dict')))
            else:
                if var_type == 'selected_env_details':
                    self.session_obj.save_env_session(request, environment, ast.literal_eval(request.POST.get('status_env_dict')))
            return
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            ah.print_exception("awsmodules.py", "save_session()", exp_object, exc_type, exc_obj, exc_tb)
            return


    def get_aggregates(self, environment=None):

        aggregates = self.get_configuration_data('aggregates')
        if environment==None:
            aggregate_values = self.get_information(aggregates='true')
            return (aggregates, aggregate_values)
        else:
            aggregates_dict = {}
            self.get_information(environment, aggregates='true')
            agg_values = self.get_information(environment, aggregates='true')
            for index in range(0, len(aggregates)):
                aggregates_dict[aggregates[index]] = agg_values[index]
            return aggregates_dict

    """
    other functions specific to aws_module
    """

    def get_stack_attributes(self, environment=None):
        pass

    def get_attribute_values(self, environment=None):
        pass

    def refresh_information(self, environment=None):
        self.awshelper_obj.cache_aws_instances_information()
        return
