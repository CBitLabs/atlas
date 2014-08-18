#imports
import requests
import json
import os
import sys
from decimal import *
import datetime
import memcache
import collections
from datetime import date, timedelta
from aws_helper import AwsHelper
from atlas_helper_methods import AtlasHelper
from awsdetails import AwsInstanceHelper

class Cloudability:
    #constructor

    def __init__(self):
        self.cloudability_dict = {}
        self.ah_obj = AtlasHelper()
        self.aws_helper_object = AwsHelper()
        self.module = "cloudability_module"
        self.auth_token =  os.environ.get('CLOUDABILITY_AUTH_TOKEN')
        self.cl_base_url = self.ah_obj.get_atlas_config_data(self.module, "cloudability_base_url")
        self.cl_cost_url = self.ah_obj.get_atlas_config_data(self.module, "cloudability_cost_url")
        self.report_query = ""
        self.memcache_var = memcache.Client([self.ah_obj.get_atlas_config_data("global_config_data",
                                                                'memcache_server_location')

                                    ], debug=1)
        self.environment_subnets_details = self.aws_helper_object.get_environment_subnets_details()


    def construct_cost_query(self, query_parameters):
        try:
            self.report_query = self.cl_base_url+self.cl_cost_url+query_parameters+self.auth_token
            return self.report_query
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "construct_cost_query()", exp_object, exc_type, exc_obj, exc_tb)
            return

   
    def generate_report(self, query):
        try:
            report_json = {}
            response = requests.get(query)
            if response.status_code == 200:
                report_json = json.loads(response.text) #convert the json into a python dictionary
                return report_json
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "generate_report()", exp_object, exc_type, exc_obj, exc_tb)
            return {}


    def get_previous_period(self, start_date, end_date):
        try:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            period = ((end - start).days)+1
            previous_start_date = (start-datetime.timedelta(days=period)).strftime('%Y-%m-%d')
            previous_end_date = (end-datetime.timedelta(days=period)).strftime('%Y-%m-%d')
            return (previous_start_date, previous_end_date)
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_previous_period()", exp_object, exc_type, exc_obj, exc_tb)
            return


    #get ec2 costs
    def get_ec2_costs(self, start_date, end_date):
        ec2_costs={'region_zone': 0.0}
        try:
            query_parameters = "verbose=1&start_date="+start_date+"&end_date="+end_date+"&dimensions=linked_account_name&metrics=invoiced_cost&sort_by=invoiced_cost&order=desc&max_results=50&offset=0&auth_token="
            ec2_costs_query = self.construct_cost_query(query_parameters)
            ec2_cost_dict = self.generate_report(ec2_costs_query)
            if ec2_cost_dict:
                ec2_costs['region_zone']= round(float(ec2_cost_dict['meta']['aggregates'][0]['value'].strip('$').replace(',','')),2)
            if ec2_costs['region_zone']:
                return ec2_costs
            else:
                raise Exception("Could not generate EC2 costs")
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "calculate_ec2_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return ec2_costs

    #get aggregate cost spent for ec2 for the specified period
    def get_current_prev_ec2_costs(self, start_date, end_date):
        #query parameters should be moved to config file
        ec2_cost_dict = {'current_period': 0.0, 'previous_period': 0.0}
        try:
            previous_period = self.get_previous_period(start_date,end_date)
            previous_start_date, previous_end_date = previous_period[0], previous_period[1]
            ec2_cost_dict['current_period'] = self.get_ec2_costs(start_date, end_date)
            ec2_cost_dict['previous_period'] = self.get_ec2_costs(previous_start_date, previous_end_date)
            return ec2_cost_dict
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_ec2_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def create_envcost_dict(self):
        try:
            env_subnet_zip = self.environment_subnets_details
            per_environment_costs = {}
            for env_subnet_tuple in env_subnet_zip:
                per_environment_costs[env_subnet_tuple[0]] = 0
            return per_environment_costs
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "create_envcost_dict()", exp_object, exc_type, exc_obj, exc_tb)
            return {}

    def get_environment_costs(self, start_date, end_date):
        try:
            query_parameters = "verbose=1&start_date="+start_date+"&end_date="+end_date+"&dimensions=tag2&metrics=invoiced_cost&sort_by=invoiced_cost&order=desc&auth_token="
            subnets_cost_query = self.construct_cost_query(query_parameters)
            subnet_cost_dict = self.generate_report(subnets_cost_query)
            cost_dict = self.create_envcost_dict()
            env_subnet_zip = self.environment_subnets_details
            subnet_details = subnet_cost_dict['results']
            for subnet_index in subnet_details:
                for env_subnet_tuple in env_subnet_zip:
                    if subnet_index['tag2'] in env_subnet_tuple[1]:
                        #strip of the $ symbol and , convert the string to float with 2 precisions
                        subnet_cost = float((subnet_index['invoiced_cost'].strip('$')).strip(',').replace(",",""))
                        env_cost = cost_dict[env_subnet_tuple[0]]
                        if subnet_index['tag2'] in cost_dict.keys():
                            cost_dict[env_subnet_tuple[0]]+= round((env_cost+subnet_cost),2)
                        else:
                            cost_dict[env_subnet_tuple[0]] = round((env_cost+subnet_cost),2)
            if cost_dict:
                return cost_dict
            else:
                raise Exception('Could not calculate environment costs')
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_environment_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return {}
       

    def get_current_prev_environment_costs(self, start_date, end_date):
        #query parameters should be moved to config file
        try:
            env_cost_dict = {}
            previous_period = self.get_previous_period(start_date,end_date)
            previous_start_date, previous_end_date = previous_period[0], previous_period[1]
            env_cost_dict['current_period'] = self.get_environment_costs(start_date, end_date)
            env_cost_dict['previous_period'] = self.get_environment_costs(previous_start_date, previous_end_date)
            return env_cost_dict
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_subnet_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return


    #calculate costs subnet wise
    def get_subnet_costs(self, start_date, end_date):
        subnet_cost_dict = {}
        try:
            query_parameters = "verbose=1&start_date="+start_date+"&end_date="+end_date+"&dimensions=tag2&metrics=invoiced_cost&sort_by=invoiced_cost&order=desc&auth_token="
            subnets_cost_query = self.construct_cost_query(query_parameters)
            subnet_cost_json = self.generate_report(subnets_cost_query)
            env_subnet_zip = self.environment_subnets_details
            subnet_details = subnet_cost_json['results']
            for subnet_index in subnet_details:
                for env_subnet_tuple in env_subnet_zip:
                    if subnet_index['tag2'] in env_subnet_tuple[1]:
                    #strip of the $ symbol and , convert the string to float with 2 precisions
                        subnet_cost = float((subnet_index['invoiced_cost'].strip('$')).strip(',').replace(",",""))
                        if subnet_index['tag2'] in subnet_cost_dict.keys():
                            subnet_cost_dict[subnet_index['tag2']] += round(subnet_cost,2)
                        else:
                            subnet_cost_dict[subnet_index['tag2']] = round(subnet_cost,2)
            return subnet_cost_dict
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_subnetwise_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return {}

    def get_current_prev_subnet_costs(self, start_date, end_date):
        #query parameters should be moved to config file
        subnet_cost_dict = {}
        try:
            previous_period = self.get_previous_period(start_date,end_date)
            previous_start_date, previous_end_date = previous_period[0], previous_period[1]
            subnet_cost_dict['current_period'] = self.get_subnet_costs(start_date, end_date)
            subnet_cost_dict['previous_period'] = self.get_subnet_costs(previous_start_date, previous_end_date)
            return subnet_cost_dict
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_subnet_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return {}

    def split_string(self, input_string, delimiters):
        #this function splits a string on multiple delimiters
        delimiters = tuple(delimiters)
        string_list = [input_string,]
        for delimiter in delimiters:
            for index1, input_sub_string in enumerate(string_list):
                temp_var = input_sub_string.split(delimiter)
                string_list.pop(index1)
                for index2, input_sub_string in enumerate(temp_var):
                    string_list.insert(index1+index2, input_sub_string)
        return string_list

    def get_ebs_costs(self, start_date, end_date):
        try:
            query_parameters = "&start_date="+start_date+"&end_date="+end_date+"&filters=usage_type=@EBS&dimensions=usage_type,tag1,&metrics=invoiced_cost&order=desc&auth_token="
            ebs_cost_query = self.construct_cost_query(query_parameters)
            ebs_cost_json = self.generate_report(ebs_cost_query)
            ebs_details = ebs_cost_json['results']
            ebs_cost_dict = collections.defaultdict(dict)
            for instance_index in ebs_details:
                if instance_index['tag1'] in ebs_cost_dict:
                    ebs_cost_dict[instance_index['tag1']] += round(float(instance_index['invoiced_cost'].strip('$').replace(',','')),2)
                else:
                    ebs_cost_dict[instance_index['tag1']] = round(float(instance_index['invoiced_cost'].strip('$').replace(',','')),2)
            return dict(ebs_cost_dict)
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_instances_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return {}


    def get_instances_costs(self, start_date, end_date):
        try:
            query_parameters = "&start_date="+start_date+"&end_date="+end_date+"&filters=service_key==AmazonEC2&dimensions=tag1,tag3,&metrics=invoiced_cost&order=desc&auth_token="
            instance_cost_query = self.construct_cost_query(query_parameters)
            instance_cost_json = self.generate_report(instance_cost_query)
            instance_details = instance_cost_json['results']
            instance_cost_dict = collections.defaultdict(dict)
            for instance_index in instance_details:
                if 'tag3' in instance_index:
                    if instance_index['tag3'] in instance_cost_dict:
                        instance_cost_dict[instance_index['tag3']]+= round(float(instance_index['invoiced_cost'].strip('$').replace(',','')),2)
                    else:
                        instance_cost_dict[instance_index['tag3']] = round(float(instance_index['invoiced_cost'].strip('$').replace(',','')),2)
                elif 'tag1' in instance_index:
                    if instance_index['tag1'] in instance_cost_dict:
                        instance_cost_dict[instance_index['tag1']] += round(float(instance_index['invoiced_cost'].strip('$').replace(',','')),2)
                    else:
                        instance_cost_dict[instance_index['tag1']] = round(float(instance_index['invoiced_cost'].strip('$').replace(',','')),2)
            return dict(instance_cost_dict)
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_instances_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return {}

    def get_current_prev_instances_costs(self, start_date, end_date):
        try:
            instance_cost_dict = {}
            previous_period = self.get_previous_period(start_date,end_date)
            previous_start_date, previous_end_date = previous_period[0], previous_period[1]
            instance_cost_dict['current_period'] = self.get_instances_costs(start_date, end_date)
            instance_cost_dict['previous_period'] = self.get_instances_costs(previous_start_date, previous_end_date)
            return instance_cost_dict
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_subnet_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_percentage_change(self, cost_dict):

        percentage_dict, current_costs_dict, previous_costs_dict = {},{},{}
        try:
            if cost_dict:
                if cost_dict.has_key('current_period'): current_costs_dict = cost_dict['current_period']
                if cost_dict.has_key('previous_period'): previous_costs_dict = cost_dict['previous_period']
            else:
                raise Exception("Invalid value: No values for current and previous costs")
            for key in current_costs_dict:
                if key in previous_costs_dict.keys():
                    current_cost = current_costs_dict[key]
                    previous_cost = previous_costs_dict[key]
                    difference = current_cost - previous_cost

                    if difference < 0:
                        tag = 'decrease'
                    elif difference >0:
                        tag = 'increase'
                    else:
                        tag = 'equal'
                    if previous_cost == 0.0:
                        percentage = round((abs(difference)),2)
                    else:
                        percentage = round((abs(difference)*100/previous_cost),2)
                    percentage_dict[key] = (current_cost, tag, percentage)
                else:
                    percentage_dict[key] = (current_costs_dict[key], '',0)
            return percentage_dict
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_subnet_costs()", exp_object, exc_type, exc_obj, exc_tb)
            return {}

    def get_cloudability_costs(self):
        cloud_cost_dict = self.memcache_var.get('cloud_costs')
        if cloud_cost_dict is None:
            cloud_cost_dict = self.memcache_var.get('global_cloudability_costs')
            if cloud_cost_dict is not None:
                self.memcache_var.set("cloud_costs", cloud_cost_dict, 600)
            with threading.RLock():
                thread = threading.Thread(target= self.cache_cloud_costs)
                thread.start()
        return cloud_cost_dict

    def cache_cloud_costs(self):
        try:
            cloudability_dict = self.get_cloud_costs()
            self.memcache_var.set("cloud_costs", cloudability_dict,2*60*60)
            if cloudability_dict is None:
                raise Exception("Clodability data is not available. Please ensure data is available and populate the cache.")
            if cloudability_dict is not None:
                self.memcache_var.set("global_cloudability_costs", cloudability_dict,86400)
            self.memcache_var.disconnect_all()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "cache_cloud_costs()", exp_object, exc_type, exc_obj, exc_tb)
            self.memcache_var.disconnect_all()
      
    def get_cloud_costs(self):
        current_date= date.today().strftime('%Y-%m-%d')
        month = date.today().month
        if month in [1, 3, 5, 7, 8, 10, 12]:
            previous_date = (date.today()-timedelta(days=30)).strftime('%Y-%m-%d')
        elif month in [2]:
            previous_date = (date.today()-timedelta(days=28)).strftime('%Y-%m-%d')
        else:
            previous_date = (date.today()-timedelta(days=29)).strftime('%Y-%m-%d')
        organization_list = self.aws_helper_object.get_organizations()
        region_list = self.aws_helper_object.get_regions()
        self.cloudability_dict = self.ah_obj.create_nested_defaultdict()
        for organization in organization_list:
            for region in region_list:
                vpc_list = self.aws_helper_object.get_vpc_in_region(region)
                if vpc_list:
                    for vpc in ["ame1"]:
                        if vpc:
                           
                            ec2_costs = self.get_ec2_costs(previous_date, current_date)
                            self.cloudability_dict = self.ah_obj.create_nested_defaultdict()
                            self.cloudability_dict['ec2_costs'][organization] = ec2_costs   
                            ec2_costs = self.get_current_prev_ec2_costs(previous_date, current_date)
                            ec2_percentage_change = self.get_percentage_change(ec2_costs)
                            self.cloudability_dict['ec2_percentage_change'][organization]= ec2_percentage_change
                            
                            environment_costs = self.get_environment_costs(previous_date, current_date)
                            self.cloudability_dict['environment_costs'][organization] = environment_costs
                            environment_costs = self.get_current_prev_environment_costs(previous_date, current_date) 
                            env_percentage_change = self.get_percentage_change(environment_costs)
                            self.cloudability_dict['env_percentage_change'][organization] = env_percentage_change
                           
                            subnet_costs = subnet_costs = self.get_subnet_costs(previous_date, current_date)
                            self.cloudability_dict['subnet_costs'][organization]= subnet_costs
                            subnet_costs = self.get_current_prev_subnet_costs(previous_date, current_date)
                            subnet_percentage_change = self.get_percentage_change(subnet_costs)
                            self.cloudability_dict['subnet_percentage_change'][organization] = subnet_percentage_change
                            
                            instances_costs = self.get_instances_costs(previous_date, current_date)
                            self.cloudability_dict['instances_costs'][organization]= instances_costs
                            instances_costs = self.get_current_prev_instances_costs(previous_date, current_date)
                            instances_percentage_change = self.get_percentage_change(instances_costs)
                            self.cloudability_dict['instances_percentage_change'][organization] = instances_percentage_change
                            
                            ebs_costs = self.get_ebs_costs(previous_date, current_date)
                            self.cloudability_dict['ebs_costs'][organization]= ebs_costs
        return self.ah_obj.defaultdict_to_dict(self.cloudability_dict)

