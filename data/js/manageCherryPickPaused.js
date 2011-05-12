$(document).ready(function() { 

    function make_row(tvdb_id, season, episode, name, checked, cherry_status) {
        if (checked)
            var checked = ' checked';
        else
            var checked = '';
        
        
        var row = '';
        if ( cherry_status == 3 ) {
            row += ' <tr class="wanted">';
        } else {
            row += ' <tr class="unaired">';
        }
        row += '  <td><input type="checkbox" class="'+tvdb_id+'-epcheck" name="'+tvdb_id+'-'+season+'x'+episode+'"'+checked+'></td>';
        row += '  <td>'+season+'x'+episode+'</td>';
        row += '  <td style="width: 90%">'+name+'</td>';
        if ( cherry_status == 3 ) {
            row += '  <td>Wanted</td>';
        } else {
            row += '  <td>Unaired</td>';
        }
        row += ' </tr>'
        
        return row;
    }

    $('.allCheck').click(function(){
        var tvdb_id = $(this).attr('id').split('-')[1];
        $('.'+tvdb_id+'-epcheck').attr('checked', $(this).attr('checked'));
    });

    $('.get_more_eps').click(function(){
        var cur_tvdb_id = $(this).attr('id');
        var checked = $('#allCheck-'+cur_tvdb_id).attr('checked');
        var last_row = $('tr#'+cur_tvdb_id);
        
        $.getJSON(sbRoot+'/manage/showCherryPickPaused',
                  {
                   tvdb_id: cur_tvdb_id
                  },
                  function (data) {
                      $.each(data, function(season,eps){
                          $.each(eps, function(episode, name) {
                                  //alert(season+'x'+episode+': '+name);
                                  last_row.after(make_row(cur_tvdb_id, season, episode, name.name, checked, name.cherry_pick_status));
                          });
                      });
                  });
        $(this).hide();
    });

});
