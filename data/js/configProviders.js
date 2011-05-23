$(document).ready(function(){

	/*
	 * Below is the stuff for built-in provider management
	 */
	
    $.fn.showHideProviders = function() {
        $('.providerDiv').each(function(){
            var providerName = $(this).attr('id');
            var selectedProvider = $('#editAProvider :selected').val();
            
            if (selectedProvider+'Div' == providerName)
                $(this).show();
            else
                $(this).hide();
            
        });
    } 

    // when an built-in provider's key is changed we want to update it in the backend
    $('.newznab_key').change(function(){

    	var provider_id = $(this).attr('id');
    	provider_id = provider_id.substring(0, provider_id.length-'_hash'.length);
    	
    	var url = $('#'+provider_id+'_url').val();
    	var key = $(this).val();

    	$(this).updateProvider(provider_id, url, key);
    	
    });
    
    $('#editAProvider').change(function(){
        $(this).showHideProviders();
    });


    
    /*
     * Below is the stuff for custom newznab provider editing
     */
    
    // store our newznab data here
    var newznabProviders = new Array();

    // create a new newznab provider from the given data and add it to our newznab string
    $.fn.addProvider = function (id, name, url, key, isDefault) {

    	// tweak the URL if necessary
        if (url.match('/$') == null)
            url = url + '/';

        // add the data to the provider dict
        var newData = [isDefault, [name, url, key]];
        newznabProviders[id] = newData;

        // default providers will get edited in the built-in section
        if (!isDefault)
        {
	        $('#editANewznabProvider').addOption(id, name);
	        $(this).populateNewznabSection();
        }

        // add the provider to the provider list so it can be enabled/sorted
        if ($('#provider_order_list > #'+id).length == 0) {
            var toAdd = '<li class="ui-state-default" id="'+id+'"> <input type="checkbox" id="enable_'+id+'" class="provider_enabler" CHECKED> <a href="'+url+'" class="imgLink" target="_new"><img src="'+sbRoot+'/images/providers/newznab.gif" alt="'+name+'" width="16" height="16"></a> '+name+'</li>'

            $('#provider_order_list').append(toAdd);
            $('#provider_order_list').sortable("refresh");
        }
        
        // build up the hidden form element that contains the config string
        $(this).makeNewznabProviderString();
    
    }

    // updates the newznab provider dict with the new config info for a provider
    $.fn.updateProvider = function (id, url, key) {

        newznabProviders[id][1][1] = url;
        newznabProviders[id][1][2] = key;

        $(this).populateNewznabSection();

        $(this).makeNewznabProviderString();
    
    }

    // removes a provider from the lists
    $.fn.deleteProvider = function (id) {
    
        $('#editANewznabProvider').removeOption(id);
        delete newznabProviders[id];
        $(this).populateNewznabSection();

        $('#provider_order_list > #'+id).remove();

        $(this).makeNewznabProviderString();
    
    }

    // populates the custom newznab section with the relevant info for whatever is selected in the dropbox
    $.fn.populateNewznabSection = function() {
    
        var selectedProvider = $('#editANewznabProvider :selected').val();
    
        if (selectedProvider == 'addNewznab') {
            var data = ['','',''];
            var isDefault = 0;
            $('#newznab_add_div').show();
            $('#newznab_update_div').hide();
        } else {
            var data = newznabProviders[selectedProvider][1];
            var isDefault = newznabProviders[selectedProvider][0];
            $('#newznab_add_div').hide();
            $('#newznab_update_div').show();
        }
        
        $('#newznab_name').val(data[0]);
        $('#newznab_url').val(data[1]);
        $('#newznab_key').val(data[2]);
        
        if (selectedProvider == 'addNewznab') {
            $('#newznab_name').removeAttr("disabled");
            $('#newznab_url').removeAttr("disabled");
        } else {

            $('#newznab_name').attr("disabled", "disabled");
            
            if (isDefault) {
                $('#newznab_url').attr("disabled", "disabled");
                $('#newznab_delete').attr("disabled", "disabled");
            } else {
                $('#newznab_url').removeAttr("disabled");
                $('#newznab_delete').removeAttr("disabled");
            }
        }
            
    }
    
    // build up the config string that goes in the hidden form field 
    $.fn.makeNewznabProviderString = function() {
        
        var provStrings = new Array();
        
        for (var id in newznabProviders) {
            provStrings.push(newznabProviders[id][1].join('|'));
        }
        
        $('#newznab_string').val(provStrings.join('!!!'))
        
    }

    // when a custom provider's key is changed we wan to update it on the backend
    $('.custom_newznab_field').change(function(){
        
    	var selectedProvider = $('#editANewznabProvider :selected').val();

    	// don't fire the update method if this is a new provider
    	if (selectedProvider == 'addNewznab')
    		return false;
    	
        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();
        
        $(this).updateProvider(selectedProvider, url, key);
        
    });
    
    // checks with the server that we can add a new provider and then does the required actions
    $('#newznab_add').click(function(){
        
        var selectedProvider = $('#editANewznabProvider :selected').val();
        
        var name = $('#newznab_name').val();
        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();
        
        var params = { name: name }
        
        // send to the form with ajax, get a return value
        $.getJSON(sbRoot + '/config/providers/canAddNewznabProvider', params,
            function(data){
                if (data.error != undefined) {
                    alert(data.error);
                    return;
                }

                $(this).addProvider(data.success, name, url, key, 0);
        });
        
        
    });

    // deletes a provider from our local backend
    $('.newznab_delete').click(function(){
    
        var selectedProvider = $('#editANewznabProvider :selected').val();

        $(this).deleteProvider(selectedProvider);

    });
    
    $('#editANewznabProvider').change(function(){
        $(this).populateNewznabSection();
    });



    
    /*
     * Below is the stuff for custom torrent provider editing
     */

    // store our newznab data here
    var torrentProviders = new Array();

    // create a new torrent provider from the given data and add it to our torrent string
    $.fn.addTorrentProvider = function (id, name, url, isDefault) {

        // add the data to the provider dict
        var newData = [isDefault, [name, url]];
        torrentProviders[id] = newData;

        // default providers will get edited in the built-in section
        if (!isDefault)
        {
	        $('#editATorrentProvider').addOption(id, name);
	        $(this).populateTorrentSection();
        }

        // add the provider to the provider list so it can be enabled/sorted
        if ($('#provider_order_list > #'+id).length == 0) {
            var toAdd = '<li class="ui-state-default" id="'+id+'"> <input type="checkbox" id="enable_'+id+'" class="provider_enabler" CHECKED> <a href="'+url+'" class="imgLink" target="_new"><img src="'+sbRoot+'/images/providers/torrent.gif" alt="'+name+'" width="16" height="16"></a> '+name+'</li>'

            $('#provider_order_list').append(toAdd);
            $('#provider_order_list').sortable("refresh");
        }
        
        // build up the hidden form element that contains the config string
        $(this).makeTorrentProviderString();
    
    }

    // populates the custom torrent section with the relevant info for whatever is selected in the dropbox
    $.fn.populateTorrentSection = function() {
    
        var selectedProvider = $('#editATorrentProvider :selected').val();
    
        if (selectedProvider == 'addTorrent') {
            var data = ['',''];
            var isDefault = 0;
            $('#torrent_add_div').show();
            $('#torrent_update_div').hide();
        } else {
            var data = torrentProviders[selectedProvider][1];
            var isDefault = torrentProviders[selectedProvider][0];
            $('#torrent_add_div').hide();
            $('#torrent_update_div').show();
        }
        
        $('#torrent_name').val(data[0]);
        $('#torrent_url').val(data[1]);
        
        if (selectedProvider == 'addTorrent') {
            $('#torrent_name').removeAttr("disabled");
            $('#torrent_url').removeAttr("disabled");
        } else {

            $('#torrent_name').attr("disabled", "disabled");
            
            if (isDefault) {
                $('#torrent_url').attr("disabled", "disabled");
                $('#torrent_delete').attr("disabled", "disabled");
            } else {
                $('#torrent_url').removeAttr("disabled");
                $('#torrent_delete').removeAttr("disabled");
            }
        }
            
    }
    
    // build up the config string that goes in the hidden form field 
    $.fn.makeTorrentProviderString = function() {
        
        var provStrings = new Array();
        
        for (var id in torrentProviders) {
            provStrings.push(torrentProviders[id][1].join('|'));
        }
        
        $('#torrent_string').val(provStrings.join('!!!'))
        
    }

    // checks with the server that we can add a new provider and then does the required actions
    $('#torrent_add').click(function(){
        
        var selectedProvider = $('#editANewznabProvider :selected').val();
        
        var name = $('#torrent_name').val();
        var url = $('#torrent_url').val();
        
        var params = { name: name }
        
        // send to the form with ajax, get a return value
        $.getJSON(sbRoot + '/config/providers/canAddTorrentProvider', params,
            function(data){
                if (data.error != undefined) {
                    alert(data.error);
                    return;
                }

                $(this).addTorrentProvider(data.success, name, url, 0);
        });
        
    });

    // updates the torrent provider dict with the new config info for a provider
    $.fn.updateTorrentProvider = function (id, url) {

        torrentProviders[id][1][1] = url;

        $(this).populateTorrentSection();

        $(this).makeTorrentProviderString();
    
    }

    // when a custom provider's url is changed we wan to update it on the backend
    $('#torrent_url').change(function(){
        
    	var selectedProvider = $('#editATorrentProvider :selected').val();

    	// don't fire the update method if this is a new provider
    	if (selectedProvider == 'addTorrent')
    		return false;
    	
        var url = $(this).val();
        
        $(this).updateTorrentProvider(selectedProvider, url);
        
    });
    

    // removes a provider from the lists
    $.fn.deleteTorrentProvider = function (id) {
    
        $('#editATorrentProvider').removeOption(id);
        delete torrentProviders[id];
        $(this).populateTorrentSection();

        $('#provider_order_list > #'+id).remove();

        $(this).makeTorrentProviderString();
    
    }

    // deletes a provider from our local backend
    $('.torrent_delete').click(function(){
    
        var selectedProvider = $('#editATorrentProvider :selected').val();

        $(this).deleteTorrentProvider(selectedProvider);

    });
    
    $('#editATorrentProvider').change(function(){
        $(this).populateTorrentSection();
    });


    
    
    /*
     * Code for the provider list which allows sorting/enabling
     */ 
    
    $.fn.refreshProviderList = function() {
            var idArr = $("#provider_order_list").sortable('toArray');
            var finalArr = new Array();
            $.each(idArr, function(key, val) {
                    var checked = + $('#enable_'+val).attr('checked') ? '1' : '0';
                    finalArr.push(val + ':' + checked);
            });

            $("#provider_order").val(finalArr.join(' '));
    }

    $('.provider_enabler').live('click', function(){
        $(this).refreshProviderList();
    }); 
    


    // initialization stuff

    $(this).showHideProviders();

    $("#provider_order_list").sortable({
        placeholder: 'ui-state-highlight',
        update: function (event, ui) {
            $(this).refreshProviderList();
        }
    });
    
    $("#provider_order_list").disableSelection();

});