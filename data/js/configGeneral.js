$(document).ready(function(){

    $.fn.setExampleText = function() { 

        params = {'show_name': $('#naming_show_name').attr('checked')?"1":"0",
                  'ep_type': $('#naming_ep_type :selected').val(),
                  'multi_ep_type': $('#naming_multi_ep_type :selected').val(),
                  'ep_name': $('#naming_ep_name').attr('checked')?"1":"0",
                  'use_periods': $('#naming_use_periods').attr('checked')?"1":"0",
                  'quality': $('#naming_quality').attr('checked')?"1":"0",
                  'sep_type': $('#naming_sep_type :selected').val(),
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

  $('#naming_use_periods').click(function(){
        $(this).setExampleText();
    });  

  $('#naming_quality').click(function(){
        $(this).setExampleText();
    });  

  $('#naming_multi_ep_type').change(function(){
        $(this).setExampleText();
    });  

  $('#naming_ep_type').change(function(){
        $(this).setExampleText();
    });  

  $('#naming_sep_type').change(function(){
        $(this).setExampleText();
    });  

});