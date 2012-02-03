$(document).ready(function(){

    function logMsg(msg) {
        if (window.console && window.logMsg)
            console.log(msg)
    }

    function addRootDir(path){
        // check if it's the first one
        var is_default = false;
        if (!$('#whichDefaultRootDir').val().length)
            is_default = true;

        $('#rootDirs').append('<option value="'+path+'">'+path+'</option>');
        
        syncOptionIDs();
        
        if (is_default)
            setDefault($('#rootDirs option').attr('id'));

        refreshRootDirs();
    
        $.get(sbRoot+'/config/general/saveRootDirs', { rootDirString: $('#rootDirText').val() });
    
    }

    function editRootDir(path) {
        // as long as something is selected
        if ($("#rootDirs option:selected").length) {

            // update the selected one with the provided path
            if ($("#rootDirs option:selected").attr('id') == $("#whichDefaultRootDir").val())
                $("#rootDirs option:selected").text('*'+path);
            else
                $("#rootDirs option:selected").text('*'+path);
            $("#rootDirs option:selected").val(path);
        }

        refreshRootDirs();
        $.get(sbRoot+'/config/general/saveRootDirs', {rootDirString: $('#rootDirText').val()});
    }
    
    $('#addRootDir').click(function(){$(this).nFileBrowser(addRootDir)});
    $('#editRootDir').click(function(){$(this).nFileBrowser(editRootDir, {initialDir: $("#rootDirs option:selected").val()})});

    $('#deleteRootDir').click(function(){
        if ($("#rootDirs option:selected").length) {

            var toDelete = $("#rootDirs option:selected");

            var newDefault = (toDelete.attr('id') == $("#whichDefaultRootDir").val());
            var deleted_num = $("#rootDirs option:selected").attr('id').substr(3);

            toDelete.remove();
            syncOptionIDs();

            if (newDefault) {

                logMsg('new default when deleting')
                
                // we deleted the default so this isn't valid anymore
                $("#whichDefaultRootDir").val('');

                // if we're deleting the default and there are options left then pick a new default
                if ($("#rootDirs option").length)
                    setDefault($('#rootDirs option').attr('id'));
            
            } else if ($("#whichDefaultRootDir").val().length) {
                var old_default_num = $("#whichDefaultRootDir").val().substr(3);
                if (old_default_num > deleted_num)
                    $("#whichDefaultRootDir").val('rd-'+(old_default_num-1))
            }

        }
        refreshRootDirs();
        $.get(sbRoot+'/config/general/saveRootDirs', {rootDirString: $('#rootDirText').val()});
    });

    $('#defaultRootDir').click(function(){
        if ($("#rootDirs option:selected").length)
            setDefault($("#rootDirs option:selected").attr('id'));
        refreshRootDirs();
        $.get(sbRoot+'/config/general/saveRootDirs', 'rootDirString='+$('#rootDirText').val());
    });

    function setDefault(which, force){

        logMsg('setting default to '+which)

        if (which != undefined && !which.length)
            return

        if ($('#whichDefaultRootDir').val() == which && force != true)
            return

        // put an asterisk on the text
        if ($('#'+which).text().charAt(0) != '*')
            $('#'+which).text('*'+$('#'+which).text());

        // if there's an existing one then take the asterisk off
        if ($('#whichDefaultRootDir').val() && force != true) {
            var old_default = $('#'+$('#whichDefaultRootDir').val());
            old_default.text(old_default.text().substring(1));
        }
        
        $('#whichDefaultRootDir').val(which);
    }

    function syncOptionIDs() {
        // re-sync option ids
        var i = 0;
        $('#rootDirs option').each(function() {
            $(this).attr('id', 'rd-'+(i++));
        });
    }

    function refreshRootDirs() {

        if (!$("#rootDirs").length)
            return
        
        var do_disable = 'true';

        // re-sync option ids
        syncOptionIDs();

        // if nothing's selected then select the default
        if (!$("#rootDirs option:selected").length && $('#whichDefaultRootDir').val().length)
            $('#'+$('#whichDefaultRootDir').val()).prop("selected", true)

        // if something's selected then we have some behavior to figure out
        if ($("#rootDirs option:selected").length) {
            do_disable = '';
        }

        // update the elements
        $('#deleteRootDir').prop('disabled', do_disable);
        $('#defaultRootDir').prop('disabled', do_disable);
        $('#editRootDir').prop('disabled', do_disable);

        var log_str = '';
        var dir_text = '';
        if ($('#whichDefaultRootDir').val().length >= 4)
            var dir_text = $('#whichDefaultRootDir').val().substr(3);
        $('#rootDirs option').each(function() {
            log_str += $(this).val()+'='+$(this).text()+'->'+$(this).attr('id')+'\n';
            if (dir_text.length)
                dir_text += '|' + $(this).val()
        });
        log_str += 'def: '+ $('#whichDefaultRootDir').val();
        logMsg(log_str)
        
        $('#rootDirText').val(dir_text);
        $('#rootDirText').change();
        logMsg('rootDirText: '+$('#rootDirText').val())
    }

    $('#rootDirs').click(refreshRootDirs);

    // set up buttons on page load
    syncOptionIDs();
    setDefault($('#whichDefaultRootDir').val(), true)
    refreshRootDirs();

});