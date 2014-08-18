from aws_module import AwsModule
from chef_module import ChefModule
from cloudability_module import CloudabilityModule
from jenkins_module import JenkinsModule
from graphite_module import GraphiteModule

class ObjectHelper:

    def get_module_object(self, module_name, request=None, environment=None):
        """Create and return objects for each module."""
        if module_name == 'aws_module':
            return AwsModule(request=request, environment=environment)
        elif module_name == 'chef_module':
            return ChefModule(request=request, environment=environment)
        elif module_name == 'cloudability_module':
            return CloudabilityModule(request=request, environment=environment)
        elif module_name == 'jenkins_module':
            return JenkinsModule(request=request,environment=environment)
        elif module_name == 'graphite_module':
            return GraphiteModule(request=request,environment=environment)

