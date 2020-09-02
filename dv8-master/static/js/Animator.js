function Animator(renderAll, charts, leftDate, rightDate){
	this.left = 0;
	this.right = 25;
	this.beginDate = leftDate;
	this.endDate = rightDate;
	this.dateLeft;
	this.dateRight;
	
	var myInter;
	var isCummulative;
	
	function changeFilter(i, u, n){//i is increment; u is upper bound; n is chart number
			if(n >= 0){
				charts[n].filter([left, right]);
			}
			else if (n == -1){
				charts[charts.length-1].filter([dateLeft, dateRight]);
			}
			
			renderAll();
						
			if(n >= 0){
			
				if(right >= u){
					clearInterval(myInter);
				}
				if (!isCummulative){
					left += i;
				}
				right += i;
			}
			else if (n == -1){
			
				if(dateRight >= u){
					clearInterval(myInter);
				}
				if (!isCummulative){
					dateLeft.setDate(dateLeft.getDate() + i);
				}
				dateRight.setDate(dateRight.getDate() + i);
			}
				
	};
	
	//grabs parameters once then sets up increment to repeatedly change filter
	function animate (n){
		var delay = 1000;
		isCummulative = document.getElementById("cummulative_checkbox").checked;
		
		if(n >= 0){
			//grab params
			var increment = parseInt(document.getElementById("inc" + n.toString()).value);
			var width = parseInt(document.getElementById("width" + n.toString()).value);
			//set params
			right = left + width;
			var upper = 24;
			//every second, move the filter
			myInter = setInterval(function() {changeFilter(increment, upper, n)}, delay);
		}
		//Special case for dates
		else if(n == -1){
			//grab params
			var increment = parseInt(document.getElementById("date_inc").value);
			var width = parseInt(document.getElementById("date_width").value);
			//set params
			dateRight = new Date();
			dateRight.setFullYear(dateLeft.getFullYear(), dateLeft.getMonth(), dateLeft.getDate()+width);
			var upper = endDate;
			//every second, move the filter
			myInter = setInterval(function() {changeFilter(increment, upper, n)}, delay);
		}
		else{
			alert(n);
		}
	}
	
    function filter(filters) {
      filters.forEach(function(d, i) { charts[i].filter(d); });
    };

	this.startAnimate = function(n){
		//calling animate stops all old animations
		this.reset(n);
		paused = false;
		
		//reset left before animation
		if(n >= 0){
			left = 0;
		}
		else if(n == -1){
			dateLeft = new Date();
			//i used beginDate.getDate()-1 because it works
			dateLeft.setFullYear(beginDate.getFullYear(), beginDate.getMonth(), beginDate.getDate()-1);
		}
		
		animate(n);	
	};
	
	this.pause = function(n){
		if(!paused){
			clearInterval(myInter);
			paused = true;
		}
		//if pause is called when it's already paused, resume
		else{
			paused = false;
		
			animate(n);
		}
	}
	
	this.reset = function(i) {
		clearInterval(myInter);
		paused = false;
		if(i == -1) { i = charts.length-1; }
        charts[i].filter(null);
        renderAll();
    };
	
	//ONLY WORKS WITH 4 CHARTS
	this.resetAll = function() {
		clearInterval(myInter);
		paused = false;
		for (var i=0; i<4; i++){
			charts[i].filter(null);
		}
        renderAll();
	}
}


	