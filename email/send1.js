document.getElementById('emailForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const to = document.getElementById('to').value;
  const subject = document.getElementById('subject').value;
  const message = document.getElementById('message').value;

  const data = { to, subject, message };

  try {
    const response = await fetch('https://giridharan789.app.n8n.cloud/webhook-test/sender', {
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
