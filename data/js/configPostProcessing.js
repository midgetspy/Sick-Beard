$(document).ready(function(){

    $.fn.setExampleText = function() { 

        params = {'show_name': $('#naming_show_name').prop('checked')?"1":"0",
                  'ep_type': $('#naming_ep_type :selected').val(),
                  'multi_ep_type': $('#naming_multi_ep_type :selected').val(),
                  'ep_name': $('#naming_ep_name').prop('checked')?"1":"0",
                  'use_periods': $('#naming_use_periods').prop('checked')?"1":"0",
                  'quality': $('#naming_quality').prop('checked')?"1":"0",
                  'sep_type': $('#naming_sep_type :selected').val(),
                  'whichTest': 'single'
                  }
        
        $.get(sbRoot+"/config/postProcessing/testNaming", params,
              function(data){
                  $('#normalExampleText').text(data);
        });

        params['whichTest'] = 'multi'
        $.get(sbRoot+"/config/postProcessing/testNaming", params,
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

    // -- start of metadata options div toggle code --
    $('#metadataType').change(function(){
        $(this).showHideMetadata();
    });

    $.fn.showHideMetadata = function() {
        $('.metadataDiv').each(function(){
            var targetName = $(this).attr('id');
            var selectedTarget = $('#metadataType :selected').val();

            if (selectedTarget == targetName)
                $(this).show();
            else
                $(this).hide();

        });
   } 
    //initalize to show the div
    $(this).showHideMetadata();	
    // -- end of metadata options div toggle code --
    
    $('.metadata_checkbox').click(function(){
        $(this).refreshMetadataConfig(false);
    });

    $.fn.refreshMetadataConfig = function(first) {

        var cur_most = 0;
        var cur_most_provider = '';

        $('.metadataDiv').each(function(){
            var generator_name = $(this).attr('id');

            var config_arr = new Array();
            var show_metadata = $("#"+generator_name+"_show_metadata").prop('checked');
            var episode_metadata = $("#"+generator_name+"_episode_metadata").prop('checked');
            var fanart = $("#"+generator_name+"_fanart").prop('checked');
            var poster = $("#"+generator_name+"_poster").prop('checked');
            var episode_thumbnails = $("#"+generator_name+"_episode_thumbnails").prop('checked');
            var season_thumbnails = $("#"+generator_name+"_season_thumbnails").prop('checked');

            config_arr.push(show_metadata ? '1':'0');
            config_arr.push(episode_metadata ? '1':'0');
            config_arr.push(poster ? '1':'0');
            config_arr.push(fanart ? '1':'0');
            config_arr.push(episode_thumbnails ? '1':'0');
            config_arr.push(season_thumbnails ? '1':'0');

            var cur_num = 0;
            for (var i = 0; i < config_arr.length; i++)
                cur_num += parseInt(config_arr[i])
            if (cur_num > cur_most) {
                cur_most = cur_num
                cur_most_provider = generator_name
            }

            $("#"+generator_name+"_eg_show_metadata").attr('class', show_metadata ? 'enabled' : 'disabled');
            $("#"+generator_name+"_eg_episode_metadata").attr('class', episode_metadata ? 'enabled' : 'disabled');
            $("#"+generator_name+"_eg_poster").attr('class', poster ? 'enabled' : 'disabled');
            $("#"+generator_name+"_eg_fanart").attr('class', fanart ? 'enabled' : 'disabled');
            $("#"+generator_name+"_eg_episode_thumbnails").attr('class', episode_thumbnails ? 'enabled' : 'disabled');
            $("#"+generator_name+"_eg_season_thumbnails").attr('class', season_thumbnails ? 'enabled' : 'disabled');
            
            $("#"+generator_name+"_data").val(config_arr.join('|'))
            
        });

        if (cur_most_provider != '' && first) {
            $('#metadataType option[value='+cur_most_provider+']').attr('selected', 'selected')
            $(this).showHideMetadata();
        }
        
    }

    $(this).refreshMetadataConfig(true);

});