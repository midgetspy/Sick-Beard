$(document).ready(function(){

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
        $('#tvdbLangSelect').html(resultStr)

        $('#tvdbLangSelect').change(function() { searchTvdb() });
    });


    function searchTvdb(){
        $('#searchResults').html('<img id="searchingAnim" src="'+sbRoot+'/images/searching_anim.gif">searching..</img>');

        $.getJSON(sbRoot+'/home/addShows/searchTVDBForShowName', {'name': $('#nameToSearch').val(), 'lang': $('#tvdbLangSelect').val()}, function(data){
            var resultStr = '';
            
            if (data.results.length == 0) {
                resultStr = '<b>No results found, try a different search.</b>';
            } else {
            
                $.each(data.results, function(index, obj){
                    if (resultStr == '')
                        checked = ' checked';
                    else
                        checked = '';
                    resultStr += '<input type="radio" name="whichSeries" value="' + obj[0] + '|' + obj[1] + '"' + checked + ' /> ';
                    if(data.langid && data.langid != "")
                            resultStr += '<a href="http://thetvdb.com/?tab=series&id=' + obj[0] + '&lid=' + data.langid + '" target="_new"><b>' + obj[1] + '</b></a>';
                    else
                        resultStr += '<a href="http://thetvdb.com/?tab=series&id=' + obj[0] + '" target="_new"><b>' + obj[1] + '</b></a>';

                    if (obj[2] != null)
                        resultStr += ' (started on ' + obj[2] + ')';
                    resultStr += '<br />';
                });
                resultStr += '</ul>';
            }
            $('#searchResults').html(resultStr);
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
        revealfx: ['slide', 500]
    });

    $('#nameToSearch').focus();



});