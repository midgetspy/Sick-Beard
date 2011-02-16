$(document).ready(function(){

    $('#saveDefaultsButton').click(function() {
        $.get(sbRoot+'/config/general/saveAddShowDefaults', {defaultStatus: $('#statusSelect').val(),
                                                             defaultQuality: $('#qualityPreset').val(),
                                                             defaultSeasonFolders: $('#seasonFolders').val()} );
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