import jenkins
import jenkinsapi
import sys, os, collections
from jenkinsapi.jenkins import Jenkins
from jenkinsapi import api
from jenkinsapi import build
from jenkinsapi.job import *
from jenkinsapi.build import *
from jenkinsapi.api import *
from atlas_helper_methods import AtlasHelper
from aws_module import AwsModule


class JenkinsActions:

    def __init__(self, request=None, environment=None):

        self.ah_obj = AtlasHelper()
        self.module="jenkins_module"
        self.python_jenkinsurl = self.ah_obj.get_atlas_config_data(self.module, "python_jenkins_url")
        self.build_record_count = self.ah_obj.get_atlas_config_data(self.module, "build_record_count")
        self.jenkins_password = os.environ.get('JENKINS_PASSWORD')
        self.jenkins_username = os.environ.get('JENKINS_USERNAME')
        self.jenkinsurl = os.environ.get('JENKINS_URL')
        self.python_jenkinsurl = self.jenkinsurl+"/job/"
        self.memcache_var = memcache.Client([self.ah_obj.get_atlas_config_data("global_config_data",
                                                                    'memcache_server_location')
                                        ], debug=0)
        if environment:
            self.aws_obj = AwsModule(request, environment)

    """
    helper methods
    """

    def get_jenkins_job_folder(self, jobname):
        job_folder_information = self.ah_obj.get_atlas_config_data(self.module, "folders")[1]
        for folder, job_list in job_folder_information.iteritems():
            if jobname in job_list:
                return folder

    def cache_jenkins_build_userinfo(self):
        try:
            jobname = 'AWS-Build-Dev-Deploy-Dev'
            build_userinfo_dict = self.jenkins_build_userinfo(jobname)
            self.memcache_var.set(jobname+'_build_userinfo', build_userinfo_dict,15*60)
            if build_user_info_dict is None:
                raise Exception("Source data from Jenkins server is unavailable. Please ensure data is available and populate the cache.")
            if build_userinfo_dict is not None:
                self.memcache_var.set('global_'+jobname+'_build_userinfo', build_userinfo_dict,86400)
            self.memcache_var.disconnect_all()
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.ah_obj.print_exception("cloudability.py", "construct_cost_query()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def jenkins_build_userinfo(self, jobname):
        job_info_dict, job_info = {}, {}
        jenkinsapi_obj = api.Jenkins(self.jenkinsurl, username=self.jenkins_username, password=self.jenkins_password)
        jenkins_url = self.python_jenkinsurl+self.get_jenkins_job_folder(jobname)
        jenkins_obj = jenkins.Jenkins(jenkins_url, username=self.jenkins_username, password=self.jenkins_password)
        build_user_info_dict = collections.defaultdict(dict)
        try:
            if jenkins_obj.job_exists(jobname):
                job_info = jenkins_obj.get_job_info(jobname)
                build_information_list = job_info['builds']
                latest_build_number = build_information_list[0]['number']
                build_info = jenkins_obj.get_build_info(jobname, latest_build_number)
                for build_number in range(latest_build_number-self.build_record_count, latest_build_number+1):
                    try:
                        build_info_dict = jenkins_obj.get_build_info(jobname, build_number)
                        build_user_info_dict[build_number] = {'deployed_by':"", 'branch':"", 'last_deployed': "", 'subnet':"", 'commit_hash':""}
                        branch= ""
                        if 'actions' in build_info_dict:
                            if 'parameters' in build_info_dict['actions'][0]:
                                for parameter_dict in build_info_dict['actions'][0]['parameters']:
                                    if parameter_dict['name'] == 'subnet':
                                        build_user_info_dict[build_number]['subnet'] = parameter_dict['value']   
                                    if parameter_dict['name'] == 'branch':
                                        build_user_info_dict[build_number]['branch'] = parameter_dict['value']
                                        branch = parameter_dict['value']
                            if 'causes' in build_info_dict['actions'][1]:
                                actions = build_info_dict['actions'][1]
                                if 'userName' in actions['causes'][0]:
                                    build_user_info_dict[build_number]['deployed_by'] = build_info_dict['actions'][1]['causes'][0]['userName']
                            if 'buildsByBranchName' in build_info_dict['actions'][2]:
                                commit_hash =  build_info_dict['actions'][2]['buildsByBranchName']['origin/develop']['revision']['SHA1'][:7]
                                build_user_info_dict[build_number]['commit_hash'] = commit_hash
                        if 'timestamp' in build_info_dict:
                            timestamp = str(datetime.datetime.now() - datetime.datetime.fromtimestamp(build_info_dict['timestamp']/1000))
                            deployed_before = ""
                            if isinstance(timestamp, list):
                                hours_minutes = timestamp[1].split(":")[:2]
                                deployed_before = timestamp[0] + " "+hours_minutes[0]+"hrs "+hours_minutes[1]+"mins"
                            else:
                                hours_minutes = timestamp.split(":")[:2]
                                deployed_before = hours_minutes[0]+" hrs "+hours_minutes[1]+" mins"
                            build_user_info_dict[build_number]['last_deployed'] = deployed_before
                    except:
                        continue  
            return self.ah_obj.defaultdict_to_dict(build_user_info_dict)   
        except Exception as exp_object:
            return {}
        
    def get_jenkins_build_userinfo(self, jobname):
        build_userinfo_dict = self.memcache_var.get(jobname+'_build_userinfo')
        if not build_userinfo_dict:
            build_userinfo_dict = self.memcache_var.get('global_'+jobname+'_build_userinfo')
            if build_userinfo_dict is not None:
                self.memcache_var.set(jobname+'_build_userinfo', build_userinfo_dict, 3*60*60)
                with threading.Lock():
                    thread = threading.Thread(target=self.cache_jenkins_build_userinfo)
                    thread.start()
        return build_userinfo_dict


    def get_jenkins_job_info(self, jobname):
        job_info_dict, job_info = {}, {}
        jenkins_url = self.python_jenkinsurl+self.get_jenkins_job_folder(jobname)
        jenkins_obj = jenkins.Jenkins(jenkins_url, username=self.jenkins_username, password=self.jenkins_password)
        try:
            if jenkins_obj.job_exists(jobname):
               job_info = jenkins_obj.get_job_info(jobname)
            job_info_dict= {'last_successful_build_number':job_info['lastSuccessfulBuild']['number'],
                            'last_successful_build_url': job_info['lastSuccessfulBuild']['url'],
                            'last_unsuccessful_build_number': job_info['lastUnsuccessfulBuild']['number'],
                            'last_unsuccessful_build_url': job_info['lastUnsuccessfulBuild']['url'],
                            'last_completed_build_number':job_info['lastCompletedBuild']['number'],
                            'last_completed_build_url':job_info['lastCompletedBuild']['url'],
                            'last_unstable_build_number':job_info['lastUnstableBuild'],
                            'last_unstable_build_url':job_info['lastUnstableBuild'],
                            'last_stable_build_number':job_info['lastStableBuild']['number'],
                            'last_stable_build_url':job_info['lastStableBuild']['url'],
                            'last_build': job_info['lastBuild']['url'],
                            'last_build-number': job_info['lastBuild']['number'],
                            'nextBuildNumber':job_info['nextBuildNumber']
                        }
            return job_info_dict
        except Exception as exp_object:
            return {}

   
    def get_console_output(self,build):
        console_output = build.get_console()
        if console_output:
            return console_output

    def check_build_status(self, job_name):
        status_dict = {}
        try:
            jenkinsapi_obj = api.Jenkins(self.jenkinsurl, username=self.jenkins_username, password=self.jenkins_password)
            job = jenkinsapi_obj.get_job(job_name)
            build = job.get_last_build()
            other_info = self.get_jenkins_job_info(job_name)
            if other_info:
                status_dict['other_info'] = self.get_jenkins_job_info(job_name)
            status_dict['console_output'] = self.get_console_output(build)
            if build.is_running():
                status_dict['exit_status'] = "Build not complete"
                status_dict['action_state'] = "action_in_progress"
            else:
                if build.is_good():
                    status_dict['exit_status'] = "Build Successful"
                    status_dict['action_state'] = "action_completed"
            return status_dict
        except Exception as exp_object:
            status_dict['action_state'] = 'action_failed'
            return status_dict

    """
    action methods    
    """

    def server_create_test(self, subnet, profile, node_name):
        """
        Create a server on aws_obj.
        """
        jenkinsapi_obj = api.Jenkins(self.jenkinsurl, username=self.jenkins_username, password=self.jenkins_password)
        if profile == "ops-general":
            jenkinsapi_obj.build_job('server_create_test', {'subnet': subnet, 'profile': profile, 'name':node_name})
        else:
            jenkinsapi_obj.build_job('server_create_test', {'subnet': subnet, 'profile': profile})
        

    def echo_contents(self, text1, text2):
        """
        Echo contents sample jenkins job.
        """
        jenkinsapi_obj = api.Jenkins(self.jenkinsurl, username=self.jenkins_username, password=self.jenkins_password)
        jenkinsapi_obj.build_job('echo_contents', {'text1': text1, 'text2': text2})

   

    def initiate_actions(self, action, parameters):
        """
        Initiate jenkins actions. 
        """
        initial_status = {}
        try:
            if parameters is None or parameters =='':
                return
            other_info = self.get_jenkins_job_info(action)
            if other_info:
                initial_status['other_info'] = other_info
            if action =='echo_contents':
                self.echo_contents(parameters['text1'], parameters['text2'])
            if action == 'server_create_test':
                self.server_create_test(parameters['subnet'], parameters['profile'], parameters['node_name'])
            initial_status = self.check_build_status(action)
            initial_status['action_state'] = 'action_initiated'
            return initial_status
        except Exception as exp_object:
            return initial_status

    def action_state(self, action):
        """
        Check the status of builds.
        """
        action_state = self.check_build_status(action)
        return action_state

    def parameter_values(self, action, parameter, environment=None):
        """
        Return parameter values for each build to be displayed as options to user.
        """
        if action == 'server_create_test':
            if parameter == 'subnet':
                return self.aws_obj.get_information(environment, env_subnet_list='true')
            if parameter == 'profile':
                return self.aws_obj.get_information(environment, profiles='true')
            if parameter == 'name':
                return ""
        if action == 'echo_contents':
            if parameter == 'text1':
                return ""
            if parameter == 'text2':
                return ""

    def action_parameters(self, action_type, environment=None):
        """
        Get parameters for each action.
        """
        action_parameters_dict={}
        if (action_type=='vpc_actions'):
            action_parameters_dict = self.unpack_action_parameters(self.ah_obj.get_atlas_config_data(self.module, 'vpc_actions')[1], environment)
        elif action_type == 'instance_actions':
            pass
        elif action_type == 'instance_group_actions':
            pass
        elif action_type == 'stack_actions':
            action_parameters_dict = self.unpack_action_parameters(self.ah_obj.get_atlas_config_data(self.module, 'stack_actions')[1], environment)
        return action_parameters_dict

    def unpack_action_parameters(self, action_parameters_dict, environment=None):
        parameter_dict = {}
        for key, values in action_parameters_dict.iteritems():
            parameter_list = values['parameters']
            parameter_dict[key] = {}
            for parameter in parameter_list:
                temp_list = []
                temp_parameter = parameter.split(',')
                temp_list.append(temp_parameter[1])
                temp_list.append(self.parameter_values(key, temp_parameter[0], environment))
                parameter_dict[key][temp_parameter[0]] = temp_list
        return parameter_dict
