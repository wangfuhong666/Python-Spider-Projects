let decrypt_url = (url) => {
    url = url
        .replace("__ba", "")
        .replace(/[@#$%]/g, c => ({
            "@": "1",
            "#": "2",
            "$": "3",
            "%": "4"
        })[c])
        .replace(/-/g, "+")
        .replace(/_/g, "/")
        .replace(/[^A-Za-z0-9+/]/g, "");

    const data = JSON.parse(
        Buffer.from(url, "base64").toString("utf8")
    );

    return data[0].url;
};