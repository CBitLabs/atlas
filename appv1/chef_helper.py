import chef
from chef import DataBag, DataBagItem
from chef import DataBagItem
from chef import Node
from chef.node import NodeAttributes
import sys
from atlas_helper_methods import AtlasHelper
from aws_module import AwsModule
import collections
from collections import OrderedDict, defaultdict, Counter
import memcache
import aws_helper
from aws_helper import AwsHelper
from database_helper import DatabaseHelper
import threading

   
class ChefHelper:

    def __init__(self):
        self.ah_obj = AtlasHelper()
        self.awshelper_obj = aws_helper.AwsHelper()
        self.module = "chef_module"
        self.db_obj = DatabaseHelper()
        self.environment_groups = self.ah_obj.get_atlas_config_data("global_config_data", "environment_groups")
        self.memcache_var = memcache.Client([self.ah_obj.get_atlas_config_data("global_config_data",
                                                                    'memcache_server_location')
                                        ], debug=0)
        self.environment_subnets_details = self.awshelper_obj.get_environment_subnets_details()

        try:
            base_path = self.ah_obj.get_atlas_config_data("chef_module", 'chef-base-path')
            self.api = chef.autoconfigure(base_path)
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("chef_helper.py", "__init__()", exp_object, exc_type, exc_obj, exc_tb)

    def get_databag_list(self, databag=''):
        #returns a list of all available data bags on the chef_server
        data_bag_list = []
        try:
            data_bags = DataBag(databag,self.api)
            for items in data_bags.list(self.api):
                data_bag_list.append(items)
            if not data_bag_list:
                raise Exception, "No Data bags items found"
            else:
                return data_bag_list
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("chef_helper.py", "get_databag_list()", exp_object, exc_type, exc_obj, exc_tb)
            return []


    def cache_databag_attributes_foritem(self, databag, item):
        """
        Fetch databag attributes from chef server using databag name and item name and cache it locally.
        """
        try:
            databag_attributes_foritem = self.get_databag_attribute_foritem(databag, item)
            self.memcache_var.set("cpdeployment_databag_attrs", databag_attributes_foritem,600) 
            if databag_attributes_foritem is None:
                raise Exception("Databag attributes cannot be obtained from Chef server. Please make sure data is obtained and populate the cache !!!")
            if databag_attributes_foritem is not None:
                self.memcache_var.set("global_cpdeployment_databag_attributes", databag_attributes_foritem ,86400)
            self.memcache_var.disconnect_all()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("chef_helper.py", "cache_databag_attributes_foritem()", exp_object, exc_type, exc_obj, exc_tb)
            self.memcache_var.disconnect_all()
            return

      
    def get_chefdbag_attributes_foritem(self, databag, item):
        """
        Check in short term cache if not fetch results from global cache
        """
        db_attribute_dict = self.memcache_var.get('cpdeployment_databag_attrs')
        if db_attribute_dict is None:
            db_attribute_dict = self.memcache_var.get('global_cpdeployment_databag_attrs')
            if db_attribute_dict is not None:
                self.memcache_var.set("cpdeployment_databag_attrs", db_attribute_dict, 600)
                self.memcache_var.disconnect_all()
                with threading.Lock():
                    thread = threading.Thread(target=self.cache_databag_attributes_foritem, args=(databag, item))
                    thread.start()
        return db_attribute_dict
       

    def get_databag_attribute_foritem(self, databag, item):
        try:
            data_bag = DataBag(databag,self.api)
            data_bag_item = data_bag[item]
            chef_databags = self.ah_obj.get_atlas_config_data("chef_module", 'chef_databags')[0]
            chef_databags_info = self.ah_obj.get_atlas_config_data("chef_module", 'chef_databags')[1]
            key_list = []
            for index in chef_databags:
                if databag in chef_databags_info.keys():
                    for item_index in chef_databags_info[databag]['items'].keys():
                        if item == item_index:
                            key_list = chef_databags_info[databag]['items'][item]['keys']

            data_bag_attr = {}
            data_bag_attr.fromkeys(data_bag_item.keys(), None)
            for d_item_key, d_item_values in data_bag_item.iteritems():

                if type(d_item_values)== unicode:
                    if d_item_key in key_list:
                        data_bag_attr[d_item_key] = {}
                        data_bag_attr[d_item_key] = d_item_values
                        break;
                elif type(d_item_values) == dict:
                    data_bag_attr[d_item_key] = {}

                    for key in key_list:
                        data_bag_attr[d_item_key][key] = self.ah_obj.get_nested_attribute_values(d_item_values, key)

            return data_bag_attr
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("chef_helper.py", "get_databag_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            return []

    def cache_chef_node_attributes(self):
        """
        Fetch node attributes from chef server and cache it locally.
        """
        try:
            chef_node_attributes_dict = self.get_node_attrs_from_chef()
            if chef_node_attributes_dict is None:
                raise Exception("Chef node attributes not available from the Chef server. Please make sure the data is available and populate the cache.")
            if chef_node_attributes_dict is not None:
                self.memcache_var.set("global_chef_node_attributes_cache", chef_node_attributes_dict,86400)
            self.memcache_var.disconnect_all()
            self.memcache_var.set("chef_node_attr_caches", chef_node_attributes_dict,2*60*60)
            self.memcache_var.disconnect_all()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("chef_helper.py", "cache_chef_node_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            self.memcache_var.disconnect_all()
            return
    
    def get_node_attributes(self):
        node_attribute_dict = self.memcache_var.get('chef_node_attr_caches')
        if node_attribute_dict is None:
            node_attribute_dict = self.memcache_var.get('global_chef_node_attributes_cache')
            self.memcache_var.disconnect_all()
            if node_attribute_dict is not None:
                self.memcache_var.set('chef_node_attr_caches', node_attribute_dict, 600)
                with threading.Lock():
                    thread = threading.Thread(target=self.cache_chef_node_attributes)
                    thread.start()
        return node_attribute_dict


    def get_node_attrs_from_chef(self):
        try:
            env_subnets_dict = {}
            node_attribute_dict = {}
            for organization in self.awshelper_obj.get_organizations():
                node_attribute_dict = defaultdict(dict)
                node_list = Node.list(self.api)
                for environment in self.awshelper_obj.get_environments(organization):
                    for region in self.awshelper_obj.get_regions():
                        vpc_list = self.awshelper_obj.get_vpc_in_region(region)
                        if vpc_list:
                            for vpc in self.awshelper_obj.get_vpc_in_region(region):
                                env_subnets_dict = self.awshelper_obj.get_env_subnets(organization, region, vpc)
                for node in node_list:
                    node_obj = Node(node, api=self.api)
                    node_split = self.ah_obj.split_string(node, ["."])
                    if node_split is None or len(node_split)<=1:
                        pass
                    else:
                        node_subnet = self.ah_obj.split_string(node, ['.'])[1]
                        for key_tuple, environment in env_subnets_dict.iteritems():
                            if node_subnet in key_tuple:
                                environment = env_subnets_dict[key_tuple]
                                attribute_list = node_obj.attributes
                                if 'ec2' in attribute_list:
                                    if 'instance_id' in node_obj.attributes.get_dotted('ec2'):
                                        instance_id = node_obj.attributes.get_dotted('ec2.instance_id')
                                        node_attribute_dict[instance_id]['node'] = node
                                if 'os' in attribute_list:
                                    node_attribute_dict[instance_id]['os']=node_obj['os']
                                if 'os_version' in attribute_list:
                                    node_attribute_dict[instance_id]['os_version'] = node_obj['os_version']
                                if 'platform' in attribute_list:
                                    node_attribute_dict[instance_id]['platform'] = node_obj['platform']
                                if 'platform_version' in attribute_list:
                                    node_attribute_dict[instance_id]['platform_version'] = node_obj['platform_version']
                                if 'uptime' in attribute_list:
                                    node_attribute_dict[instance_id]['uptime'] = node_obj['uptime']
                                if 'idletime' in attribute_list:
                                    node_attribute_dict[instance_id]['idletime'] = node_obj['idletime']
            return dict(node_attribute_dict)
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("chef_helper.py", "get_node_attrs_from_chef1()", exp_object, exc_type, exc_obj, exc_tb)
            return {}

    def map_node_databag_attributes(self, node_attributes, databag_attributes, environment):
        tabs_info_dict = {}
        for instance_id, details in node_attributes.iteritems():
            tabs_info_dict[instance_id] = {'chef_information':{}}
            tabs_info_dict[instance_id]['chef_information'] = details
            for node_attr, node_attr_value in details.iteritems():
                tabs_info_dict[instance_id]['chef_information'][node_attr]=node_attr_value
            if databag_attributes.has_key(details['node']):
                for key, value in databag_attributes.iteritems():
                    if details['node'] == key:
                        for attribute, attribute_value in value.iteritems():
                            tabs_info_dict[instance_id]['chef_information'][attribute] = attribute_value           
        return tabs_info_dict

    def get_values_for_attribute(self, environment, region, vpc, subnet, stack, attribute, details):
        attribute_value_dict = {}
        if attribute == "owner":
            ownership_records = self.db_obj.get_stack_ownership_details(environment, region, vpc, subnet, stack)
            if ownership_records is not None:
                attribute_value_dict["owner"] = ownership_records.owner
                attribute_value_dict["start_time"] = int(ownership_records.start_time.strftime("%s")) * 1000
            else:
                attribute_value_dict["owner"] = "none"
        if attribute == "dbhost" or attribute == "email_override" or attribute == "branch":
            attribute_record = self.db_obj.get_stack_attribute_value(environment, region, vpc, subnet, stack, attribute)
            if attribute_record is not None:
                attribute_value_dict[attribute] = attribute_record.attribute_value
            else:
                custportal_dbag_attrs = self.memcache_var.get('cpdeployment_databag_attrs');
                if custportal_dbag_attrs is not None:
                    for keys, values in custportal_dbag_attrs.iteritems():
                        custportal_dbag_attrs_subnet = keys.split(".")[1]
                        if custportal_dbag_attrs_subnet == subnet and stack in details['stack']:
                            if attribute == "dbhost":
                                if values['AWS_DB_HOST']:
                                    attribute_value_dict["dbhost"] = values['AWS_DB_HOST']
                                else:
                                    attribute_value_dict["dbhost"] = "none"
                            if attribute == "email_override":
                                if values['EMAIL_OVERRIDE'] and values['EMAIL_OVERRIDE'] is not None:
                                    attribute_value_dict["email_override"] = values['EMAIL_OVERRIDE'] 
                                if values['EMAIL_OVERRIDE'] == "none":
                                    pass 
                            if attribute == "branch":
                                if values["branch"]:
                                    attribute_value_dict["branch"] = values['branch']
                                else:
                                  "none"
        return attribute_value_dict


    def stack_attribute_values(self, request, environment, region_vpc_dict):
        """
        Get attributes and values for each stack.
        """
        stack_attribute_dict = collections.defaultdict(dict)
        awsmodule_obj = AwsModule(request, environment)
        (stack_attr_list, stack_attr_details) = stack_attributes = self.ah_obj.get_atlas_config_data(self.module, 'stack_attributes')
        application_subnets = awsmodule_obj.get_information(environment, application_subnets='true')
        apps_in_environment = awsmodule_obj.get_information(environment, apps_in_environment='true')
        if application_subnets is not None and apps_in_environment is not None:
            for region, vpc_list in region_vpc_dict.iteritems():
                stack_attribute_dict[region] = {}
                if vpc_list is not None:
                    for vpc in vpc_list:
                        stack_attribute_dict[region][vpc] = {}
                        for subnet in application_subnets:
                            stack_attribute_dict[region][vpc][subnet] = {}
                            for stack in apps_in_environment:
                                stack_attribute_dict[region][vpc][subnet][stack] = {}
                                for attribute in stack_attr_list:
                                    details = stack_attr_details[attribute]
                                    stack_attribute_dict[region][vpc][subnet][stack].update(self.get_values_for_attribute(environment, region, vpc, subnet, stack, attribute, details))                
        return dict(stack_attribute_dict)

    def get_stack_attribute_values(self, request, environment, region_vpc_dict):
        """
        Get stack attribute values for environment or environment groups.
        """
        stack_attribute_dict = {}
        stack_attribute_dict = self.stack_attribute_values(request, environment, region_vpc_dict)

        return stack_attribute_dict

    def get_stack_attributes(self, environment):
        """
        Get stack attributes from config file.
        """
        stack_attribute_list = []
        stack_attributes_dict = self.ah_obj.get_atlas_config_data('chef_module', 'stack_attributes')[1]
        for attribute, details in stack_attributes_dict.iteritems():
            stack_attribute_list.append((attribute, details['editable']))
        return(stack_attribute_list, stack_attributes_dict)    
    

