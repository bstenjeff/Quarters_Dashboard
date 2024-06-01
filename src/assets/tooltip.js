window.dccFunctions = window.dccFunctions || {};
window.dccFunctions.integertodate = function(value) {
     // Create a new Date object using the integer value (milliseconds since Jan 1, 1970)
    const date = new Date(value*1000);
    
    // Define months array for formatting
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    // Extract day, month, and year from the Date object
    const day = date.getDate();
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    
    // Construct the formatted string
    const formattedDate = `${month} ${day}, ${year}`;
    
    return formattedDate;
 }