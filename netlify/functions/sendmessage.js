const fetch = require("node-fetch");

exports.handler = async (event) => {
  const message = event.queryStringParameters.message || "No message given";

  // Send only to Flask — Flask handles both Telegram + Memory
  const flaskUrl = "https://solacebot.onrender.com/send-message";
  const flaskRes = await fetch(flaskUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });

  const data = await flaskRes.json();

  return {
    statusCode: 200,
    body: JSON.stringify({ success: true, result: data })
  };
};
