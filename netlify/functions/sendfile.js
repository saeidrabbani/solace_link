const fs = require('fs');
const axios = require('axios');
const FormData = require('form-data');

exports.handler = async function(event, context) {
  const fileContent = "This is a message from Solace.\nCustom code will be added here.";
  const filePath = '/tmp/solace_message.txt';

  fs.writeFileSync(filePath, fileContent);

  const telegramBotToken = '7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA';
  const chatId = '253893212'; // chat_id from getUpdates

  const formData = new FormData();
  formData.append('chat_id', chatId);
  formData.append('document', fs.createReadStream(filePath));

  try {
    await axios.post(`https://api.telegram.org/bot${telegramBotToken}/sendDocument`, formData, {
      headers: formData.getHeaders()
    });

    return {
      statusCode: 200,
      body: '✅ File sent successfully via Telegram!'
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: '❌ Error sending file: ' + error.message
    };
  }
};
