import boto
import boto, boto.ec2
from aws_helper import AwsHelper
from atlas_helper_methods import AtlasHelper
import jenkins
from jenkins import Jenkins
import re
from boto.exception import AWSConnectionError, EC2ResponseError
import memcache

class AwsActions:

    def __init__(self):
        self.awshelper_obj = AwsHelper()
        self.ah_obj = AtlasHelper()
        self.connection_obj = ""
        self.module = "aws_module"
        self.memcache_var = memcache.Client([self.ah_obj.get_atlas_config_data("global_config_data",
                                                                    'memcache_server_location')
                                        ], debug=0)


    def get_instance_state(self, connection, instance_id):

        instance = connection.get_only_instances(instance_id)
        if instance:
            return instance[0].__dict__.get('_state')
        else:
            return "action_failed"

    def get_action_status(self, connection, instance_id, action, parameters=None):

        instance_state = self.get_instance_state(connection, instance_id)

        if instance_state == "action_failed":
            return {'instance_id': instance_id, 'action_state': "action_failed", 'instance_state':"unknown", 'error_message': "Action Failed!!!"}

        else:
            if action == 'start_instance' or action=='start_instances':
                if str(instance_state) == 'running(16)':
                    return {'instance_id': instance_id, 'action_state':"action_completed", 'instance_state':"running"}
                else:
                    return {'instance_id': instance_id, 'action_state':"action_in_progress", 'instance_state':str(instance_state)}
            elif action == 'stop_instance' or action== 'stop_instances':

                if str(instance_state) == 'stopped(80)':

                    return {'instance_id': instance_id, 'action_state':"action_completed", 'instance_state':"stopped"}
                else:
                    return {'instance_id': instance_id, 'action_state':"action_in_progress", 'instance_state':str(instance_state)}

            elif action == 'terminate_instance' or action=='terminate_instances':
                if str(instance_state) == 'terminated(48)':
                    return {'instance_id': instance_id, 'action_state':"action_completed", 'instance_state':"terminated"}
                else:
                    return {'instance_id': instance_id, 'action_state':"action_in_progress", 'instance_state':str(instance_state)}
            elif action == 'edit_tags':
                tag_dict = self.get_tags(connection, instance_id)
                return {'instance_id': instance_id, 'editable_output':tag_dict, 'action_state': 'action_completed', 'editable':'true'}
            elif action == 'create_tag':
                return {'instance_id': instance_id, 'editable_output':{}, 'action_state': 'action_intiated', 'editable':'true'}
            elif action == 'delete_tag':
                return {'instance_id': instance_id, 'editable_output':{}, 'action_state': 'action_intiated', 'editable':'true'}


    def start_instance(self, connection, instance_id):
        start_list = connection.start_instances([instance_id])
        started_instance = re.findall(instance_id, str(start_list[0]))
        if cmp(started_instance, [instance_id]) == 0:
            return {'instance_id': instance_id, 'action_state':"action_initiated", 'instance_state':"unknown"}
        else:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown",'error_message': 'Could not start instance!!!'}



    def stop_instance(self, connection, instance_id):

        stop_list = connection.stop_instances([instance_id])
        stopped_instance = re.findall(instance_id, str(stop_list[0]))
        if cmp(stopped_instance, [instance_id]) == 0:
            return {'instance_id': instance_id, 'action_state':"action_initiated", 'instance_state':"unknown"}
        else:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown", 'error_message': 'Could not stop instance!!!'}


    def terminate_instance(self, connection, instance_id):

        terminated_list = connection.terminate_instances([instance_id])
        terminated_instance = re.findall(instance_id, str(terminated_list[0]))
        if cmp(terminated_instance, [instance_id]) == 0:
            return {'instance_id': instance_id, 'action_state':"action_initiated", 'instance_state':"unknown"}
        else:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown", 'error_message': 'Could not stop instance!!!'}


    def get_tags(self, connection, instance_id):
        instance = connection.get_only_instances(instance_id)
        tag_dict = instance[0].tags
        if tag_dict:
            return tag_dict

    def create_tag(self, connection, instance_id, tag_name, tag_value):
        result = connection.create_tags(instance_id, {tag_name: tag_value})
        if result:
            tag_dict=self.get_tags(connection, instance_id)
            return {'instance_id': instance_id, 'editable_output':tag_dict, 'action_state': 'action_completed', 'editable':'true'}


    def delete_tag(self, connection, instance_id, tag_name, tag_value):
        result = connection.delete_tags(instance_id, {tag_name : tag_value})
        if result:
            tag_dict=self.get_tags(connection, instance_id)
            return {'instance_id': instance_id, 'editable_output':tag_dict, 'action_state': 'action_completed', 'editable':'true'}

    def initiate_actions(self, action, region,instance_id, parameters=None):
        try:
            connection = self.awshelper_obj.get_aws_connection(region)
            if action == 'start_instance' or action == 'start_instances':
                return self.start_instance(connection, instance_id)
            elif action == 'stop_instance' or action == 'stop_instances':
                return self.stop_instance(connection, instance_id)
            elif action == 'terminate_instance' or action == 'terminate_instances':
                return self.terminate_instance(connection, instance_id)
            elif action == 'create_tag':
                tag = parameters.keys()[0]
                value = parameters[tag]
                return self.create_tag(connection, instance_id,tag,value)
            elif action == 'delete_tag':
                tag = parameters.keys()[0]
                value = parameters[tag]
                return self.delete_tag(connection, instance_id, tag, value)
            elif action == 'edit_tags':
                return self.get_tags(connection, instance_id)
        
        except AWSConnectionError:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown", 'error_message': "AWS Connection Error!!!"}
        except EC2ResponseError as exp_object:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown", 'error_message': "Error in response from EC2!!!"}
        except Exception as exp_object:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown", 'error_message': "Action failed!!! An excpetion occurred!!!"}

    def check_action_status(self, action, region, instance_id, parameters=None):

        connection = ""
        try:
             
            connection = self.awshelper_obj.get_aws_connection(region)
            action_status = self.get_action_status(connection, instance_id, action, parameters)
            console_output = connection.get_console_output(instance_id)
            if console_output:
                action_status['console_output'] = console_output.output
                action_status['other_info'] = {'instance_id':console_output.instance_id, 'timestamp':console_output.timestamp}
            return action_status

        except AWSConnectionError:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown", 'error_message': "AWS Connection Error!!!"}
        except EC2ResponseError:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown", 'error_message': "Error in response from EC2!!!"}
        except Exception as exp_object:
            return {'instance_id': instance_id, 'action_state':"action_failed", 'instance_state':"unknown", 'error_message': "Action failed!!! An excpetion occurred!!!"}


    """
    helpers
    """

    def instance_actions(self, instance_json, environment):
        status_dict={}
        action_status=""
        parameters=""
        for instance in instance_json['instance_details_dict']['instances']:
            instance_details = instance_json['instance_details_dict']['instances'][instance]
            region, vpc, subnet, instance_id= instance_details['region'], instance_details['vpc'],instance_details['subnet'], instance_details['instance_id']
            status = instance_details['status']
            status_dict[instance_id] = {}
            if 'parameters' in instance_json.keys():
                parameters = instance_json['parameters']
            
            action_status = self.check_action_status(instance_json['action'], region, instance_id, parameters)
            if 'editable' in action_status.keys() and action_status['editable'] == 'true':
                if action_status['action_state'] == 'action_completed':
                    status_dict[instance_id] = action_status
                else:
                    status_dict[instance_id] = self.initiate_actions(instance_json["action"], region, instance_id, instance_json['parameters'])
            elif action_status['instance_state'] == status:
                status_dict[instance_id]['error_message'] = "Cannot perform action!!!"+ " Instance: " + action_status['instance_id']+ " already "+action_status['instance_state']
            elif action_status['action_state'] == "action_failed":
                status_dict[instance_id] = action_status
            else:
                action_status = self.initiate_actions(instance_json["action"], region, instance_id, parameters)
                status_dict[instance_id] = action_status
            status_dict[instance_id]['action'] = instance_json['action']
            status_dict[instance_id]['table_id'] = instance_json['table_id']
            status_dict[instance_id]['stack_name'] = instance_json['for_stack']
        return status_dict

    def instance_status(self,instance_json, environment):
        status_dict = {}
        action_status=""

        #check if action can be performed
        instance_details_dict = instance_json['instance_details_dict'];
        for instance in instance_details_dict['instances']:
            instance_details = instance_details_dict['instances'][instance]
            region, vpc, subnet,stack, instance_name, instance_id = instance_details['region'], \
                instance_details['vpc'],instance_details['subnet'], instance_details['stack'], \
                instance_details['instance'], instance_details['instance_id']
            status = instance_details['status']
            status_dict[instance_id] = {}
            environment_information = self.read_instance_details();
            org_name = environment_information['organizations'].keys()[1]
            action_status = self.check_action_status(instance_json["action"], region, instance_id, instance)
            status_dict[instance_id] = action_status
            if action_status['action_state'] == "action_failed":
                status_dict[instance_id] = action_status
            if action_status['action_state'] == 'action_completed' and action_status['instance_state'] != 'terminated':
                env_info = ""
                if environment != 'uncategorized':
                    env_info = environment_information['organizations'][org_name]['environments'][environment]['regions'][region]['vpc'][vpc]['subnets'][subnet]['instances'][instance_name]['instance_attributes']
                else:
                    env_info = environment_information['organizations'][org_name]['environments'][environment]['regions'][region]['uncat_instances'][instance_name]['instance_attributes']
                    if env_info:
                        env_info.__setitem__('status', action_status["instance_state"])
                        self.write_instance_details(environment_information)

            elif action_status['action_state'] == 'action_complete' and action_status['instance_state'] == 'terminated':
                if environment != 'uncategorized':
                    environment_information.pop(environment_information['organizations'][org_name]['environments'][environment]['regions'][region]['vpc'][vpc]['subnets'][subnet]['instances'][instance_name])
                else:
                    environment_information.pop(environment_information['organizations'][org_name]['environments'][environment]['regions'][region]['uncat_instances'][instance_name])

                self.write_instance_details(environment_information)
            status_dict[instance_id]['action_type'] = instance_json['action_type']
            status_dict[instance_id]['action'] = instance_json['action']
            status_dict[instance_id]['table_id'] = instance_json['table_id']
            status_dict[instance_id]['stack_name'] = instance_json['for_stack']
            status_dict[instance_id]['action_type'] = instance_json['action_type']
            status_dict[instance_id]['action'] = instance_json['action']
        return status_dict


    def write_instance_details(self, instance_details):
        self.memcache_var.set("aws_instances_details_cache", instance_details)


    def read_instance_details(self):
        instance_details = self.awshelper_obj.get_instances_details()
        if instance_details:
            return instance_details
