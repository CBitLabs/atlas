from appv1.models import UserProfile, StackOwnership
from appv1.models import StackAttributes, Hierarchy, Stack
from appv1.aws_helper import *
from appv1.atlas_helper_methods import *
from appv1.awsdetails import *
from aws_module import *
from django.db import connection
import collections, sys
from collections import defaultdict
import memcache



class DatabaseHelper:

    def __init__(self):
        self.inst_obj = AwsInstanceHelper()
        self.ah_obj = AtlasHelper()
        self.awshelper_obj = AwsHelper()
        self.memcache_var = memcache.Client([self.ah_obj.get_atlas_config_data("global_config_data",
                                                                    'memcache_server_location')
                                        ], debug=0)

    def populate_hierarchy(self):
        total=0
        awshelper_obj = AwsHelper()
        ownership_dict, attribute_dict=collections.defaultdict(list), collections.defaultdict(list)
        stack_ownership_records, stack_attribute_records = StackOwnership.objects.all(), StackAttributes.objects.all()
        if stack_ownership_records.count() > 0:
            for s_owner_record in stack_ownership_records:
                stack_record_set = Stack.objects.filter(id=s_owner_record.stack_id)
                for s_record in stack_record_set:
                    hierarchy_record_set = Hierarchy.objects.filter(id=s_record.subnet_id)
                    for h_record in hierarchy_record_set:
                        ownership_dict[s_owner_record.owner].append({'environment':h_record.environment,
                        'region':h_record.region,
                        'vpc':h_record.vpc,
                        'subnet':h_record.subnet,
                        'stack':s_record.stack,
                        'start_time':s_owner_record.start_time})
        if stack_attribute_records.count() > 0:
            for s_attr_record in stack_attribute_records:
                stack_record_set = Stack.objects.filter(id=s_attr_record.stack_id)
                for s_record in stack_record_set:
                    hierarchy_record_set = Hierarchy.objects.filter(id=s_record.subnet_id)
                    for h_record in hierarchy_record_set:
                        attribute_dict[s_attr_record.attribute].append({'environment':h_record.environment,
                                                                         'region':h_record.region,
                                                                         'vpc':h_record.vpc,
                                                                         'subnet':h_record.subnet,
                                                                         'stack':s_record.stack,
                                                                         'attribute_value':s_attr_record.attribute_value})
        

        cursor = connection.cursor()
        hierarchy = Hierarchy.objects.all()
        hierarchy.delete()
        cursor.execute("SELECT setval(pg_get_serial_sequence('appv1_hierarchy','id'), coalesce(max(id), 1), max(id) IS NOT null) FROM appv1_hierarchy")
        stack = Stack.objects.all()
        stack.delete()
        cursor.execute("SELECT setval(pg_get_serial_sequence('appv1_stack','id'), coalesce(max(id), 1), max(id) IS NOT null) FROM appv1_stack")
        cursor.execute("SELECT setval(pg_get_serial_sequence('appv1_stackattributes','id'), coalesce(max(id), 1), max(id) IS NOT null) FROM appv1_stackattributes")
        cursor.execute("SELECT setval(pg_get_serial_sequence('appv1_stackownership','id'), coalesce(max(id), 1), max(id) IS NOT null) FROM appv1_stackownership")
        self.create_hierarchy()
        self.create_subnet_stack()
        self.populate_ownership_attributes(ownership_dict, attribute_dict)
  
    def create_hierarchy(self):
        awshelper_obj = AwsHelper()
        for organization in awshelper_obj.get_organizations():
            environment_list = awshelper_obj.get_environments(organization)
            environment_list.append('uncategorized')
            for environment in environment_list:
                for region in awshelper_obj.get_regions():
                    vpc_list = awshelper_obj.get_vpc_in_region(region)
                    if vpc_list:
                        for vpc in vpc_list:
                            for subnet in awshelper_obj.get_subnets_in_environment(region, vpc, environment):
                                try:
                                    hierarchy_record = Hierarchy( environment = environment,
                                            region = region,
                                            vpc = vpc,
                                            subnet = subnet)
                                    hierarchy_record.save()
                                except Exception as exp_object:
                                        exc_type, exc_obj, exc_tb = sys.exc_info()
                                        self.ah_obj.print_exception("stack_attributes.py", "create_hierarchy", exp_object, exc_type, exc_obj, exc_tb)
                                        return

    def create_subnet_stack(self):
        awshelper_obj = AwsHelper()
        for organization in awshelper_obj.get_organizations():
            environment_list = awshelper_obj.get_environments(organization)
            environment_list.append('uncategorized')
            for environment in environment_list:
                env_details_dict = self.inst_obj.get_environment_details(environment, self.get_region_vpc_dict())
                for subnet in env_details_dict['application_subnets']:
                    hierarchy_records = Hierarchy.objects.filter(environment=environment, subnet=subnet)
                    for hierarchy in hierarchy_records:
                        for apps in env_details_dict['apps_in_environment']:
                            stack_records = Stack(subnet_id=hierarchy.id, stack = apps)
                            stack_records.save()


    def populate_ownership_attributes(self, ownership_dict, attributes_dict):
        try:
            for owner, ownership_dict_list in ownership_dict.iteritems():
                for ownership_data in ownership_dict_list:
                    environment = ownership_data['environment']
                    region = ownership_data['region']
                    vpc = ownership_data['vpc']
                    subnet = ownership_data['subnet']
                    stack = ownership_data['stack']
                    stack_id = self.get_stack_id(environment, region, vpc, subnet, stack)
                    ownership_record = StackOwnership(stack_id=stack_id, owner=owner, start_time=ownership_data['start_time'])
                    ownership_record.save()
            for attribute, attribute_dict_list in attributes_dict.iteritems():
                for attribute_data in attribute_dict_list:
                    environment = attribute_data['environment']
                    region = attribute_data['region']
                    vpc = attribute_data['vpc']
                    subnet = attribute_data['subnet']
                    stack = attribute_data['stack']
                    stack_id = self.get_stack_id(environment, region, vpc, subnet, stack)
                    attribute_record = StackAttributes(stack_id=stack_id, attribute=attribute, attribute_value=attribute_data['attribute_value'])
                    attribute_record.save()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("stack_attributes.py", "create_hierarchy", exp_object, exc_type, exc_obj, exc_tb)
            return


    def get_hierarchy_id(self, environment, region, vpc, subnet, stack):
        try:
            hierarchy = Hierarchy.objects.get(environment=environment, region=region, vpc=vpc, subnet=subnet)
            if hierarchy:
                h_id = hierarchy.id
                return h_id
        except Exception as exp_object:
            return

    def get_stack_id(self, environment, region, vpc, subnet, stack):
        try:
            h_id = self.get_hierarchy_id(environment, region, vpc, subnet, stack)
            if h_id:
                stack_record = Stack.objects.get(subnet_id=h_id, stack=stack)
                return stack_record.id
        except Exception as exp_object:
            return

    def get_region_vpc_dict(self):
        region_vpc_dict = {}
        for region in self.awshelper_obj.get_regions():
            region_vpc_dict[region] = []
            vpc_list = self.awshelper_obj.get_vpc_in_region(region)
            if vpc_list:
                for vpc in vpc_list:
                    region_vpc_dict[region].append(vpc)
        return region_vpc_dict


    """
    ownership functions
    """
    def take_ownership(self, username, environment, region, vpc, subnet, stack):
        """Acquire ownership for a class."""
      
        stack_id = self.get_stack_id(environment, region, vpc, subnet, stack)
        try:
            ownership_records = StackOwnership.objects.filter(stack_id= stack_id)
            if ownership_records:
                self.release_stack_ownership(username, environment, region, vpc, subnet, stack)
            ownership_record = StackOwnership(stack_id=stack_id, owner=username)
            ownership_record.save()
            return "ownership created"
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("stack_attributes.py", "take_ownership", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_stack_ownership_details(self, environment, region, vpc, subnet, stack):
        """Get the details from StackOwnership table."""

        try:
            stack_id = self.get_stack_id(environment, region, vpc, subnet, stack)
            s_owner_records = StackOwnership.objects.get(stack_id=stack_id)
            if s_owner_records:
                return s_owner_records
        except Exception as exp_object:
            return

    def release_stack_ownership(self, username, environment, region, vpc, subnet, stack):
        try:
            stack_id = self.get_stack_id(environment, region, vpc, subnet, stack)
            ownership_details = StackOwnership.objects.get(stack_id=stack_id)
            if ownership_details:
                ownership_details.delete()
                return "ownership released"
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("stack_attributes.py", "release_stack_ownership", exp_object, exc_type, exc_obj, exc_tb)
            return


    
    """
    stack attribute functions
    """


    def create_stack_attribute(self, environment, region, vpc, subnet, stack, attribute, attribute_value):
        """Add a stck_attribute with value."""
        try:
            attribute_record = StackAttributes( environment = environment,
                                    region = region,
                                    vpc = vpc,
                                    subnet = subnet,
                                    stack = stack,
                                    attribute = attribute,
                                    attribute_value = attribute_value)
            attribute_record.save()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("stack_attributes.py", "create_stack_attribute", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_stack_attribute_value(self, environment, region, vpc, subnet, stack, stack_attribute):
        """Edit stack attribute value."""
        try:
            stack_id = self.get_stack_id(environment, region, vpc, subnet, stack)
            attribute_record = StackAttributes.objects.get(stack_id=stack_id, attribute=stack_attribute)
            if attribute_record:
                return attribute_record
        except Exception as exp_object:
            return


    def insert_stack_attributes(self, environment, region, vpc, subnet, stack, stack_attribute, attribute_value):
        try:
            stack_id = self.get_stack_id(environment, region, vpc, subnet, stack)
            stack_attribute_record = StackAttributes(stack_id=stack_id, attribute=stack_attribute, attribute_value=attribute_value)
            stack_attribute_record.save()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("database_helper.py", "edit stack attributes", exp_object, exc_type, exc_obj, exc_tb)
            return


    def edit_stack_attributes(self, environment, region, vpc, subnet, stack, stack_attribute, new_value):
        try:
            stack_id = self.get_stack_id(environment, region, vpc, subnet, stack)
            stack_attribute_record = StackAttributes.objects.get(stack_id=stack_id, attribute=stack_attribute)
            if stack_attribute_record:
                stack_attribute_record.attribute_value=new_value
                stack_attribute_record.save()
            else:
                insert_stack_attributes(environment, region, vpc, subnet, stack, stack_attribute, new_value)
                stack_attribute_record = StackAttributes.objects.get(stack_id=stack_id, attribute=stack_attribute, attribute_value=new_value)
            return stack_attribute_record
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("database_helper.py", "edit stack attributes", exp_object, exc_type, exc_obj, exc_tb)
            return
 
    def save_and_create_atlas_data(self):
        self.populate_hierarchy()
