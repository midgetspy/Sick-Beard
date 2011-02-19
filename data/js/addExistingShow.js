$(document).ready(function() { 

    $('#checkAll').live('click', function(){
    
        var seasCheck = this;

        $('.dirCheck').each(function(){
           this.checked = seasCheck.checked;
        });
    });

    $('#submitShowDirs').click(function(){

        var dirArr = new Array();

        $('.dirCheck').each(function() {
      
        if (this.checked == true) {
           dirArr.push(encodeURIComponent($(this).attr('id')));
        }

        });  

        if (dirArr.length == 0)
            return false;

        url = sbRoot+'/home/addShows/addExistingShows?promptForSettings='+ ($('#promptForSettings').attr('checked') ? 'on' : 'off');

        url += '&shows_to_add='+dirArr.join('&shows_to_add=');

        window.location.href = url;
    });


    function loadContent() {
        var url = '';
        $('.dir_check').each(function(i,w){
            if ($(w).is(':checked')) {
                if (url.length)
                    url += '&'
                url += 'rootDir=' + encodeURIComponent($(w).attr('id'));
            }
        });

        $('#tableDiv').html('<img id="searchingAnim" src="'+sbRoot+'/images/loading32.gif" height="32" width="32" /> loading folders...');
        $.get(sbRoot+'/home/addShows/massAddTable', url, function(data) {
            $('#tableDiv').html(data);
            $("#addRootDirTable").tablesorter({
                //sortList: [[1,0]],
                widgets: ['zebra'],
                headers: {
                    0: { sorter: false }
                }
            });
        });

    }

    var last_txt = '';
    $('#rootDirText').change(function() {
        if (last_txt == $('#rootDirText').val())
            return false;
        else
            last_txt = $('#rootDirText').val();
        $('#rootDirStaticList').html('');           
        $('#rootDirs option').each(function(i, w) {
            $('#rootDirStaticList').append('<li class="ui-state-default ui-corner-all"><input type="checkbox" class="dir_check" id="'+$(w).val()+'" checked=checked> <label for="'+$(w).val()+'">'+$(w).val()+'</label></li>')
        });
        loadContent();
    });
    
    $('.dir_check').live('click', loadContent);
   
    $('.showManage').live('click', function() {
      $( "#tabs" ).tabs( 'select', 0 );
    });
    
});