// login.js

document.getElementById('loginForm').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent form from submitting and refreshing the page

    // Get the username and password values from the form
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    // Define mock credentials (username, password, role)
    const adminCredentials = { username: 'admin', password: 'adminpass', role: 'admin' };
    const vendorCredentials = { username: 'vendor', password: 'vendorpass', role: 'vendor' };
    const hospitalCredentials = { username: 'hospital', password: 'hospitalpass', role: 'hospital' };

    // Check the entered credentials
    if (username === adminCredentials.username && password === adminCredentials.password) {
        // Redirect to Admin Page
        window.location.href = 'adminpage.html'; // Make sure 'adminpage.html' exists
    } else if (username === vendorCredentials.username && password === vendorCredentials.password) {
        // Redirect to Vendor Page
        window.location.href = 'vendor.html'; // Make sure 'vendor.html' exists
    } else if (username === hospitalCredentials.username && password === hospitalCredentials.password) {
        // Redirect to Hospital Page
        window.location.href = 'hospital.html'; // Make sure 'hospital.html' exists
    } else {
        alert('Invalid credentials. Please try again.');
    }
});
