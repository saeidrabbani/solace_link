import { fetch } from 'undici';

const token = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA";
const chat_id = "253893212"; // Chat ID Saeid

export const handler = async (event) => {
  const message = event.queryStringParameters.message || "No message given";

  try {
    // 1. Send message to Telegram
    const telegramUrl = `https://api.telegram.org/bot${token}/sendMessage`;
    const telegramRes = await fetch(telegramUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id, text: message })
    });

    // 2. Save message to Flask memory
    const flaskUrl = "https://solacebot.onrender.com/save-message";
    await fetch(flaskUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const telegramData = await telegramRes.json();

    return {
      statusCode: 200,
      body: JSON.stringify({ success: true, telegram: telegramData })
    };
  } catch (error) {
    console.error("Error in sendmessage:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ success: false, error: error.message })
    };
  }
};
