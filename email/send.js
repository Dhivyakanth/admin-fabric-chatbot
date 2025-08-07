// Function to go back to the dashboard
function goBack() {
  // Navigate to the dashboard in the same tab
  // Try different common ports for the dashboard
  const possibleUrls = [
    'http://localhost:8080/dashboard',
    'http://localhost:8081/dashboard',
    'http://127.0.0.1:8080/dashboard',
    'http://127.0.0.1:8081/dashboard'
  ];
  
  // For simplicity, try the most likely port first
  window.location.href = 'http://localhost:8081/dashboard';
}

document.getElementById('emailForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const to = document.getElementById('to').value;
  const subject = document.getElementById('subject').value;
  const message = document.getElementById('message').value;

  const data = { to, subject, message };

  try {
    const response = await fetch('http://localhost:5678/webhook-test/email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (response.ok) {
      document.getElementById('status').textContent = '✅ Email sent!';
    } else {
      const text = await response.text();
      document.getElementById('status').textContent = '❌ Failed: ' + text;
    }
  } catch (err) {
    document.getElementById('status').textContent = '⚠️ Error: ' + err.message;
  }
});
