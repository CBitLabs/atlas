from appv1.models import UserProfile, StackOwnership
from appv1.models import StackAttributes, Hierarchy, Stack
from appv1.aws_helper import AwsHelper
from appv1.atlas_helper_methods import AtlasHelper
from appv1.awsdetails import AwsInstanceHelper
import database_helper
from database_helper import DatabaseHelper

class ChefActions:

    def __init__(self):
        self.awshelper_obj = AwsHelper()
        self.ah_obj = AtlasHelper()
        self.inst_obj = AwsInstanceHelper()
        self.db_helper = database_helper.DatabaseHelper()
        self.module = 'chef_module'

    """
    end of stack ownership functions
    """
    def find_env_in_envgroup(self, region, vpc, subnet, environment):
        env_groups = self.ah_obj.get_atlas_config_data("global_config_data","environment_groups")
        if environment in env_groups[1].keys():
            for env in env_groups[1][environment]:
                subnet_list = self.awshelper_obj.get_subnets_in_environment(region, vpc, env)
                if subnet in subnet_list:
                    return env


    def initiate_actions(self, json_data):
        initial_status = {}
        action = json_data['action']
        parameters_dict = json_data['parameters']
        user = json_data['username']
        environment = json_data['environment']
        region = json_data['region']
        vpc = json_data['vpc']
        subnet = json_data['subnet']
        stack = json_data['application']
        attribute = json_data['parameters'].keys()[0]
        attribute_value = json_data['parameters'][attribute]
        env_from_group = self.find_env_in_envgroup(region, vpc, subnet, environment)
        if env_from_group:
            environment=env_from_group
        if parameters_dict is None or parameters_dict =='':
            return
        if action =='release_ownership':
            action_result = self.db_helper.release_stack_ownership(user, environment, region, vpc, subnet, stack)
            if action_result == "ownership released":
                ownership = self.db_helper.get_stack_ownership_details(environment, region, vpc, subnet, stack)
                result_dict = {'owner': "none", 'attribute':'owner'}
                return {'action': action, 'stack': stack, 'region': region, 'vpc': vpc, 'subnet':subnet, 'editable_output':result_dict, 'action_state': 'action_completed', 'editable':'true', 'action_output': "Ownership Released!!!",}
            else:
                return {'action': action, 'stack': stack, 'region': region, 'vpc': vpc, 'subnet':subnet, 'action_state': 'action_failed', 'editable':'true', 'action_output': "Ownership is not released!!!",}

        if action == 'acquire_ownership':
            action_result = self.db_helper.take_ownership(user, environment, region, vpc, subnet, stack)
            if action_result == "ownership created":
                ownership = self.db_helper.get_stack_ownership_details(environment, region, vpc, subnet, stack)
                result_dict = {'attribute':attribute, 'owner': ownership.owner, 'start_time': int(ownership.start_time.strftime("%s")) * 1000}
                return {'action': action, 'stack': stack, 'region': region, 'vpc': vpc, 'subnet':subnet, 'editable_output':result_dict, 'action_state': 'action_completed', 'editable':'true', 'action_output': "Ownership Acquired!!!"}
            else:
                return {'action': action, 'stack': stack, 'region': region, 'vpc': vpc, 'subnet':subnet, 'action_state': 'action_failed', 'editable':'true', 'action_output': "Ownership is not acquired!!!"}

        if action == 'edit_attributes':
            stack_attribute_values =""
            stack_attributes = self.db_helper.get_stack_attribute_value(environment, region, vpc, subnet, stack, attribute)
            if stack_attributes:
                stack_attr_values = self.db_helper.edit_stack_attributes(environment, region, vpc, subnet, stack, attribute, attribute_value)
                stack_attr_dict = {'attribute': attribute, attribute: stack_attr_values.attribute_value}
                return {'editable_output': stack_attr_dict, 'action': action, 'stack':stack, 'action_state': 'action_completed',
                                  'region': region, 'vpc': vpc, 'subnet':subnet, 'editable': 'true'}


            else:
                self.db_helper.insert_stack_attributes(environment, region, vpc, subnet, stack, attribute, attribute_value)
                stack_attributes = self.db_helper.get_stack_attribute_value(environment, region, vpc, subnet, stack, attribute)
                if stack_attributes:
                    stack_attr_values = self.db_helper.edit_stack_attributes(environment, region, vpc, subnet, stack, attribute, attribute_value)
                    stack_attr_dict = {'attribute': attribute, attribute: stack_attr_values.attribute_value}
                    return {'editable_output': stack_attr_dict, 'action': action, 'stack':stack, 'action_state': 'action_completed',
                                  'region': region, 'vpc': vpc, 'subnet':subnet, 'editable': 'true'}
                else:
                    return {'action': action, 'stack': stack, 'action_state': 'action_failed', 'editable':'true', 'action_output': "Attribute edit failed!!!"}
