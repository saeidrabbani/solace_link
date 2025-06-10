const fetch = require("node-fetch");

exports.handler = async function(event, context) {
  try {
    const response = await fetch("https://solacebot.onrender.com/latest-message");
    const data = await response.json();

    return {
      statusCode: 200,
      body: JSON.stringify({ message: data.message })
    };
  } catch (error) {
    console.error("Error fetching latest message:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ message: "Error fetching message" })
    };
  }
};
