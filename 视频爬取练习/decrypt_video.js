const { spawnSync } = require("child_process");


function decrypt_video(m3u8_path, output_path) {

    const args = [
        "-y",

        "-protocol_whitelist",
        "file,http,https,tcp,tls,crypto",

        "-i",
        m3u8_path,

        "-c",
        "copy",

        output_path
    ];


    const result = spawnSync("ffmpeg", args, {
        encoding: "utf8",
        stdio: [
            "ignore",
            "ignore",
            "inherit"
        ]
    });


    if (result.error) {
        throw new Error(
            "FFmpeg 启动失败：" + result.error.message
        );
    }


    if (result.status !== 0) {
        throw new Error(
            "FFmpeg 执行失败，退出码：" + result.status
        );
    }


    return "视频处理完成：" + output_path;
}