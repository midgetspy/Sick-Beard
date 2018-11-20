$("#mitm-post").click(function() {
    $("#ajaxform").submit(function(e) {
        $('.content').html("<center><div class='jumbotron-icon'><i class='fa fa-refresh fa-spin fa-6 fa-fw' aria-hidden='true'></i></div></center>");
        var postData = $(this).serializeArray(); 
        var formURL = $(this).attr("action");
        $.ajax( 
        { 
            url : formURL, 
            type: "POST", 
            data : postData, 
            success: function(data, textStatus, jqXHR)
            {
                $('.content').html('<center><h3>TorrentDay Email</h3></br><h1><font color="green"><b>Successful</b></font></h1></br>Please, check for an Email from TorrentDay,</br>Copy the url/code in said Email and, Paste it into input field on the</br>next screen.</br></br>Ensure you click "<b>save changes</b>".</br></br><div class="jumbotron-icon"><i class="fa fa-smile-o fa-6" aria-hidden="true"></i></div></center>');
                $('#popup_div').hide();
                $('#response_email').show();
            }, 
            error: function(jqXHR, textStatus, errorThrown)
            {
                $(".content").html("<center><h3>TorrentDay Email</h3></br><h1><font color='red'><b>Failed</b></font></h1></br></br><div class='jumbotron-icon'><i class='fa fa-refresh fa-frown-o fa-6' aria-hidden='true'></i></div></center>");
            } 
        }); 
        e.preventDefault(); 
    }); 
});

