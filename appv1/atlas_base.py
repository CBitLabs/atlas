import abc
from abc import abstractmethod

class AtlasBase:
    __metaclass__ = abc.ABCMeta


    @abstractmethod
    def get_information():
        pass

    @abstractmethod
    def get_status():
        pass

    @abstractmethod
    def get_tabs():
        pass

    @abstractmethod
    def get_instance_actions():
        pass

    @abstractmethod
    def get_instance_group_actions():
        pass

    @abstractmethod
    def get_stack_actions():
        pass

    @abstractmethod
    def get_vpc_actions():
        pass

    @abstractmethod
    def get_action_parameters():
        pass

    @abstractmethod
    def perform_instance_actions():
        pass

    @abstractmethod
    def perform_instancegroup_actions():
        pass

    @abstractmethod
    def perform_stack_actions():
        pass

    @abstractmethod
    def perform_vpc_actions():
        pass

    @abstractmethod
    def get_columns():
        pass

    @abstractmethod
    def load_session():
        pass

    @abstractmethod
    def save_session():
        pass

    @abstractmethod
    def get_aggregates():
        pass

    @abstractmethod
    def get_stack_attributes():
        pass

    @abstractmethod
    def get_attribute_values():
        pass


    @abstractmethod
    def get_configuration_data():
        pass

    @abstractmethod
    def refresh_information():
        pass
