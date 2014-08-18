from atlas_helper_methods import AtlasHelper
from aws_helper import AwsHelper
import jenkinsapi
from jenkinsapi.jenkins import Jenkins
from jenkins_actions import JenkinsActions
from atlas_base import AtlasBase


class JenkinsModule(AtlasBase):

    def __init__(self, request=None, environment=None):
        self.ah_obj = AtlasHelper()
        self.aws_helperobj = AwsHelper()
        self.module = "jenkins_module"
        if environment is None:
            self.awsact_obj = AwsActions()
            self.jenkinsact_obj = JenkinsActions(request)
        else:
            self.jenkinsact_obj = JenkinsActions(request,environment)

    def get_configuration_data(self, key):
        value = self.ah_obj.get_atlas_config_data(self.module, key)
        if isinstance(value, dict):
            return value[0]
        else:
            return value


    def get_information(self, environment, **kwargs):
        pass


    def get_status(self, environment=None):
        pass


    def get_tabs(self, environment=None):
        pass


    def get_instance_actions(self, environment=None):
        pass


    def get_instance_group_actions(self):
        pass


    def get_stack_actions(self, environment=None):
        stack_actions = self.get_configuration_data('stack_actions')
        if stack_actions:
            return stack_actions[0]


    def get_vpc_actions(self):
        vpc_actions = self.get_configuration_data("vpc_actions")
        if vpc_actions:
            return vpc_actions[0]


    def get_parameter_values(self, environment, parameter):
        return self.jenkinsact_obj.parameters_values(environment, parameter)


    def get_action_parameters(self, action_type, environment=None):
        return self.jenkinsact_obj.action_parameters(action_type, environment)

    def perform_instance_actions():
        pass


    def perform_instancegroup_actions():
        pass

    def perform_stack_actions(self, json_data, environment=None):
        action = json_data['action']
        parameters_dict = json_data['parameters']
        initial_status = self.jenkinsact_obj.initiate_actions(action, parameters_dict)
        if initial_status is not None:
            initial_status['action_type'] = json_data['action_type']
            initial_status['start_time'] = json_data['start_time']
            initial_status['action'] = json_data['action']
        return initial_status

    def perform_vpc_actions(self, json_data, environment=None):
        action = json_data['action']
        action_type = json_data['action_type']
        parameters_dict = json_data['parameters']
        initial_status = self.jenkinsact_obj.initiate_actions(action, parameters_dict)
        if initial_status is not None:
            initial_status['action_type'] = json_data['action_type']
            initial_status['start_time'] = json_data['start_time']
            initial_status['action'] = json_data['action']
        return initial_status

    def get_action_status(self, json_data, environment=None):
        action = json_data['action']
        action_type = json_data['action_type']
        parameter_dict = json_data['parameters']
        action_status = self.jenkinsact_obj.action_state(action)
        if action_status is not None:
            action_status['action_type'] = json_data['action_type']
            action_status['start_time'] = json_data['start_time']
            action_status['action'] = json_data['action']
        return action_status

   
    def get_columns(self, environment=None):
        pass

    def load_session(self, request, environment=None):
        pass

    def save_session(self, request, environment=None):
        pass


    def get_defaults():
        pass

    def get_aggregates(self, environment=None):
        pass

    def get_stack_attributes(self, environment=None, stack=None):
        stack_attribute_list = []
        stack_attributes_dict = self.ah_obj.get_atlas_config_data('jenkins_module', 'stack_attributes')[1]
        for attribute, details in stack_attributes_dict.iteritems():
            stack_attribute_list.append((attribute, details['editable']))
        return(stack_attribute_list, stack_attributes_dict)  

    def get_attribute_values(self, environment=None):
        jenkins_build_infodict = self.jenkinsact_obj.get_jenkins_build_userinfo('AWS-Build-Dev-Deploy-Dev')
        rev_sorted_buildno_list = list(reversed(sorted(jenkins_build_infodict.keys())))
        (stack_attr_list, stack_attr_details) = self.get_configuration_data("stack_attributes")
        stack_attr_values_dict = self.ah_obj.create_nested_defaultdict()
        organization_list = self.aws_helperobj.get_organizations()
        temp_subnet_list = []
        for organization in organization_list:
            region_list = self.aws_helperobj.get_regions()
            for region in region_list:
                vpc_list = self.aws_helperobj.get_vpc_in_region(region)
                if vpc_list:
                    for vpc in vpc_list:
                        for attribute, attr_details in stack_attr_details.iteritems():
                            for build_number in rev_sorted_buildno_list:
                                subnet = jenkins_build_infodict[build_number]['subnet']
                                if subnet not in temp_subnet_list:
                                    temp_subnet_list.append(subnet)
                                    for attribute in stack_attr_list:
                                        for stack in stack_attr_details[attribute]['stack']:
                                            if attribute in jenkins_build_infodict[build_number]:
                                                stack_attr_values_dict[region][vpc][subnet][stack][attribute] = \
                                                    jenkins_build_infodict[build_number][attribute]
        return self.ah_obj.defaultdict_to_dict(stack_attr_values_dict)


    def refresh_information(self, environment=None):
        self.jenkinsact_obj.cache_jenkins_build_userinfo()


