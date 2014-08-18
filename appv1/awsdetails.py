import boto, boto.ec2
import re, datetime
from dateutil import parser
from dateutil import tz
import collections
from collections import OrderedDict
import ast
from operator import add
from atlas_helper_methods import AtlasHelper
from aws_helper import AwsHelper

class AwsInstanceHelper:
#class to fetch data from aws for atlas

    def __init__(self, environment=None):
        """Initialize variables."""

        self.ah_obj = AtlasHelper()
        self.awshelper_obj = AwsHelper()
        self.module = 'aws_module'
        self.environment_dict = {}
        self.env_subnet_dict = {}
        self.env_details_dict = {}
        self.environment_groups = self.ah_obj.get_atlas_config_data("global_config_data", "environment_groups")


    def get_aws_details(self,regionvpcselected):
        organizations = self.awshelper_obj.get_organizations()
        aws_details_dict={}
        environment_list=[]
        aws_details = self.awshelper_obj.get_instances_details()
        for organization in organizations:
            environment_list = self.awshelper_obj.get_environments(organization)
            environment_list.append('uncategorized')
            environment_list.append('all')
            ah_obj = AtlasHelper()
            total_count, total_running, total_stopped=0, 0, 0
            region_dict = {}
            region_env_list=[]
            for environment in environment_list:
                if environment != 'all':
                    env_attributes = self.ah_obj.get_nested_attribute_values(aws_details, environment)[1]
                    for region in regionvpcselected.keys():
                        if 'regions' in env_attributes.keys() and region in env_attributes['regions'].keys():
                            region_keys, region_attributes = ah_obj.get_nested_attribute_values(env_attributes['regions'], region)
                            if 'count' in region_keys and 'running' in region_keys and 'stopped' in region_keys:
                                region_count =region_attributes['count']
                                region_running =region_attributes['running']
                                region_stopped =region_attributes['stopped']

                                if environment == "uncategorized":
                                    total_count+=region_count
                                    total_running+=region_running
                                    total_stopped+=region_stopped
                                    region_env_list.append([region, "none", environment, region_count, region_running, region_stopped])
                                else:
                                    vpc_list = regionvpcselected[region]
                                    for vpc in vpc_list:
                                        if 'vpc' in region_attributes.keys():
                                            vpc_attributes = self.ah_obj.get_nested_attribute_values(region_attributes['vpc'], vpc)[1]
                                            vpc_count = vpc_attributes['count']
                                            vpc_running = vpc_attributes['running']
                                            vpc_stopped = vpc_attributes['stopped']
                                            total_count+=vpc_count
                                            total_running+=vpc_running
                                            total_stopped+=vpc_stopped
                                    region_env_list.append([region, vpc, environment, vpc_count, vpc_running, vpc_stopped])
                else:
                    region_env_list.append([region, vpc, environment, total_count, total_running, total_stopped])

        temp_list, total_list = [], []
        for count in range(0, len(environment_list)):
            total_list.append([environment_list[count],0,0,0])

        for index in range(0, len(region_env_list)):
            for index1 in range(0, len(total_list)):
                if region_env_list[index][2] == total_list[index1][0]:
                    temp_list = [region_env_list[index][3], region_env_list[index][4], region_env_list[index][5]]
                    total_list[index1][1]+=temp_list[0]
                    total_list[index1][2]+=temp_list[1]
                    total_list[index1][3]+=temp_list[2]
        aws_details_dict['total_count'] = total_count
        aws_details_dict['total_running'] = total_running
        aws_details_dict['total_stopped'] = total_stopped
        aws_details_dict['environment_list'] = environment_list
        aws_details_dict['region_dict'] = region_dict
        aws_details_dict['total_list'] = total_list
        return aws_details_dict


    def calculate_environment_aggregates(self, environment, env_attributes, region_vpc_dict):
        """
        Calculate aggregate values for each environment.
        """
        total_list = [0,0,0]
        for region in region_vpc_dict.keys():
            if region in env_attributes['regions'].keys():
                region_attributes = env_attributes['regions'][region]
                if environment == 'uncategorized':
                    region_aggs = [region_attributes['count'],region_attributes['running'], region_attributes['stopped']]
                    total_list = map(add, total_list, region_aggs)
                else:
                    for vpc in region_vpc_dict[region]:
                        if vpc and vpc in region_attributes['vpc'].keys():
                            vpc_properties = self.ah_obj.get_nested_attribute_values(env_attributes['regions'][region], vpc)[1]
                            vpc_aggregates = [vpc_properties['count'], vpc_properties['running'], vpc_properties['stopped']]
                            total_list = map(add, total_list, vpc_aggregates)
        return total_list

    def get_environment_aggregates(self, environment, region_vpc_dict):
        """
        Get aggregate status values.
        """
        aggregate_list = [0,0,0]
        organizations = self.awshelper_obj.get_organizations()
        org_attributes = self.ah_obj.get_nested_attribute_values(self.awshelper_obj.get_instances_details(), 'organizations')[1]
        for organization in organizations:
            if self.environment_groups and environment in self.environment_groups[1].keys():
                if environment == 'all':
                    env_group_for_environment = self.awshelper_obj.get_environments(organization)
                else:
                    env_group_for_environment = self.environment_groups[1][environment]
                for env in env_group_for_environment:
                    env_attributes = self.ah_obj.get_nested_attribute_values(org_attributes[organization], env)[1]
                    env_agg_list = self.calculate_environment_aggregates(env, env_attributes, region_vpc_dict)
                    aggregate_list = map(add, aggregate_list, env_agg_list)
            else:
                env_attributes = self.ah_obj.get_nested_attribute_values(org_attributes[organization], environment)[1]
                aggregate_list = self.calculate_environment_aggregates(environment, env_attributes, region_vpc_dict)
        return aggregate_list


    def determine_environment_status(self, environment, env_attributes, region_vpc_dict):
        vpc_status_dict = {}
        for region in region_vpc_dict.keys():
            if region not in env_attributes['regions'].keys():
                continue
            else:
                region_attributes = env_attributes['regions'][region]
                vpc_status_dict[region] = {'status': []}
                if environment == 'uncategorized':
                    vpc_status_dict[region]['status'] = [region_attributes['count'], region_attributes['running'], region_attributes['stopped']]
                else:
                    for vpc in region_vpc_dict[region]:
                        if vpc and vpc in region_attributes['vpc'].keys():
                            vpc_status_dict[vpc] = {'status': []}
                            vpc_properties = self.ah_obj.get_nested_attribute_values(env_attributes['regions'][region], vpc)[1]
                            vpc_status_dict[vpc]['status'] = [vpc_properties['count'], vpc_properties['running'], vpc_properties['stopped']]
        return vpc_status_dict

    def get_environment_status(self, environment, region_vpc_dict):

        """Get environment status."""
        ah_obj = AtlasHelper()
        vpc_status_dict = {}
        organizations = self.awshelper_obj.get_organizations()
        org_attributes = self.ah_obj.get_nested_attribute_values(self.awshelper_obj.get_instances_details(), 'organizations')[1]
        for organization in organizations:
            if self.environment_groups and environment in self.environment_groups[1].keys():
                env_status_dict = {}
                if environment == 'all':
                    env_group_for_env = self.awshelper_obj.get_environments(organization)
                else:
                    env_group_for_env = self.environment_groups[1][environment]
                for env in env_group_for_env:
                    env_attributes = self.ah_obj.get_nested_attribute_values(org_attributes[organization], env)[1]
                    env_status_dict = self.determine_environment_status(env, env_attributes, region_vpc_dict)
                    if not vpc_status_dict:
                        vpc_status_dict.update(env_status_dict)
                    else:
                        for vpc in env_status_dict.keys():
                            vpc_status_dict[vpc]['status'] = map(add,vpc_status_dict[vpc]['status'],env_status_dict[vpc]['status'])
            else:
                env_attributes = self.ah_obj.get_nested_attribute_values(org_attributes[organization], environment)[1]
                vpc_status_dict = self.determine_environment_status(environment, env_attributes, region_vpc_dict)
        return vpc_status_dict


    def find_env_details(self, environment, env_attributes, region_vpc_dict):
        organizations = self.awshelper_obj.get_organizations()
        details_dict, env_subnets_dict = {}, {}
        environment_subnets = {'vpc':{}}
        apps_in_environment, instances_list, application_subnets, env_subnet_list = [], [], [], []
        vpc_attribute_dict, aws_info_dict, env_info_dict={}, {}, {}
        instances_list,apps_in_environment, env_subnet_list = [], [], []
        subnets_with_instances = {} #new addition
        instance_keys = self.ah_obj.get_atlas_config_data(self.module, "instance_keys")
        for region in region_vpc_dict.keys():
                if region not in env_attributes['regions'].keys():
                    continue
                else:
                    region_attributes = env_attributes['regions'][region]
                    if environment == 'uncategorized':
                        vpc_attribute_dict[region] = {"subnets":{"none":{"instance_attributes":{}}}}
                        for instance, details in region_attributes['uncat_instances'].iteritems():
                            if details.has_key('instance_attributes') and details['instance_attributes'].has_key('instance_id'):
                                instance_id = details['instance_attributes']['instance_id']
                                vpc_attribute_dict[region]["subnets"]["none"]["instance_attributes"][instance_id] = details['instance_attributes']
                                aws_info_dict[instance_id] = {}
                                aws_info_dict[instance_id]['aws_information'] = details['aws_information']
                                aws_info_dict[instance_id]['aws_tags'] = details['aws_tags']
                    else:
                        for vpc in region_vpc_dict[region]:
                            if vpc and vpc in region_attributes['vpc'].keys():
                                environment_subnets['vpc'][vpc] = {'subnets':[]}
                                env_subnet_list.extend(self.awshelper_obj.get_subnets_in_environment(region, vpc, environment))
                                environment_subnets['vpc'][vpc]['subnets'] = env_subnet_list
                                vpc_attribute_dict[vpc] = {'subnets': {}, 'applications':[]}
                                vpc_attribute_dict[vpc]['subnets'] = {}
                                vpc_properties = self.ah_obj.get_nested_attribute_values(env_attributes['regions'][region], vpc)[1]

                                if 'subnets' in vpc_properties.keys():
                                    for subnet in vpc_properties['subnets'].keys():
                                        instances_details = vpc_properties['subnets'][subnet]['instances']
                                        if instances_details:
                                            #env_subnet_list.append(subnet)
                                            subnets_with_instances[subnet] = []
                                            vpc_attribute_dict[vpc]['subnets'][subnet] = {'instance_attributes': {}}
                                            if subnet not in application_subnets: application_subnets.append(subnet)
                                            for instance, details in instances_details.iteritems():
                                                instance_attributes = details['instance_attributes']
                                                if instance_attributes:
                                                    details_key = details['instance_attributes']['instance_id']
                                                    vpc_attribute_dict[vpc]['subnets'][subnet]['instance_attributes'][details_key] = instance_attributes
                                                aws_info_dict[details_key] = {}
                                                aws_info_dict[details_key]['aws_information'] = details['aws_information']
                                                aws_info_dict[details_key]['aws_tags'] = details['aws_tags']
                                                instance_application = instance_attributes['application']
                                                if instance_application not in subnets_with_instances[subnet]:
                                                    subnets_with_instances[subnet].append(instance_application)
                                                if instance_attributes['application'] not in apps_in_environment:
                                                    apps_in_environment.append(instance_attributes['application'])

        details_dict['subnets_with_instances']    = subnets_with_instances
        details_dict['environment_subnets'] = environment_subnets
        details_dict['application_subnets'] = application_subnets
        details_dict['vpc_attribute_dict'] = vpc_attribute_dict
        details_dict['aws_info_dict'] = aws_info_dict
        details_dict['env_subnet_list'] = env_subnet_list
        details_dict['apps_in_environment'] = apps_in_environment
        return details_dict

    def get_environment_details(self, environment, region_vpc_dict):
        """
        Get details for a particular environment or environment_group.
        """
        organizations = self.awshelper_obj.get_organizations()
        org_attributes = self.ah_obj.get_nested_attribute_values(self.awshelper_obj.get_instances_details(), 'organizations')[1]
        for organization in organizations:
            if self.environment_groups and environment in self.environment_groups[0]:
                if environment == 'all':
                    env_group_for_environment = self.awshelper_obj.get_environments(organization)
                else:
                    env_group_for_environment = self.environment_groups[1][environment]
                for env in env_group_for_environment:
                        env_attributes = self.ah_obj.get_nested_attribute_values(org_attributes[organization], env)[1]
                        environment_details = self.find_env_details(env, env_attributes, region_vpc_dict)
                        if not self.env_details_dict:
                            self.env_details_dict.update(environment_details)
                        else:
                            generator_obj = self.ah_obj.merge_dictionaries(self.env_details_dict, environment_details)
                            self.env_details_dict = {key:value for key, value in generator_obj}
            else:
                env_attributes = self.ah_obj.get_nested_attribute_values(org_attributes[organization], environment)[1]
                self.env_details_dict = self.find_env_details(environment, env_attributes, region_vpc_dict)
        return self.env_details_dict


    def get_column_data(self, environment):
        column_dict = {}
        if 'vpc_attribute_dict' in self.env_details_dict:
            environment_attributes = self.env_details_dict['vpc_attribute_dict']
            for vpc, vpc_attrs_dict in environment_attributes.iteritems():
                 column_dict[vpc] = {'subnets': {}}
                 if 'subnets' in vpc_attrs_dict:
                    for subnet , subnet_attributes in vpc_attrs_dict['subnets'].iteritems():
                        column_dict[vpc]['subnets'][subnet] = {'instance_attributes':[]}
                        if 'instance_attributes' in subnet_attributes:
                            column_dict[vpc]['subnets'][subnet]['instance_attributes'] = subnet_attributes['instance_attributes']
        return column_dict

