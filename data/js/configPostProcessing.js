$(document).ready(function(){

	// http://stackoverflow.com/questions/2219924/idiomatic-jquery-delayed-event-only-after-a-short-pause-in-typing-e-g-timew
	var typewatch = (function(){
		var timer = 0;
		return function(callback, ms){
			clearTimeout (timer);
			timer = setTimeout(callback, ms);
			}  
	})();
	
	function fill_examples() {

		var pattern = $('#naming_pattern').val();
		var multi = $('#naming_multi_ep :selected').val();
		
		$.get(sbRoot+'/config/postProcessing/testNaming', {pattern: pattern},
			function(data){
				$('#naming_example').text(data+'.ext');
		});

		$.get(sbRoot+'/config/postProcessing/testNaming', {pattern: pattern, multi: multi},
				function(data){
					$('#naming_example_multi').text(data+'.ext');
		});

		$.get(sbRoot+'/config/postProcessing/isNamingValid', {pattern: pattern, multi: multi},
				function(data){
					if (data == "invalid") {
						//$('input[type=submit]').attr('disabled', true);
						$('#temp_color_div').css('background-color', 'red');
					} else if (data == "seasonfolders") {
						$('input[type=submit]').attr('disabled', false);
						$('#temp_color_div').css('background-color', 'yellow');
					} else {
						$('input[type=submit]').attr('disabled', false);
						$('#temp_color_div').css('background-color', 'white');
					}						
		});
	}
	
	function do_custom_help() {
		var show_help = false;
		$('.naming_custom_span').each(function(){
			if ($(this).is(':visible')) {
				show_help = true;
				return false;
			}
		});

		if (show_help)
			$('#naming_custom_help').show();
		else
			$('#naming_custom_help').hide();
	}
	
	function do_preset(me) {

		var preset = $(me+' :selected').attr('id');

		if (preset == 'none')
			preset = '';
		
		if (preset == 'custom')
			$(me).parent().siblings('.naming_custom_span').show();
		else
			$(me).parent().siblings('.naming_custom_span').hide();

		if (preset != 'custom')
			$(me).parent().siblings('.naming_custom_span').children('.component-desc').children('.naming_pattern').val(preset);

		fill_examples();
		
		do_custom_help();
	}

	// initialize the presets
	do_preset('#dir_presets');
	do_preset('#name_presets');
	
	$('.naming_preset_select').change(function(){
		var me = '#'+$(this).attr('id');
		do_preset(me);
	});
	
	$('#naming_multi_ep').change(fill_examples);
	$('#naming_pattern').keyup(function(){
		typewatch(function () {
			do_preset('#'+$(this).attr('id'));
		}, 500);
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