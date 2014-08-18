"""
This module has all the helper functions for atlas
"""
import json, yaml, ast
import sys, traceback, os
import memcache
import threading 
import logging
import datetime
from threading import Lock
import collections
from collections import defaultdict

class AtlasHelper:

    def __init__(self):
        self.output_value = ""
        self.atlas_config_json_content = self.convert_yaml_to_json_string(os.environ.get("ATLAS_CONFIG_FILEPATH"))
        self.memcache_server_location= json.loads(self.atlas_config_json_content)['global_config_data']['memcache_server_location']
        self.memcache_var = memcache.Client([self.memcache_server_location], debug=0)
    
    def get_atlas_configuration_data(self, module):
        """Get configuration data for a particular module from atlas configuration file."""
        if module == 'global_config_data':
            return self.atlas_configuration_data()[module]
        else:
            return self.atlas_configuration_data()['modules'][module]

    def atlas_configuration_data(self):
        atlas_config_dict = self.memcache_var.get('atlas_config_data')
        if not atlas_config_dict:
            atlas_config_dict = self.memcache_var.get('global_atlas_config_data')
            if atlas_config_dict is not None:
                self.memcache_var.set("atlas_config_dict", atlas_config_dict, 12*60*60)
            with threading.Lock():
                thread = threading.Thread(target=self.cache_atlas_config_data)
                thread.start()

        return atlas_config_dict

    def cache_atlas_config_data(self):
        atlas_config_filepath = os.environ.get("ATLAS_CONFIG_FILEPATH")
        atlas_config_dict = {}
        with open(atlas_config_filepath, 'r') as filepointer:
            atlas_config_dict = yaml.load(filepointer)
        self.memcache_var.set("global_atlas_config_data", atlas_config_dict , 24*60*60)
        self.memcache_var.set("atlas_config_data", atlas_config_dict, 12*60*60) 
        self.memcache_var.disconnect_all()


    def get_yaml_from_file(self, filepath):
        """Fetch yaml contents given file path."""
        try:
            yaml_file = open(filepath)
            yaml_documents = yaml.load_all(yaml_file)
            return yaml_documents
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.print_exception("atlas_helper_methods.py", "get_yaml_from_file()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def json_object_hook(self, unicode_data):
        """Convert each element of the json dictionary to string."""
        string_equivalent = {}
        try:
            for json_key, json_value in unicode_data.iteritems():
                if isinstance(json_key, unicode):
                    json_key = json_key.encode('utf-8') #convert unicode values to string
                if isinstance(json_value, unicode):
                    json_value = json_value.encode('utf-8')
                string_equivalent[json_key] = json_value   #construct a string dictionary
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.print_exception("atlas_helper_methods.py", "json_object_hook()", exp_object, exc_type, exc_obj, exc_tb)
        return string_equivalent  #return the json content with strings


    def get_json_from_file(self, filepath):
        """Write the data into a json file specified by the filepath."""
        with open(filepath,'r') as json_file:
            try:
                json_content = json.loads(json_file.read(), object_hook=self.json_object_hook)
                return json_content
            except Exception as exp_object:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.print_exception("atlas_helper_methods.py", "get_json_from_file()", exp_object, exc_type, exc_obj, exc_tb)

    def write_to_json(self, filepath, dump_data):
        """ Dump data into file as json."""
        with open(filepath, 'w') as filepointer:
                json_string = json.dumps(dump_data, filepointer, indent=4)
                filepointer.write(json_string)
        return


    def process_nested_dict(self, json_content, find_key):
        """Search recusively into a nested dictionary."""
        try:
            if type(json_content) == str:
                json_content = json.loads(json_content) #loads the string as json
            if type(json_content) is dict:     #if the argument is a dict recursively parse
                for jsonkey in json_content:
                    if isinstance(json_content[jsonkey],dict): #if the key is a dictionary
                        if str(jsonkey) == str(find_key):
                            self.output_value = json_content[jsonkey].keys(), json_content[jsonkey]
                            break
                        else:
                            self.process_nested_dict(json_content[jsonkey], find_key)
                    elif str(jsonkey) == str(find_key):

                        self.output_value = json_content[jsonkey]
            return self.output_value
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.print_exception("atlas_helper_methods.py", "process_nested_dict()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def get_nested_attribute_values(self, json_content, find_key):
        """Get nested attribute values."""
        try:
            self.output_value= ""
            return self.process_nested_dict(json_content, find_key)

        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.print_exception("atlas_helper_methods.py", "get_nested_attribute_values()", exp_object, exc_type, exc_obj, exc_tb)
            return ()

    def convert_yaml_to_json_string(self, yaml_path):
        """Convert yaml into json given the yaml file path."""
        json_string = ""
        try:
            documents=self.get_yaml_from_file(yaml_path)
            for docs in documents:
                json_document = json.dumps(docs, indent=4, sort_keys=True)
                json_string = json_string+json_document
            json_content = json_string
            return json_content
        except Exception as exp_object:
            print exp_object
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.print_exception("atlas_helper_methods.py", "convert_yaml_to_json_string()", exp_object, exc_type, exc_obj, exc_tb)
            return

    #defining getters
    def get_attributes(self, filepath, find_field):
        try:
            self.output_value = ""
            json_content = self.get_json_from_file(filepath)
            return self.get_nested_attribute_values(json_content, find_field)
        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.print_exception("atlas_helper_methods.py", "get_attributes()", exp_object, exc_type, exc_obj, exc_tb)
            return

    #get configuration data from atlas config file
    def get_atlas_config_data(self, module, findfield):
        """Get configuration data from atlas configuration file."""
        try:
            if module == 'global_config_data':
                return self.get_nested_attribute_values(self.atlas_config_json_content, findfield)
            else:
                module_json = self.get_nested_attribute_values(self.atlas_config_json_content, module)[1]
                return self.get_nested_attribute_values(module_json, findfield)

        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.print_exception("atlas_helper_methods.py", "get_atlas_config_data()", exp_object, exc_type, exc_obj, exc_tb)
            return

    def split_string(self, input_string, delimiters):
        """Split a string based on a list of delimiters."""
        delimiters = tuple(delimiters)
        string_list = [input_string,]
        for delimiter in delimiters:
            for index1, input_sub_string in enumerate(string_list):
                temp_var = input_sub_string.split(delimiter)
                string_list.pop(index1)
                for index2, input_sub_string in enumerate(temp_var):
                    string_list.insert(index1+index2, input_sub_string)
        return string_list

    
    def merge_dictionaries(self, dictionary1, dictionary2):
        """Merge the contents of two nested dictionaries."""
        for key in list(dictionary1.keys()+dictionary2.keys()):
            if key in dictionary1 and key in dictionary2:
                if type(dictionary1[key]) is list and type(dictionary2[key]) is list:
                    yield (key, self.merge_lists(dictionary1[key], dictionary2[key]))
                else:
                    if type(dictionary1[key]) is dict and type(dictionary2[key]) is dict:
                        result = self.merge_dictionaries(dictionary1[key], dictionary2[key])
                        if type(result) is list:
                            yield(key, result)
                        else:
                            yield (key, dict(result))
            elif key in dictionary1: yield (key, dictionary1[key])
            else: yield (key, dictionary2[key])

    def merge_lists(self, list1, list2):
        """Merge two lists."""
        final_list = []
        if list1 is None:
            final_list = list1
        elif list2 is None:
            final_list = list2
        else:
            final_list = list1
            if not set(list2).issubset(set(final_list)):
                final_list.extend(list2)
        return list(set(final_list))

    def create_nested_defaultdict(self):
        """Create nested default dictionary."""
        return collections.defaultdict(self.create_nested_defaultdict)
        
    def defaultdict_to_dict(self, nested_defaultdict):
        """Convert defaultdict to a regular python dictionary."""
        if isinstance(nested_defaultdict, collections.defaultdict):
            return {key:self.defaultdict_to_dict(value) for key,value in nested_defaultdict.iteritems()} 
        else:
            return nested_defaultdict

    def print_exception(self, filename, method, exp_object, exc_type, exc_obj, exc_tb):
        """Print exception to console."""
        log_file_name = self.get_atlas_configuration_data('global_config_data')['atlas_log_file']
        if log_file_name != 'none' or log_file_name is not None:
            message_string = ""
            atlas_log_file = "atlas-"+str(datetime.date.today())+".log"
            logging.basicConfig(filename=atlas_log_file, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
            logging.warning(exc_tb)
            if exc_type and method and filename and exc_tb:
                message_string = str(exc_type)+" in method "+method+" in file "+filename+" in line number "+ str(exc_tb.tb_lineno)
            if exp_object:
                logging.warning(message_string+" Description: "+ str(exp_object))
            return
        else:
            print exc_tb
            print "%s in method %s in file %s at line number %d-->" %(exc_type, method,filename, exc_tb.tb_lineno)
            print "Description: "+ str(exp_object)
