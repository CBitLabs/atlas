Atlas
=====

######Cloud Control Console - Version 1.0 


Description
-----------
**Atlas** provides a centralized console to manage instances on the AWS (amazon Web Services) cloud aided by the 
integration of various tools and their functionalities through simple and extensible API (Application Program Interface).

Installation Requirements
-------------------------

Listed below are the back end, front end and databse requirements for Atlas.

#####Operating System
  1. Linux (Developed and tested on Ubuntu 12.04 and above)

#####Backend
  1. Python
    * Version 2.7 or above
  2. Django 
    * Version 1.6 or above

#####Frontend
  1. Jquery 1.10 and above
  2. Jquery UI - 1.10.4
  3. Bootstrap 3
  4. Metro UI
  5. Flat UI
  6. Datatables - 1.10
  7. date.js
  8. sessvars 1.01
  9. mmenu

#####Database
  1. Postgres 9.3 (for Ubuntu)

#####Browser Support
  1. Google Chrome
  2. Firefox
  3. Safari


Modules
-------
Atlas currently supports four modules in addition to the base module which is the AWS module. Modules can be added further through simple and extensible API.  

#####Base Module

  * aws_module - base module
    * Required for atlas to function.
    * Provides information about all the instances identified by the region, vpc and subnet.

#####Other Modules
  * chef_module - Allows users to take/release ownership of any subnet or application.
  * cloudability_module - Instance, storage costs on a per instance, per subnet and EC2 basis.
  * jenkins_module - Display build information for specific jobs, trigger jenkins actions.
  * graphite_module - Display status from graphite server on a per subnet basis.

Configuration
-------------
**Atlas** is based on the cloud infrastructure of an organization in a yaml ([sample - atlas.yaml]( https://github.com/CBitLabs/knife-bs/blob/master/README.md#bs-atlasyaml-sample)) file which contains declaration of **organizations** with **environments**(production, stage, quality assurance, etc.), **profiles** for instances(master, slaves, etc.,) and **stacks**(combination of instance profiles). Instances and stacks can be deployed to **subnets** in a **vpc** belonging to a Amazon EC2 **regions**.


##Steps

The steps in setting up atlas are outlined below:

#####1-Package downloads

  1. Refer to installation requirements above.
  2. Download all the javascript and css requirements and place the folders and files into the **static** folder inside the **appv1** folder. Verify if all the files and all dependencies confirm to path specifications in **base.html** template in **templates** in **appv1** folder.

#####2-Create atlas configuration file
  1. Create a file in yaml format (atlas_config.yaml) with configuration parameters for each module.
  2. Attributes under 'global_config_data' are **Required**
  3. Environment group **all** is **required**. Others are optional.
  3. Under **modules** 'aws_module' is **required**. Other modules are **optional**
  4. Every module can have status, aggregates, columns, tabs and actions.
  5. Under actions, instance_actions, instance_group_actions, stack_actions and vpc_actions can be defined.
  6. To add or remove any module, include the required attributes under each module. All attributes other than the ones described in 4 & 5 can be included under "other". 

  
######Sample atlas_config.yaml
  This is a sample atlas_configuration_file. 

    global_config_data:
  
      memcache_server_location:
      atlas_log_file: 'none' 
    
      atlas_cache_variables:
        jobname: 'jenkins_job_name'
        databag: 'chef_databag'
        databag_item: 'chef_databag_item'
    
      atlas_yaml_databag:
        atlas:
          items:
            main:
              keys:
              - organizations
              - regions
              - stack
              - profile
          
      environment_groups:
      - all
      development:
      - development
      - integration-testing
      - aggregation
      quality_assurance:
      - quality_assurance
      - functional_testing
    
    modules:
  
      aws_module:
    
        status:
          count:
            icon_file: '/static/icons/count_icon.ico'
            position: right
          running:
            icon_file: '/static/icons/running_icon.ico'
            position: right
          stopped:
            icon_file: '/static/icons/stopped_icon.ico'
            position: right
          
        columns:
        - instance
        - instance_id
        - subnet
        - status
    
        tabs:
        - aws_information
        - aws_tags
    
        actions:
  
          instance_actions:
          - start_instance
          - stop_instance
          - terminate_instance
          - edit_tags

          instance_group_actions:
          - start_instances
          - stop_instances
          - terminate_instances
        
          stack_action:
          - sample_action_1
          - sample_action_2
        
          vpc_action:
          - sample_action_1
          - sample_action_2
        
        stack_attributes:
        - attribute1:
          stack:
          - all
          editable: false
        - attribute2:
          stack:
          - stack1
          - stack2
          editable: true
   
        aggregates:
        - count
        - running
        - stopped
  
        others:
          instances-regex:
      
            knowledgebase:
            - 'kb1\\d{2}'
            cluster:
            - 'ms\\d{3}'
            - 'rs\\d{3}'
            quality-assurance:
            - 'qa\\d{3}'
            
      cloudability_module:
      
        status:
          cost:
            icon_file: '/static/icons/cost_icon.ico'
            position: right
            
        aggregates:
        - cost
          
        columns:
        - instance_cost
        - storage_cost
          
        stack_attributes:
        - total_cost:
          stack:
          - all
          editable: false
          
        others:
          cloudability_base_url: 'https://app.cloudability.com/api/1'
          cloudability_cost_url: '/reporting/cost/run.json?'
        
  
#####3-Store infrastructure data on the chef server
  2. Store infrastructure data on the Chef server as a databag. (More flexibility and multiple file formats will be included in the next version)

#####4-Postgres setup
  1. Ensure postgres database is setup and functional
  2. Run "syncdb" to generate tables corresponding to Django models.

#####5-Add new site
  1. Log in as admin
  2. Add new site.

#####6-Google oauth
  1. Using the client key and secret set up the google oauth through the admin UI.
  2. Create admin or other user user accounts if needed.

#####7-Environment variables setup
  1. set all the required environment variables.
    * ATLAS_CONFIG_FILEPATH   - filepath for atlas configuration data (.yaml)
    * ATLAS_YAML_FILEPATH     - filepath for infrastructure data (.yaml)
    * APPLICATION_URL         - 'http://127.0.0.1:8000/'
    * POSTGRES_PASSWORD       - Postgres database password
    * POSTGRES_USERNAME       - Postgres database username
    * AWS_ACCESS_KEY_ID       - AWS access key ID.
    * AWS_SECRET_ACCESS_KEY   - AWS secret access key
    * CLOUDABILITY_AUTH_TOKEN - Cloudability API token
    * JENKINS_URL             - Jenkins build server url
    * JENKINS_USERNAME        - Jenkins build server username
    * JENKINS_PASSWORD        - Jenkins build server password
   
#####8-Set up cron jobs

1. Atlas has a two level cache. The long term cache is 24 hours. The short term depends on the requirements and can be specified in each module. Both the caches are updated whenever data on short term cache expires.

  *execute the setatlascache.py management command once every 24 hours.
    python manage.py setatlascache --options all
    
2. If chef_module is included, 
  *execute expireownership.py management command with expiry in days, hours or minutes.
    python manage.py expireownership.py --days 2

Logs
----
  Logging is provided at two levels.
    1. atlas_debug.log, the log file generated using Django log settings under settings.py
    2. Setting **atlas_log_file** attribute under **global_config_data** in the atlas_config.yaml configuration file.
        * If the filepath is set, a log file is generated every day.
        * If the filepath is set to 'none' then error logs are generated through Django log settings.

Usage
-----
Once all the above steps are completed the Atlas console will be up and operational. Users are **login** using their accounts or their gmail account. The UI is self explanatory and has tool tips on each icon for guidance.

License
-------

The MIT License (http://opensource.org/licenses/mit-license.php)







