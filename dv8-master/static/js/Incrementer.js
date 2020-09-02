/**
 * Increments the value of an element
 * @param {string} id - The HTML id of the element.
 * @param {string} inc - The amount by which to increment the element.
 */
function incrementValue(id, inc)
{
	// Get value from element
	var value = parseInt(document.getElementById(id).value);

	// Increment value
	value += inc;

	// If value is less than one, cancel the increment
	if (value < 1)
	{
		value -= inc;
	}

	// Set element value to new value
	document.getElementById(id).value = value;
}

/**
 * Unused: a copy of the preceeding function, but with the ID set internally
 */
function abc(){
	id = "inc0";
	var value = parseInt(document.getElementById(id).value);
	value += inc;
	if (value < 1)
	{
		value -= inc;
	}
	document.getElementById(id).value = value;
}
