var crypto = require('crypto');

var AES_KEY = Buffer.from('weixin_smallmina', 'utf8');
var AES_IV = Buffer.concat([Buffer.from('weixin', 'utf8'), Buffer.alloc(10)]);

var SECRET_CIPHER = 'Ql4mW09F3urBNdzBLfK6UuRTqj22Bta7eEKTO7n5jFf9uU6FZZmcfe/gurOAOB+o';

function aesDecryptSecret(b64) {
    var d = crypto.createDecipheriv('aes-128-cbc', AES_KEY, AES_IV);
    return Buffer.concat([d.update(Buffer.from(b64, 'base64')), d.final()]).toString('utf8');
}

var SECRET = aesDecryptSecret(SECRET_CIPHER);

function sha1(s) {
    return crypto.createHash('sha1').update(s, 'utf8').digest('hex');
}

function toPath(url) {
    return url.replace(new RegExp('^http(s)?://.*?/', 'g'), '/').split('?')[0];
}

function getParamHash(params) {
    var str = Object.keys(params)
        .sort()
        .filter(function (k) { return k !== 'api_key'; })
        .map(function (k) {
            var v = params[k];
            if (v === null || v === undefined) { v = ''; }
            return k + '=' + (typeof v === 'object' ? JSON.stringify(v) : String(v));
        })
        .join('&');
    return sha1(str);
}

function getApiSign(urlOrPath, params, marsCid, vipTank) {
    var path = toPath(urlOrPath);
    var paramHash = getParamHash(params || {});
    return sha1(path + paramHash + (vipTank || '') + (marsCid || '') + SECRET);
}

function getAuthorization(urlOrPath, params, marsCid, vipTank) {
    return 'OAuth api_sign=' + getApiSign(urlOrPath, params, marsCid, vipTank);
}

if (typeof global !== 'undefined') {
    global.SECRET_VALUE = SECRET;
    global.sha1 = sha1;
    global.toPath = toPath;
    global.getParamHash = getParamHash;
    global.getApiSign = getApiSign;
    global.getAuthorization = getAuthorization;
}
