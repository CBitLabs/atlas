from atlas_base import AtlasBase
from atlas_helper_methods import AtlasHelper
from cloudability import Cloudability
from collections import defaultdict, OrderedDict
from aws_module import AwsModule
from aws_helper import AwsHelper

class CloudabilityModule(AtlasBase):

    def __init__(self, request=None,environment=None):

        self.module = "cloudability_module"
        self.ah_obj = AtlasHelper()
        self.cloud_obj = Cloudability()
        self.awshelper_obj = AwsHelper()
        self.request = request
        self.aws_object = AwsModule(request, environment)
        self.instance_cost = 0.0
        self.storage_cost = 0.0

    def get_information(self, environment=None, **kwargs):
        organization_list = self.awshelper_obj.get_organizations()
        if environment is None:
            if 'env_cost_dict' in kwargs:
                if kwargs['env_cost_dict'] == 'true':
                    for organization in organization_list:
                        env_cost_dict= self.cloud_obj.get_cloudability_costs()['environment_costs'][organization]
                        env_cost_dict['all'] = self.get_information(ec2_cost_dict='true')['region_zone']
                        return env_cost_dict
            if 'ec2_cost_dict' in kwargs:
                if kwargs['ec2_cost_dict'] == 'true':
                    for organization in organization_list:
                        ec2_costs= self.cloud_obj.get_cloudability_costs()['ec2_costs'][organization]
                        return ec2_costs
        else:
            if 'env_cost_dict' in kwargs:
                if kwargs['env_cost_dict'] == 'true':
                    env_costs = 0
                    for organization in organization_list:
                        env_cost_dict = self.cloud_obj.get_cloudability_costs()['environment_costs'][organization]
                        environment_groups = self.ah_obj.get_atlas_config_data("global_config_data", "environment_groups")
                        if environment_groups and environment in environment_groups[1].keys():
                            if environment == 'all':
                                env_group_for_environment = self.awshelper_obj.get_environments(organization)
                            else:
                                 env_group_for_environment = environment_groups[1][environment]
                            for env in env_group_for_environment:
                                env_costs+=env_cost_dict[env] 
                            env_cost_dict[environment] = env_costs
                return env_cost_dict
                            
            if 'apps_in_environment' in kwargs:
                if kwargs['apps_in_environment'] == 'true':
                    return self.aws_object.get_information(environment, apps_in_environment='true')
            if 'instance_data' in kwargs:
                if kwargs['instance_data'] == 'true':
                    return self.aws_object.get_information(environment, instance_data='true')
            if 'instances_cost_dict' in kwargs:
                if kwargs['instances_cost_dict'] == 'true':
                    for organization in organization_list:
                        return self.cloud_obj.get_cloudability_costs()['instances_costs'][organization]
            if 'ebs_cost_dict' in kwargs:
                if kwargs['ebs_cost_dict'] == 'true':
                    for organization in organization_list:
                        return self.cloud_obj.get_cloudability_costs()['ebs_costs'][organization]
            if 'aws_info_dict' in kwargs:
                if kwargs['aws_info_dict'] == 'true':
                    return self.aws_object.get_information(environment, 'aws_info_dict')  
            if 'application_subnets' in kwargs:
                if kwargs['application_subnets'] == 'true': 
                    return self.aws_object.get_information(environment, 'application_subnets')  

    def get_configuration_data(self, key):
        value = self.ah_obj.get_atlas_config_data(self.module, key)
        if isinstance(value, dict):
            return value[0]
        else:
            return value

    def get_stack_attributes(self, environment=None):
        """
        Get stack attributes from config file.
        """
        stack_attribute_list = []
        stack_attributes_dict = self.ah_obj.get_atlas_config_data('cloudability_module', 'stack_attributes')[1]
        for attribute, details in stack_attributes_dict.iteritems():
            stack_attribute_list.append((attribute, details['editable']))
        return(stack_attribute_list, stack_attributes_dict)    
            
    def get_attribute_values(self, environment=None):
        return self.__get_detailed_instances_cost_dict(environment, 'stack_costs')
            

    def get_status(self,environment=None):
        status_information = self.get_configuration_data('status')
        cloud_status_dict = {}
        organization_list = self.awshelper_obj.get_organizations()
        environment_list = []
        if environment==None:
            env_cost_dict = self.get_information(env_cost_dict='true')
            cloud_status_dict = {environment: ["$"+str(env_cost_dict[environment])] for environment in env_cost_dict.keys()}
        else:
            env_cost_dict = self.get_information(environment, env_cost_dict='true')
            region_vpc_selection = self.aws_object.get_information(environment, region_vpc_dict='true')
            if environment == "uncategorized":
                region_list = self.awshelper_obj.get_regions()
                for region in region_vpc_selection:
                    if region =='east':
                        cloud_status_dict[region] = ["$"+str(env_cost_dict[environment])]
                    else:
                         cloud_status_dict[region] = ["$"+ "0.0"]
            else:
                for vpc in ['ame1']:   #should be changed later to include all vpcs.
                    cloud_status_dict[vpc] = ["$"+str(env_cost_dict[environment])]
        return (status_information, cloud_status_dict)


    def get_tabs(self, environment=None):
       pass

    def get_instance_actions(self, environment=None):
         pass

    def get_environment_actions(self, environment=None):
        pass

    def get_instance_group_actions(self, environment=None):
        pass

    def get_stack_actions(self, environment=None):
        pass

    def get_vpc_actions(self):
        pass

    def get_action_status(self, json_data, environment=None):
        pass

    def perform_instance_actions(self, environment=None):
        pass


    def perform_instancegroup_actions():
        pass


    def perform_stack_actions():
        pass


    def perform_vpc_actions(self, json_data):
        pass


    def perform_environment_actions(self, environment=None):
        pass


    def get_columns(self, environment=None):
        column_list = self.ah_obj.get_atlas_config_data(self.module, 'columns')
        column_dict= self.ah_obj.create_nested_defaultdict()
        if column_list:
            column_dict = self.__get_detailed_instances_cost_dict(environment, 'instances_cost')
        return (column_list, self.ah_obj.defaultdict_to_dict(column_dict))
        

    def get_action_parameters(self, action_type, environment=None):
        pass

    def load_session(self, request, environment=None):
        pass

    def save_session(self, request, environment=None):
        pass


    def get_defaults():
        pass

    def get_aggregates(self, environment=None):
        aggregates = self.ah_obj.get_atlas_config_data(self.module, 'aggregates')
        if environment is None:
            aggregate_list = ["$"+str(self.get_information(ec2_cost_dict='true')['region_zone'])]
            return (aggregates, aggregate_list)
        else:
            aggregate_dict = collections.defaultdict(dict)
            for agg_key in aggregates:
                if agg_key == 'cost':
                    aggregate_dict[agg_key] = self.get_information(env_cost_dict='true')[environment]
            return dict(aggregate_dict)

    def refresh_information(self, environment=None):
        self.cloud_obj.cache_cloud_costs()
        return

    def __get_detailed_instances_cost_dict(self, environment, cost_type):
        instances_cost_dict = self.get_information(environment, instances_cost_dict = 'true')
        ebs_cost_dict = self.get_information(environment, ebs_cost_dict = 'true')
        aws_tabs_dict = self.aws_object.get_tabs(environment)[1]
        instance_information = self.aws_object.get_information(environment, instance_data='true')
        organization_list = self.awshelper_obj.get_organizations()
        (stack_attr_list, stack_attr_details) = self.get_configuration_data('stack_attributes')
        apps_in_environment = self.get_information(environment, apps_in_environment='true')
        application_subnets = self.get_information(environment, application_subnets='true')
        region, vpc, subnet = "", "", ""
        instance_cost_column_dict= self.ah_obj.create_nested_defaultdict()
        ebs_cost_column_dict = self.ah_obj.create_nested_defaultdict()
        stack_cost_dict= self.ah_obj.create_nested_defaultdict()
        stack_cost_string_dict  = self.ah_obj.create_nested_defaultdict()
        name_tag_value, fqdn_tag_value = "", ""
        for instance, aws_tabs_dict in aws_tabs_dict.iteritems():
            attribute_cost={}
            if 'Name' in aws_tabs_dict['aws_tags']: name_tag_value = aws_tabs_dict['aws_tags']["Name"] 
            if 'fqdn' in aws_tabs_dict['aws_tags']: fqdn_tag_value = aws_tabs_dict['aws_tags']['fqdn'] 
            instance_details = self.ah_obj.get_nested_attribute_values(instance_information, instance)[1]
            region = instance_details['region'] if "region" in instance_details else "none"
            subnet = instance_details['subnet'] if "subnet" in instance_details else "none"
            attribute_cost[subnet] = {}
            vpc = instance_details['vpc'] if "vpc" in instance_details else "none"
            attribute_cost[vpc] = {}
            attribute_cost[vpc][subnet] = {}
            stack = instance_details['application'] if "application" in instance_details else "none"
            if cost_type == 'instances_cost' or cost_type == 'stack_costs':
                if fqdn_tag_value in ebs_cost_dict:
                    self.storage_cost = ebs_cost_dict[fqdn_tag_value]
                    if environment == "uncategorized":
                       
                        instance_cost_column_dict[region]['subnets']['none']['instance_attributes'][instance]['storage_cost'] = "$" +str(ebs_cost_dict[fqdn_tag_value])+"/m"
                    else:
                        instance_cost_column_dict[vpc]['subnets'][subnet]['instance_attributes'][instance]['storage_cost'] = "$" +str(ebs_cost_dict[fqdn_tag_value])+"/m"
                else:
                    self.storage_cost = 0.0
                    if environment == "uncategorized":
                        instance_cost_column_dict[region]['subnets']['none']['instance_attributes'][instance]['storage_cost'] = "$" + "0.0"+"/m"
                    else:
                        instance_cost_column_dict[vpc]['subnets'][subnet]['instance_attributes'][instance]['storage_cost'] = "$" + "0.0"+"/m"

                if fqdn_tag_value in instances_cost_dict: 
                    if environment == "uncategorized":
                        instance_cost_column_dict[region]['subnets']['none']['instance_attributes'][instance]['instance_cost'] = "$" + str(instances_cost_dict[fqdn_tag_value])+"/m"
                    else:
                        self.instance_cost = instances_cost_dict[fqdn_tag_value]
                        instance_cost_column_dict[vpc]['subnets'][subnet]['instance_attributes'][instance]['instance_cost'] = "$" + str(instances_cost_dict[fqdn_tag_value])+"/m"    
                elif name_tag_value in instances_cost_dict:
                    self.instance_cost = instances_cost_dict[name_tag_value]
                    if environment == "uncategorized":
                        instance_cost_column_dict[region]['subnets']['none']['instance_attributes'][instance]['instance_cost'] = "$" + str(instances_cost_dict[name_tag_value]) +"/m"
                    else:
                        self.instance_cost = instances_cost_dict[fqdn_tag_value]
                        instance_cost_column_dict[vpc]['subnets'][subnet]['instance_attributes'][instance]['instance_cost'] = "$" + str(instances_cost_dict[name_tag_value]) +"/m"
                else:
                    if environment=="uncategorized":
                        instance_cost_column_dict[region]['subnets']['none']['instance_attributes'][instance]['instance_cost'] = "(empty)"
                    else:
                        self.instance_cost = 0.0
                        instance_cost_column_dict[vpc]['subnets'][subnet]['instance_attributes'][instance]['instance_cost'] = "(empty)"
                      
                if cost_type == 'stack_costs':
                    attr_cost = 0.0
                    for attribute in stack_attr_list:
                        if attribute == 'instance_cost':
                            attr_cost = self.instance_cost
                        elif attribute == 'storage_cost':
                            attr_cost = self.storage_cost
                        elif attribute == 'total_cost':
                            attr_cost = self.instance_cost + self.storage_cost
                        if stack_attr_details[attribute]['stack'] == ['all']:
                            for apps in apps_in_environment:
                                if stack == apps:
                                    if not stack_cost_dict[region][vpc][subnet][stack][attribute]:
                                        stack_cost_dict[region][vpc][subnet][stack][attribute] = attr_cost
                                    else:
                                        cost = stack_cost_dict[region][vpc][subnet][stack][attribute]
                                        stack_cost_dict[region][vpc][subnet][stack][attribute]+=attr_cost
                        else:
                            for attr_stack in stack_attr_details[attribute]['stack']:
                                if attr_stack == stack:
                                    if not stack_cost_dict[region][vpc][subnet][stack][attribute]:
                                        stack_cost_dict[region][vpc][subnet][stack][attribute] = attr_cost
                                    else:
                                        stack_cost_dict[region][vpc][subnet][stack][attribute]+=attr_cost 
                        stack_cost_string_dict[region][vpc][subnet][stack][attribute] = \
                            "$"+str(stack_cost_dict[region][vpc][subnet][stack][attribute])+"/m"
    
        if cost_type == 'stack_costs': return self.ah_obj.defaultdict_to_dict(stack_cost_string_dict)
        if cost_type == 'instances_cost' : return self.ah_obj.defaultdict_to_dict(instance_cost_column_dict)

