from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import datetime
from datetime import timedelta
import memcache
import sys
import logging
from appv1.atlas_helper_methods import AtlasHelper
from appv1.aws_helper import AwsHelper
from appv1.chef_helper import ChefHelper
from appv1.cloudability import Cloudability
from appv1.jenkins_actions import JenkinsActions
from appv1.database_helper import DatabaseHelper


class Command(BaseCommand):
    """Extend Base class and define options with values."""
    option_list = BaseCommand.option_list + (
        make_option('--options',
        action='store',
        type='string',
        dest='option',
        help='cache options'),
    )

    def handle(self, *args, **options):
        """Handle options and supplied arguments."""
        if options['option']:
            self.set_atlas_cache(options['option'], "all")


    def set_atlas_cache(self,expirytime, cachetype):
        """Set values for atlas cache variables."""
        
        ah_obj = AtlasHelper()
        atlas_log_filepath = ah_obj.get_atlas_configuration_data("global_config_data")['atlas_log_file']
        if atlas_log_filepath != 'none':
            atlas_log_file = "atlas-"+str(datetime.date.today())+".log"
            logging.basicConfig(filename=atlas_log_file, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
            logging.info('Starting setatlascache.py...')
            logging.info('Started to cache data for Atlas...')

        try:
            
            ah_obj.cache_atlas_config_data()
            memcache_location = ah_obj.get_atlas_configuration_data('global_config_data')['memcache_server_location']
            memcache_var = memcache.Client([memcache_location], debug=1)
            if atlas_log_filepath != 'none': logging.info('Obtained memcache server location...')

        
            #Cache atlas yaml data
            aws_object = AwsHelper()
            if atlas_log_filepath != 'none': logging.info('Caching atlas yaml data...')
            atlas_yaml_attributes = aws_object.get_databag_attributes("global_config_data", "atlas_yaml_databag")
            memcache_var.set("global_atlas_yaml", atlas_yaml_attributes, 24*60*60)
            memcache_var.set("atlas_yaml", atlas_yaml_attributes, 2*60*60)
            if atlas_log_filepath != 'none': logging.info('Completed caching atlas yaml data...')
        
            
            #AWS instance data
            if atlas_log_filepath != 'none': logging.info('Started caching instance data from AWS...')
            aws_instances_details = aws_object.get_aws_instances_information()
            memcache_var.set("global_aws_cache",aws_instances_details, 24*60*60)
            memcache_var.set("aws_instances_details_cache", aws_instances_details, 60*60)
            if atlas_log_filepath != 'none': logging.info('Completed caching aws instance data...')
            

            #Cloudability module
            cloud_object = Cloudability()
            if atlas_log_filepath != 'none': logging.info('Started caching aws cloud costs from Cloudability...')
            cloud_costs = cloud_object.get_cloud_costs()
            memcache_var.set("global_cloudability_costs", cloud_costs, 24*60*60)
            memcache_var.set("cloud_costs", cloud_costs, 2*60*60)
            if atlas_log_filepath != 'none': logging.info('Completed caching aws cloud costs from Cloudability...')

            #Chef module
            chef_object = ChefHelper()
            if atlas_log_filepath != 'none': logging.info('Started caching node attributes from Chef...')
            chef_node_attributes = chef_object.get_node_attrs_from_chef()
            memcache_var.set("global_chef_node_attributes_cache", chef_node_attributes ,24*60*60)
            memcache_var.set("chef_node_attr_caches", chef_node_attributes, 2*60*60)
            if atlas_log_filepath != 'none': 
                logging.info('Completed caching node attributes from Chef...')
                logging.info('Started caching databag attributes from Chef...')

            
            databag =  ah_obj.get_atlas_configuration_data('global_config_data')['atlas_cache_variables']['databag']
            databag_item = ah_obj.get_atlas_configuration_data('global_config_data')['atlas_cache_variables']['databag_item']
            chef_databag_attributes = chef_object.get_databag_attribute_foritem(databag, databag_item)
            memcache_var.set("global_cpdeployment_databag_attrs", chef_databag_attributes, 24*60*60)
            memcache_var.set("cpdeployment_databag_attrs", chef_databag_attributes, 15*60)
            if atlas_log_filepath != 'none': logging.info('Completed caching databag attributes from Chef...')


            #Jenkins module
            jenkins_object = JenkinsActions()
            if atlas_log_filepath != 'none': logging.info('Started caching jenkins build user information...')
            jobname = ah_obj.get_atlas_configuration_data('global_config_data')['atlas_cache_variables']['jobname']
            build_userinfo_dict = jenkins_object.jenkins_build_userinfo(jobname)
            memcache_var.set('global_'+jobname+'_build_userinfo', build_userinfo_dict, 24*60*60)
            memcache_var.set(jobname+'_build_userinfo', build_userinfo_dict, 15*60)
            if atlas_log_filepath != 'none': 
                logging.info('Completed caching jenkins build user information...')
                logging.info('Started saving database attribute values...')
                logging.info('Creating new database entries based on atlas yaml changes...')


            #Database helper
            db_helperobj = DatabaseHelper()
            db_helperobj.save_and_create_atlas_data()
            if atlas_log_filepath != 'none': logging.info("Database changes completed...")
            
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            if atlas_log_filepath != 'none': 
                logging.info('Error in caching data...')
                logging.info('Atlas may not function due to caching errors...')
                logging.info('Exception in setlascache.py...')
                logging.info(exp_object)
                logging.info(str(exc_type)+" in line number "+ str(exc_tb.tb_lineno))
            else:
                print "Error in setatlas cache.py...Atlas caching failed!!!"
                #print exc_tb
                #print "%s in method %s in file %s at line number %d-->" %(exc_type, method,filename, exc_tb.tb_lineno)
                #print "Description: "+ str(exp_object)
        

        
