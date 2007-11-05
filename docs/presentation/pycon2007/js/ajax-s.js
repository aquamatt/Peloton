// ---
/*
	Code and concept by Robert Nyman, http.//www.robertnyman.com
*/
/* 
	Set these value depending on what input data and presentation logic you want to use
*/
// Settings
var strXMLURL = "xml/tm.xml";
var strPagingXSLTURL = "xslt/ajax-s-paging-html.xml";
var strXSLTURL = "xslt/ajax-s-html.xml";
var bUseFontScaling = true;
var bUseHTMLContent = true;
var bSelectFirstIncrementWhenBacking = true;
// ---
// Global variables
var intCurrentPage = 1;
var intPreviousPage = 1;
var intTotalNumberOfPages = 1;
var oXML;
// ---
function getElementsByClassName(oElm, strTagName, strClassName){
	var arrElements = (strTagName == "*" && document.all)? document.all : oElm.getElementsByTagName(strTagName);
	var arrReturnElements = new Array();
	strClassName = strClassName.replace(/\-/g, "\\-");
	var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$)");
	var oElement;
	for(var i=0; i<arrElements.length; i++){
		oElement = arrElements[i];		
		if(oRegExp.test(oElement.className)){
			arrReturnElements.push(oElement);
		}	
	}
	return (arrReturnElements)
}
// ---
function addEvent(oElm, strEvent, oFunction, bCapture){
	if(oElm.addEventListener){
		oElm.addEventListener(strEvent, oFunction, bCapture);
	}
	else if(oElm.attachEvent){
		oElm.attachEvent(("on" + strEvent), oFunction);
	}
}
// ---
function windowLoad(){	
	if(document.getElementById){
		if(bUseFontScaling){
			setFontSize();
			window.onresize = setFontSize;
		}
		if(typeof XMLHttpRequest != "undefined" && typeof XSLTProcessor != "undefined"){
			var oXMLHTTP = new XMLHttpRequest();
			oXMLHTTP.onreadystatechange = function (){
				if(oXMLHTTP.readyState == 4){
					oXML = oXMLHTTP.responseXML;
					createPaging();
					getContent(intCurrentPage);
				}
			};
			oXMLHTTP.open("GET", strXMLURL, true);
			oXMLHTTP.send(null);
		}
		else if(window.ActiveXObject){
			oXML = new ActiveXObject("Microsoft.XMLDOM");
		    oXML.async = false;
			oXML.onreadystatechange = function (){
	        	if(oXML.readyState == 4){
					createPaging();
					getContent(intCurrentPage);
				}                            
			};
			oXML.load(strXMLURL);
		}
		else{
			if(confirm("You need to use a web browser that supports:\nXMLHttpRequest and XSLTProcessor\nor:\nActiveXObject\n\nDo you want to go to the printable page instead?")){
				location.href = strXMLURL;
			}
		}
	}
}
// ---
function documentClick(oEvent){	
	var oEvent = (typeof oEvent != "undefined")? oEvent : event;
	var oTarget = (typeof oEvent.target != "undefined")? oEvent.target : oEvent.srcElement;
	if(oTarget.nodeName.search(/select|option|\ba\b/i) == -1){
		getContent(intCurrentPage + 1);
	}
}
// ---
function documentKeyDown(oEvent){
	var oEvent = (typeof oEvent != "undefined")? oEvent : event;
	var oTarget = (typeof oEvent.target != "undefined")? oEvent.target : oEvent.srcElement;
	if(oTarget.nodeName.search(/select|option/i) == -1){
		var intKeyCode = oEvent.keyCode;
		switch(intKeyCode){			
			case 8:
			case 37:
			case oEvent.altKey && 37:
				oEvent.cancelBubble = true;
				oEvent.returnValue = false;
				if(oEvent.preventDefault){
					oEvent.preventDefault();
				}
				getContent(intCurrentPage - 1);				
				return false;
			case 13:
			case 32:
			case 39:
			case oEvent.altKey && 37:
				oEvent.cancelBubble = true;
				oEvent.returnValue = false;
				if(oEvent.preventDefault){
					oEvent.preventDefault();
				}
				getContent(intCurrentPage + 1);
				break;
		}
	}	
}
// ---
function cancelDefaultNavigationEvents(oEvent){
	var oEvent = (typeof oEvent != "undefined")? oEvent : event;
	var oTarget = (typeof oEvent.target != "undefined")? oEvent.target : oEvent.srcElement;
	if(oTarget.nodeName.search(/select|option/i) == -1){
		var intKeyCode = oEvent.keyCode;
		switch(intKeyCode){			
			case 8:
			case oEvent.altKey && 37:
			case oEvent.altKey && 39:
				oEvent.cancelBubble = true;
				oEvent.returnValue = false;
				if(oEvent.preventDefault){
					oEvent.preventDefault();
				}
				documentKeyDown(oEvent);
				break;
		}	
	}
}
// ---
function setFontSize(){
	var intWindowHeight;
	if(typeof window.innerHeight != "undefined"){
		intWindowHeight = window.innerHeight;
	}
	else if(document.body.clientHeight){
		intWindowHeight = document.body.clientHeight;
	}
	else{
		return false;
	}
	document.body.style.fontSize = intWindowHeight / 40 + "px";
}
// ---
function createPaging(){
	var oElmToPresentIn = document.getElementById("navigation");
	transformXML(strPagingXSLTURL, oElmToPresentIn, null, true);
	intTotalNumberOfPages = oXML.getElementsByTagName("page").length	
	addDropDownEvents();	
}
// ---
var oTimer;
function addDropDownEvents(){
	var oSelectPage = document.getElementById("select-page");
	if(oSelectPage){
		clearTimeout(oTimer);
		oSelectPage.onchange = function (){
			bPageIsIncremental = false;
			getContent(this.selectedIndex);
		}
		oSelectPage.onkeydown = function (oEvent){
			var oEvent = (typeof oEvent != "undefined")? oEvent : event;
			var intKeyCode = oEvent.keyCode;
			switch(intKeyCode){
				case 13:
				case 32:
					bPageIsIncremental = false;
					getContent(this.selectedIndex);
					break;
			}	
		}
	}
	else{
		oTimer = setTimeout("addDropDownEvents()", 30);
	}
}
// ---
function getContent(intPage){
	if(bPageIsIncremental){
		incrementalNavigate(intPage);		
	}
	else if(intPage > 0 && intPage <= intTotalNumberOfPages){
		intPreviousPage = intCurrentPage;
		intCurrentPage = intPage;
		var oPageNumber = document.getElementById("page-number");
		if(oPageNumber){
			oPageNumber.innerHTML = intPage;
		}
		var oSelectPage = document.getElementById("select-page");
		if(oSelectPage){
			oSelectPage.selectedIndex = intPage;
		}
		var oElmToPresentIn = document.getElementById("main-content");
		transformXML(strXSLTURL, oElmToPresentIn, intPage, null);
	}
}
// ---
function transformXML(strXSLT, oElmToPresentIn, intPage, bPaging){
	var strOutputHTML;
	var oElmToPresentIn = oElmToPresentIn;
	if(typeof XSLTProcessor != "undefined"){
		var oXSLTRequest = new XMLHttpRequest();
		oXSLTRequest.onreadystatechange = function (){			
			if(oXSLTRequest.readyState == 4){
				oXSLTProcessor = new XSLTProcessor();
				if(typeof intPage == "number"){
					oXSLTProcessor.setParameter("", "pageNo", intPage);
				}
				if(bPaging){
					oXSLTProcessor.setParameter("", "printVersionURL", strXMLURL);					
				}
				oXSLTProcessor.importStylesheet(oXSLTRequest.responseXML);
				var oXMLSerializer = new XMLSerializer();			
				strOutputHTML = oXMLSerializer.serializeToString(oXSLTProcessor.transformToFragment(oXML, document));
				if(!bUseHTMLContent){
					strOutputHTML = strOutputHTML.replace(/&(lt|gt);/g, function (strMatch, p1){
						return (p1 == "lt")? "<" : ">";
					});
				}
				oElmToPresentIn.innerHTML = strOutputHTML;
				incrementalRendering(oElmToPresentIn);
				fixCodeDisplay();
				setScrollTop();
			}
		}
		oXSLTRequest.open("GET", strXSLT, true);
		oXSLTRequest.send(null);
	}
	else if(window.ActiveXObject){		
	    var oXSLTDoc = new ActiveXObject("Msxml2.FreeThreadedDOMDocument.3.0");		
	    oXSLTDoc.async = false;
		oXSLTDoc.validateOnParse = false;
		oXSLTDoc.onreadystatechange = function (){
			if(oXSLTDoc.readyState == 4){
				var oXSLTTemp = new ActiveXObject("Msxml2.XSLTemplate.3.0");
				oXSLTTemp.stylesheet = oXSLTDoc;	     
			    oXSLTProcessor = oXSLTTemp.createProcessor();
			    oXSLTProcessor.input = oXML;
				if(typeof intPage == "number"){		   
			    	oXSLTProcessor.addParameter("pageNo", intPage);
				}
				if(bPaging){
					oXSLTProcessor.addParameter("printVersionURL", strXMLURL);					
				}
				oXSLTProcessor.transform;
				strOutputHTML = oXSLTProcessor.output;
				if(!bUseHTMLContent){
					strOutputHTML = strOutputHTML.replace(/&(lt|gt);/g, function (strMatch, p1){
						return (p1 == "lt")? "<" : ">";
					});					
					strOutputHTML = strOutputHTML.replace(/\n/g, "<br />");
				}
				oElmToPresentIn.innerHTML = strOutputHTML;
				incrementalRendering(oElmToPresentIn);
				fixCodeDisplay();
				setScrollTop();
			}                            
		}
		oXSLTDoc.load(strXSLT);
	}
}
// ---
function fixCodeDisplay(){
	var oMainContent = document.getElementById("main-content");
	var arrAllCodeTags = oMainContent.getElementsByTagName("code");
	var oCodeTag;
	for(var i=0; i<arrAllCodeTags.length; i++){
		oCodeTag = arrAllCodeTags[i];
    	oCodeTag.innerHTML = oCodeTag.innerHTML.replace(/&amp;(lt|gt);|(<|>)/g, function (strMatch, p1, p2){
			return (p1 == "lt" || p2 == "<")? "&lt;" : "&gt;";
		});
    }
}
// ---
var bPageIsIncremental = false;
var intIncrementalSteps = 0;
var intCurrentIncrement = 0;
var arrIncrementalElements;
function incrementalRendering(oElmToPresentIn){
	arrIncrementalElements = getElementsByClassName(oElmToPresentIn, "li", "incremental");
	intIncrementalSteps = arrIncrementalElements.length;
	bPageIsIncremental = (intIncrementalSteps > 0)? true : false;
	if(bPageIsIncremental){
		intCurrentIncrement = (!bSelectFirstIncrementWhenBacking && intPreviousPage > intCurrentPage)? (intIncrementalSteps - 1) : 0;
		setIncrementalClasses();
	}
}
// ---
function setIncrementalClasses(){
	var oIncrement;
	for(var i=0; i<arrIncrementalElements.length; i++){
		oIncrement = arrIncrementalElements[i];
		if(intCurrentIncrement > i){
			oIncrement.className = oIncrement.className.replace(/incremental(-(active|past))?/i, "incremental-past");
		}
		else if(intCurrentIncrement == i){
			oIncrement.className = oIncrement.className.replace(/incremental(-(active|past))?/i, "incremental-active");
		}
		else{
			oIncrement.className = oIncrement.className.replace(/incremental(-(active|past))?/i, "incremental");
		}
	}
	setScrollTop();
}
// ---
function incrementalNavigate(intPage){
	var bForward = (intPage > intCurrentPage)? (intCurrentIncrement++) : (intCurrentIncrement--);
	var bGetOtherPage = (intCurrentIncrement >= arrIncrementalElements.length || intCurrentIncrement < 0)? true : false;
	
	if(bGetOtherPage){
		bPageIsIncremental = false;
		getContent(intPage);
	}
	else{
		setIncrementalClasses();
	}
}
// ---
function setScrollTop(){
	var intScrollTop = 0;
	var oMainContainer = document.getElementById("main");
	if(bPageIsIncremental){
		var oCurrentIncrementElm = arrIncrementalElements[intCurrentIncrement];
		if(oCurrentIncrementElm.offsetTop > oMainContainer.offsetHeight){
			intScrollTop = oCurrentIncrementElm.offsetTop + oCurrentIncrementElm.offsetHeight;
		}	
	}
	oMainContainer.scrollTop = intScrollTop;
}
// ---
addEvent(window, "load", windowLoad);
addEvent(document, "click", documentClick);
addEvent(document, "keypress", cancelDefaultNavigationEvents, true);
addEvent(document, "keydown", documentKeyDown, true);
// ---
