/*jQuery Form to Form Wizard (Initial: Oct 1st, 2010)
* This notice must stay intact for usage 
* Author: Dynamic Drive at http://www.dynamicdrive.com/
* Visit http://www.dynamicdrive.com/ for full source code
*/

//Oct 21st, 2010: Script updated to v1.1, which adds basic form validation functionality, triggered each time the user goes from one page to the next, or tries to submit the form.

//jQuery.noConflict()


function formtowizard(options){
	this.setting=jQuery.extend({persistsection:false, revealfx:['slide', 500], oninit:function(){}, onpagechangestart:function(){}}, options)
	this.currentsection=-1
	this.init(this.setting)
}

formtowizard.prototype={

	createfieldsets:function($theform, arr){ //reserved function for future version (dynamically wraps form elements with a fieldset element)
		$theform.find('fieldset.sectionwrap').removeClass('sectionwrap') //make sure no fieldsets carry 'sectionwrap' before proceeding
		var $startelement=$theform.find(':first-child') //reference first element inside form
		for (var i=0; i<arr.length; i++){ //loop thru "break" elements
			var $fieldsetelements=$startelement.nextUntil('#'+arr[i].breakafter+', *[name='+arr[i].breakafter+']').andSelf() //reference all elements from start element to break element (nextUntil() is jQuery 1.4 function)
			$fieldsetelements.add($fieldsetelements.next()).wrapAll('<fieldset class="sectionwrap" />') //wrap these elements with fieldset element
			$startelement=$theform.find('fieldset.sectionwrap').eq(i).prepend('<legend class="legendStep">'+arr[i].legend+'</legend>').next() //increment startelement to begin at the end of the just inserted fieldset element
		}
	},

	loadsection:function(rawi, bypasshooks){
		var thiswizard=this
  	//doload Boolean checks to see whether to load next section (true if bypasshooks param is true or onpagechangestart() event handler doesn't return false)
		var doload=bypasshooks || this.setting.onpagechangestart(jQuery, this.currentsection, this.sections.$sections.eq(this.currentsection))
		doload=(doload===false)? false : true //unless doload is explicitly false, set to true
		if (!bypasshooks && this.setting.validate){
			var outcome=this.validate(this.currentsection)
			if (outcome===false)
				doload=false
		}	
		var i=(rawi=="prev")? this.currentsection-1 : (rawi=="next")? this.currentsection+1 : parseInt(rawi) //get index of next section to show
		i=(i<0)? this.sections.count-1 : (i>this.sections.count-1)? 0 : i //make sure i doesn't exceed min/max limit
		if (i<this.sections.count && doload){ //if next section to show isn't the same as the current section shown
			this.$thesteps.eq(this.currentsection).addClass('disabledstep').end().eq(i).removeClass('disabledstep') //dull current "step" text then highlight next "step" text
			if (this.setting.revealfx[0]=="slide"){
				this.sections.$sections.css("visibility", "visible")
				this.sections.$outerwrapper.stop().animate({height: this.sections.$sections.eq(i).outerHeight()}, this.setting.revealfx[1]) //animate fieldset wrapper's height to accomodate next section's height
				this.sections.$innerwrapper.stop().animate({left:-i*this.maxfieldsetwidth}, this.setting.revealfx[1], function(){ //slide next section into view
					thiswizard.sections.$sections.each(function(thissec){
						if (thissec!=i) //hide fieldset sections currently not in veiw, so tabbing doesn't go to elements within them (and mess up layout)
							thiswizard.sections.$sections.eq(thissec).css("visibility", "hidden")
					})
				})
			}
			else if (this.setting.revealfx[0]=="fade"){ //if fx is "fade"
				this.sections.$sections.eq(this.currentsection).hide().end().eq(i).fadeIn(this.setting.revealfx[1], function(){
					if (document.all && this.style && this.style.removeAttribute)
						this.style.removeAttribute('filter') //fix IE clearType problem
				})
			}
			else{
				this.sections.$sections.eq(this.currentsection).hide().end().eq(i).show()
			}
			this.paginatediv.$status.text("Page "+(i+1)+" of "+this.sections.count) //update current page status text
			this.paginatediv.$navlinks.css('visibility', 'visible')
			if (i==0) //hide "prev" link
				this.paginatediv.$navlinks.eq(0).css('visibility', 'hidden')
			else if (i==this.sections.count-1) //hide "next" link
				this.paginatediv.$navlinks.eq(1).css('visibility', 'hidden')
			if (this.setting.persistsection) //enable persistence?
				formtowizard.routines.setCookie(this.setting.formid+"_persist", i)
			this.currentsection=i
			if(i === 0) { setTimeout(function() { $('#nameToSearch').focus(); }, 250); }
		}
	},

	addvalidatefields:function(){
		var $=jQuery, setting=this.setting, theform=this.$theform.get(0), validatefields=[]
		var validatefields=setting.validate //array of form element ids to validate
		for (var i=0; i<validatefields.length; i++){
			var el=theform.elements[validatefields[i]] //reference form element
			if (el){ //if element is defined
				var $section=$(el).parents('fieldset.sectionwrap:eq(0)') //find fieldset.sectionwrap this form element belongs to
				if ($section.length==1){ //if element is within a fieldset.sectionwrap element
					$section.data('elements').push(el) //cache this element inside corresponding section
				}
			}
		}
	},

	validate:function(section){
		var elements=this.sections.$sections.eq(section).data('elements') //reference elements within this section that should be validated
		var validated=true, invalidtext=["Please fill out the following fields:\n"]
		function invalidate(el){
			validated=false
			invalidtext.push("- "+ (el.id || el.name))
		}
		for (var i=0; i<elements.length; i++){
			if (/(text)/.test(elements[i].type) && elements[i].value==""){ //text and textarea elements
				invalidate(elements[i])
			}
			else if (/(select)/.test(elements[i].type) && (elements[i].selectedIndex==-1 || elements[i].options[elements[i].selectedIndex].text=="")){ //select elements
				invalidate(elements[i])
			}
			else if (elements[i].type==undefined && elements[i].length>0){ //radio and checkbox elements
				var onechecked=false
				for (var r=0; r<elements[i].length; r++){
					if (elements[i][r].checked==true){
						onechecked=true
						break
					}
				}
				if (!onechecked){
					invalidate(elements[i][0])
				}
			}
		}
		if (!validated)
			alert(invalidtext.join('\n'))
		return validated
	},


	init:function(setting){
		var thiswizard=this
		jQuery(function($){ //on document.ready
			var $theform=$('#'+setting.formid)
			if ($theform.length==0) //if form with specified ID doesn't exist, try name attribute instead
				$theform=$('form[name='+setting.formid+']')
			if (setting.manualfieldsets && setting.manualfieldsets.length>0)
				thiswizard.createfieldsets($theform, setting.manualfieldsets)
			var $stepsguide=$('<div class="stepsguide" />') //create Steps Container to house the "steps" text
			var $sections=$theform.find('fieldset.sectionwrap').hide() //find all fieldset elements within form and hide them initially
			if (setting.revealfx[0]=="slide"){ //create outer DIV that will house all the fieldset.sectionwrap elements
				$sectionswrapper=$('<div style="position:relative;overflow:hidden;"></div>').insertBefore($sections.eq(0)) //add DIV above the first fieldset.sectionwrap element
				$sectionswrapper_inner=$('<div style="position:absolute;left:0;top:0;"></div>') //create inner DIV of $sectionswrapper that will scroll to reveal a fieldset element
			}
			var maxfieldsetwidth=$sections.eq(0).outerWidth() //variable to get width of widest fieldset.sectionwrap
			$sections.slice(1).each(function(i){ //loop through $sections (starting from 2nd one)
				maxfieldsetwidth=Math.max($(this).outerWidth(), maxfieldsetwidth)
			})
			maxfieldsetwidth+=2 //add 2px to final width to reveal fieldset border (if not removed via CSS)
			thiswizard.maxfieldsetwidth=maxfieldsetwidth
			$sections.each(function(i){ //loop through $sections again
				var $section=$(this)
				if (setting.revealfx[0]=="slide"){
					$section.data('page', i).css({position:'absolute', top:0, left:maxfieldsetwidth*i}).appendTo($sectionswrapper_inner) //set fieldset position to "absolute" and move it to inside sectionswrapper_inner DIV
				}
				$section.data('elements', []) //empty array to contain elements within this section that should be validated for data (applicable only if validate option is defined)
				//create each "step" DIV and add it to main Steps Container:
				var $thestep=$('<div class="step disabledstep" />').data('section', i).html('Step '+(i+1)+'<div class="smalltext">'+$section.find('legend:eq(0)').text()+'<p></p></div>').appendTo($stepsguide)
				$thestep.click(function(){ //assign behavior to each step div
					thiswizard.loadsection($(this).data('section'))
				})
			})
			if (setting.revealfx[0]=="slide"){
				$sectionswrapper.width(maxfieldsetwidth) //set fieldset wrapper to width of widest fieldset
				$sectionswrapper.append($sectionswrapper_inner) //add $sectionswrapper_inner as a child of $sectionswrapper
			}
			$theform.prepend($stepsguide) //add $thesteps div to the beginning of the form
			//$stepsguide.insertBefore($sectionswrapper) //add Steps Container before sectionswrapper container
			var $thesteps=$stepsguide.find('div.step')
			//create pagination DIV and add it to end of form:
			var $paginatediv=$('<div class="formpaginate" style="overflow:hidden;"><span class="prev" style="float:left">Prev</span> <span class="status">Step 1 of </span> <span class="next" style="float:right">Next</span></div>')
			$theform.append($paginatediv)
			thiswizard.$theform=$theform
			if (setting.revealfx[0]=="slide"){
				thiswizard.sections={$outerwrapper:$sectionswrapper, $innerwrapper:$sectionswrapper_inner, $sections:$sections, count:$sections.length} //remember various parts of section container
				thiswizard.sections.$sections.show()
			}
			else{
				thiswizard.sections={$sections:$sections, count:$sections.length} //remember various parts of section container
			}
			thiswizard.$thesteps=$thesteps //remember this ref
			thiswizard.paginatediv={$main:$paginatediv, $navlinks:$paginatediv.find('span.prev, span.next'), $status:$paginatediv.find('span.status')} //remember various parts of pagination DIV
			thiswizard.paginatediv.$main.click(function(e){ //assign behavior to pagination buttons
				if (/(prev)|(next)/.test(e.target.className))
					thiswizard.loadsection(e.target.className)
			})
			var i=(setting.persistsection)? formtowizard.routines.getCookie(setting.formid+"_persist") : 0
			thiswizard.loadsection(i||0, true) //show the first section
			thiswizard.setting.oninit($, i, $sections.eq(i)) //call oninit event handler
			if (setting.validate){ //if validate array defined
				thiswizard.addvalidatefields() //seek out and cache form elements that should be validated
				thiswizard.$theform.submit(function(){
					var returnval=true
					for (var i=0; i<thiswizard.sections.count; i++){
						if (!thiswizard.validate(i)){
							thiswizard.loadsection(i, true)
							returnval=false
							break
						}
					}
					return returnval //allow or disallow form submission
				})
			}
		})
	}
}

formtowizard.routines={

	getCookie:function(Name){ 
		var re=new RegExp(Name+"=[^;]+", "i"); //construct RE to search for target name/value pair
		if (document.cookie.match(re)) //if cookie found
			return document.cookie.match(re)[0].split("=")[1] //return its value
		return null
	},

	setCookie:function(name, value){
		document.cookie = name+"=" + value + ";path=/"
	}
}