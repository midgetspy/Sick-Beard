$(document).ready(function(){
    $(".enabler").each(function(){
        if (!$(this).attr('checked'))
            $('#content_'+$(this).attr('id')).hide();
    });

    $(".enabler").click(function() {
        if ($(this).attr('checked'))
            $('#content_'+$(this).attr('id')).show();
        else
            $('#content_'+$(this).attr('id')).hide();
  });
});