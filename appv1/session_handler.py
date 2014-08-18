#function to save session variables
from appv1.models import UserProfile, UserEnvironmentSelections, UserRegion, UserConfigSelections
import ast, sys
from atlas_helper_methods import AtlasHelper
from aws_helper import AwsHelper

ah = AtlasHelper()

class SessionHandler:
    def __init__(self, request=None):
        pass

    def save_on_logout(self, request):
        up = UserProfile.objects.get(user__username=request.user.username)
        up.url = request.POST.get("url", "")
        up.save()

    def save_dash_session(self, request, env_status_dict):
        try:
            up = UserProfile.objects.get(user__username=request.user.username)
            if up and env_status_dict:
                user_profile_record = UserProfile.objects.filter(user__username=request.user.username)
                if user_profile_record and user_profile_record.count()==1:
                    for u_profile in user_profile_record:
                        config_record =  UserConfigSelections.objects.filter(abstractuser_id = up.id)
                        if config_record:
                            if env_status_dict['config_status']<> []:
                                config_record.update(status_selected = env_status_dict['config_status'])
                            if env_status_dict['env_status'] <> []:
                                config_record.update(envs_selected = env_status_dict['env_status'])
                        else:
                            config_record = UserConfigSelections(status_selected=env_status_dict['config_status'],
                                                                envs_selected = env_status_dict['env_status'],
                                                                abstractuser_id=u_profile.id);
                            config_record.save() 
                return
        except Exception as exp_object:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                ah.print_exception("session_handler.py", "save_dash_session", exp_object, exc_type, exc_obj, exc_tb)
                return

    def load_dash_session(self, request):
        awsobj = AwsHelper()
        env_status_dict = {}
        try:
            user_profile_record = UserProfile.objects.filter(user__username=request.user.username)
            if user_profile_record and user_profile_record.count()==1:
                for user_profile in user_profile_record:
                    user_config_selections = UserConfigSelections.objects.filter(abstractuser_id=user_profile.id)
                    if user_config_selections and user_config_selections.count()==1:
                        for user_configs in user_config_selections:
                            env_status_dict = {'config_selected': user_configs.status_selected,
                                'env_selected': user_configs.envs_selected }
            return env_status_dict
        except Exception as exp_object:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                ah.print_exception("session_handler.py", "load_dash_session", exp_object, exc_type, exc_obj, exc_tb)
                return



    def save_region_session(self, request, region_vpc_selected):
        try:
            up = UserProfile.objects.get(user__username=request.user.username)
            if up:
                    user_region_selections = UserRegion.objects.filter(user_id=up.id)
                    if user_region_selections and user_region_selections.count() == 1:
                        user_region_selections.update(region_selected = region_vpc_selected)
                    else:
                        user_selection = UserRegion(region_selected=region_vpc_selected, user=up)
                        user_selection.save()
                    return
        except Exception as exp_object:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                ah.print_exception("session_handler.py", "save_region_session", exp_object, exc_type, exc_obj, exc_tb)
                return

    def load_region_session(self, request):
        awsobj = AwsHelper()
        region_vpc_dict = {}
        region_list = awsobj.get_regions()
        for region in region_list:
            vpc_list = awsobj.get_vpc_in_region(region)
            region_vpc_dict[region] = vpc_list
        try:
            u_profile = UserProfile.objects.filter(user__username=request.user.username)
            if u_profile and u_profile.count()==1:
                for user_profile in u_profile:
                    user_region_selections = UserRegion.objects.filter(user_id=user_profile.id)
                    if user_region_selections and user_region_selections.count()==1:
                        for user_region_object in user_region_selections:
                            region_vpc_selected = user_region_object.region_selected
                            if region_vpc_selected == "{}" or region_vpc_selected is None:
                                return region_vpc_dict
                            else:
                                return ast.literal_eval(region_vpc_selected)
                    else:
                        return region_vpc_dict
            else:
                return region_vpc_dict

        except Exception as exp_object:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            ah.print_exception("session_handler.py", "load_region_session", exp_object, exc_type, exc_obj, exc_tb)
            return region_vpc_dict



    def save_env_session(self, request, environment, env_selection_dict):
        url, subnets, columns, tabs, applications, status = "", "", "", "", "", ""
        try:
            up = UserProfile.objects.get(user__username=request.user.username)
            app_url = os.environ.get("APPLICATION_URL")+"environment/"+environment+"/"
            if up and env_selection_dict:
                if env_selection_dict.has_key("url"):
                    url = env_selection_dict["url"]
                if env_selection_dict.has_key("selected_subnets"):
                    subnets = env_selection_dict["selected_subnets"]
                if env_selection_dict.has_key("selected_apps"):
                    applications = env_selection_dict["selected_apps"]
                if env_selection_dict.has_key("selected_columns"):
                    columns = env_selection_dict["selected_columns"]
                if env_selection_dict.has_key("selected_tabs"):
                    tabs = env_selection_dict["selected_tabs"]
                if env_selection_dict.has_key("config_status"):
                    status= env_selection_dict["config_status"]
                if url:
                    user_env_selections = UserEnvironmentSelections.objects.filter(abstractuser_id=up.id)
                    if user_env_selections and len(user_env_selections) >= 1:
                        for user_selection in user_env_selections:
                            if user_selection.app_url == app_url:
                                if len(subnets)>0 :
                                    user_selection.subnets_selected = subnets
                                    up.subnet_selections = subnets
                                if len(applications)>0:
                                    user_selection.apps_selected = applications
                                if len(columns)>0:
                                    user_selection.columns_selected = columns
                                if len(tabs)>0:
                                    user_selection.tabs_selected = tabs
                                if len(status)>0:
                                    user_selection.status_selected = status
                                user_selection.save()
                                up.save()
                    else:
                        user_selection =  UserEnvironmentSelections(app_url = url,
                                                            apps_selected=applications,
                                                            subnets_selected=subnets,
                                                            columns_selected=columns,
                                                            tabs_selected=tabs,
                                                            status_selected=status,
                                                            abstractuser=up)
                        user_selection.save()
                    return
        except Exception as exp_object:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                ah.print_exception("session_handler.py", "save_app_session", exp_object, exc_type, exc_obj, exc_tb)
                return

    def load_env_session(self, request, environment):
        env_selections_dict = {}
        try:
            app_url = os.environ.get("APPLICATION_URL")+"environment/"+environment+"/"
            up = UserProfile.objects.get(user__username=request.user.username)
            if not environment == 'uncategorized':
                env_selections_dict["selected_applications"] = ""
                env_selections_dict["selected_subnets"] = ""
            env_selections_dict["selected_columns"]=""
            env_selections_dict["selected_tabs"]=""
            env_selections_dict["selected_status"]=""
            if up:
                user_selections_list = UserEnvironmentSelections.objects.filter(abstractuser=up.id)
                if user_selections_list and len(user_selections_list) >= 1:
                    for user_selection in user_selections_list:
                        if user_selection.app_url == app_url:
                            if environment != "uncategorized":
                                env_selections_dict["selected_applications"] = user_selection.apps_selected
                                env_selections_dict["selected_subnets"]= user_selection.subnets_selected
                            env_selections_dict["selected_columns"]= user_selection.columns_selected
                            env_selections_dict["selected_tabs"]= user_selection.tabs_selected
                            env_selections_dict["selected_status"]= user_selection.status_selected
            return env_selections_dict

        except Exception as exp_object:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                ah.print_exception("session_handler.py", "load_env_session", exp_object, exc_type, exc_obj, exc_tb)
                return {}
