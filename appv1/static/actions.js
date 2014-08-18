/*
  actions.js 
  this file contains the functions called by the actions part.
 */


$(document).ready(function(){

    var tag_attributes = {}
    var attr_timer_dict = {}
    
    //check_action_display_status();
   
    $.each($(".app-div .stack-attribute-timer"), function(){
        var attribute = $(this).attr("for-attr");
        var identifier = $(this).attr("for-app-subnet").split(":");
        var start_time = new Date(attribute_values_string[identifier[0]][identifier[1]][identifier[2]][identifier[3]]['start_time'])
        display_ownership_timer("owner", identifier, $(this), start_time)
    });


    function check_action_display_status(){
        //to be completed for status on browser close and open
      
       $.each($(".vpc-status-display"), function(){
            var vpc = $(this).attr("for");
            vpc_action_status = localStorage.getItem("action_in_progress_"+vpc);
            vpc_action = localStorage.getItem("current_vpc_action_"+vpc);
            $(".vpc-action-label[for="+vpc+"]").append(vpc_action);
            if (vpc_action_status == 'true'){
                 $( "#vpc-status-progress-"+vpc).progressbar({
                value: false,
                });
                $("#vpc-status-display-"+vpc).show();
                $("#vpc-status-progress-"+vpc).height(15);
                $("#vpc-status-progress-"+vpc).show();
                $("#status-bar-minimize-"+vpc).show();
                $("#status-bar-close-"+vpc).show();
            }
            else{
                $("#vpc-status-display-"+vpc).hide();
                $("#status-bar-minimize-"+vpc).hide();
                $("#status-bar-close-"+vpc).hide();
            }
        });
    }
    

    /* 
    make action calls
    */

    function make_action_calls(url, json_data)
    {
        $.ajax({
            url : document.URL,
            type: "POST", 
            data : {
                actions_flag: 1,
                actions_data: JSON.stringify(json_data),
                csrfmiddlewaretoken: csrftoken
            },
            dataType : "text",
            success: function( status_in ){
                
                if ((status_in != null) || (status_in != undefined))
                {
                    on_instaction_success(status_in, json_data);
                }
            }
        });
        return false;
    }

/* 
query instance status on instance actions
*/

function query_instance_status(json_data)
{
    $.ajax({ 
            url: document.URL, 
            type:"POST", 
            data:{
                status_flag:1, 
                actions_data: JSON.stringify(json_data), 
                csrfmiddlewaretoken: csrftoken
            }, 
            dataType : "text",
            success: function(status_in)
            {
                on_instaction_success(status_in, json_data);
            } 
        });
    }


$("instance-stack-console").tooltip("show")

function instack_console_output(console_identifier, other_information, console_information, action_type, action_state)
{   
    var html_string = "<font face='fedra sans' size=4><b>Action Information</b></font>"
    html_string+=get_console_contents(action_type, console_identifier, console_information, other_information);
    html_string+="</div>"
    if ((action_state === 'action_initiated') || (action_state === 'action_in_progress'))
    {
        html_string+=["<div id='output-spinner'><br/><br/>",
                    "<center> <img id='loader-icon' src='/static/icons/action_status.gif'>",
                    "</img></center></div>"].join("\n")
    }
    if (action_type === 'vpc_action')
        {
            localStorage.setItem(console_identifier, html_string)
        }
        else
        {
            localStorage.setItem(console_identifier, html_string)
        }
}

function on_instaction_success(status_in, json_data)
{  
    var status = JSON.parse(status_in);
    var action_state=status["action_state"];
    if (json_data['action_type'] === "stack_action")
    {
        var action = status['action'];
        var editable = status['editable'];
        var other_info = "";
        var console_output =status['console_output'];
        var identifier = json_data["region"]+"-"+json_data["vpc"]+"-"+json_data["subnet"]+"-"+json_data["application"];
        var progress_id = "#"+identifier+"-progress-bar";
        if ((status["other_info"]!= null) || (status["other_info"] != undefined))
            other_info = status["other_info"];

        if (!(editable === 'true')){ 
            $("#"+identifier+"-stack-action-label").html("action: "+action);
            $("#"+identifier+"-stack-action-label").html("action: "+action).show();
        }
        if (action_state==="action_initiated") 
        {
            display_action_status(status['action_type'], action, identifier);
            display_time_status(identifier,"stack_action", "Action initiated...", get_time_elapsed(json_data["start_time"]));
            instack_console_output(identifier, other_info, console_output, status['action_type'], action_state);
            query_instance_status(json_data);
        }
        else if(action_state === "action_completed") 
        {   
            if (editable === 'true')
            {
                display_edited_attributes(status, action);
            }
            else
            {
                $(progress_id+" .ui-progressbar-value").css({'background-color':'#336600'});
                $(progress_id).progressbar( "option", "value", 100 );
                instack_console_output(identifier, other_info, console_output, json_data['action_type'], action_state);
                display_time_status(identifier, "stack_action","Action completed...", get_time_elapsed(json_data['start_time']))
                return (action_state);
            }
          
        }
        else if(action_state === "action_in_progress")
        {
            display_time_status(identifier, "stack_action", "Action in progress...", get_time_elapsed(json_data['start_time']))
            instack_console_output(identifier, other_info, console_output, json_data['action_type'], action_state);
            query_instance_status(json_data);
        }
        else
        {
            if (editable === 'true')
            {
                alert(status['action_output']);
                return;
            }
            $(progress_id+" .ui-progressbar-value").css({'background-color':'#BC4016'});
            $(progress_id).progressbar( "option", "value", 100 );
            instack_console_output(identifier, other_info, console_output, status['action_type'], action_state);
            display_time_status(identifier, "stack_action","Action failed...", get_time_elapsed(status['start_time']));
            return (action_state);
        }
    }
            
    else
    {
    for(var instance in status){  
        var action_state = status[instance]["action_state"];
        if (((action_state==="action_initiated") || (action_state==="action_completed")) && (status[instance]["editable"] === "true"))
        {
            generate_tags_foredit(status[instance]["editable_output"], status[instance]["action"], status);
            $("#output-edit-console").modal('show')
            return;
        }
        if ((action_state==="action_initiated") || (action_state === "action_in_progress"))
        {
            update_instance_status(instance, status[instance])
            query_instance_status(json_data)

        }
        else if(action_state === "action_completed")
        {
            update_instance_status(instance, status[instance])
            delete status[instance];
            if ((editable == 'true') && ((action == 'create_tag') || (action == 'delete_tag')))
            {
                display_instance_tags()
            }
        }   
        else
        {
            alert(status[instance]['error_message']);
        }//end if then else
    }//end of for loop
}//end of else
return;
}

function update_instance_status(instance,status){
    var instance_id = status["instance_id"];
    var instance_state = status["instance_state"];
    var action_state = status["action_state"]
    var action = status['action']
    var table_name = sessvars['actions_table'] 
    var header_row =  $("#"+table_name+" thead tr")[0];
    var oTable=$("#"+status["table_id"]).dataTable();

    var row_ids = sessvars['rows_selected']
    var instid_index = 0;
    var inststatus_index = 0;
    var console_information = {instance: {}}
    var console_identifier = ""

    if (environment_selected!= "uncategorized")
    {
        identifier = oTable.attr("for-app-subnet").split(":");
        console_identifier = identifier[0]+"-"+identifier[1]+"-"+identifier[2]+"-"+identifier[3]
    }
    else
    {
        console_identifier = oTable.attr("for-region").split("-")[0];
    }

     output_string = "<font face='fedra sans' size=3> Action:&nbsp"+action+"</h6>\n"+"Instance id: "+instance_id+"\n"+"Instance state: "+instance_state+"\n"+"Action state: "+action_state+"\n</font>";
    if ((status["console_output"] === undefined) || (status["console_output"] === "")){
        instack_console_output(console_identifier,{},output_string,status["action_type"], action_state);
    }
    else{
        instack_console_output(console_identifier ,status['other_info'], status["console_output"], status["action_type"], action_state);
    }
    if (action_state === "action_completed")
        var status_data = instance_state
    else
        var status_data = instance_state+ " <img class='instance_status' src='/static/icons/roller.gif'> </img>"
    

    var oTable1=$("#"+status["table_id"]).DataTable();
    var instid_index = oTable1.column('instance_id:name').index()
    var inststatus_index = oTable1.column('status:name').index()
    var instname_index = oTable1.column('instance:name').index()

    //update status
    var oTable=$("#"+status["table_id"]).dataTable();
    for (row=0;row<row_ids.length; row++){
        var data_row = oTable.fnGetData(row_ids[row]);
        if (data_row[instid_index] === instance_id){
            oTable.fnUpdate(status_data, row_ids[row], inststatus_index);
            oTable.fnDisplayRow(oTable.fnGetNodes()[row_ids[row]]);
            return;
        }
    }
}

function get_subnets(application)
{
    var subnet_list=[]
    for (var subnet in not_present_dict){
        var application_list = not_present_dict[subnet]
        if (application_list.indexOf(application) != -1)
            subnet_list.push(subnet);   
    }
    return subnet_list;
}

function get_region(vpc)
  {
        for (var region in region_vpc_dict){
            var vpc_list = region_vpc_dict[region];
            if (vpc_list.indexOf(vpc) != -1){
                return region;
            }
        }
  }

    //actions-javascript code
    $(".instack-action-icon").add($(".uncat-action-icon")).click(function(event){

        if (environment_selected != "uncategorized"){    
            app_name = $(this).attr("for-app-subnet");
        }
        else{
            app_name = $(this).attr("for-region")+"-uncat";
        }
        var table_name = "#"+app_name+"-table"
        var checkbox_selector = $("#"+app_name+"-table"+" tr td input:checked");
        var checkbox_count = 0;
        
        //initialize the dropdown list to be empty

        $("#"+app_name+"-action-menu").text("");
        $.each(checkbox_selector, function(){
            checkbox_count++;
        });
        if (((checkbox_count == ($(table_name+" tr").length)-1) && $("#"+app_name+"-table").find(".header-checkbox").is(":checked")) || (checkbox_count == 0))
        {
            $("#"+app_name+"-action-menu").append("<font size=3>Stack Actions</font>");
            $("#"+app_name+"-action-menu").append("<li class='divider'></li>");
            for(count=0; count<stack_actions.length; count++)
            {   
                $("#"+app_name+"-action-menu").append("<li>"+stack_actions[count]+"</li>");
                $("#"+app_name+"-action-menu").append("<li class='divider'></li>");
            }
        }
        else if ((checkbox_count == 1) && (!($("#"+app_name+"-table").find(".header-checkbox").is(":checked"))))
        {
            $("#"+app_name+"-action-menu").append("<font size=3>Instance Actions</font>");
            $("#"+app_name+"-action-menu").append("<li class='divider'></li>");
            for(count=0; count<instance_actions.length; count++)
            {
                $("#"+app_name+"-action-menu").append("<li>"+instance_actions[count]+"</li>");
                $("#"+app_name+"-action-menu").append("<li class='divider'></li>");
            }
        }
        else if ((checkbox_count > 1) || (checkbox_count < $(table_name+" tr").length)-2)
        {
            $("#"+app_name+"-action-menu").append("<font size=3 color='DarkBlue'>Group Actions</font>");
            $("#"+app_name+"-action-menu").append("<li class='divider'></li>");
            for(count=0; count<group_actions.length-1; count++)
            {
                $("#"+app_name+"-action-menu").append("<li>"+group_actions[count]+"</li>");
                $("#"+app_name+"-action-menu").append("<li class='divider'></li>");
            }
        }
    
        $("#" +app_name+"-action-menu").slideDown();
        event.stopPropagation();
    });


    $(".header-checkbox").change(function(){

        var application = $(this).attr("for-app")
        var table_name= $(this).parents("table").attr("id");
        var selector = "#"+table_name+" tbody tr td input";
        var oTable = $("#"+table_name).dataTable();
        $(selector).prop("checked", this.checked);
    });

    function get_selected_rows(table_name, app_name)
    {
       
        var oTable1 = $("#"+table_name).DataTable()
        
        var selected_rows = new Array();
        var row_count = 0;
        var headers = new Array();
        var header_row =  $("#"+table_name+" thead tr")[0]; //fetch the first row of the table which is the header
        sessvars['actions_table'] = table_name
        sessvars['rows_selected'] = new Array()
        status_array = new Array()
        var instid_index = 0;
        var inststatus_index = 0;
        var instname_index = 0;
        var instance_details_dict = new Object();
        var status_details_dict = new Object();
        var vpc_subnet_app = $("#"+app_name+"-div").find($(".vpc-subnet-app-identifier")).text().trim().split(":");
        var subnet_list = get_subnets(app_name);
        var instid_index = oTable1.column('instance_id:name').index()
        var inststatus_index = oTable1.column('status:name').index()
        //var instname_index = oTable1.column('instance:name').index()
        //get the data for each row
        instance_details_dict['instances'] = {}
        status_details_dict['instances'] = {}
        var table_rows = oTable1.rows()[0];
        for (var rowindex=0; rowindex<table_rows.length; rowindex++){ 
            var rowdata = oTable1.row(rowindex).data()
            instance_id = rowdata[instid_index]
            checkbox_id = rowdata[instid_index]+'-checkbox';
            if ($("#"+checkbox_id).is(":checked"))
            {
                instance_details_dict['instances'][instance_id] = new Object();
                if (environment_selected === 'uncategorized')
                { 
                    instance_details_dict['instances'][instance_id]['region'] = vpc_subnet_app[0];
                    instance_details_dict['instances'][instance_id]['vpc'] = "none";
                    instance_details_dict['instances'][instance_id]['subnet'] = "none";
                    instance_details_dict['instances'][instance_id]['stack'] = "none";
                }
                else
                {
                    instance_details_dict['instances'][instance_id]['region'] = get_region(vpc_subnet_app[0]);
                    instance_details_dict['instances'][instance_id]['vpc'] = vpc_subnet_app[0];
                    instance_details_dict['instances'][instance_id]['subnet'] = vpc_subnet_app[1];
                    instance_details_dict['instances'][instance_id]['stack'] = vpc_subnet_app[2];
                    insta
                }

                instance_details_dict['instances'][instance_id]['instance']= rowdata[1];
                instance_details_dict['instances'][instance_id]['instance_id'] = rowdata[instid_index];
                instance_details_dict['instances'][instance_id]['status'] = rowdata[inststatus_index];
                status_details_dict['instances'][instance_id] = new Object();
                status_details_dict['instances'][instance_id]['status'] = rowdata[inststatus_index]
                sessvars['rows_selected'].push(rowindex);
                row_count++;
            }
        }
        return [row_count, instance_details_dict, status_details_dict]
    }

    function find_module(action)
    {
        var action_module = "";
        for (var module in module_actions_dict)
            {
                for (var action_type in module_actions_dict[module])
                {
                    var module_actions = module_actions_dict[module][action_type];
                    for (var index=0; index< module_actions.length; index++)
                    {
                        if (action === module_actions[index])
                        {
                            action_module = module;
                        }
                    }
                }
            }
        
        return action_module
    }

/* actions performed when any instance, instance group or stack actions is selected */

    $(".action_menu").on("mouseleave", function(){
        $(this).dropdown("hide");
    });

    $(".action-menu").on('click', "li", function(event){    
            event.preventDefault()
            var identifier="";
            if (environment_selected != "uncategorized")
                identifier = $(this).closest("ul").attr("for-app-subnet").split(":");
            else
                identifier = ($(this).closest("ul").attr("for-region")+"-uncat").split("-");
            var action = $(this).text().trim();
            var table_name = app_name+"-table";
            var action_type = "";
            var instance_details = get_selected_rows(table_name, app_name);
            var row_count = instance_details[0];
            var action_parameters=""
            $(app_name+"action-menu").dropdown("toggle");
            module = find_module(action);
            if ((row_count == 0) || (row_count == ($("#"+table_name+" tr").length)-1))
            { 
                action_type = "stack_action"
                html_string = parameter_input_form(action_type, action, stack_action_parameters);
                request_parameter_input(identifier[0], identifier[1], identifier[2], identifier[3], action_type, action,html_string);
                var label_id = identifier[0]+"-"+identifier[1]+"-"+identifier[2]+"-"+identifier[3]
                $("#"+label_id+"-stack-action-label").html("action: "+action);
                $("#"+label_id+"-stack-action-label").html("action: "+action).show();
                display_time_status(label_id,"stack_action", "Action initiated...", get_time_elapsed(Date.now()));
                return false;
            }
            else if(row_count == 1)
            {
                action_type = "instance_action";

            }
            else if ((row_count > 1) || (row_count < $("#"+table_name+" tr").length)-2)
            {
                action_type = "instance_group_action";
            }
                    
            var instance_details_dict = {
                                            'instance_count': instance_details[0], 
                                            'instance_details_dict': instance_details[1], 
                                            'module':module, 
                                            'action': action, 
                                            'flag': "perform_action", 
                                            'action_type': action_type, 
                                            'status_dict': instance_details[2],
                                            'start_time': Date.now(),
                                            'parameters': action_parameters, 
                                            'table_id': table_name, 
                                            'for_stack': app_name,
                                            'region' : identifier[0],
                                            'vpc': identifier[1],
                                            'subnet': identifier[2],
                                            'application': identifier[3]
                                        }
            //this step is to make sure the actions for tags edit have correct parameters.
            if ((action === "create_tag") || (action === "delete_tag")|| (action==="edit_tags"))
                sessvars.tag_action_data = instance_details_dict;
        
            action_response = make_action_calls(document.URL, instance_details_dict);
        return false;
    });


    

$("#close-actions-modal").click(function(event){
    return false;
});

  
// javascript-jquery functions for vpc actions

$(".vpc-action-icon").click(function(event){
        
        event.preventDefault();
        var selector = "#"+"vpc-action-menu-"+$(this).attr("for");
        $(selector).slideDown();
        return false;
    });

$(".vpc-actions-modal").on("hide", function(event){
    event.preventDefault();
    return false;
});

/*
code block for console output display
*/

function show_console_output(console_object, html_string)
{
    console_object.dialog({
            height: 800,
            width: 800,
            title: "Console output",
            modal: true,
            dragabble: true,
            resizeable: true,
            autoOpen: true,
            
            open: function(){
            var close_icon= $('.ui-dialog-titlebar-close');
            close_icon.append('<span class="ui-button-icon-primary ui-icon ui-icon-closethick"></span><span class="ui-button-text">close</span>');
            }
        });
    $("#output-spinner").show(); 
    console_object.html(html_string);
    console_object.show("Slide", 1000);
}


/*
open a new window to display the page when hyperlinks from action outputs are clicked on.
*/
$(".action_info_links").on("click", function(){
    window.open($(this).attr('href'), '_blank');
});
/* assemble all output information */
function get_console_contents(action_type, action_source, console_output, other_information)
{
    var results="";
    var html_string = "";
    var information = "";
    html_string+="<div style='float:left;width:100%;border:1px; border-style:grooved; border-color:DarkGray; background:#D9D9DC'>"
    html_string+="<table>"
    html_string+="<thead><tr>Action Information</tr></thead><tbody>"
    for (var info in other_information){
         information=other_information[info]  
        if (typeof(other_information[info])=="string"){
            if ((other_information[info].indexOf("http://") == 0) || (other_information[info].indexOf("https://")== 0)){
                information = "<a class=action_info_links href='"+other_information[info]+"'>"+other_information[info]+"</a>"
            }
            else{
                information = other_information[info]
            }
        }
        else{
            information=other_information[info]
        }
       
        html_string+="<tr><td>"+info+": </td><td><font face='fedra sans' size=3>"+information+"</font></td></tr>",
                      "</font>"
    }
    html_string+="</tbody></table></div><br/><br/><br/>";
    if ((console_output != undefined) || (console_output != null))
    {
        results = console_output.split("\n");
        html_string+="<br/><div style='float:left; width:100%;border:1px; border-style:inset; border-color:DarkGray; background:#D9D9DC'>"
        html_string+="<font face='fedra sans' size=4><b> Console Output </b></font>"
        html_string+="<font face='fedra sans' size=3><br/>"

        $.each(results, function(index, element){
            html_string+=element;
            html_string+="<br/>";
        });
        html_string+="</font></div>"
    }
    return html_string
}

/* call function to display instance stack action console output */
$(".instance-stack-console").click(function(event){
    var selector = $(this).attr("for");
    show_console_output($("#stack-console-output-"+selector), localStorage.getItem(selector));
});

/* call function to display vpc action console output */
$(".vpc-action-output").click(function(event){
    var selector=$(this).attr("for");
    show_console_output($("#vpc-console-output-"+selector), localStorage.getItem(selector));
});

/* end of status display */
$(".status-bar-close").click(function(){
    var selector = $(this).attr("for");
    $("#vpc-status-display-"+selector).hide();
     $("#vpc-status-table-"+selector).hide();
    $("#status-bar-minimize-"+selector).hide();
    $("#status-bar-close-"+selector).hide();

    var vpc_action_status_id = "action_in_progress_"+selector
    localStorage.setItem(vpc_action_status_id, "false");
});

$(".status-bar-minimize").click(function(){
    var selector = $(this).attr("for");
    $("#vpc-status-table-"+selector).toggle();
});


/* get action parameters from the user input form */
function get_parameter_values(region, vpc, subnet, application, action_type, action)
{
    var action_parameters = new Object();
    var selector = "";
    if (action_type === "vpc_action")
    {
        selector = vpc;
    }
    else
    {
        selector = application;
    }
    action_parameters['parameters'] = {};
    $("#action-parameters-div input").each(function(){
        var input_text = $(this).val();
        var parameter = $(this).attr("for-para");
        action_parameters['parameters'][parameter] = input_text;
    });

    $("#action-parameters-div select option:selected").each(function(){
        var option_selected = $(this ).text();
        var parameter = $(this).parent().attr("for-para");
        action_parameters['parameters'][parameter] = option_selected;
    });
    action_parameters['action'] = action;
    action_parameters['action_type'] = action_type;
    action_parameters['module'] = find_module(action);
    action_parameters['region'] = region;
    action_parameters['vpc'] = vpc;
    action_parameters['subnet'] = subnet;
    action_parameters['application'] = application;
    return action_parameters
}

/* display input form for action parameters */
function parameter_input_form(action_type, selected_action, parameters_dict)
{
    var html_string=["<h5>Parameters</h5><hr>",
                    "<label id='category-label'> </label>",
                    "<input type='text' id='category-text'/><hr>"].join("\n");
        
        for (var action in parameters_dict)
        {   
            if (action === selected_action)
            {   
                for (var parameter in parameters_dict[action])
                {  
                    var parameter_type = parameters_dict[action][parameter][0];
                    var parameters_list = parameters_dict[action][parameter][1];
                    
                    if (parameter_type === 'text')
                    {   
                        
                        html_string+=[parameter+" :",
                                        "<input type='text' class='actions-paratext'",
                                                 "for-act='"+action+"' for-para='"+parameter+"'/><hr>",].join("\n");
                    }
                    else if (parameter_type === 'list')
                    {   
                        
                            if (parameters_list.length>0)
                            {
                                html_string+=[parameter+" :",
                                        "<select class='action-paralist' for-act='"+action+"'",
                                        "for-para='"+parameter+"'>"].join("\n");
                                for (var index=0; index<parameters_list.length; index++)    
                                {
                                    html_string+=["<option><font size=3 color=DarkGrey>"+parameters_list[index]+"</font></option>"].join("\n");
                                }  
                                html_string+=["</select><hr>"].join("\n"); 
                            }
                            
                    }   
                }
            }
        }
        
        return html_string
}

function request_parameter_input(region, vpc, subnet, application, action_type, action, html_string)
{   
    var selector = ""
    var progress_selector=""

    if (action_type === "vpc_action")
    {
        selector = vpc;
        progress_selector = vpc;
    }
    else if ((action_type === "stack_action") || 
            (action_type === "instance_action") || 
            (action_type === "instance_group_action"))
    {
        if (environment_selected === "uncategorized")
        {
            selector = region;
            progress_selector = region;
        }
        else
        {   
            selector = subnet+":"+application;
            progress_selector=region+"-"+vpc+"-"+subnet+"-"+application;
        }
    }
    $("#action-parameters-div").dialog({
             height: 600,
             width: 400,
             modal: true,
             dragabble: true,
             resizable: true,
             title: action,
            'buttons' : {
                'ok' :{
                    text: "Ok",
                    click: function(){
                        action_parameters = get_parameter_values(region, vpc, subnet, application, action_type, action);
                        $(this).dialog('close');
                        if (action_type==="vpc_action")
                        {
                            var status_dict = {'action_type' : action_type, 
                                                'action_status': 'action_initiated', 
                                                'region': region, 
                                                'vpc': vpc
                                                }
                                                
                            
                            action_parameters['start_time'] = Date.now()
                            display_action_status("stack_action", action, progress_selector);
                            display_time_status(vpc,"vpc_action","Action initiated...", get_time_elapsed(Date.now()));
                            make_vpc_action_calls(document.URL, action_parameters);
                        }
                        else if (action_type==="stack_action")
                        {
                            var status_dict = {'action_type' : action_type, 
                                                'action_status': 'action_initiated',
                                                'region': region,
                                                'vpc': vpc,
                                                'subnet' : subnet,
                                                'application': application
                                                }
                            identifier = region+"-"+vpc+"-"+"-"+subnet+"-"+application
                            display_action_status("stack_action", action, progress_selector);
                            action_parameters["start_time"] = Date.now();
                            display_time_status(identifier, "stack_action","Action initiated...", get_time_elapsed(Date.now()));
                            make_action_calls(document.URL, action_parameters);

                        }
                        else if (action_type==="instance_action")
                        {
                            make_action_calls(document_URL, action_parameters);
                        }
                    },
                },
                'cancel' : {
                    text: "Cancel",
                    click: function(){
                        $(".stack-status-label").hide();
                        $(".vpc-status-label").hide();
                        $(".stack-action-label").hide();
                        $(".vpc-action-label").hide();
                        $(this).dialog('close');

                    },
                },  
            },
            open: function(){
            var close_icon= $('.ui-dialog-titlebar-close');
            close_icon.append('<span class="ui-button-icon-primary ui-icon ui-icon-closethick"></span><span class="ui-button-text">close</span>');
        },
        });
    $("#action-parameters-div").html(html_string);
    if (action_type === "vpc_action")
    {
        
        $("#action-parameters-div").find("#category-label").text("vpc:");
        $("#action-parameters-div").find("#category-text").val(selector)
    }
    else if ((action_type === "stack_action") || 
            (action_type === "instance_action") || 
            (action_type === "instance_group_action"))
    {
        
        $("#action-parameters-div").find("#category-label").text("stack:");
        $("#action-parameters-div").find("#category-text").val(selector);
    }
    $("#action-parameters-div").show();   
}


    $(".vpc-action-menu").on("click", "li", function(event){

        event.preventDefault();
        var action = $(this).text().trim();
        var action_type = "vpc_action"
        var identifier = $(this).closest("ul").attr("for").split(":")
        html_string = parameter_input_form(action_type, action, vpc_action_parameters);
        request_parameter_input("", identifier[0], "", "", action_type, action, html_string)
        return false;
    });




 /* make vpc calls for actions */
    function make_vpc_action_calls(url, json_data)
    {   
        var action = json_data['action'];
        var vpc = json_data['vpc'];
        localStorage.setItem("action_in_progress_"+vpc, "true")
        localStorage.setItem("current_vpc_action_"+vpc, action)
        $("#vpc-status-display-"+vpc).show();
        $("#vpc-status-table-"+vpc).show();
        $("#vpc-status-table-"+vpc).css("width", $(".quadro-full").css("width"));
        $("#vpc-action-label-"+vpc).html("action: " +action);
        display_action_status("vpc_action", action, vpc);
        display_time_status(vpc, "vpc_action", "Action initiated...",get_time_elapsed(json_data['start_time']));
        
        $.ajax({
            url : document.URL,
            type: "POST",
            data : {
                actions_flag: 1,
                actions_data: JSON.stringify(json_data),
                csrfmiddlewaretoken: csrftoken
            },
            dataType : "text",
            success: function(status_in)
            {
                
                var status = JSON.parse(status_in)
                var vpc = json_data["vpc"]
                var action_status = status['action_state']
                var selector = "#vpc-status-progress-"+json_data["vpc"]
                if (action_status == 'action_failed')
                {
                    $(selector+" .ui-progressbar-value").css({'background-color':'#BC4016'});
                    $(selector).progressbar( "option", "value", 100 );
                    display_time_status(vpc, "vpc_action", "Action failed....", get_time_elapsed(json_data["start_time"]));
                    instack_console_output(vpc, status['other_info'], status['console_output'], json_data['action_type'], action_status);
                    return
                }
                else if (action_status == 'action_initiated')
                {
                    $(selector+" .ui-progressbar-value").css({'background-color':'#66C266'});
                    instack_console_output(vpc, status['other_info'], status['console_output'], json_data['action_type'], action_status);
                    on_vpcaction_success(status, json_data);
                }
                
            }   
        });
    return false;
    }
  

    function get_time_elapsed(start_time)
    {   
        var final_seconds=0;
        var final_minutes =0;
        var hours=0;
        var minutes=0;
        var current_time = Date.now();
        var time_difference = current_time - start_time; // this is a time in milliseconds
        var seconds = Math.floor(time_difference/1000);
        if (seconds >= 60)
        {
            minutes=Math.floor(seconds/60)
            seconds=seconds%60;
        }
        if (minutes >= 60)
        {
            hours=Math.floor(minutes/60);
            minutes = minutes%60;   
        }
        var timer = hours.toString()+"h : "+minutes.toString()+"m : "+seconds.toString()+"s";
        return timer
    }


    function on_vpcaction_success(status, json_data)
    {   
        
        var action_status = status['action_state'];
        var vpc = json_data["vpc"]
        var selector = "#vpc-status-progress-"+vpc;
        if (action_status === 'action_completed')
        {
            display_time_status(vpc, "vpc_action","Action completed!!!", get_time_elapsed(json_data["start_time"]))
            $(selector).progressbar( "option", "value", 100 );
            instack_console_output(vpc, status['other_info'], status['console_output'], json_data['action_type'], action_status);
        }
        else if (action_status === 'action_failed')
        {
            display_time_status(vpc, "vpc_action","Action failed!!!", get_time_elapsed(json_data["start_time"]))
            $(selector+" .ui-progressbar-value").css({'background-color':'#BC4016'});
            $(selector).progressbar( "option", "value", 100 );
            instack_console_output(vpc, status['other_info'], status['console_output'], json_data['action_type'], action_status);
        }
        else
        {
            display_time_status(vpc, "vpc_action","Action in progress.....", get_time_elapsed(json_data["start_time"]))
            $(selector+" .ui-progressbar-value").css({'background-color':'#66C266'});
            instack_console_output(vpc, status['other_info'], status['console_output'], json_data['action_type'], action_status);
            query_vpc_action_status(json_data);
        }
        return
    }


    function query_vpc_action_status(json_data)
    {
        $.ajax({
            url : document.URL,
            type: "POST",
            data : {
                status_flag: 1,
                actions_data: JSON.stringify(json_data),
                csrfmiddlewaretoken: csrftoken
            },
            dataType : "text",
            success: function( status_in )
            {
                var status = JSON.parse(status_in)
                var action_status = status['action_status']
                on_vpcaction_success(status, json_data);
            }
        });
        return false;
    }

    /* display action status */
    function display_action_status(action_type, action, selector)
    {   
        
        if (action_type=="vpc_action")
        {   
            $( "#vpc-status-progress-"+selector ).progressbar({
                value: false,
            });
            $(selector+" .ui-progressbar-value").css({'background-color':'#66C266'});
            $("#vpc-status-display-"+selector).show();
            $("#vpc-status-table-"+selector).show();
            $("#vpc-status-progress-"+selector).height(15);
            $("#vpc-status-progress-"+selector).show();
            $("#status-bar-minimize-"+selector).show();
            $("#status-bar-close-"+selector).show();
        }
        if (action_type == "stack_action")
        {
            var progress_bar="#"+selector+"-progress-bar"
            $(progress_bar).progressbar({
                value:false,
            });
            $(progress_bar).show();
            $(progress_bar).height(12);
            $(progress_bar).css("width:50px");
            $("#"+selector+"-status-close").show();
            $("#"+selector+"-status-minimize").show();
        }
    }


function display_time_status(identifier, action_type, status_text, time_elapsed)
    {   
        var label_name="";
        if (action_type==="vpc_action")
        {
            label_name = "#vpc-status-"+identifier;
        }
        else if (action_type==="stack_action")
        {
            label_name = "#"+identifier+"-stack-status";
        }
        $(label_name).text(status_text+ "  "+time_elapsed);
        $(label_name).show();
        return 
    }


    
    function tag_attributes_edit_html(tag_dict)
    {   
        return display_instance_tags(tag_dict);
    }

    function generate_tags_foredit(tag_dict, action)
    {
        html_string = tag_attributes_edit_html(tag_dict);
            $(".tag-list").html(html_string);
            $("#tag-create-button").show();
            $("#tag-delete-button").show();
            $("#tag-ok-button").hide();
    }

    $("#tag-create-button").click(function()
    {
        sessionStorage.setItem('tag_action', 'create_tag')
        var html_string = $(".tag-list").html();
        $("#awstags-table").append("<tr><td></td><td><input type='text' id='tag-text'/></td><td><input id='tag-value' type='text'/></td></tr>");
        $("#tag-create-button").hide();
        $("#tag-delete-button").hide();
        $("#tag-edit-button").hide();
        $("#tag-ok-button").show();
        
       

    });
    
    
    $("#tag-delete-button").click(function()
    {
        var json_data = sessvars["tag_action_data"]
        sessionStorage.setItem('tag_action', 'delete_tag')
        $(".awstag-checkbox").show()
        $("#tag-create-button").hide();
        $("#tag-delete-button").hide();
        $("#tag-edit-button").hide();
        $("#tag-ok-button").show();
    
    });
    $("#tag-ok-button").click(function()
    {   
        var json_data=sessvars["tag_action_data"]
        $("#tag-ok-button").hide();
        $("#tag-create-button").show();
        $("tag-edit-button").show();
        $("#tag-delete-button").show();
     
        if (sessionStorage.tag_action == "create_tag")
        {
            var tag_dict = {}

            tag_dict[$("#tag-text").val()] = $("#tag-value").val();
            json_data['parameters'] = tag_dict;
            json_data['edit_flag'] = 1;
            json_data['action'] = "create_tag";
            make_action_calls(document.URL, json_data);

        }
        else if (sessionStorage.tag_action == 'delete_tag')
        {

            var tag_dict = {}
            $("#awstags-table tr").each(function(e)
            {       json_data['parameters'] = {}
                    var tag_checkbox = $(this).find('.awstag-checkbox');
                    if (tag_checkbox.is(":checked"))
                    {
                        var tag = $(this).find(".tag-text").val();
                        var value = $(this).find(".tag-value").val();
                        tag_dict[tag]=value;
                    }
            });
            json_data["parameters"] = tag_dict;
            $(".awstag-checkbox").hide();
            json_data['edit_flag'] = 1;
            json_data['action'] = 'delete_tag'
            make_action_calls(document.URL, json_data)
        }
        

    });

    function display_instance_tags(tag_dict){

        var html_string="<table id='awstags-table' cellspacing='3' cellpadding='3' style='background-color:DarkGray'>"+
                        "<tr><th> </th><th align='center'>Tag</th><th align='center'>Columns</th></tr>";
                for (var tag in tag_dict)
                {

                    html_string+= ["<tr><td width=2%><input class='awstag-checkbox' type=checkbox for='"+tag+"' style='display:none'/></td>",
                            "<td width=20%><input class='tag-text' type=text value='"+tag+"'/></td>",
                            "<td width=50%><input class='tag-value' type=text value='"+tag_dict[tag]+"'/></td>",
                            "</tr></table"].join("\n")
                }
            
        return html_string
    }

   
    $(".stack-status-close").add($(".uncat-status-close")).click(function(){
        var selector = ""
        if (environment_selected === "uncategorized")
        {
            selector = $(this).attr("for-region")
        }
        else
        {
            selector = $(this).attr("for-app-subnet")
        }
        var progress_id = "#"+selector+"-progress-bar"
        $("#"+selector+"-progress-bar").hide();
        $("#"+selector+"-stack-status").hide();
        $("#"+selector+"-status-minimize").hide();
        $("#"+selector+"-stack-action-label").hide();
        $(this).hide();
    });

    $(".stack-status-minimize").add($(".uncat-status-minimize")).click(function(){
        var selector = ""
        if (environment_selected === "uncategorized")
        {
            selector = $(this).attr("for-region")
        }
        else
        {
            selector = $(this).attr("for-app-subnet")
        }
            $("#"+selector+"-progress-bar").toggle();
            $("#"+selector+"-stack-status").toggle();
            $("#"+selector+"-stack-status-label").toggle();
            $("#"+selector+"-stack-action-label").toggle();
    });




/*
stack attributes
*/
$(".app-div .stack-attribute").click(function(){
    var identifier = $(this).attr("for-app-subnet");
    var attribute = $(this).text().trim();
    var attribute_value = $(this).parent("div").find(".stack-attribute-value").text().trim();
    var attribute_editability = $(this).parent("div").find(".stack-attribute-editable").val()
    if (attribute_editability === "False"){
        alert("Attribute cannot be edited !!!")
        return;
    }
    else{
        var html_string="<table id='stackattribute-table' cellspacing='3' cellpadding='3' style='margin:0; padding:0; width:100%; height:100%; background-color: DarkGray'>"+
                            "<tr><th align='center'><font font-family='fedra sans' size=3 color='white'> Stack&nbsp;:</font></th><th align='center'>"+identifier+"</th></tr>";
        html_string+= ["<td width=20%><label class='attr-text' style='color:white'>"+attribute+"</label></td>",
                        "<td width=50%><input class='attr-value' size='"+attribute_value.length+"' disabled type=text value='"+attribute_value+"'/></td>",
                        "</tr>"].join("\n");
        html_string+="</table>"
        $("#stack-attribute-dialog").dialog({
                height: 250,
                width: 600,
                title: "Edit stack attributes",
                modal: true,
                dragabble: true,
                resizeable: true,
                'buttons' : {
                                                
                    'edit' :{    
                        text: "Edit",
                        click: function(){
                        $(".attr-value").prop("disabled", false);
                        $(".attr-value").focus();
                        }
                    },
                    'ok' :{
                        text: "Ok",
                        click: function(){
                            attribute = $(".attr-text").text();
                            attribute_value = $(".attr-value").val();
                            edit_stack_attributes("edit_attributes", identifier, attribute, attribute_value)
                            $(this).dialog('close');
                            }
                        },

                    'acquire':{
                        text: "Acquire ownership",
                        click: function(){
                                edit_stack_attributes("acquire_ownership", identifier, attribute, attribute_value)
                                $(this).dialog('close');
                                 var attribute_timer = $("div[for-attr='start_time'][for-app-subnet='"+identifier+"']");
                                 display_ownership_timer("owner", identifier, attribute_timer, Date.now());
                                attribute_timer.add();
                            }   
                        },
                    'release':{
                        text: "Release ownership",
                        click: function(){
                                var stack_attr_timer = $(".stack-attribute-timer[for-app-subnet='"+identifier+"']");
                                edit_stack_attributes("release_ownership", identifier, attribute, attribute_value)
                                $(this).dialog('close');
                                attr_timer_dict[identifier] = stack_attr_timer.detach();
                            }
                        },
                 
                },
                open: function(){
                var close_icon= $('.ui-dialog-titlebar-close');
                close_icon.append('<span class="ui-button-icon-primary ui-icon ui-icon-closethick"></span><span class="ui-button-text">close</span>');
                if (attribute.indexOf("owner")>-1)
                {
                    $(":button:contains('Edit')").hide();
                    $(":button:contains('Ok')").hide();

                }
                else
                {
                    $(":button:contains('Acquire ownership')").hide();
                    $(":button:contains('Release ownership')").hide();
                }
             }
          });  
        $("#stack-attribute-dialog").html(html_string);
    }
});

function edit_stack_attributes(action, location_identifier, attribute, attribute_value)
{
    var app_identifier= location_identifier.trim().split(":");
    var vpc = app_identifier[1];
    var region = app_identifier[0];
    var subnet = app_identifier[2];
    var stack = app_identifier[3];
    var parameter_dict = Object()
    parameter_dict[attribute] = attribute_value;
    attributes_dict = {'parameters': parameter_dict, 
                        'action' : action, 'region': region, 'vpc': vpc, 
                        'subnet' : subnet, 'module':'chef_module', 
                        'action_type': 'stack_action', 'application': stack}
    make_action_calls(document.URL, attributes_dict)
}


function display_edited_attributes(status, action)
{
    var attribute = status['editable_output']['attribute']
    delete(status['editable_output']['attribute'])
    var attribute_dict = status['editable_output']
    var attr_identifier = status['region']+":"+status['vpc']+":"+status['subnet']+":"+status["stack"]
    var attr_value = attribute_dict[attribute]
    var ownership_duration = ""
    if (status['action_state'] != "action_failed")
    {    
    
        var table_attribute = $(".stack-attribute-value[for-attr='"+attribute+"'][for-app-subnet='"+attr_identifier+"']");
        if ((table_attribute.attr("for-attr") === attribute) && (table_attribute.attr("for-app-subnet") === attr_identifier))
        {
            table_attribute.html(attr_value).fadeIn('fast');
                      
            if ((action==='acquire_ownership') || (action === 'release_ownership'))
            {
                if ('start_time' in attribute_dict)
                {
                    var attribute_timer = $("div[for-attr='start_time'][for-app-subnet='"+attr_identifier+"']");
                    display_ownership_timer("owner", attr_identifier, attribute_timer, Date.now());
                   
                }
            }
       }
    }
}
 
function display_ownership_timer(attribute, location_identifier, attribute_timer, start_time)

{
    var timer = new Date()
    if (!isNaN(start_time))
     {   
        timer = new Date(timer.setTime(new Date(start_time).getTime()+2*(1000*60*60*24)));
        attribute_timer.countdown(timer.format("yyyy/mm/dd HH:mm:ss").toString())
         .on('update.countdown', function(event) {
             var format = '%Hh';
            
             if(event.offset.days > 0) {
                 format = '%-dd %!d ' + format;
            }
            attribute_timer.html(event.strftime(format)).fadeIn('fast');
         })
         .on('finish.countdown', function(event) {
            attribute_timer.detach();
            edit_stack_attributes("release_ownership", attribute_timer.attr("for-app-subnet"), attribute, "");
        });
    }
}
    



});//end of file