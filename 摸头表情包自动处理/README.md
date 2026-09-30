# 摸头表情包批量生成工具

本工具会读取当前目录下 `image` 文件夹中的图片，使用 Python、Requests 和 DrissionPage 操作 [petpet generator](https://benisland.neocities.org/petpet/) 网站，并将生成的摸头 GIF 保存到 `output` 文件夹。

## 目录结构

```text
摸头表情包自动处理/
├─ image/            # 放置待处理图片
├─ output/           # 生成的 GIF
├─ main.py           # 主程序
├─ README.md
└─ requirements.txt
```

程序只扫描 `image` 文件夹的当前层，不会扫描子文件夹，也不会移动或修改原图片。

## 环境要求

- Python 3.10 或更高版本
- Chromium、Google Chrome 或 Microsoft Edge
- 可以正常访问 petpet generator 网站

安装 Python 依赖：

```powershell
python -m pip install -r requirements.txt
```

## 使用方法

1. 把需要处理的图片放入 `image` 文件夹。
2. 在当前目录运行：

   ```powershell
   python main.py
   ```

3. 程序会打开一个独立的可见浏览器窗口，逐张上传图片并点击 `export`。
4. 生成的 GIF 会保存在 `output` 文件夹。

支持的输入格式：

```text
PNG、JPG、JPEG、GIF、WEBP、BMP、SVG、ICO、AVIF
```

## 输出规则

- 输出名称默认与原图片名称相同，扩展名改为 `.gif`。
- 例如：`image/avatar.png` 会生成 `output/avatar.gif`。
- 如果同名文件已经存在，程序不会覆盖，而会生成 `avatar_1.gif`、`avatar_2.gif` 等。
- 网站参数保持默认值；每张图片处理前都会点击一次 `reset`。
- 单张图片失败不会中断后续图片，程序结束时会显示成功和失败汇总。

## 退出码

- `0`：全部处理成功，或者 `image` 文件夹中没有可处理图片。
- `1`：至少有一张图片处理失败。
- `2`：依赖缺失、网站不可用、浏览器启动失败或页面结构发生变化。

## 注意事项

- GIF 由网站中的 JavaScript 在浏览器本地生成，并不是由服务器接口返回，因此运行期间不要手动关闭自动化浏览器窗口。
- 网站更新后，如果上传框或 `export` 按钮结构发生变化，程序会停止并给出提示。
- 图片数量较多时请等待程序依次处理，不要同时重复启动多个实例。

