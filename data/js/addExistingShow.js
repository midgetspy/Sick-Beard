$(document).ready(function() 
{ 
    $('#checkAll').live('click', function(){
    
        var seasCheck = this;

        $('.dirCheck').each(function(){
           this.checked = seasCheck.checked 
        });
    });

    $('#submitShowDirs').click(function(){
  
        var dirArr = new Array()

        $('.dirCheck').each(function() {
      
        if (this.checked == true) {
           dirArr.push($(this).attr('id'))
        }
      
        });  

        if (dirArr.length == 0)
            return false

        url = 'addExistingShows?showDirs='+dirArr.join('&showDirs=')

        window.location.href = url

  });


    var showing_dir = '';

    function loadContent(which_dir) {
        if (which_dir != showing_dir) {
            $.get('/home/addShows/massAddTable', {root_dir: which_dir}, function(data) {
                $('#tableDiv').html(data);
            });
            showing_dir = which_dir;

            $("#addRootDirTable").tablesorter({
                sortList: [[1,0]],
                widgets: ['zebra'],
                headers: {
                    0: { sorter: false }
                }
            });
        }
    }

    $('#rootDirText').change(function(){
        if ($("#rootDirs option:selected").length)
            loadContent($("#rootDirs option:selected").val());
    });

    if ($("#rootDirs option:selected").length)
        loadContent($("#rootDirs option:selected").val());
    
});