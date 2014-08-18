$(document).ready(function(){

    /* before unload save session data */
    $(window).on('beforeunload', function(event){

            var selected_env_status = get_selected_apps_subnets()
            event.stopPropagation();
            event.preventDefault(); 
            var last_url = document.URL;
            post_session_data(selected_env_status, "aws_module")
     });
    
    /* call functions to display details related to selected application and subnets */
    show_hide_subnets();
    show_applications();
    hide_applications();
    show_status_tile();
    hide_status_tile();
    initialize_datatables();
    $(".quadro-full").show();


    /* activate information tabs */
    $.each($(".info-tabs"), function(){
        $("#"+$(this).attr("id")+"-info-tabs").tabs({'active':0})
    });
   

    /* initialize datatables for displaying all envirpnments including uncategorized */
    function initialize_datatables()
    {
        if (environment_selected === "uncategorized")
         {
            $('.uncat-table').DataTable({
                "bJQueryUI": true,
                "bDestroy": true,
                "bLengthChange": true,
                "bInfo": true,
                "bAutoWidth": false,
                "bPaginate" : true,
                "iDisplayLength": 10,
                "pagingType": "simple_numbers",
                //"bStateSave" : true,
                "bFilter" : true,
                "bSort" : false,
                "sDom" : '<<t><lp>>',
                "language": {
                    "info": "Showing _TOTAL_ entries"
                },
                "order": [[1, 'asc']],
                "columnDefs": [
                    {"name": "instance_id", "targets":2, "visible": false},
                    {"name:": "instance", "targets":1, "orderable": true},
                    {"name": "status", "targets":4, "orderable": false},
                    {"name": "instance_cost", "targets": 5, "orderable": true},
                    {"name": "storage_costs", "targets": 6, "orderable": true},
                    {"name": "subnet", "targets": 3, "orderable": false},
                    {"targets":0, "orderable":false},
                ],
            })
            $(".uncat-table").show()
            
         }
         else
         {
             $('.app-table').DataTable({
                "bJQueryUI": true,
                "bDestroy": true,
                "bLengthChange": true,
                "bInfo": true,
                "bAutoWidth": false,
                "bPaginate" : true,
                "pagingType": "simple_numbers",
                "iDisplayLength": 10,
                //"bStateSave" : true,
                "bFilter" : true,
                "bSort" : true,
                "sDom" : '<<t><lp>>',
                "language": {
                    "info": "Showing _TOTAL_ entries"
                },
                "order": [[1, 'asc']],
                "columnDefs": [
                    {"name": "instance_id", "targets":2, "visible": false},
                    {"name:": "instance", "targets":1, "orderable": true},
                    {"name": "status", "targets":4, "orderable": false},
                    {"name": "instance_cost", "targets": 5, "orderable": true},
                    {"name": "storage_costs", "targets": 6, "orderable": true},
                    {"name": "subnet", "targets": 3, "orderable": false},
                    {"targets":0, "orderable":false},
                ],
            })
            $(".app-table").show()  
         }
    }


    /* initialize menu to navigate between environments */
    $("#navigation-menu").mmenu({
         classes: "mm-slide mm-dark"
         
         },
         {
         selectedClasses: "active",
         header: "True",
         position: "top",
         zposition: "front",
         zindex: 1,
        });

    /* initialize menu to select applications */
    $("#applications-menu").mmenu({
         classes: "mm-slide mm-dark"
         },
         {
         selectedClasses: "active",
         header: "True",
         position: "top",
         zposition: "front",
         zindex: 1,
        });
           

    /* send user session data to back end through ajax post calls */
    function post_session_data(selected_env_status, module){
        if (selected_env_status, module)
        {
            $.ajax({
                        url : document.URL,
                        type: "POST",
                        data : {
                        session_var_save: 1,
                        var_type: 'selected_env_details',
                        module: module,
                        status_env_dict: JSON.stringify(selected_env_status),
                        navigation: "navigate",
                        csrfmiddlewaretoken: csrftoken
                        },
                        dataType : "text",
                        success: function( data ){  
                        }
            });
            return false;
        }
    }


    /* get region given the vpc */
    function get_region(vpc){
        for (var region in region_vpc_dict){
            var vpc_list = region_vpc_dict[region];
            if (vpc_list.indexOf(vpc) != -1)
            {
                return region;
            }
        }
    }


    /* get vpc given the subnet*/
    function get_vpc(subnet){
        var env_subnet_dict = environment_subnets_dict['vpc'];
        for (var vpc in env_subnet_dict){
            subnet_list = env_subnet_dict[vpc]['subnets']
            if (subnet_list.indexOf(subnet) != -1)
            {
                return vpc;
            }
        }

    }


    /* get the identifier for a particular vpc and subnet running an application */
    function get_vpc_subnet_app_id(app_header){
        var vpc_subnet_app = app_header.split(":")
        for (var index=0; index <= vpc_subnet_app.length; index++)
        {
            vpc_subnet_app[index].trim();
        }
        return vpc_subnet_app
    }


    /* activate the environment configuration modal */
    $("#env-status-configure").click(function(){
        $("#env-config-modal").dialog({
            height: 250,
            width: 600,
            title: "Configuration options",
            modal: true,
            dragabble: true,
            resizeable: false,
            'buttons' : {
                                            
                'close' :{    
                    text: "Close",
                    click: function(){
                        $(this).dialog('close')
                        show_status_tile();
                        hide_status_tile();
                    },
                },
                'save' :{    
                    text: "Save",
                    click: function(event){
                        event.preventDefault()
                        $(this).dialog('close')
                        show_status_tile();
                        hide_status_tile();
                        var selected_env_status = new Object()
                        selected_env_status['config_status'] = save_env_status();
                        selected_env_status['url'] = document.URL;
                        post_session_data(selected_env_status, "aws_module")
                        $(this).dialog('close');
                    },
                },
            },
            open: function(){
            var close_icon= $('.ui-dialog-titlebar-close');
            close_icon.append('<span class="ui-button-icon-primary ui-icon ui-icon-closethick"></span><span class="ui-button-text">close</span>');
         }
      });  
    });


    /* display status tile */
    function show_status_tile(){
        var tile_name=""
        $.each($("input[name='env-config-controls']:checked"), function(){
          tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
         $.each($(tile_name), function(){
              $(this).show()
          }); 
        });
    }


    /* hide status tile */
    function hide_status_tile(){
        $.each($("input[name='env-config-controls']:not(:checked)"), function(){
            tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
            $.each($(tile_name), function(){
                $(this).hide()
            }); 
        }); 
    }


    /* save environment status */
    function save_env_status()
    {
        env_status = new Array()
        $.each($("input[name='env-config-controls']:checked"), function(){
            env_status.push($.trim($(this).attr("data-value")));
        });
        return env_status
    }


    /* code to change appearance of subnet buttons on selection and deselection */
    $(".subnet-buttons").click(function(event){
        event.preventDefault();
        var subnet = $(this).text();
        var vpc = get_vpc(subnet);
        var region = get_region(vpc);
        var subnet_div_id = region +"-"+vpc+"-"+subnet+"-div";
        

        if ($(this).hasClass('subnet-unselect')) {
            $(this).removeClass('subnet-unselect');
            $(this).addClass('subnet-select');
            $("#"+subnet_div_id).show();
        }
        else{
            $(this).removeClass('subnet-select');
            $(this).addClass('subnet-unselect');
            $("#"+subnet_div_id).hide();
        }
        
    });


    /*get a list of subnets running a partcular application */
    function get_subnets(application){
        var subnet_list=[]
        for (var subnet in not_present_dict)
        {
            var application_list = not_present_dict[subnet]
            if (application_list.indexOf(application) != -1)
                subnet_list.push(subnet);   
        }
        return subnet_list;
    }


    /* show and hide system details related to subnets */
    function show_hide_subnets(){ 
        $.each($("button.subnet-select"), function(){
            var subnet = $(this).text();
            var vpc = get_vpc(subnet);
            var region = get_region(vpc);
            if ((not_present_dict != undefined) && (not_present_dict[subnet] != undefined))
            {
                for (var app_index=0;app_index<=not_present_dict[subnet].length; app_index++)
                {
                    var subnet_div_id = region +"-"+vpc+"-"+subnet+"-"+not_present_dict[subnet][app_index]+"-div";
                    $("#"+subnet_div_id).show(); 
                }
            }
        });
    }


    /* display system details related to the application */
    function show_applications(){
        $.each($("button.application-select"), function(){
            var application = ($(this).text()).trim();
            var subnet_list = get_subnets(application);
            for(var index=0; index<subnet_list.length; index++)
            {
                var subnet = subnet_list[index];
                var vpc = get_vpc(subnet);
                var region = get_region(vpc);
                app_div_id = region+"-"+vpc+"-"+subnet+"-"+application+"-div";
                $("#"+app_div_id).show();
             }
        });
    }


    /* hide system details related to the application */
    function hide_applications(){
        $.each($("button.application-unselect"), function(){
            var application = ($(this).text()).trim();
            var subnet_list = get_subnets(application);
            for(var index=0; index<subnet_list.length; index++){
                var subnet = subnet_list[index];
                var vpc = get_vpc(subnet);
                var region = get_region(vpc);
                app_div_id = region+"-"+vpc+"-"+subnet+"-"+application+"-div";
                $("#"+app_div_id).hide();
             }
        });
    }


    /* code to change apprerance of application menu on selection and deselection */
    $(".app-buttons").click(function(){
        var application = ($(this).text()).trim();
         if ($(this).hasClass('application-unselect')) {
            $(this).removeClass('application-unselect');
            $(this).addClass('application-select');
            show_applications();   
        }
        else{
            $(this).removeClass('application-select');
            $(this).addClass('application-unselect');
            hide_applications();
        }
    });


    /* keep track of selected apps whenever any application check box state changes */
    function get_selected_apps_subnets()
    {
        var selected_app_subnets = new Object();
        selected_app_subnets['url'] = document.URL;
        selected_app_subnets['selected_apps'] = new Array();
        selected_app_subnets['selected_subnets'] = new Array();
        $.each($(".application-select"), function(){
            selected_app_subnets['selected_apps'].push($.trim($(this).text()));
        });
        $.each($(".subnet-select"), function(){
            selected_app_subnets['selected_subnets'].push($.trim($(this).text()));
        });
        return selected_app_subnets
    }   


    /* loading on all toggle selections */
    $("#app-icon").add($("#filter-app-label")).click(function(){
        $("#applications-menu").trigger("open");
    });

   
    /* display the environment navigation menu */
    $("#env-icon").click(function(){
        $("#navigation-menu").trigger("open");
    });

        
    /* called when the application menu closes */   
    $("#applications-menu").mouseleave(function(){
        $("#applications-menu").trigger("close");
        get_selected_apps_subnets(); 
    }); 

                
    /* called when subnets are selected */
    $(".status").add(".double").on("click", function(event){
        event.preventDefault();
        var status_attribute = $(this).attr("vpc-name")+" " +$(this).attr("data-name");
        $(".dt_filter").val(status_attribute);
            $(".app-table").each( function () {
                var oTable = $(this).dataTable();
                oTable.fnFilter(status_attribute);  
            });
        return false;
    }); 


    /*  mimimize and maximize stack all table rows for all tables concurrently */
    $(".stack-minmax").on("click", function(){
       var min_max_icon = $(this).find("img")
        if (min_max_icon.hasClass("minimize-all-stack")){
            min_max_icon.parent().html("<img class='maximize-all-stack' src='/static/icons/maximize-stack.gif'/>");
            if (environment_selected === 'uncategorized')
                $(".uncat-table").hide();
            else
                $(".app-table").hide();
            $(".dataTables_paginate").hide();
            $(".dataTables_length").hide();
            $(".minmax-stack-icon").each(function(){
                minimize_maximize_stack($(this).attr("id"), $(this).find("img"));
            });
        }
        if (min_max_icon.hasClass("maximize-all-stack")){
            min_max_icon.parent().html("<img class='minimize-all-stack' src='/static/icons/minimize-stack.gif'/>");
            if (environment_selected === 'uncategorized')
                $(".uncat-table").show();
            else
                $(".app-table").show();
            $(".dataTables_paginate").show();
            $(".dataTables_length").show();
            $(".minmax-stack-icon").each(function(){
                minimize_maximize_stack($(this).attr("id"), $(this).find("img"));
            });
        }
    });

    
    /* actual function that hides and displays table rows, changes maximize-minimize icons */
    function minimize_maximize_stack(container_id, icon){
        if (icon.hasClass("minimize-stack")){
            var selector = icon.attr("for-app-subnet");
            var icon_html = ["<img class=maximize-stack",
                             "src=/static/icons/maximize-stack.gif",
                             "id="+selector+"-maximize-stack",
                             "for-app-subnet="+selector,
                             "/>"].join("\n");
            $("#"+container_id).html(icon_html);
            $("#"+selector+"-table").hide();
            $("#"+selector+"-table_paginate").hide();
            $("#"+selector+"-table_length").hide();
        }
        if (icon.hasClass("maximize-stack")){
            var selector = icon.attr("for-app-subnet");
            var icon_html = ["<img class=minimize-stack",
                             "src=/static/icons/minimize-stack.gif",
                             "id="+selector+"-minimize-stack",
                             "for-app-subnet="+selector,
                             "/>"].join("\n")
            $("#"+container_id).html(icon_html);

            $("#"+selector+"-table").show();
            $("#"+selector+"-table_paginate").show();
            $("#"+selector+"-table_length").show();
        }
        $(".minimize-stack").show();
        $(".maximize-stack").show();
    }

    
    /* minimize a stack by hiding all the table rows*/
    $(".minmax-stack-icon").on("click", function(){
        var icon = $(this).find("img");
        minimize_maximize_stack($(this).attr("id"), icon);
    });


    /* get the name of the div that identifies the instances that run a certain application in a subnet and region */
    function get_application_div_identifier(table_object){
        var selector = ""
        var div_name = ""
        if (table_object.hasClass("app-table"))
            {
                selector = table_object.attr("for-app-subnet").split(":")
                div_name = selector[0]+"-"+selector[1]+"-"+selector[2]+"-"+selector[3]+"-div"
            }
            if (table_object.hasClass("uncat-table"))
            {
                selector = table_object.attr("for-region")
                div_name = selector+"-div"
            }
        return div_name
    }


    /* apply filters to each columns in datatables */
    function filter_app_tables(table_object, table_settings, filter_text){
        for(iCol = 0; iCol < table_settings.aoPreSearchCols.length; iCol++) {
            table_settings.aoPreSearchCols[ iCol ].sSearch = filter_text;
        }
        table_object.fnStandingRedraw()
        table_object.show()
    }


    /* clear the search box filter */
    function clear_app_table_filters(){
        $(".app-table").add($(".uncat-table")).each( function () {

            var oTable = $(this).dataTable();
            var oSettings = oTable.fnSettings();
            div_name = get_application_div_identifier($(this))
            $("#"+div_name).show(); 
            filter_app_tables(oTable, oSettings, '');
        });
    }


    /* filter system details based on the search box filter */
    $("#datatable_filter").on('keyup', function(event){
        event.preventDefault();
        if ($(this).val() == ''){

            clear_app_table_filters();
        }
        if (event.keyCode == 13)
        {
            var text_input = $(this).val();
            $(".app-table").add($(".uncat-table")).each( function () {
                var oTable = $(this).dataTable();
                var oSettings = oTable.fnSettings();
                var stack_identifier = $(this).closest(".panel").find($(".vpc-subnet-app-identifier")).text();
                div_name = get_application_div_identifier($(this))
                $("#"+div_name).show();           
                if (stack_identifier.indexOf(text_input) == -1){
                     filter_app_tables(oTable, oSettings, text_input)
                    if (((oTable.$('tr', {"filter": "applied"})).length == $("this").length)){
                        $("#"+div_name).hide();
                    }   
                    else{
                        if ($("#"+div_name).is(":visible")){
                            $("#"+div_name).show(); 
                        }
                    }   
                }
           filter_app_tables(oTable, oSettings, '')
            });
        }
        return false;
    });


    /* close tab information div */
    $(".infodiv-close").on('click', function(){
        $(".info-div").hide();
    });

    /* close uncat information div */
    $(".uncat-infodiv-close").on('click', function(){
        $(".uncat-info-div").hide();
    });

    /* display information in selected tab given the tab identifier, tab name and instance_id */
    function display_tab_information(identifier, tab_name, instance_id){
        var html_string1 = "";
        var tab_info_index = 0
        for (var i=0; i<=tabs_list.length; i++){
            if (tabs_list[i]){
                for(var j=0; j<tabs_list[i].length; j++){
                    if (tab_name == tabs_list[i][j]){
                        tab_info_index = i;
                    }
                }
            }
        }
        html_string1 = [
        '<div class="panel panel-default">',
            '<div class="panel-title">',
            '<h4 style="color:#002E5C">Description</h4> <br>',
            '</div>',
            '<div class="panel-content">',
                '<table id="instance-description" cellspacing="20">',
                    '<thead></thead><tbody>',
                    '<tr>'].join("\n");

        for (instances in tabs_information[tab_info_index]){    
            if (instances == instance_id){   
                for (information in tabs_information[tab_info_index][instances][tab_name]){
                        var value = tabs_information[tab_info_index][instances][tab_name][information];
                        html_string1+= '<td align="left" style="color:#002E5C"><b>'+information+' :</b></td> <td align="left">'+value+'</td>';
                        html_string1+='</tr><tr>';
                }
                break;
            }
        }
        html_string1+= ['</tr>',
                '</tbody></table>',
            '</div>',
        '</div>'
        ].join("\n");
        
    $("#"+identifier+"-"+tab_name+"-div").show();  
    $("#"+identifier+"-"+tab_name+"-div").html(html_string1);
    $("#"+identifier+"-"+tab_name+"-div").show();
    }


    /* call the function to display tab information when a tab anchor is clicked on */
    $(".tabs-anchor").add($(".uncat-tabs-anchor")).on("click", function(){
        var identifier = "";
        if (environment_selected === "uncategorized")
        {
            identifier = $(this).attr("for-region")+"-uncat";
        }
        else
        {
            identifier = $(this).attr("for-app-subnet");
        }
        var tab_name = $(this).attr("for-tab");
        display_tab_information(identifier, tab_name, sessvars['selected_instance']);
        
    });


    /* when a click is performed on a table row for an instance
       the check box related to the instance is checked or unchecked based on previous status
       tabs are displayed or hidden based on previous status
       row colors are changed to show high light and unhighlight status. */
    $(".app-table tbody").add($(".uncat-table tbody")).on('click', "tr", function(event) {
        var app_subnet_string = $(this).parents("table").attr("for-app-subnet");
        var identifier = ""
        var id = "";
        if (environment_selected === "uncategorized"){
            identifier = $(this).parents("table").attr("for-region")
            id = identifier
        }
        else{
            identifier = $(this).parents("table").attr("for-app-subnet").split(":");
            id = identifier[0]+"-"+identifier[1]+"-"+identifier[2]+"-"+identifier[3];
        }
        var table = $("#"+id+"-table").dataTable();
        var data = table.fnGetData(this);
        var check_box_selection = data[2]+"-checkbox"
        var selected_instance_id = data[2];
        sessvars['selected_instance']=data[2];
        for (instances in tabs_information[0]){             
            if (selected_instance_id == instances){ 
                var tab_name = tabs_list[0][0];
                $("#"+id+"-information-div").show();
                if ($("#"+id+"-"+tab_name+"-checkbox").prop("checked"))
                {
                    display_tab_information(id, tab_name, selected_instance_id); //default aws_information tab
                }
            }
        }
        if ($("#"+check_box_selection).is(":checked")){
            $(".app-table tbody tr:odd").add($(".uncat-table tbody tr:odd")).css({"background-color":"#F9F9F9", "color":"000000"});
            $(".app-table tbody tr:even").add($(".uncat-table tbody tr:even")).css({"background-color":"#FFFFFF", "color": "000000"});
            uncheck_action_checkbox(check_box_selection,id, selected_instance_id);
        }
         else {
            $(this).css({"background-color":"#585859", "color": "FFFFFF"});
            check_action_checkbox(check_box_selection,id, selected_instance_id);
         }
    });


    /* hide tabs when a instance check box is unchecked */
    function uncheck_action_checkbox(checkbox_id, identifier, instance_id){   
        $("#"+identifier+"-information-div").hide();
        $("#"+checkbox_id).prop("checked", false);  
    }


    /* display all the tabs when the check box related to each instance is clicked */
    function check_action_checkbox(checkbox_id, identifier, instance_id){ 
        var tab_name = "aws_information" //default_tab name
        $("#"+checkbox_id).prop("checked", true);
        $(".info-tabs").tabs();
        $( "#"+identifier+"-info-tabs" ).tabs( {active : 0});
        $( "#"+identifier+"-info-tabs" ).tabs( "option", "hide", { effect: "fade" });
        $( "#"+identifier+"-info-tabs" ).tabs( "option", "heightStyle", "content" );
        $("#"+identifier+"-information-div").show();
        $("#"+identifier+"-"+tab_name+"-div").show();
        display_tab_information(identifier, tab_name, instance_id);
    }

    /* highlight row color on hovering on each table row */
     $(".app-table tbody tr").hover(function(event) {
        $(this).addClass('row_selected');
     });

    /* un highlight row on moving away from the row */
    $(".app-table tbody tr").on('mouseleave', function(event) {
        $(this).removeClass('row_selected');
        $(this).addClass('row_unselected');
     });


    /* action taken when clied on each table row */
    $(".app-table tbody").add(".uncat-table tbody").on('click', "tr input", function(){
            var app_name = $(this).attr("app_name");
            var checkbox_id = $(this).attr("id")
            if ($(this).is(":checked")){
                uncheck_action_checkbox(checkbox_id, app_name);
            }
            else{
                check_action_checkbox(checkbox_id, app_name);
            }
        });
}); //end of all function
