from atlas_base import AtlasBase
from graphite_helper import GraphiteHelper
from atlas_helper_methods import AtlasHelper

class GraphiteModule(AtlasBase):

    def __init__(self, request=None, environment=None):
        self.ah_obj = AtlasHelper()
        self.module = "graphite_module"
        self.graphite_obj =  GraphiteHelper(request=request, environment=environment)

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
        pass

    def get_vpc_actions(self):
        pass

    def get_parameter_values(self, environment, parameter):
        pass


    def get_action_parameters(self, action_type, environment=None):
        pass


    def get_environment_actions():
        pass


    def perform_instance_actions():
        pass


    def perform_instancegroup_actions():
        pass

    def perform_stack_actions(self, json_data, environment=None):
        pass

    def perform_vpc_actions(self, json_data, environment=None):
        pass

    def get_action_status(self, json_data, environment=None):
        pass

    def perform_environment_actions():
        pass

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

    def get_stack_attributes(self, environment=None):
        return self.graphite_obj.get_stack_attributes(environment)


    def get_attribute_values(self, environment=None):
        return self.graphite_obj.get_stack_attribute_values(environment)

    def refresh_information(self, environment=None):
        pass


