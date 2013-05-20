$(document).ready(function () {

    function populateSelect() {
        if (!$('#nameToSearch').length) {
            return;
        }

        if ($('#tvdbLangSelect option').length <= 1) {
            $.getJSON(sbRoot + '/home/addShows/getTVDBLanguages', {}, function (data) {
                var selected, resultStr = '';

                if (data.results.length === 0) {
                    resultStr = '<option value="en" selected="selected">en</option>';
                } else {
                    $.each(data.results, function (index, obj) {
                        if (resultStr == '') {
                            selected = ' selected="selected"';
                        } else {
                            selected = '';
                        }

                        resultStr += '<option value="' + obj + '"' + selected + '>' + obj + '</option>';
                    });
                }

                $('#tvdbLangSelect').html(resultStr);
                $('#tvdbLangSelect').change(function () { searchTvdb(); });
            });
        }
    }

    function searchTvdb() {
        if (!$('#nameToSearch').val().length) {
            return;
        }

        $('#searchResults').html('<img id="searchingAnim" src="' + sbRoot + '/images/loading32.gif" height="32" width="32" /> searching...');

        $.getJSON(sbRoot + '/home/addShows/searchTVDBForShowName', {'name': $('#nameToSearch').val(), 'lang': $('#tvdbLangSelect').val()}, function (data) {
            var firstResult = true;
            var resultStr = '<fieldset>\n<legend>Search Results:</legend>\n';
            var checked = '';

            if (data.results.length === 0) {
                resultStr += '<b>No results found, try a different search.</b>';
            } else {
                $.each(data.results, function (index, obj) {
                    if (firstResult) {
                        checked = ' checked';
                        firstResult = false;
                    } else {
                        checked = '';
                    }
                    resultStr += '<input type="radio" id="whichSeries" name="whichSeries" value="' + obj[0] + '|' + obj[1] + '"' + checked + ' /> ';
                    if (data.langid && data.langid != "") {
                        resultStr += '<a href="http://thetvdb.com/?tab=series&id=' + obj[0] + '&lid=' + data.langid + '" onclick=\"window.open(this.href, \'_blank\'); return false;\" ><b>' + obj[1] + '</b></a>';
                    } else {
                        resultStr += '<a href="http://thetvdb.com/?tab=series&id=' + obj[0] + '" onclick=\"window.open(this.href, \'_blank\'); return false;\" ><b>' + obj[1] + '</b></a>';
                    }

                    if (obj[2] !== null) {
                        var startDate = new Date(obj[2]);
                        var today = new Date();
                        if (startDate > today) {
                            resultStr += ' (will debut on ' + obj[2] + ')';
                        } else {
                            resultStr += ' (started on ' + obj[2] + ')';
                        }
                    }

                    resultStr += '<br />';
                });
                resultStr += '</ul>';
            }
            resultStr += '</fieldset>';
            $('#searchResults').html(resultStr);
            updateSampleText();
            myform.loadsection(0);
        });
    }

    $('#searchName').click(function () { searchTvdb(); });

    if ($('#nameToSearch').length && $('#nameToSearch').val().length) {
        $('#searchName').click();
    }

    $('#addShowButton').click(function () {
        // if they haven't picked a show don't let them submit
        if (!$("input:radio[name='whichSeries']:checked").val() && !$("input:hidden[name='whichSeries']").val().length) {
            alert('You must choose a show to continue');
            return false;
        }

        $('#addShowForm').submit();
    });

    $('#skipShowButton').click(function () {
        $('#skipShow').val('1');
        $('#addShowForm').submit();
    });

    $('#qualityPreset').change(function () {
        myform.loadsection(2);
    });

    /***********************************************
    * jQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
    * This notice MUST stay intact for legal use
    * Visit http://www.dynamicdrive.com/ for this script and 100s more.
    ***********************************************/

    var myform = new formtowizard({
        formid: 'addShowForm',
        revealfx: ['slide', 500],
        oninit: function () {
            populateSelect();
            updateSampleText();
            if ($('input:hidden[name=whichSeries]').length && $('#fullShowPath').length) {
                goToStep(3);
            }
        }
    });

    function goToStep(num) {
        $('.step').each(function () {
            if ($.data(this, 'section') + 1 == num) {
                $(this).click();
            }
        });
    }

    $('#nameToSearch').focus();

    function updateSampleText() {
        // if something's selected then we have some behavior to figure out

        var show_name, sep_char;
        // if they've picked a radio button then use that
        if ($('input:radio[name=whichSeries]:checked').length) {
            show_name = $('input:radio[name=whichSeries]:checked').val().split('|')[1];
        }
        // if we provided a show in the hidden field, use that
        else if ($('input:hidden[name=whichSeries]').length && $('input:hidden[name=whichSeries]').val().length) {
            show_name = $('#providedName').val();
        } else {
            show_name = '';
        }

        var sample_text = 'Adding show <b>' + show_name + '</b> into <b>';

        // if we have a root dir selected, figure out the path
        if ($("#rootDirs option:selected").length) {
            var root_dir_text = $('#rootDirs option:selected').val();
            if (root_dir_text.indexOf('/') >= 0) {
                sep_char = '/';
            } else if (root_dir_text.indexOf('\\') >= 0) {
                sep_char = '\\';
            } else {
                sep_char = '';
            }

            if (root_dir_text.substr(sample_text.length - 1) != sep_char) {
                root_dir_text += sep_char;
            }
            root_dir_text += '<i>||</i>' + sep_char;

            sample_text += root_dir_text;
        } else if ($('#fullShowPath').length && $('#fullShowPath').val().length) {
            sample_text += $('#fullShowPath').val();
        } else {
            sample_text += 'unknown dir.';
        }

        sample_text += '</b>';

        // if we have a show name then sanitize and use it for the dir name
        if (show_name.length) {
            $.get(sbRoot + '/home/addShows/sanitizeFileName', {name: show_name}, function (data) {
                $('#displayText').html(sample_text.replace('||', data));
            });
        // if not then it's unknown
        } else {
            $('#displayText').html(sample_text.replace('||', '??'));
        }

        // also toggle the add show button
        if (($("#rootDirs option:selected").length || ($('#fullShowPath').length && $('#fullShowPath').val().length)) &&
            ($('input:radio[name=whichSeries]:checked').length) || ($('input:hidden[name=whichSeries]').length && $('input:hidden[name=whichSeries]').val().length)) {
            $('#addShowButton').attr('disabled', false);
        } else {
            $('#addShowButton').attr('disabled', true);
        }
    }

    $('#rootDirText').change(updateSampleText);
    $('#whichSeries').live('change', updateSampleText);

    $('#nameToSearch').keyup(function (event) {
        if (event.keyCode == 13) {
            $('#searchName').click();
        }
    });

});
