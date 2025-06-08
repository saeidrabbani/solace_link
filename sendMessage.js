const token = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA";
const chat_id = "YOUR_CHAT_ID"; // Injaro bad to mizari

exports.handler = async (event) => {
    const message = event.queryStringParameters.message || "No message given";

    const url = `https://api.telegram.org/bot${token}/sendMessage`;
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id, text: message })
    });

    const data = await res.json();

    return {
        statusCode: 200,
        body: JSON.stringify({ success: true, data })
    };
};
