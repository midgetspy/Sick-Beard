$(document).ready(function () {

    function find_dir_index(which) {
        var dir_parts = which.split('_');
        return dir_parts[dir_parts.length - 1];
    }

    function edit_root_dir(path, options) {
        $('#new_root_dir_' + options.which_id).val(path);
        $('#new_root_dir_' + options.which_id).change();
    }

    $('.new_root_dir').change(function () {
        var cur_index = find_dir_index($(this).attr('id'));
        $('#display_new_root_dir_' + cur_index).html('<b>' + $(this).val() + '</b>');
    });

    $('.edit_root_dir').click(function () {
        var cur_id = find_dir_index($(this).attr('id'));
        var initial_dir = $("#new_root_dir_" + cur_id).val();
        $(this).nFileBrowser(edit_root_dir, {initialDir: initial_dir, which_id: cur_id, title: 'Select Show Location', autocomplete: false});
    });

});
