$(document).ready(function(){

    function populateSelect() {
        if ($('#tvdbLangSelect option').length <= 1) {
            $.getJSON(sbRoot+'/home/addShows/getTVDBLanguages', {}, function(data){
                var resultStr = '';
        
                if (data.results.length == 0) {
                    resultStr = '<option value="en" selected="selected">en</option>';
                } else {
                    $.each(data.results, function(index, obj){
                        if (resultStr == '')
                                selected = ' selected="selected"';
                        else
                                selected = '';
        
                        resultStr += '<option value="' + obj + '"' + selected + '>' + obj + '</option>';
                    });
                }
        
                $('#tvdbLangSelect').html(resultStr);
        
                $('#tvdbLangSelect').change(function() { searchTvdb() });
            });
        }
    }

    function searchTvdb(){
        $('#searchResults').html('<img id="searchingAnim" src="'+sbRoot+'/images/loading32.gif" height="32" width="32" /> searching...');

        $.getJSON(sbRoot+'/home/addShows/searchTVDBForShowName', {'name': $('#nameToSearch').val(), 'lang': $('#tvdbLangSelect').val()}, function(data){
            var firstResult = true;
            var resultStr = '<fieldset>\n<legend>Search Results:</legend>\n';
            
            if (data.results.length == 0) {
                resultStr += '<b>No results found, try a different search.</b>';
            } else {
            
                $.each(data.results, function(index, obj){
                    if (firstResult) {
                        checked = ' checked';
                        firstResult = false;
                    } else
                        checked = '';
                    resultStr += '<input type="radio" id="whichSeries" name="whichSeries" value="' + obj[0] + '|' + obj[1] + '"' + checked + ' /> ';
                    if(data.langid && data.langid != "")
                            resultStr += '<a href="http://thetvdb.com/?tab=series&id=' + obj[0] + '&lid=' + data.langid + '" onclick=\"window.open(this.href, \'_blank\'); return false;\" ><b>' + obj[1] + '</b></a>';
                    else
                        resultStr += '<a href="http://thetvdb.com/?tab=series&id=' + obj[0] + '" onclick=\"window.open(this.href, \'_blank\'); return false;\" ><b>' + obj[1] + '</b></a>';

                    if (obj[2] != null)
                        resultStr += ' (started on ' + obj[2] + ')';
                    resultStr += '<br />';
                });
                resultStr += '</ul>';
            }
            resultStr += '</fieldset>';
            $('#searchResults').html(resultStr);
            updateSampleText();
        });
    };

    $('#searchName').click(function() {searchTvdb()});

    if ($('#nameToSearch').val().length)
        $('#searchName').click()

    $('#cancelShow').click(function(){
        $('#cancelShowItem').val(1);
        $('#addShowForm').submit();
    });
    

    $('#addShowButton').click(function(){
        
        // if they haven't picked a show don't let them submit
        if (!$("input[name='whichSeries']:checked").val()) {
            alert('You must choose a show to continue');
            return false;
        }

        $('#addShowForm').submit()

    });
    
    $('#skipShowButton').click(function(){
        $('#skipShow').val('1');
        $('#addShowForm').submit();
    });
    
    /***********************************************
* jQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
* This notice MUST stay intact for legal use
* Visit http://www.dynamicdrive.com/ for this script and 100s more.
***********************************************/

    var myform=new formtowizard({
        formid: 'addShowForm',
        revealfx: ['slide', 500],
        oninit: function () { populateSelect(); }
    });

    $('#nameToSearch').focus();

    $('#makeStatusDefault').live('click', function() {
        $.get(sbRoot+'/config/general/saveDefaultStatus', {defaultStatus: $('#statusSelect').val()} );
        return false;
    });

    $('#makeQualityDefault').live('click', function() {
        $.get(sbRoot+'/config/general/saveDefaultQuality', {defaultQuality: $('#qualityPreset').val()} );
        return false;
    });

    $('#makeSeasonFoldersDefault').live('click', function() {
        $.get(sbRoot+'/config/general/saveDefaultSeasonFolders', {defaultSeasonFolders: $('#seasonFolders').val()} );
        return false;
    });

    /*
    $('#statusSelect').after('(<a href="#" id="makeStatusDefault">make default</a>)');
    $('#qualityPreset').after('(<a href="#" id="makeQualityDefault">make default</a>)');
    $('#seasonFolders').after('(<a href="#" id="makeSeasonFoldersDefault">make default</a>)');
    */

    function updateSampleText() {
        // if something's selected then we have some behavior to figure out
        if ($("#rootDirs option:selected").length) {
            sample_text = $('#rootDirs option:selected').val();
            if (sample_text.indexOf('/') >= 0)
                sep_char = '/';
            else if (sample_text.indexOf('\\') >= 0)
                sep_char = '\\';

            sample_text = 'Destination: <b>' + sample_text;
            if (sample_text.substr(sample_text.length-1) != sep_char)
                sample_text += sep_char;
            sample_text += '</b><i>||</i>' + sep_char;

            if ($('input:radio[name=whichSeries]:checked').length) {
                var selected_name = $('input:radio[name=whichSeries]:checked').val().split('|')[1];
                $.get(sbRoot+'/home/addShows/sanitizeFileName', {name: selected_name}, function(data){
                     $('#sampleRootDir').html(sample_text.replace('||', data));
                });
            } else {
                $('#sampleRootDir').html(sample_text.replace('||', 'Show Name'));
            }
        } else {
            $('#sampleRootDir').html('No root dir selected.');
        }
        
        if ($("#rootDirs option:selected").length && $('input:radio[name=whichSeries]:checked').length)
            $('#addShowButton').attr('disabled', false);
        else
            $('#addShowButton').attr('disabled', true);
    }
    
    $('#rootDirText').change(updateSampleText);
    $('#whichSeries').live('change', updateSampleText);

    $('#nameToSearch').keyup(function(event){
        if(event.keyCode == 13)
            $('#searchName').click();
    });

});