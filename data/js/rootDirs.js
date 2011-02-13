$(document).ready(function(){

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
    
        $.get('/config/general/saveRootDirs', { rootDirString: $('#rootDirText').val() });
    
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
        $.get('/config/general/saveRootDirs', {rootDirString: $('#rootDirText').val()});
    }
    
    $('#addRootDir').click(function(){$(this).nFileBrowser(addRootDir)});
    $('#editRootDir').click(function(){$(this).nFileBrowser(editRootDir, {initialDir: $("#rootDirs option:selected").val()})});

    $('#deleteRootDir').click(function(){
        if ($("#rootDirs option:selected").length) {

            var toDelete = $("#rootDirs option:selected");

            var newDefault = (toDelete.attr('id') == $("#whichDefaultRootDir").val());

            toDelete.remove();
            syncOptionIDs();

            if (newDefault) {

                console.log('new default when deleting')
                
                // we deleted the default so this isn't valid anymore
                $("#whichDefaultRootDir").val('')

                // if we're deleting the default and there are options left then pick a new default
                if ($("#rootDirs option").length)
                    setDefault($('#rootDirs option').attr('id'));
            
            }

        }
        refreshRootDirs();
        $.get('/config/general/saveRootDirs', {rootDirString: $('#rootDirText').val()});
    });

    $('#defaultRootDir').click(function(){
        if ($("#rootDirs option:selected").length)
            setDefault($("#rootDirs option:selected").attr('id'));
        refreshRootDirs();
        $.get('/config/general/saveRootDirs', 'rootDirString='+$('#rootDirText').val());
    });

    function setDefault(which, force){

        if (!which.length)
            return

        console.log('setting default to '+which)

        // put an asterisk on the text
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
        var do_disable = 'true';
        var sample_text = '';
        var sep_char = '';
        
        // re-sync option ids
        syncOptionIDs();

        // if nothing's selected then select the default
        if (!$("#rootDirs option:selected").length && $('#whichDefaultRootDir').val().length)
            $('#'+$('#whichDefaultRootDir').val()).attr('selected', 'selected')

        // if something's selected then we have some behavior to figure out
        if ($("#rootDirs option:selected").length) {
            do_disable = '';
            sample_text = $('#rootDirs option:selected').val();
            if (sample_text.indexOf('/') >= 0)
                sep_char = '/';
            else if (sample_text.indexOf('\\') >= 0)
                sep_char = '\\';

            sample_text = 'Eg. <b>' + sample_text;
            if (sample_text.substr(sample_text.length-1) != sep_char)
                sample_text += sep_char;
             sample_text += '</b><i>Sample Show</i>' + sep_char;
        }
        
        // update the elements
        $('#sampleRootDir').html(sample_text)
        $('#deleteRootDir').attr('disabled', do_disable);
        $('#defaultRootDir').attr('disabled', do_disable);
        $('#editRootDir').attr('disabled', do_disable);
        
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
        console.log(log_str)
        
        $('#rootDirText').val(dir_text);
        $('#rootDirText').change();
        console.log('rootDirText: '+$('#rootDirText').val())
    }
    
    $('#rootDirs').click(refreshRootDirs);
    
    // set up buttons on page load
    syncOptionIDs();
    setDefault($('#whichDefaultRootDir').val(), true)
    refreshRootDirs();

});