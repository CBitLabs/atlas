(function() {
       var po = document.createElement('script'); po.type = 'text/javascript'; po.async = true;
       po.src = 'https://apis.google.com/js/client:plusone.js';
       var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(po, s);
     })();

 (function() {
   var po = document.createElement('script');
   po.type = 'text/javascript'; po.async = true;
   po.src = 'https://apis.google.com/js/client:plusone.js?onload=render';
   var s = document.getElementsByTagName('script')[0];
   s.parentNode.insertBefore(po, s);
 })();

   /* Executed when the APIs finish loading */
 function render() {

   // Additional params including the callback, the rest of the params will
   // come from the page-level configuration.
   var additionalParams = {
     'callback': signinCallback
   };

   // Attach a click listener to a button to trigger the flow.
   var signinButton = document.getElementById('signinButton');
   signinButton.addEventListener('click', function() {
     gapi.auth.signIn(additionalParams); // Will use page level configuration
   });
 }
 
 
 function signinCallback(authResult) {
  if (authResult['status']['signed_in']) {
    // Update the app to reflect a signed in user
    // Hide the sign-in button now that the user is authorized, for example:
    document.getElementById('signinButton').setAttribute('style', 'display: none');
  } else {
    // Update the app to reflect a signed out user
    // Possible error values:
    //   "user_signed_out" - User is signed-out
    //   "access_denied" - User denied access to your app
    //   "immediate_failed" - Could not automatically log in the user
    console.log('Sign-in state: ' + authResult['error']);
  }
}
 
document.getElementById('id_username').focus()
