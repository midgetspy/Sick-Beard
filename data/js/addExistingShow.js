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

        url = sbRoot+'/home/addShows/addExistingShows?promptForSettings='+ ($('#promptForSettings').prop('checked') ? 'on' : 'off');

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
            $("#addRootDirTable").dataTable({
            	
        		// disable most stuff for the table
                "bPaginate": false,
                "bInfo": false,
                "bFilter": false,
                "bAutoWidth": false,
                "bProcessing": false,

        		// only show the basic DOM elements
        		"sDom": "lftipr",
                "bJQueryUI": true,
                
                "aoColumnDefs": [
                	{ "sClass": "center", "aTargets": [0] },

        			// checkbox
                    {
        				"bSortable": false,
        				"bSearchable": false,
        				"aTargets": [0],
                    },
                    
        			// path
                    {
                    	"sType": "titles",
                    	"aTargets": [ 1 ]
                    },
                    
        			// TVDB link
                    {
                    	"sType": "link-text",
                    	"aTargets": [ 2 ]
                    },
                    
            	],
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