$(document).ready(function(){


toggle_tiles();  
function toggle_tiles()
{
    
      var tile_name
      $.each($("input[name='config-controls']:not(:checked)"), function(){
      tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
      $.each($(tile_name), function(){
        $(tile_name).hide(); 
      }); 

    }); 
    $.each($("input[name='config-controls']:checked"), function(){
      tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
      $.each($(tile_name), function(){
        $(this).show(); 
    }); 
    }); 
  
    var tile_name=""    
    $.each($("input[name='env-controls']:checked"), function(){
      tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
      $.each($(tile_name), function(){
        $(this).show(); 
      }); 
    }); 
  
    $.each($("input[name='env-controls']:not(:checked)"), function(){
      tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
      $.each($(tile_name), function(){
        $(this).hide(); 
      }); 

    }); 
  }
  
function call_modal_save(url)
  {
    var dash_status_dict=new Object();
    var config_status = new Array();

    dash_status_dict["url"] = document.URL
    dash_status_dict['config_status'] = new Array();
    dash_status_dict['env_status'] = new Array();
    $.each($("input[name='config-controls']:checked"), function(){
      dash_status_dict['config_status'].push($(this).attr("data-value"));

    });
    
    var env_status = new Array();
    $.each($("input[name='env-controls']:checked"), function(){
      dash_status_dict['env_status'].push($(this).attr("data-value"));
    }); 
    
   
    $.ajax({
          url : url,
          type: "POST",
          data : {
          module: "aws_module",
          session_var_save: 1,
          var_type: "selected_status_env",
          status_env_dict: JSON.stringify(dash_status_dict),
          csrfmiddlewaretoken: csrftoken
          },
          dataType : "text",
          success: function( data ){
            
        }
    });
  }
  /* 
   * modal for selecting configuration options
   */
 
  $("#configure").hover(function(){
    $("#myModal").modal('show');
  });
    
    
  /*
   * shows or removes the tiles for the options not selected
   */ 
  $("#close-config-modal").click(function(){
    var tile_name=""
    $.each($("input[name='config-controls']:checked"), function(){
      tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
     $.each($(tile_name), function(){
          $(this).show()
      
      }); 
    });
    
    $.each($("input[name='config-controls']:not(:checked)"), function(){
      tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
      console.log(tile_name);
      $.each($(tile_name), function(){
          console.log("reaching here");
          $(this).hide()
      }); 
    }); 


      $("#configuration-modal").modal('hide');
 
    
  });      

  
  
  /*
   * removes the tiles for the options not selected
   */ 
  $("#close-env-modal").click(function(){
    
    $.each($("input[name='env-controls']:checked"), function(){
    
      tile_name = "div[data-name='"+$(this).attr("data-value")+"']";
      $.each($(tile_name), function(){
        $(this).show(); 
      }); 

    }); 
    var tile_name=""
    $.each($("input[name='env-controls']:not(:checked)"), function(){
      tile_name = "div[data-name='"+$(this).attr("data-value")+"']";

      $.each($(tile_name), function(){
        $(this).hide(); 
      }); 

    }); 
     $("#environment-modal").modal('hide');
    
  });   

  $("#save-config").click(function(){
    //code to save the values to configuration database 
      
    call_modal_save("");
    toggle_tiles();
    $("#configuration-modal").modal('hide');

  });
  
  $("#save-env").click(function(){
    //code to save the values to configuration database
    
    call_modal_save("");
    toggle_tiles();
    $("#environment-modal").modal('hide')
  });
     
  /*
   * when clicked on the tile the page for that environment is selected
   */

  $(".environment-bar").add(".status-value-bar").on("click", function(event){
      
      var environment= $(this).attr("for-env");
      url = "../environment/"+environment;
      window.location=url;
      $.get('applications/'+environment+'/', function (data) {  
         
      }); 
      
    });
}); 
  
  