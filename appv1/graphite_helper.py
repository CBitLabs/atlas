from atlas_helper_methods import AtlasHelper
import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout
import collections
from collections import defaultdict
import sys
import json
from json import loads
import memcache
import threading
from threading import Thread, Lock
from aws_helper import AwsHelper
from aws_module import AwsModule

class GraphiteHelper():
    

    def __init__(self, request=None, environment=None):
        self.module = 'graphite_module'
        self.ah_obj = AtlasHelper() 
        self.aws_helperobj = AwsHelper()
        self.module_config_data = self.ah_obj.get_atlas_configuration_data(self.module)
        self.graphite_url = " "
        self.framework = ""
        self.parameters_list = []
        self.time_interval = 0.0
        self.server_monitored = []
        self.format = ""
        self.from_time = ""
        self.to_time = ""
        self.memcache_var = memcache.Client([self.ah_obj.get_atlas_config_data("global_config_data",'memcache_server_location')], debug=0)
        if environment is not None:
            self.aws_moduleobj = AwsModule(request=request,environment=environment)

    def get_subnet_list(self, environment):
        """
        Get the subnets for environment which has instances and decide if an attribute should be displayed on a subnet.
        """
        if environment != 'uncategorized':
            subnets_with_instances = self.aws_moduleobj.get_information(environment, subnets_with_instances='true')
            subnet_list = []
            for subnet, stack_list in subnets_with_instances.iteritems():
                for attribute, attr_details in self.module_config_data['stack_attributes'].iteritems():
                    if attr_details['stack'] == 'all' or set(attr_details['stack']).issubset(set(stack_list)):
                        if subnet not in subnet_list: subnet_list.append(subnet)
            return subnet_list
        
    def get_query_parameters(self):
        """Get the query parameters from atlas config yaml"""
        self.graphite_url = self.module_config_data['others']['graphite_url']+"render/?"
        self.framework = self.module_config_data['others']['framework']
        self.servers_monitored =  self.module_config_data['others']['server_name']
        self.database = self.module_config_data['others']['database']
        self.time_interval = self.module_config_data['others']['time_duration']
        if 'from' in self.time_interval: self.from_time = self.time_interval['from']
        if 'to' in self.time_interval: self.to_time = self.time_interval['to']
        if self.to_time is not None and self.from_time is not None:
            self.time_string = "&from="+str(self.from_time)+"&to="+str(self.to_time)
        if self.from_time is None:
            self.time_string = "&to="+str(self.to_time)
        if self.to_time is None:
            self.time_string = "&from="+str(self.from_time)
        self.parameters_list = self.module_config_data['others']['parameters']
        self.format = self.module_config_data['others']['format']

      
    def queries_for_graphite(self, subnet_list):
        """Construct queries for grahite"""
        query_dict = collections.defaultdict(dict)
        self.get_query_parameters()
        for subnet in subnet_list:
            for server in self.servers_monitored:
                for parameter in self.parameters_list:
                    target = self.framework+"."+subnet+".ms."+server+"."+self.database+"."+parameter   
                    query_dict[subnet][parameter] = self.graphite_url+"target="+target+self.time_string+"&format="+self.format      
        return dict(query_dict)                             


    def generate_report(self, query):
        """Retrieve query results from the graphite server."""
        try:
            report_json = {}
            response = requests.get(query)
            if response.status_code == 200:
                report_json = json.loads(response.text) #convert the json into a python dictionary
                return report_json
        except ConnectionError as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("graphite_helper.py", "generate_report()", exp_object, exc_type, exc_obj, exc_tb)   
        except HTTPError as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("graphite_helper.py", "generate_report()", exp_object, exc_type, exc_obj, exc_tb)   
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("graphite_helper.py", "generate_report()", exp_object, exc_type, exc_obj, exc_tb)
            return {}

    
    def get_stack_attributes(self, environment):
        """Get all stack attributes."""
        stack_attribute_list, stack_attribute_dict = [], {}
        for attribute, details in self.module_config_data['stack_attributes'].iteritems():
            stack_attribute_list.append((details['display_name'], details['editable']))
            stack_attribute_dict[details['display_name']] = details
        return(stack_attribute_list, stack_attribute_dict)


    def get_stack_attribute_values(self, environment):
        """Get stack attribute values from cache. If it does not exists get it from the the global cache."""
        stack_attribute_values = self.memcache_var.get(str(environment+"graphite_stack_attributes"))
        if not stack_attribute_values:
            stack_attributes_values = self.memcache_var.get(str(environment+"global_graphite_stack_attributes"))
            if stack_attribute_values is not None:
                self.memcache_var.set(str(environment+"graphite_stack_attributes"), stack_attribute_values, 10*60)
            with threading.Lock():
                thread = threading.Thread(target=self.cache_stack_attribute_values, args=[environment])
                thread.start()
        return stack_attribute_values

    def cache_stack_attribute_values(self, environment):
        """Cache stack attribute values."""
        try:
            stack_attribute_values =  self.stack_attribute_values(environment)    
            self.memcache_var.set(str(environment+"graphite_stack_attributes"), stack_attribute_values, 10*60)
            if stack_attribute_values is None:
                raise Exception("The graphite attribute values for environment "+environment+" has not been fetched. Please make sure the cache is populated !!!")
            if stack_attribute_values is not None:     
                self.memcache_var.set(str(environment+"global_graphite_stack_attributes"),stack_attribute_values, 15*60)
            self.memcache_var.disconnect_all()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("graphite_helper.py", "cache_stack_attribute_values()", exp_object, exc_type, exc_obj, exc_tb)
            return {}


    def stack_attribute_values(self, environment):
        """get stack attribute values from graphite server and parse it."""
        if environment != 'uncategorized':
            stack_attribute_dict = self.ah_obj.create_nested_defaultdict()
            organization_list = self.aws_helperobj.get_organizations()
            region_list = self.aws_helperobj.get_regions()
            stack_attributes_from_config = self.module_config_data['stack_attributes']
            attributes_list = stack_attributes_from_config.keys()
            subnet_list = self.get_subnet_list(environment)
            graphite_query_dict = self.queries_for_graphite(subnet_list)
            for organization in organization_list:
                for region in region_list:
                    vpc_list = self.aws_helperobj.get_vpc_in_region(region)
                    if vpc_list:
                        for vpc in vpc_list:
                            for subnet in subnet_list:
                                for attribute in stack_attributes_from_config:
                                    stack_list = stack_attributes_from_config[attribute]['stack']
                                    attribute_value=""
                                    suffix=""
                                    if 'suffix' in stack_attributes_from_config[attribute]: 
                                        suffix = stack_attributes_from_config[attribute]['suffix'] 
                                        display_name= ""
                                    if 'display_name' in stack_attributes_from_config[attribute]:
                                        display_name = stack_attributes_from_config[attribute]['display_name']
                                        report = self.generate_report(graphite_query_dict[subnet][attribute])
                                        if report:
                                            target = self.ah_obj.split_string(report[0]['target'], ('.'))
                                            if subnet in target and attribute in target:
                                                for index in range(len(report[0]['datapoints'])-1, 0, -1):
                                                    if report and report[0]['datapoints'][index][0] is not None:
                                                        attribute_value = str(int(report[0]['datapoints'][index][0]))+" "+suffix
                                                        break
                                                    else: attribute_value = "null"
                                        else:attribute_value = "null"
                                    for stack in stack_list:
                                        stack_attribute_dict[region][vpc][subnet][stack][display_name] = attribute_value               
            return self.ah_obj.defaultdict_to_dict(stack_attribute_dict)                                               
        
        