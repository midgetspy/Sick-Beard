$(document).ready(function(){
    
    $.fn.refreshPluginList = function() {
        var idArr = $("#plugin_order_list").sortable('toArray');
        var finalArr = new Array();
        $.each(idArr, function(key, val) {
            var checked = $('#enable_'+val).attr('checked') ? '1' : '0';
            finalArr.push(val + ':' + checked);
        });

        $("#subtitles_plugins").val(finalArr.join(' '));
    }

    $.fn.showHideSubtitles = function() {
        if ($('#use_subtitles').attr('checked')) {
            $('#core-component-group2').show()
            $('#core-component-group3').show()
        } else {
            $('#core-component-group2').hide()
            $('#core-component-group3').hide()
        }
    }
    
    $('.plugin_enabler').live('click', function(){
        $(this).refreshPluginList();
    }); 

    $('#use_subtitles').change(function(){
        $(this).showHideSubtitles();
    });

    // initialization stuff
    $("#plugin_order_list").sortable({
        placeholder: 'ui-state-highlight',
        update: function (event, ui) {
            $(this).refreshPluginList();
        }
    });
    
    $("#plugin_order_list").disableSelection();

    $(this).showHideSubtitles();

});
