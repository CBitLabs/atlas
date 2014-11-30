import os, sys, collections
import boto, boto.ec2
from atlas_helper_methods import *
import re, datetime
import memcache, collections
from concurrent.futures import ThreadPoolExecutor
import chef
from chef import DataBag, DataBagItem
from chef import DataBagItem
from dateutil import parser
from dateutil import tz
from collections import OrderedDict, defaultdict
import threading


class AwsHelper:

    def __init__(self):
        self.ah_obj = AtlasHelper()
        self.module = "aws_module"
        self.instance_info = []
        self.env_subnet_dict={}
        self.environment_dict = {}
        self.memcache_var = memcache.Client([self.ah_obj.get_atlas_config_data("global_config_data",'memcache_server_location')], debug=0)
        self.environment_details = {}
        self.regions_for_env_dict = {}
  
    def get_databag_attributes(self, atlas_set_header, databag_set_name):
        """
        Returns all items of a databag given the header and databag name in the atlas config file.
        """
        data_bag_attr = {}
        base_path = self.ah_obj.get_atlas_config_data("chef_module", 'chef-base-path')
        api = chef.autoconfigure(base_path)
        chef_databags = self.ah_obj.get_atlas_config_data(atlas_set_header, databag_set_name)[1]
        for databag in chef_databags.keys():
                data_bag = DataBag(databag,api)
                key_list = {}
                items = chef_databags[databag]['items'].keys()
                for item_index in items:
                    key_list = chef_databags[databag]['items'][item_index]['keys']
                    chef_databag_item = DataBagItem(databag,item_index,api)
                    for item_keys, item_values in chef_databag_item.iteritems():
                        if item_keys in key_list:
                            data_bag_attr[item_keys] =  item_values
                        elif type(item_values) == dict:
                            data_bag_attr[item_keys] = {}
                            for key in key_list:
                                attr_values = self.ah_obj.get_nested_attribute_values(item_values, key)
                                data_bag_attr[item_keys][key] = attr_values
        return data_bag_attr

    def get_databag_attrs_fromcache(self, atlas_set_header, databag_set_name):
        """
        Check in short term cache if not fetch from long term cache
        """
        db_attribute_dict = self.memcache_var.get('atlas_yaml')
        if not db_attribute_dict:
            db_attribute_dict = self.memcache_var.get('global_atlas_yaml')
            if db_attribute_dict is not None:
                self.memcache_var.set("atlas_yaml", db_attribute_dict, 10800)
            with threading.Lock():
                thread = threading.Thread(target=self.cache_databag_attributes, args=[atlas_set_header, databag_set_name])
                thread.start()
        return db_attribute_dict

    def cache_databag_attributes(self, atlas_set_header, databag_set_name):
        """
        Fetch databag attributes from chef server using keys defined in atlas configuration file and cache it locally.
        """
        try:
            databag_attribute_dict = self.get_databag_attributes(atlas_set_header, databag_set_name) 
            if databag_attribute_dict is None:
                raise Exception("The infrastructure data is not available. Please make sure you get the data from atlas.yaml and populate the cache !!!")
            if databag_attribute_dict:
                 self.memcache_var.set("atlas_yaml", databag_attribute_dict, 15*60)         
            self.memcache_var.set("global_atlas_yaml",databag_attribute_dict, 24*60*60)
            self.memcache_var.disconnect_all()
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "cache_databag_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            return


   
    def initialize_environments(self, organization, env_list):
        """
        Construct an initial dictionary self.environment_dict.
        """
        aws_variables = self.ah_obj.get_atlas_config_data(self.module, "status")[0]
        self.regions_for_env_dict = self.regions_for_env()
        for environment in env_list:
            self.environment_dict['organizations'][organization]['environments'][environment] = {'regions':{}}
            temp_env_regions = self.environment_dict['organizations'][organization]['environments'][environment]['regions']
            region_list = self.regions_for_env_dict[environment]
            for region in region_list:
                if environment == 'uncategorized':
                    temp_env_regions[region] = {'uncat_instances': {}}
                    for variables in aws_variables:
                        temp_env_regions[region][variables]= 0
                else:
                    temp_env_regions[region] = {'vpc':{}}
                    for variables in aws_variables:
                        temp_env_regions[region][variables]= 0
                    vpc_list = self.get_vpc_in_region(region)
                    if vpc_list:
                        for vpc in vpc_list:
                            if vpc:
                                temp_env_regions[region]['vpc'][vpc] = {'subnets':{}}
                                for variables in aws_variables:
                                    temp_env_regions[region]['vpc'][vpc][variables]= 0
                                subnets = self.get_subnets_in_environment(region, vpc,environment)
                                for subnet in subnets:
                                    temp_env_regions[region]['vpc'][vpc]['subnets'][subnet] = {'instances':{}}
                                    self.env_subnet_dict[(subnet, vpc, region)]=environment

    def initialize_instance_dictionary(self):
        """
        Initialize the dictionary.
        """
        env_list=[]
        self.environment_dict = {'organizations':{}}
        try:
            for organization in self.get_organizations():
                self.environment_dict['organizations'] = {organization : {'environments':{}}}
                env_list = self.get_environments(organization)
                env_list.append('uncategorized');
                self.initialize_environments(organization, env_list)
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "initialize_instance_dictionary()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def parse_application_name(self, instance_name):
        """
        a dictionary for regex patterns for instance names
        this should be moved to the configuration file
        """
        application_regex_dictionary = self.ah_obj.get_atlas_config_data(self.module, "instances-regex")[1]
        # by iterating through the dictionary we can determine if an instance runs an application
        for key, values in application_regex_dictionary.iteritems():
            for pattern in values:
                if re.match("^"+pattern+"$", instance_name):
                    return key
        return "uncategorized"

    def get_duration(self, instance):
        """
        Get duration or uptime of an instance .
        """
        duration = instance.__dict__.get("launch_time")
        local_time_duration = datetime.datetime.now().replace(tzinfo=tz.tzlocal())-parser.parse(str(duration)).astimezone(tz.tzlocal())
        return local_time_duration


    def timedelta_to_duration(self,timedelta):
        """
        this method receives date information in timedelta format
        the hours, minutes and seconds are retrieved in hours, minutes and seconds
        """
        return str(timedelta.days)+"d "+str(timedelta.seconds//3600)+"h "+str((timedelta.seconds//60)%60)+"m"


    def count_return_state(self, instances, count_dict):
        """
        Count the number of instances based on _state.
        """
        instance_state=""
        try:
            count_dict['count']+=1;
            if str(instances.__dict__.get('_state', 'none')) == "running(16)":
                instance_state = "running"
                count_dict['running']+=1;
            if str(instances.__dict__.get('_state', 'none')) == 'stopped(80)':
                instance_state="stopped"
                count_dict['stopped']+=1;
            return instance_state
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("awshelper.py", "count_return_state()", exp_object, exc_type, exc_obj, exc_tb)
            return "None"


    def cache_aws_instances_information(self):
        """
        Cache the instances information using memcache.
        """
        try:
            aws_inst_dict = self.get_aws_instances_information()
            self.memcache_var.set("aws_instances_details_cache", aws_inst_dict,60*60)
            if aws_inst_dict is None:
                raise Exception('AWS instance data is empty. Please check if data is available from AWS and populate the cache !!!')
            if aws_inst_dict is not None:
                 self.memcache_var.set("global_aws_cache", aws_inst_dict,86400)
            self.memcache_var.disconnect_all()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("awshelper.py", "cache_aws_instances_information()", exp_object, exc_type, exc_obj, exc_tb)
            self.memcache_var.disconnect_all()


    def get_instances_details(self):
        """
        Get details of all instances.
        """
        instance_details = self.memcache_var.get("aws_instances_details_cache")
        self.memcache_var.disconnect_all()
        if not instance_details:
            instance_details = self.memcache_var.get("global_aws_cache")
            if instance_details is not None:
                self.memcache_var.set('aws_instances_details_cache', instance_details,2*60*60)
            with threading.Lock():
                thread = threading.Thread(target=self.cache_aws_instances_information)
                thread.start()
        return instance_details


    def get_aws_instances_information(self):
        try:
            self.initialize_instance_dictionary()
            organizations_list = self.get_organizations();
            instances_list = []
            if organizations_list:
                for organization in organizations_list:
                    region_list = self.get_regions()
                    for region in region_list:
                        conn_obj = self.get_aws_connection(region)
                        instances_list = self.get_aws_instances(conn_obj) 
                        images_list = conn_obj.get_all_images()
                        aws_images_dict = {}
                        for image in images_list:
                            aws_images_dict[image.id] = image
                        with ThreadPoolExecutor(max_workers=3) as executor:
                            future = executor.submit(self.fetch_awsinstance_info, organization, region, region_list, instances_list, aws_images_dict, conn_obj)
            self.memcache_var.set("aws_instances_details_cache", self.environment_dict)
            self.memcache_var.disconnect_all()
            return self.environment_dict
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("helper.py", "get_aws_instances_information()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def fetch_awsinstance_info(self, organization, region, region_list, instances_list, aws_images_dict, conn_obj):
        """
        Fetch and parse all instances information to create aws information dictionary object.
        """
        try:
            for instances in instances_list:
                #read knife tags and atlas tags
                knife_tags = instances.tags.get('knife_tags');
                atlas_tags = {}  #should read through boto in the future
                aws_instance_name = ""
                if knife_tags:
                    vpc = knife_tags['vpc'];
                    instance_subnet = knife_tags['subnet']
                    application_name = knife_tags['stack']
                    instance_name = knife_tags['hostname']
                #else get attributes from atlas tags
                elif atlas_tags:
                    pass
                else:
                    #use other aws tags or parse the instance name to get instance attributes
                    vpc_id = str(instances.__dict__.get('vpc_id', 'none'))
                    vpc = self.get_vpc_by_id(vpc_id, region)
                    instance_subnet = "none"
                    environment=""
                    if vpc:
                        subnet_id = str(instances.__dict__.get('subnet_id'))
                        if subnet_id:
                            instance_subnet = self.get_subnet_byid(subnet_id, region, vpc)
                        else:
                            instance_subnet ='none'

                    aws_instance_name = re.split('[:,.;_-]', instances.tags.get('Name', 'none'))
                    instance_name = aws_instance_name[2] if len(aws_instance_name)==3 else instances.tags.get('Name', 'none')
                    application_name = self.parse_application_name(instance_name)

                stack_list = self.get_stack()

                if (instance_subnet,vpc,region) in self.env_subnet_dict.keys():
                    environment=self.env_subnet_dict[(instance_subnet, vpc, region)]
                    env_regions = self.regions_for_env_dict[environment]
                else:
                    environment = "uncategorized"
                    env_regions = region_list

                if region not in env_regions:
                    pass
                else:
                    #read other instance tags
                    instance_tags = instances.tags
                    instance_id =  instances.__dict__['id']
                    instance_type = instances.__dict__['instance_type']
                    instance_ip_address = instances.__dict__['private_ip_address']
                    image_id = instances.__dict__['image_id']
                    image_name = ""
                    if image_id in aws_images_dict:
                        image_name = aws_images_dict[image_id].name
                    instance_attribute_dict = collections.defaultdict(dict)
                    instance_attribute_dict['region'] = region
                    instance_attribute_dict['vpc'] = vpc
                    instance_attribute_dict['subnet'] = instance_subnet
                    instance_attribute_dict['instance_id'] = instance_id
                    instance_attribute_dict['instance'] = instance_name
                    instance_attribute_dict['application'] = application_name
                    instance_attribute_dict['instance_type'] = instance_type
                    aws_information_dict = collections.defaultdict(dict)
                    aws_information_dict['instance_id'] = instance_id
                    aws_information_dict['instance_type'] = instance_type
                    aws_information_dict['private_ip_addr'] = instance_ip_address
                    aws_information_dict['image_id'] = image_id
                    aws_information_dict['image_name'] = image_name
                    aws_tags = instance_tags
                    if not vpc or instance_subnet == 'none' or application_name == 'uncategorized':
                        environment = 'uncategorized'
                        uncategorized_dict = self.environment_dict['organizations'][organization]['environments'][environment]['regions'][region]
                        instance_attribute_dict['status'] = self.count_return_state(instances, uncategorized_dict)
                        uncategorized_dict['uncat_instances'][instance_name] = {'instance_attributes' : {}, 'aws_information':{}}
                        uncategorized_dict['uncat_instances'][instance_name]['instance_attributes'] = dict(instance_attribute_dict)
                        uncategorized_dict['uncat_instances'][instance_name]['aws_information'] = dict(aws_information_dict)
                        uncategorized_dict['uncat_instances'][instance_name]['aws_tags'] = aws_tags
                        instance_attribute_dict['duration'] = self.timedelta_to_duration(self.get_duration(instances))
                    else:
                    #if vpc and instance_subnet <>'none':
                        environment_subnets = self.get_subnets_in_environment(region, vpc, environment)

                        if instance_subnet in environment_subnets:
                            count_dict = self.environment_dict['organizations'][organization]['environments'][environment]['regions'][region]
                            self.count_return_state(instances, count_dict)
                            count_dict = self.environment_dict['organizations'][organization]['environments'][environment]['regions'][region]['vpc'][vpc]
                            instance_attribute_dict['status'] = self.count_return_state(instances, count_dict)
                            instance_attribute_dict['duration'] = self.timedelta_to_duration(self.get_duration(instances))

                            #create attribute list for each instance running the application for each subnet
                            stack_subnet_dict = self.environment_dict['organizations'][organization]['environments'][environment]['regions'][region]['vpc'][vpc]['subnets']
                            if application_name in stack_list:

                                if instance_subnet not in stack_subnet_dict.keys():
                                    stack_subnet_dict[instance_subnet] = {'instances':{}} #subnets in which the application runs
                                stack_subnet_dict[instance_subnet]['instances'][instance_name] = {'instance_attributes' : {}, 'aws_information':{}}
                                stack_subnet_dict[instance_subnet]['instances'][instance_name]['instance_attributes']=dict(instance_attribute_dict)
                                stack_subnet_dict[instance_subnet]['instances'][instance_name]['aws_information'] = dict(aws_information_dict)
                                stack_subnet_dict[instance_subnet]['instances'][instance_name]['aws_tags'] = aws_tags
            

        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("awshelper.py", "fetch_aws_instance_info()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_organizations(self):
        """
        Fetch all organizations.
        """
        try:
            (organizations, org_attributes) = self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "organizations")
            return organizations
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_organizations()", exp_object, exc_type, exc_obj, exc_tb)
            return


    def get_org_attributes(self):
        """
        Fetch attributes of all organization.
        """
        try:
            (organization, org_attributes) = self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "organizations")
            return org_attributes
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_org_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_attributes_for_organization(self, org_name):
        """
        Fetch attributes when a particular organization name is given.
        """
        try:
            (organization, org_attributes) = self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "organizations")
            if org_name in organization:
                return org_attributes[org_name]
            else:
                raise Exception ("Organization not found!!")
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_org_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_regions(self):
        """
        Return a list of regions.
        """
        try:
            return self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "regions")[0]
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_regions()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_region_attributes(self):
        """
        Return a dictionary of attributes of all regions.
        """
        try:
            return self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "regions")[1]
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_region_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            return


    def get_attributes_for_region(self, region_name):
        """
        Returns the attributes of region given the region name
        """
        try:
            (regions, region_attributes) = self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "regions")
            if region_name in regions:
                return region_attributes[region_name]
            else:
                return {}
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_attributes_for_region()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_region_id(self, region):
        """
        Return region id given region name.
        """
        region_id = ""
        try:
            region_attr = self.get_attributes_for_region(region)
            if "id" in region_attr.keys():
                region_id = region_attr["id"]
            else:
                region_id = region
            return region_id

        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_attributes_for_region()", exp_object, exc_type, exc_obj, exc_tb)
            return


    def get_vpc_in_region(self, region_name):
        """
        Return the vpcs in a region given a region.
        """
        try:
            vpc_list = []
            (regions, region_attributes) = self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "regions")
            if region_name in regions:
                if 'vpc' in region_attributes[region_name]:
                    vpc_list = region_attributes[region_name]['vpc'].keys()
                    if vpc_list is not None:
                        return vpc_list
                else:
                    pass
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_vpc_in_region()", exp_object, exc_type, exc_obj, exc_tb)
            return ["none"]



    def get_vpc_by_id(self, vpc_id, region_name):
        """
        Returns the vpc id given the region name.
        """
        try:

            vpc_list = []
            (regions, region_attributes) = self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "regions")
            if region_name in regions:
                if 'vpc' in region_attributes[region_name].keys():
                    (vpc_list, vpc_attributes) = self.ah_obj.get_nested_attribute_values(region_attributes[region_name],"vpc")

                    for vpc in vpc_list:
                        (vpc_keys, vpc_values) = self.ah_obj.get_nested_attribute_values(vpc_attributes, vpc)
                        if "vpcid" in vpc_keys:
                            if vpc_values["vpcid"] == vpc_id:
                                return vpc
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_vpc_in_region()", exp_object, exc_type, exc_obj, exc_tb)
            return


    def get_subnet_list(self, region, vpc):
        """
        Return all the list of subnets in a vpc in a given region.
        """
        try:
            region_attributes = self.get_attributes_for_region(region)
            vpc_attributes = region_attributes[vpc]
            return self.ah_obj.get_nested_attribute_values(vpc_attributes[vpc], "subnets")[0]
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_subnet_list()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_subnets_in_environment(self, region, vpc, environment):
        """
        Return all the subnets belonging to an environment in a region and a vpc.
        """
        subnet_list = []
        try:
            if environment == 'uncategorized':
                return []
            if not vpc:
                return []
            region_attributes = self.get_attributes_for_region(region)
            if 'vpc' in region_attributes.keys():
                vpc_attributes = region_attributes['vpc']
                subnet_dict = self.ah_obj.get_nested_attribute_values(vpc_attributes[vpc], "subnets")[1]
                for subnet, subnet_attr in subnet_dict.iteritems():
                    if 'env' in subnet_attr:
                        if subnet_attr['env'] == environment:
                            subnet_list.append(subnet)
            return subnet_list
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_subnets_in_environment()", exp_object, exc_type, exc_obj, exc_tb)
            return []


    def get_subnet_byid(self, subnet_id, region, vpc):
        try:
            region_attributes = self.get_attributes_for_region(region)
            if 'vpc' in region_attributes.keys():
                vpc_attributes = region_attributes['vpc']
                subnet_dict = self.ah_obj.get_nested_attribute_values(vpc_attributes[vpc], "subnets")[1]
                for subnet, subnet_attr in subnet_dict.iteritems():
                    if subnet_attr['id'] == subnet_id:
                        return subnet

            return
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_subnet_byid()", exp_object, exc_type, exc_obj, exc_tb)
            return []


    def get_stack(self):
        """
        Returns a list of all stacks.
        """
        try:
            return self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "stacks")[0]

        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_stack()", exp_object, exc_type, exc_obj, exc_tb)
            return


    def get_stack_attributes(self):
        """
        Return the attribute values of all the stack entries.
        """
        try:

            return self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "stacks")[1]
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_stack_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            return


    def get_profiles_for_stack(self, stack_name):
        """
        Returns the profiles associated with the stack.
        """
        try:

            (stack,stack_attributes) = self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "stacks")
            if stack_name in stack:
                profile_list = self.ah_obj.get_nested_attribute_values(stack_attributes[stack_name],"profiles")
                return profile_list[0] if profile_list else []
            else:
                raise Exception ("Profile not found !!")

        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_profiles_for_stack()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_profiles(self):
        """
        Fetch a list of all profiles.
        """
        try:
            return self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "profiles")[0]
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_profiles()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_profile_attributes(self):
        """
        Fetch profile attributes.
        """
        try:
            return self.ah_obj.get_nested_attribute_values(self.get_databag_attrs_fromcache("global_config_data", "atlas_yaml_databag"), "profiles")[1]
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_profile_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_environments(self, organization):
        """
        Retrieve all environments given an organization name.
        """

        try:
            env_list = self.ah_obj.get_nested_attribute_values(self.get_org_attributes(), "env")[0]
            return env_list
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_environments()", exp_object, exc_type, exc_obj, exc_tb)
            return {}

    def get_env_subnets(self, organization, region, vpc):
        try:
            env_subnet_dict = {}
            environments = self.get_environments(organization)
            for env in environments:
                subnet_list = self.get_subnets_in_environment(region, vpc, env)
                for subnet in subnet_list:
                    env_subnet_dict[subnet, vpc, region] = env
            return env_subnet_dict
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_env_subnets()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def regions_for_env(self):
        """
        Return the regions in which an environment exists.
        """
        region_dict = collections.defaultdict(dict)
        try:
            organizations_list = self.get_organizations()
            for organization in organizations_list:
                region_dict['uncategorized'] = self.get_regions()
                region_list = self.get_regions()
                for region in region_list:
                    region_attributes = self.get_attributes_for_region(region)
                    if 'vpc' in region_attributes.keys():
                        vpc_attributes = region_attributes['vpc']
                        for vpc in vpc_attributes.keys():
                            subnet_dict = self.ah_obj.get_nested_attribute_values(vpc_attributes, "subnets")[1]
                            for environment in self.get_environments(organization):
                                region_dict[environment] = []
                                for subnet, subnet_attr in subnet_dict.iteritems():
                                    if subnet_attr.has_key("env"):
                                        if subnet_attr['env'] == environment and region not in region_dict[environment]:
                                            region_dict[environment].append(region)
            return dict(region_dict)
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_regions_for_env()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_aws_connection(self, region):
        """
        Return an AWS connection object.
        """
        try:
            region_id = self.get_region_id(region);
            key_id = os.environ.get('AWS_ACCESS_KEY_ID')
            secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            connection = boto.ec2.connect_to_region(region_id,aws_access_key_id=key_id,
            aws_secret_access_key=secret_key)
            return connection
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_aws_connection()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_aws_instances(self, connection):
        """
        Get all AWS instances.
        """
        try:
            all_reservations_list = connection.get_all_instances()
            all_instances_list = [instances for reservations in all_reservations_list for instances in reservations.instances]
            return all_instances_list
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("aws_helper.py", "get_aws_instances()", exp_object, exc_type, exc_obj, exc_tb)
            return

     #get all environments and corresponding subnets from json file
    def get_environment_subnets_details(self):
        try:
            subnet_list = []
            organization_list = self.get_organizations()
            if organization_list is not None:
                for organization in organization_list:
                    environment_list = self.get_environments(organization)
                    environment_list.append("uncategorized");
                    for environment in environment_list:
                        if environment == "uncategorized":
                            subnet_list.append(['none', '(not set)'])
                        region_list = self.get_regions()
                        if region_list is not None:
                            for region in region_list:
                                vpc_list= self.get_vpc_in_region(region)
                                if vpc_list is not None:
                                    for vpc in vpc_list:
                                        
                                        subnet_list.append(self.get_subnets_in_environment(region, vpc, environment))
            return zip(environment_list, subnet_list)

        except Exception as exp_object:

            self.ah_obj = AtlasHelper()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "get_env_subnets()", exp_object, exc_type, exc_obj, exc_tb)
            return ([],[])

    def get_dash_environments(self):
        """
        Get all environments for dashboard display.
        """
        organizations = self.get_organizations()
        environment_list=[]
        environment_groups = self.ah_obj.get_atlas_config_data('global_config_data', 'environment_groups')
        for organization in organizations:
            environment_list = self.get_environments(organization)
            for environment in environment_list:
                if environment in environment_groups[0]:
                    for group_member in environment_groups[1][environment]:
                        if environment != group_member:
                            environment_list.remove(group_member)
            environment_list.append('uncategorized')
            environment_list.append('all')
        return environment_list
