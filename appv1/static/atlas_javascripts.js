$(document).ready(function(){
    sessvars.appdict={}
  
    /* activate dropdowns */      
    $('.dropdown-toggle').dropdown();

    $(".dropdown-menu").hover(function(){
        $(this).stop().slideDown();
    });

    $(".dropdown-menu").mouseleave(function(){
        $(this).stop().slideUp();
    });
        
   
   /* drop down for user login and logout */      
    $( "#user-toggle").click(function() { 
        $("#user-dropdown").stop().slideDown();
    }); 
  
    $( "#user-toggle").mouseleave(function() { 

    $("#user-dropdown").stop().slideUp();
    });

    /* user logout */
    $("#user-dropdown li a").click(function(){
        var list_selection = $(this).text();
        if (list_selection == 'Logout')
        {       
            window.location = "../accounts/logout/";
        }
    });

    /* dropdowns for handling region and vpc selections */
    $( "#availability-zones-toggle").hover(function() { 
        $("#az-dropdown").stop().slideDown();
    });

    $( "#availability-zones-toggle").mouseleave(function() { 
        $("#az-dropdown").stop().slideUp();
    }); 


    /* code for selecting regions */
    $("#region-toggle").click(function(){   
        $("#region-dropdown").stop().slideDown();
        
    });
    
    $("#region-dropdown").click(function(){ 
        region_selected();
    });
    
    
    /* make ajax post calls to fetch information related to selected regions */
    function region_selected(){
        region_vpc_dict = new Object(); 
        $.each($(".region-box").find("input[type=checkbox]"), function(){
        if ($(this).is(":checked"))
            {
                var region_selected = $(this).attr("data-value")
                region_vpc_dict[region_selected]= new Array()
                $.each( $(".vpc-box input[type=checkbox][for-region='"+$(this).attr("data-value")+"']"), function(){
                    if ($(this).is(":checked"))
                    {
                         region_vpc_dict[region_selected].push($(this).attr("data-value"));
                    }
                });
            }
        });
        $.ajax({
                url : document.URL,
                type: "POST",
                data : {
                url: document.URL,
                session_var_save: 1,
                selected_region_vpcs: JSON.stringify(region_vpc_dict),
                var_type: "region_vpc_selection",
                module: "aws_module",
                csrfmiddlewaretoken: csrftoken,
                },
                dataType : "text",
                success: function(data){
                    $("body").html(data);
                    location.reload()
                }
            });
    }
    
    /* when a region box is selected select all the vpc's associated with it and viceversa*/
    $(".region-box").on('click', function(){
        var region_check_box = $(this).find("input");;
        var region = region_check_box.attr("data-value");
        if (region_check_box.is(":checked")){
            region_check_box.prop("checked", false);
            $(".vpc-box input[type=checkbox][for-region='"+region+"']").prop('checked', false);
        }
        else{
            region_check_box.prop("checked", true);
            $(".vpc-box input[type=checkbox][for-region='"+region+"']").prop('checked', true);
        }
        var region = region_check_box.attr("data-value");
    });
    
    /* when a vpc box is selected select region */
    $(".vpc-box").click(function(){
        var vpc_check_box = $(this).find("input[type=checkbox]")
        var region = vpc_check_box.attr("for-region");
        if (vpc_check_box.is(":checked")){
            vpc_check_box.prop("checked", false);
            $(".region-box input[type=checkbox][data-value='"+region+"']").prop('checked', false);
        }
        else{
            vpc_check_box.prop("checked", true);
            $(".region-box input[type=checkbox][data-value='"+region+"']").prop('checked', true);
        }
    });             


     /* refresh atlas data, change icons for indicating the progress */
    function refresh_data(){
            $.ajax({
                url : document.URL,
                type: "POST",
                data : {
                refresh_atlas_data: 1,
                refresh_flag: "refresh",
                csrfmiddlewaretoken: csrftoken
                },
                dataType : "text",
                success: function( data ){  
                    $("#refresh_data_span").html('<i id="refresh_data_icon" class="icon-cycle on-right">&nbsp;<font color="white">&nbsp;Reload</font>')
                }
                });
        return false;
    }


    /* when refresh data icon is clicked activate the refresh process */
    $("#refresh_data_icon").click(function(event){
        event.preventDefault();
        $("#refresh_data_span").html("<img src='/static/icons/refresh_data_loader.gif'> </img>&nbsp;<font color='white'>Loading...</font>")
        refresh_data();
    }); 
                
});