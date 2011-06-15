$(document).ready(function(){

    $('#saveDefaultsButton').click(function() {
        var anyQualArray = new Array();
        var bestQualArray = new Array();
        $('#anyQualities option:selected').each(function(i,d){anyQualArray.push($(d).val())});
        $('#bestQualities option:selected').each(function(i,d){bestQualArray.push($(d).val())});

        $.get(sbRoot+'/config/general/saveAddShowDefaults', {defaultStatus: $('#statusSelect').val(),
                                                             anyQualities: anyQualArray.join(','),
                                                             bestQualities: bestQualArray.join(','),
                                                             defaultSeasonFolders: $('#seasonFolders').prop('checked')} );
        $(this).attr('disabled', true);
        $.pnotify({
            pnotify_title: 'Saved Defaults',
            pnotify_text: 'Your "add show" defaults have been set to your current selections.'
        });
    });

    $('#statusSelect, #qualityPreset, #seasonFolders, #anyQualities, #bestQualities').change(function(){
        $('#saveDefaultsButton').attr('disabled', false);
    });

});