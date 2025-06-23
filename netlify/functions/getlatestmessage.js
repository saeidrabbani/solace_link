import axios from 'axios';

export const handler = async function(event, context) {
  try {
    const response = await axios.get("https://solacebot.onrender.com/latest-message");
    const data = response.data;

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
