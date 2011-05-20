$(document).ready(function(){

   $("table.sickbeardTable td").hover( 
	       function() { $(this).find("a").parent().addClass("hover"); }, 
	       function() { $(this).find("a").parent().removeClass("hover");
   } );

   $("table.sickbeardTable td").click( function() {
        var href = $(this).find("a").attr("href");
        if(href) { window.location = href; }
   });

});
