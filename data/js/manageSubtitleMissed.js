$(document).ready(function() { 

    function make_row(tvdb_id, season, episode, name, subtitles, checked) {
        if (checked)
            var checked = ' checked';
        else
            var checked = '';
        
        var row = '';
        row += ' <tr class="good">';
        row += '  <td><input type="checkbox" class="'+tvdb_id+'-epcheck" name="'+tvdb_id+'-'+season+'x'+episode+'"'+checked+'></td>';
        row += '  <td style="width: 1%;">'+season+'x'+episode+'</td>';
        row += '  <td>'+name+'</td>';
        row += '  <td style="float: right;">'; 
        	subtitles = subtitles.split(',')
        	for (i in subtitles)
        	{
        		row += '   <img src="/images/flags/'+subtitles[i]+'.png" width="16" height="11" alt="'+subtitles[i]+'" />&nbsp;';
        	}
        row += '  </td>';
        row += ' </tr>'
        
        return row;
    }

    $('.allCheck').click(function(){
        var tvdb_id = $(this).attr('id').split('-')[1];
        $('.'+tvdb_id+'-epcheck').prop('checked', $(this).prop('checked'));
    });

    $('.get_more_eps').click(function(){
        var cur_tvdb_id = $(this).attr('id');
        var checked = $('#allCheck-'+cur_tvdb_id).prop('checked');
        var last_row = $('tr#'+cur_tvdb_id);
        
        $.getJSON(sbRoot+'/manage/showSubtitleMissed',
                  {
                   tvdb_id: cur_tvdb_id,
                   whichSubs: $('#selectSubLang').val()
                  },
                  function (data) {
                      $.each(data, function(season,eps){
                          $.each(eps, function(episode, data) {
                              //alert(season+'x'+episode+': '+name);
                              last_row.after(make_row(cur_tvdb_id, season, episode, data.name, data.subtitles, checked));
                          });
                      });
                  });
        $(this).hide();
    });

    // selects all visible episode checkboxes.
    $('.selectAllShows').click(function(){
        $('.allCheck').each(function(){
                this.checked = true;
        });
        $('input[class*="-epcheck"]').each(function(){
                this.checked = true;
        });
    });

    // clears all visible episode checkboxes and the season selectors
    $('.unselectAllShows').click(function(){
        $('.allCheck').each(function(){
                this.checked = false;
        });
        $('input[class*="-epcheck"]').each(function(){
                this.checked = false;
        });
    });

});