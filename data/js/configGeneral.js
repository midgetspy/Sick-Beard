$(document).ready(function(){


    $.fn.setExampleText = function() { 

        params = {'show_name': $('#naming_show_name').attr('checked')?"1":"0",
                  'ep_type': $('#naming_ep_type :selected').val(),
                  'multi_ep_type': $('#naming_multi_ep_type :selected').val(),
                  'ep_name': $('#naming_ep_name').attr('checked')?"1":"0",
                  'whichTest': 'single'
                  }
        
        $.get(nameTestURL, params,
              function(data){
                  $('#normalExampleText').text(data);
        });

        params['whichTest'] = 'multi'
        $.get(nameTestURL, params,
              function(data){
                  $('#multiExampleText').text(data);
        });

        return

    };

  $(this).setExampleText();

  $('#naming_ep_name').click(function(){
        $(this).setExampleText();
    });  

  $('#naming_show_name').click(function(){
        $(this).setExampleText();
    });  

  $('#naming_multi_ep_type').change(function(){
        $(this).setExampleText();
    });  

  $('#naming_ep_type').change(function(){
        $(this).setExampleText();
    });  

});