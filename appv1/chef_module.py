from atlas_base import AtlasBase
from atlas_helper_methods import AtlasHelper
import atlas_helper_methods
from chef_helper import ChefHelper
from awsdetails import AwsInstanceHelper
from session_handler import SessionHandler
from chef_actions import ChefActions
from collections import OrderedDict

class ChefModule(AtlasBase):

    def __init__(self, request=None, environment=None):
        self.module = "chef_module"
        self.ah_obj = AtlasHelper()
        self.chef_obj = ChefHelper()
        self.chef_actionsobj = ChefActions()
        self.instance_obj = AwsInstanceHelper()
        self.request = request
        self.session_obj = SessionHandler()
        if environment is None:
            pass
        else:
            self.environment = environment


    def get_configuration_data(self, key):
        value = self.ah_obj.get_atlas_config_data(self.module, key)
        if isinstance(value, dict):return value[0]
        else: return value


    

    def get_information(self, environment=None, **kwargs):
        if environment is None:
            pass
        else:
            if 'instance_information' in kwargs:
                if kwargs['instance_information'] == 'true':
                    return self.chef_obj.get_node_attributes()
            if 'databag_attributes' in kwargs:
                if kwargs['databag_attributes'] == 'true':
                    return self.chef_obj.get_chefdbag_attributes_foritem('customer_portal_override', 'deployment')
            if 'tabs_information' in kwargs:
                if kwargs['tabs_information'] == 'true':
                    chef_instance_info = self.chef_obj.get_node_attributes()
                    chef_databag_info = self.chef_obj.get_chefdbag_attributes_foritem('customer_portal_override', 'deployment')
                    return self.chef_obj.map_node_databag_attributes(chef_instance_info, chef_databag_info, self.environment);

    def get_status(self, environment=None):
        return self.get_configuration_data('status')

    def get_tabs(self, environment=None):
        tabs_list = self.get_configuration_data('tabs')
        tabs_info_dict= {}
        if environment is not None:
            if tabs_list is not None:
                tabs_info_dict=self.get_information(self.environment, tabs_information='true')
        return(tabs_list, tabs_info_dict)


    def get_instance_actions(self, environment=None):
        pass


    def get_instance_group_actions(self):
        stack_actions = self.get_configuration_data('instance_group_actions')
        if stack_actions: return stack_actions[0]


    def get_stack_actions(self, environment=None):
        return self.get_configuration_data('stack_actions')

    def get_vpc_actions(self, environment=None):
        pass

    def get_action_status(self, json_data, environment=None):
        return

    def get_environment_actions(self, environment=None):
        return self.get_configuration_data('environment_actions')

    def get_action_parameters(self, action_type, environment=None):
        pass


    def perform_instance_actions():
        pass


    def perform_instancegroup_actions():
        pass

    def perform_stack_actions(self, json_data, environment=None):
        initial_status = self.chef_actionsobj.initiate_actions(json_data)
        if initial_status is not None:
            initial_status['action_type'] = json_data['action_type']
        return initial_status

    def perform_vpc_actions(self, json_data):
        pass

    def perform_environment_actions():
        pass


    def get_columns(self, environment=None):
        pass

    def load_session(self, request, environment=None):
        pass

    def save_session(self, request, environment=None):
        pass


    def get_aggregates(self, environment=None):
        if environment is None:
            return(self.get_configuration_data('columns'))


    def get_stack_attributes(self, environment, stack=None):
        return self.chef_obj.get_stack_attributes(environment)


    def get_attribute_values(self, environment):
        return self.chef_obj.get_stack_attribute_values(self.request,environment, self.session_obj.load_region_session(self.request))

    def refresh_information(self, environment=None):
        self.chef_obj.cache_chef_node_attributes()
        self.chef_obj.cache_databag_attributes_foritem('customer_portal_override', 'deployment')
