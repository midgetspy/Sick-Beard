
var comingEpsTableObj;    
var crc_url = sbRoot + '/home/json_coming_eps_list_crc';
var last_crc = "";
var json_url = sbRoot + "/json_coming_eps_list";

function check_crc() {
    $.getJSON(crc_url, function(data){
    	var cur_crc = data["crc"];
    	if (last_crc != cur_crc) {
	    	if (last_crc != "")
	    		comingEpsTableObj.fnReloadAjax(json_url);
    		last_crc = cur_crc;
    	}
    });
    
    setTimeout(check_crc, 10000)
}

$(document).ready(function(){ 
	
    comingEpsTableObj = $("#comingEpsTable").dataTable({
		// populate it with ajax
        "sAjaxSource": json_url,
        "sAjaxDataProp": "episodes",

		// disable most stuff for the table
        "bPaginate": false,
        "bInfo": false,
        "bFilter": false,
        "bAutoWidth": false,
        "bProcessing": false,

		// only show the basic DOM elements
		"sDom": "lftipr",
        "bJQueryUI": true,
        
        // don't zebra this table since we'll color it ourselves
        "asStripeClasses": [],

		// use localstorage to save state
		"bStateSave": true,
		"fnStateSave": function (oSettings, oData) {
			localStorage.setItem( 'DataTables_'+window.location.pathname, JSON.stringify(oData) );
		},
		"fnStateLoad": function (oSettings) {
			var data = localStorage.getItem('DataTables_'+window.location.pathname);
			return JSON.parse(data);
		},

		"fnCreatedRow": function( nRow, aData, iDataIndex ) {
			if (aData["status"] == "past")
				row_class = "listing_overdue";
			else if (aData["status"] == "current")
				row_class = "listing_current";
			else if (aData["status"] == "future")
				row_class = "listing_default";
			else if (aData["status"] == "distant")
				row_class = "listing_toofar";

			$(nRow).attr('class', row_class);
		},
    
            "aoColumnDefs": [
        	{ "sClass": "center", "aTargets": [0, 2, 4, 5, 6, 7] },

			// Date
			{
				"sType": "empty-last",
            	"aDataSort": [0, 1],
                "aTargets": [ 0 ]
			},				

			// Title
            {
				"sType": "titles",
				"sClass": "tvShow",
				"bUseRendered": false,
				
				// render the show name as a link
                "fnRender": function ( oObj, sVal ) {
                	return '<a href="'+sbRoot+'/home/displayShow?show=' + oObj.aData["tvdb_id"] + '">' + oObj.aData["show_name"] + '</a>';
                },
                "aTargets": [ 1 ]
            },

			// Quality
            {
            	// sort the quality in the correct order and secondarily by name
				"sType": "quality",
            	"bUseRendered": false,
            	"aDataSort": [5, 1],

            	// render the quality in a span
                "fnRender": function ( oObj, sVal ) {
                	return '<span class="quality '+sVal+'">'+sVal+'</span>';
                },
                "aTargets": [ 5 ]
            },
            
			// TVDB link
            {
				"bSortable": false,
				"bSearchable": false,
				
            	// render a link
                "fnRender": function ( oObj, sVal ) {
                	return '<a href="http://www.thetvdb.com/?tab=series&amp;id='+oObj.aData["tvdb_id"]+'" onclick="window.open(this.href, \'_blank\'); return false;" title="http://www.thetvdb.com/?tab=series&amp;id='+oObj.aData["tvdb_id"]+'"><img alt="[info]" height="16" width="16" src="'+sbRoot+'/images/thetvdb16.png" /></a>';
                },
                "aTargets": [ 6 ]
            },
            
			// search link
            {
				"bSortable": false,
				"bSearchable": false,
				
            	// render a link
                "fnRender": function ( oObj, sVal ) {
                	return '<a href="'+sbRoot+'/home/searchEpisode?show='+oObj.aData["tvdb_id"]+'&amp;season='+oObj.aData["season"]+'&amp;episode='+oObj.aData["episode"]+'" title="Manual Search" id="forceUpdate-'+oObj.aData["tvdb_id"]+'" class="forceUpdate epSearch"><img alt="[search]" height="16" width="16" src="'+sbRoot+'/images/search32.png" id="forceUpdateImage-'+oObj.aData["tvdb_id"]+'" /></a>';
                },
                "aTargets": [ 7 ]
            },
            
    	],
        "aoColumns": [
            { "mDataProp": "air_date" },
            { "mDataProp": "show_name" },
            { "mDataProp": "ep_string" },
            { "mDataProp": "ep_name" },
            { "mDataProp": "network" },
            { "mDataProp": "quality_string" },
            { "mDataProp": null },
            { "mDataProp": null }
        ]
    });
	
	// start watching the show list crcs
    //check_crc();
});
