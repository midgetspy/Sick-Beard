$(document).ready(function(){

    $('#saveDefaultsButton').click(function() {
        $.get(sbRoot+'/config/general/saveAddShowDefaults', {defaultStatus: $('#statusSelect').val(),
                                                             defaultQuality: $('#qualityPreset').val(),
                                                             defaultSeasonFolders: $('#seasonFolders').val()} );
        $(this).attr('disabled', true);
    });

    $('#statusSelect, #qualityPreset, #seasonFolders, #anyQualities, #bestQualities').change(function(){
        $('#saveDefaultsButton').attr('disabled', false);
    });

});