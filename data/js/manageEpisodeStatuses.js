$(document).ready(function() {

    function make_row(tvdb_id, season, episode, name, ischecked) {
        var row, checked = '';
        if (ischecked) {
            checked = ' checked';
        }

        var row_class = $('#row_class').val();

        row += ' <tr class="' + row_class + '">';
        row += '  <td><input type="checkbox" class="' + tvdb_id + '-epcheck" name="' + tvdb_id + '-' + season + 'x' + episode + '"' + checked + '></td>';
        row += '  <td>' + season + 'x' + episode + '</td>';
        row += '  <td style="width: 100%">' + name + '</td>';
        row += ' </tr>';

        return row;
    }

    $('.allCheck').click(function() {
        var tvdb_id = $(this).attr('id').split('-')[1];
        $('.' + tvdb_id + '-epcheck').prop('checked', $(this).prop('checked'));
    });

    $('.get_more_eps').click(function() {
        var cur_tvdb_id = $(this).attr('id');
        var ischecked = $('#allCheck-' + cur_tvdb_id).prop('checked');
        var last_row = $('tr#' + cur_tvdb_id);

        $(this).prop("disabled", true);
        $.getJSON(sbRoot + '/manage/showEpisodeStatuses',
                  {
                   tvdb_id: cur_tvdb_id,
                   whichStatus: $('#oldStatus').val(),
                   includeSpecials: $('#opt_includeSpecials').val(),
                   excludeNoAirdate: $('#opt_excludeNoAirdate').val()
                  },
                  function (data) {
                      $.each(data, function(season, eps) {
                          $.each(eps, function(episode, name) {
                              //alert(season+'x'+episode+': '+name);
                              last_row.after(make_row(cur_tvdb_id, season, episode, name, ischecked));
                          });
                      });
                  });
        $(this).hide();
    });

    $('.expandAll').click(function() {
        $(this).prop("disabled", true);
        $('.get_more_eps').each(function() {
            var cur_tvdb_id = $(this).attr('id');
            var ischecked = $('#allCheck-' + cur_tvdb_id).prop('checked');
            var last_row = $('tr#' + cur_tvdb_id);

            $(this).prop("disabled", true);
            $.getJSON(sbRoot + '/manage/showEpisodeStatuses',
                      {
                       tvdb_id: cur_tvdb_id,
                       whichStatus: $('#oldStatus').val(),
                       includeSpecials: $('#opt_includeSpecials').val(),
                       excludeNoAirdate: $('#opt_excludeNoAirdate').val()
                      },
                      function (data) {
                          $.each(data, function(season, eps) {
                              $.each(eps, function(episode, name) {
                                  last_row.after(make_row(cur_tvdb_id, season, episode, name, ischecked));
                              });
                          });
                      });
            $(this).hide();
        });
        $(this).hide();
    });

    $('.toggleAll').click(function() {
        $('.sickbeardTable input').each(function() {
            this.checked = !this.checked;
        });
    });

});
